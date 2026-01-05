#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


# =========================
# Data models
# =========================

@dataclass
class Cue:
    start_s: float
    end_s: float
    text: str


@dataclass
class VideoCuePair:
    video_path: Path
    json_path: Path
    cues: list[Cue]


# =========================
# Small helpers
# =========================

def sh_quote(s: str) -> str:
    return shlex.quote(s)


def natural_sort_key(text: str) -> list:
    def atoi(s: str):
        return int(s) if s.isdigit() else s.lower()
    return [atoi(c) for c in re.split(r"(\d+)", text)]


def http_json(method: str, url: str, payload: dict | None = None, timeout_s: float = 10.0) -> dict:
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    req = Request(url, method=method, data=data, headers=headers)
    try:
        with urlopen(req, timeout=timeout_s) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8")
        except Exception:
            pass
        raise RuntimeError(f"HTTP {e.code} calling {url}: {body or e.reason}") from e
    except URLError as e:
        raise RuntimeError(f"Failed to reach {url}: {e}") from e


def http_nojson(method: str, url: str, timeout_s: float = 10.0) -> None:
    req = Request(url, method=method)
    try:
        with urlopen(req, timeout=timeout_s) as resp:
            _ = resp.read()
    except HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8")
        except Exception:
            pass
        raise RuntimeError(f"HTTP {e.code} calling {url}: {body or e.reason}") from e
    except URLError as e:
        raise RuntimeError(f"Failed to reach {url}: {e}") from e


# =========================
# Cue parsing (Whisper JSON)
# =========================

def parse_whisper_json(path: str) -> list[Cue]:
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    segs = obj.get("segments")
    if not isinstance(segs, list):
        raise ValueError("JSON missing 'segments' array (expected Whisper JSON).")

    cues: list[Cue] = []
    for s in segs:
        start = float(s["start"])
        end = float(s["end"])
        text = str(s.get("text", "")).strip()
        if text:
            cues.append(Cue(start_s=start, end_s=end, text=text))
    return cues


# =========================
# Directory scan + playlist
# =========================

def find_matching_video_for_stem(dir_path: Path, stem: str, video_exts: list[str]) -> Path | None:
    for ext in video_exts:
        ext2 = ext.strip().lstrip(".")
        cand = dir_path / f"{stem}.{ext2}"
        if cand.exists():
            return cand
    return None


def scan_directory_for_pairs(dir_path: Path, video_exts: list[str]) -> list[VideoCuePair]:
    pairs: list[VideoCuePair] = []
    json_files = sorted(dir_path.glob("*.json"), key=lambda p: natural_sort_key(p.stem))

    for json_path in json_files:
        stem = json_path.stem
        video_path = find_matching_video_for_stem(dir_path, stem, video_exts)
        if not video_path:
            print(f"Warning: No video found for {json_path.name}, skipping", file=sys.stderr)
            continue

        try:
            cues = parse_whisper_json(str(json_path))
        except Exception as e:
            print(f"Warning: Failed to parse {json_path.name}: {e}, skipping", file=sys.stderr)
            continue

        if not cues:
            print(f"Warning: No cues in {json_path.name}, skipping", file=sys.stderr)
            continue

        pairs.append(VideoCuePair(video_path=video_path, json_path=json_path, cues=cues))

    # Sort by video basename naturally (in case json order differs)
    pairs.sort(key=lambda p: natural_sort_key(p.video_path.stem))
    return pairs


def create_m3u_playlist(pairs: list[VideoCuePair], output_path: Path) -> None:
    lines = ["#EXTM3U\n"]
    for p in pairs:
        lines.append(str(p.video_path.absolute()) + "\n")
    output_path.write_text("".join(lines), encoding="utf-8")


# =========================
# mpv IPC (NO socat; always newline)
# =========================

def mpv_send(sock_path: str, command: list) -> None:
    # mpv JSON IPC requires newline termination.
    payload = json.dumps({"command": command}) + "\n"
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        s.connect(sock_path)
        s.sendall(payload.encode("utf-8"))
    finally:
        try:
            s.close()
        except Exception:
            pass

def mpv_request(sock_path: str, command: list, timeout_s: float = 0.5) -> dict:
    payload = json.dumps({"command": command}) + "\n"
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(timeout_s)
    try:
        s.connect(sock_path)
        s.sendall(payload.encode("utf-8"))

        buf = b""
        while b"\n" not in buf:
            chunk = s.recv(4096)
            if not chunk:
                break
            buf += chunk

        line = buf.split(b"\n", 1)[0].decode("utf-8", errors="replace").strip()
        return json.loads(line) if line else {}
    finally:
        try:
            s.close()
        except Exception:
            pass


def mpv_get(sock_path: str, prop: str):
    resp = mpv_request(sock_path, ["get_property", prop])
    return resp.get("data")


def mpv_alive(sock_path: str) -> bool:
    try:
        mpv_send(sock_path, ["get_property", "mpv-version"])
        return True
    except Exception:
        return False


def mpv_ensure_running(sock_path: str, mpv_bin: str) -> None:
    sock = Path(sock_path)

    if sock.exists() and mpv_alive(sock_path):
        return

    # Stale socket cleanup
    if sock.exists():
        try:
            sock.unlink()
        except Exception:
            pass

    # Launch mpv in idle mode; we'll loadfile/loadlist explicitly per cue.
    cmd = [
        mpv_bin,
        f"--input-ipc-server={sock_path}",
        "--idle=yes",
        "--force-window=yes",
    ]
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Wait up to ~3s
    for _ in range(30):
        if sock.exists() and mpv_alive(sock_path):
            return
        time.sleep(0.1)

    raise RuntimeError("mpv launched but IPC socket did not become ready")


# =========================
# midi-mapper API helpers
# =========================

def api_get_or_create_context(base: str, ctx_payload: dict) -> int:
    resp = http_json("POST", f"{base}/api/contexts/get_or_create", ctx_payload)
    cid = int(resp.get("context_id", -1))
    if cid < 1:
        raise RuntimeError(f"Backend returned invalid context_id={cid}. Refusing to write bindings.")
    return cid


def api_set_context_label(base: str, context_id: int, label: str) -> None:
    http_json("POST", f"{base}/api/contexts/{context_id}/label", {"label": label})


def api_delete_context(base: str, context_id: int) -> None:
    http_nojson("DELETE", f"{base}/api/contexts/{context_id}")


def api_set_binding(base: str, bind_payload: dict) -> None:
    http_json("POST", f"{base}/api/bindings/set", bind_payload)


# =========================
# Stored command generation
# =========================

def build_stored_cue_command(
    command_name: str,
    sock_path: str,
    mpv_bin: str,
    time_s: float,
    file_path: str | None,
    playlist_path: str | None,
    index: int | None,
) -> str:
    """
    Build a shell-safe command stored in midi-mapper bindings.
    This command is self-contained: it includes file/playlist+index and time.
    """
    parts = [command_name, "cue", "--time", f"{time_s:.3f}", "--sock", sock_path]
    if mpv_bin != "mpv":
        parts += ["--mpv-bin", mpv_bin]

    if file_path:
        parts += ["--file", file_path]
    elif playlist_path is not None and index is not None:
        parts += ["--playlist", playlist_path, "--index", str(index)]
    else:
        # We never want to store a cue that doesn't know what to load.
        raise ValueError("cue command must include --file or --playlist+--index")

    return " ".join(sh_quote(p) for p in parts)


# =========================
# Subcommands
# =========================

def cmd_cue(args: argparse.Namespace) -> int:
    """
    Self-contained cue:
      - either --file <video>  (single video mode)
      - or     --playlist <m3u> --index <n> (playlist mode)

    Behavior:
      - File mode: only loadfile if different from currently loaded path; otherwise just seek.
      - Playlist mode: only playlist-play-index if different from current playlist-pos; otherwise just seek.
    """
    sock_path = args.sock
    mpv_bin = args.mpv_bin
    file_path = args.file
    playlist_path = args.playlist
    index = args.index
    t = float(args.time)

    # Validate targeting
    if file_path and playlist_path:
        print("Error: use either --file or --playlist, not both", file=sys.stderr)
        return 2
    if not file_path and not playlist_path:
        print("Error: cue requires --file or --playlist so the command is self-contained", file=sys.stderr)
        return 2
    if playlist_path and index is None:
        print("Error: --index is required with --playlist", file=sys.stderr)
        return 2

    mpv_ensure_running(sock_path, mpv_bin)

    # ----------------
    # File mode
    # ----------------
    if file_path:
        target = str(Path(file_path).absolute())

        # Only reload if different file is requested
        cur_path = mpv_get(sock_path, "path")
        if cur_path != target:
            mpv_send(sock_path, ["loadfile", target, "replace"])
            # Wait briefly for mpv to actually switch files before seeking
            for _ in range(30):
                if mpv_get(sock_path, "path") == target:
                    break
                time.sleep(0.02)

        mpv_send(sock_path, ["seek", t, "absolute", "exact"])
        return 0

    # ----------------
    # Playlist mode
    # ----------------
    playlist_abs = str(Path(playlist_path).absolute())

    # Ensure the right playlist is loaded (lightweight check).
    # If you always run with one playlist per session, this stays stable and cheap.
    cur_playlist = mpv_get(sock_path, "playlist-filenames")
    # playlist-filenames can be None depending on mpv version/options; treat as unknown.
    if cur_playlist is None:
        # If unknown, ensure at least something is loaded by loading the list once.
        # Use "replace" only when playlist is unknown/empty to avoid the flash on every keypress.
        count = mpv_get(sock_path, "playlist-count") or 0
        try:
            count = int(count)
        except Exception:
            count = 0
        if count == 0:
            mpv_send(sock_path, ["loadlist", playlist_abs, "replace"])
            for _ in range(30):
                c2 = mpv_get(sock_path, "playlist-count") or 0
                try:
                    if int(c2) > 0:
                        break
                except Exception:
                    pass
                time.sleep(0.02)

    # Only switch if index differs (prevents "flash to beginning" on repeated hits)
    cur_pos = mpv_get(sock_path, "playlist-pos")
    need_switch = True
    try:
        if cur_pos is not None and int(cur_pos) == int(index):
            need_switch = False
    except Exception:
        need_switch = True

    if need_switch:
        mpv_send(sock_path, ["playlist-play-index", int(index)])
        # Wait for index to apply to avoid racing seek onto previous item
        for _ in range(30):
            cur_pos2 = mpv_get(sock_path, "playlist-pos")
            try:
                if cur_pos2 is not None and int(cur_pos2) == int(index):
                    break
            except Exception:
                pass
            time.sleep(0.02)

    mpv_send(sock_path, ["seek", t, "absolute", "exact"])
    return 0

def cmd_delete(args: argparse.Namespace) -> int:
    if args.dry_run:
        print(f"DRY RUN: would DELETE context_id={args.context_id} at {args.base}")
        return 0
    api_delete_context(args.base, args.context_id)
    print(f"OK: deleted context_id={args.context_id}")
    return 0


def cmd_import(args: argparse.Namespace) -> int:
    if bool(args.file) == bool(args.dir):
        print("Error: specify exactly one of --file or --dir", file=sys.stderr)
        return 2

    video_exts = [x.strip().lstrip(".") for x in args.video_ext.split(",") if x.strip()]

    ctx_payload = {
        "daw_slot": args.daw,
        "preset_slot": args.preset,
        "port_id": args.port_id,
        "channel": args.channel,
        "bank_msb": args.msb,
        "bank_lsb": args.lsb,
        "program": args.program,
    }

    # The executable name stored in bindings must be callable from PATH
    command_name = args.command_name

    # ----------------
    # Single-file mode
    # ----------------
    if args.file:
        json_path = Path(args.file)
        if json_path.suffix.lower() != ".json":
            print("Error: --file must be a Whisper .json", file=sys.stderr)
            return 2

        cues = parse_whisper_json(str(json_path))
        if not cues:
            print("No cues found.", file=sys.stderr)
            return 1

        # Determine video file
        if args.video:
            video_path = Path(args.video)
            if not video_path.exists():
                print(f"Error: --video not found: {video_path}", file=sys.stderr)
                return 2
        else:
            # infer stem.<ext> next to json
            inferred = find_matching_video_for_stem(json_path.parent, json_path.stem, video_exts)
            if not inferred:
                print(
                    "Error: could not infer matching video next to JSON.\n"
                    "Either pass --video /path/to/file.mp4 or put <stem>.mp4 next to <stem>.json",
                    file=sys.stderr,
                )
                return 2
            video_path = inferred

        label = args.label or json_path.stem

        if args.dry_run:
            context_id = 123
        else:
            context_id = api_get_or_create_context(args.base, ctx_payload)
            if args.replace_context:
                # Delete-and-recreate to guarantee clean slate
                api_delete_context(args.base, context_id)
                context_id = api_get_or_create_context(args.base, ctx_payload)
            api_set_context_label(args.base, context_id, label)

        note = args.start_note
        for cue in cues:
            cmd = build_stored_cue_command(
                command_name=command_name,
                sock_path=args.mpv_sock,
                mpv_bin=args.mpv_bin,
                time_s=cue.start_s,
                file_path=str(video_path.absolute()),
                playlist_path=None,
                index=None,
            )
            bind_payload = {
                "context_id": context_id,
                "enabled": 1,
                "trig_type": 1,  # NOTE
                "note": note,
                "cc": None,
                "command": cmd,
                "debounce_ms": args.debounce_ms,
                "require_armed": args.require_armed,
                "notes": cue.text,
                "notify_text": cue.text if args.notify else "",
                "notify_emoji": "🎬" if args.notify else "",
            }
            if args.dry_run:
                print(f"NOTE {note} -> {cmd}")
            else:
                api_set_binding(args.base, bind_payload)
            note += 1

        print(
            f"OK: label={label!r} context_id={context_id} cues={len(cues)} "
            f"start_note={args.start_note} video={video_path.name}"
        )
        return 0

    # ----------------
    # Directory mode
    # ----------------
    dir_path = Path(args.dir)
    if not dir_path.is_dir():
        print(f"Error: --dir is not a directory: {dir_path}", file=sys.stderr)
        return 2

    pairs = scan_directory_for_pairs(dir_path, video_exts)
    if not pairs:
        print(f"No video/JSON pairs found in {dir_path}", file=sys.stderr)
        return 1

    playlist_path = dir_path / (args.playlist_name or f"{dir_path.name}.m3u")
    create_m3u_playlist(pairs, playlist_path)

    label = args.label or dir_path.name
    total_cues = sum(len(p.cues) for p in pairs)

    if args.dry_run:
        context_id = 123
    else:
        context_id = api_get_or_create_context(args.base, ctx_payload)
        if args.replace_context:
            api_delete_context(args.base, context_id)
            context_id = api_get_or_create_context(args.base, ctx_payload)
        api_set_context_label(args.base, context_id, label)

    note = args.start_note
    for video_index, pair in enumerate(pairs):
        for cue in pair.cues:
            cmd = build_stored_cue_command(
                command_name=command_name,
                sock_path=args.mpv_sock,
                mpv_bin=args.mpv_bin,
                time_s=cue.start_s,
                file_path=None,
                playlist_path=str(playlist_path.absolute()),
                index=video_index,
            )
            bind_payload = {
                "context_id": context_id,
                "enabled": 1,
                "trig_type": 1,  # NOTE
                "note": note,
                "cc": None,
                "command": cmd,
                "debounce_ms": args.debounce_ms,
                "require_armed": args.require_armed,
                "notes": f"{pair.video_path.stem}: {cue.text}",
                "notify_text": cue.text if args.notify else "",
                "notify_emoji": "🎬" if args.notify else "",
            }
            if args.dry_run:
                print(f"NOTE {note} -> {cmd}")
            else:
                api_set_binding(args.base, bind_payload)
            note += 1

    end_note = note - 1
    print(f"OK: label={label!r} context_id={context_id}")
    print(f"    playlist={playlist_path.absolute()}")
    print(f"    videos={len(pairs)} cues={total_cues}")
    print(f"    note_range={args.start_note}-{end_note}")
    return 0


# =========================
# CLI
# =========================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="vdj-midi-mapper: import Whisper cues into midi-mapper and drive mpv via IPC"
    )
    sub = parser.add_subparsers(dest="cmd")

    # --- import ---
    p_import = sub.add_parser("import", help="Import cues from a Whisper JSON file OR a directory of video+json pairs")
    p_import.add_argument("--base", default="http://127.0.0.1:8765")

    p_import.add_argument("--file", help="Single Whisper JSON file")
    p_import.add_argument("--video", help="Video file for --file mode (optional; otherwise inferred from stem)")
    p_import.add_argument("--dir", help="Directory containing video+JSON pairs")

    p_import.add_argument("--video-ext", default="mp4,mkv,webm", help="Comma-separated video extensions to match")

    p_import.add_argument("--playlist-name", default="", help="Override generated playlist filename (default: <dir>.m3u)")
    p_import.add_argument("--label", default="", help="Override context label (default: file stem or dir name)")

    # MUST be callable from PATH; default assumes you installed this script under that name.
    p_import.add_argument(
        "--command-name",
        default="vdj-midi-mapper.py",
        help="Command name stored in bindings (must be on PATH). Default: vdj-midi-mapper.py",
    )

    p_import.add_argument("--mpv-sock", default="/run/user/1000/mpv.sock")
    p_import.add_argument("--mpv-bin", default="mpv")

    # Context header fields
    p_import.add_argument("--daw", type=int, default=0)
    p_import.add_argument("--preset", type=int, default=0)
    p_import.add_argument("--port-id", type=int, required=True)
    p_import.add_argument("--channel", type=int, default=0)
    p_import.add_argument("--msb", type=int, default=0)
    p_import.add_argument("--lsb", type=int, default=0)
    p_import.add_argument("--program", type=int, default=0)

    p_import.add_argument("--start-note", type=int, required=True)
    p_import.add_argument("--debounce-ms", type=int, default=80)
    p_import.add_argument("--require-armed", type=int, default=1)
    p_import.add_argument("--notify", action="store_true")
    p_import.add_argument("--dry-run", action="store_true")

    p_import.add_argument(
        "--replace-context",
        action="store_true",
        help="If the target context exists, delete it first, then recreate + import fresh bindings.",
    )

    # --- cue ---
    p_cue = sub.add_parser("cue", help="Load file or playlist index into mpv, then seek (self-contained)")
    p_cue.add_argument("--time", type=float, required=True, help="Seek time in seconds")
    p_cue.add_argument("--sock", default="/run/user/1000/mpv.sock", help="mpv IPC socket path")
    p_cue.add_argument("--mpv-bin", default="mpv", help="mpv binary")

    # exactly one of these targeting modes:
    p_cue.add_argument("--file", default=None, help="Absolute path to a video file (single video mode)")
    p_cue.add_argument("--playlist", default=None, help="Absolute path to an m3u playlist (playlist mode)")
    p_cue.add_argument("--index", type=int, default=None, help="Playlist item index (0-based, required with --playlist)")

    # --- delete context ---
    p_del = sub.add_parser("delete", help="Delete a context by id (CLI escape hatch while web UI lacks delete)")
    p_del.add_argument("--base", default="http://127.0.0.1:8765")
    p_del.add_argument("--context-id", type=int, required=True)
    p_del.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()

    if args.cmd == "import":
        return cmd_import(args)
    if args.cmd == "cue":
        return cmd_cue(args)
    if args.cmd == "delete":
        return cmd_delete(args)

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
