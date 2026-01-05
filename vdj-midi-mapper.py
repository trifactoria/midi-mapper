#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen


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


def http_json(method: str, url: str, payload: dict | None = None) -> dict:
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = Request(url, method=method, data=data, headers=headers)
    with urlopen(req) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body) if body else {}


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


def natural_sort_key(text: str) -> list:
    """Convert a string into a list of mixed strings and integers for natural sorting."""
    def atoi(s):
        return int(s) if s.isdigit() else s.lower()
    return [atoi(c) for c in re.split(r'(\d+)', text)]


def scan_directory_for_videos(dir_path: Path, video_exts: list[str]) -> list[VideoCuePair]:
    """Scan directory for JSON+video pairs, sorted naturally by basename."""
    pairs: list[VideoCuePair] = []

    # Find all JSON files
    json_files = list(dir_path.glob("*.json"))

    for json_path in json_files:
        stem = json_path.stem

        # Look for matching video file
        video_path = None
        for ext in video_exts:
            candidate = dir_path / f"{stem}.{ext}"
            if candidate.exists():
                video_path = candidate
                break

        if not video_path:
            print(f"Warning: No video found for {json_path.name}, skipping", file=sys.stderr)
            continue

        # Parse cues from JSON
        try:
            cues = parse_whisper_json(str(json_path))
            if not cues:
                print(f"Warning: No cues in {json_path.name}, skipping", file=sys.stderr)
                continue

            pairs.append(VideoCuePair(video_path=video_path, json_path=json_path, cues=cues))
        except Exception as e:
            print(f"Warning: Failed to parse {json_path.name}: {e}, skipping", file=sys.stderr)
            continue

    # Sort by basename (natural sort)
    pairs.sort(key=lambda p: natural_sort_key(p.video_path.stem))

    return pairs


def create_playlist(pairs: list[VideoCuePair], output_path: Path) -> None:
    """Create an m3u playlist file from video paths."""
    with output_path.open('w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        for pair in pairs:
            # Use absolute paths for reliability
            f.write(f"{pair.video_path.absolute()}\n")


def send_mpv_command(sock_path: str, command: list) -> bool:
    """Send a JSON command to mpv via IPC socket. Returns True if successful."""
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(sock_path)

        # CRITICAL: mpv requires newline-terminated JSON
        payload = json.dumps({"command": command}) + "\n"
        sock.sendall(payload.encode('utf-8'))
        sock.close()
        return True
    except Exception as e:
        print(f"Failed to send mpv command: {e}", file=sys.stderr)
        return False


def ensure_mpv_running(sock_path: str, playlist_path: str, mpv_bin: str) -> bool:
    """Ensure mpv is running with the correct playlist. Launch if needed."""
    # Check if socket exists and responds
    if Path(sock_path).exists():
        # Try to ping mpv
        if send_mpv_command(sock_path, ["get_property", "playlist-count"]):
            return True
        else:
            # Socket exists but not responding, remove stale socket
            try:
                os.unlink(sock_path)
            except:
                pass

    # Launch mpv
    print(f"Launching mpv with playlist: {playlist_path}", file=sys.stderr)
    try:
        subprocess.Popen([
            mpv_bin,
            f"--input-ipc-server={sock_path}",
            "--idle=yes",
            "--force-window=yes",
            f"--playlist={playlist_path}"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Wait for socket to become available (max 3 seconds)
        for _ in range(30):
            if Path(sock_path).exists():
                time.sleep(0.1)  # Give mpv a moment to start listening
                if send_mpv_command(sock_path, ["get_property", "playlist-count"]):
                    return True
            time.sleep(0.1)

        print("mpv launched but socket not responding", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Failed to launch mpv: {e}", file=sys.stderr)
        return False


def cmd_cue(args) -> int:
    """Handle the 'cue' subcommand: control mpv to jump to playlist item and seek."""
    sock_path = args.sock
    playlist_path = args.playlist
    index = args.index
    time_s = args.time
    mpv_bin = args.mpv_bin

    # Ensure mpv is running with correct playlist
    if not ensure_mpv_running(sock_path, playlist_path, mpv_bin):
        print("Failed to start or connect to mpv", file=sys.stderr)
        return 1

    # Switch to playlist item
    if not send_mpv_command(sock_path, ["playlist-play-index", index]):
        print(f"Failed to switch to playlist index {index}", file=sys.stderr)
        return 1

    # Small delay to let mpv load the file
    time.sleep(0.05)

    # Seek to exact time
    if not send_mpv_command(sock_path, ["seek", time_s, "absolute", "exact"]):
        print(f"Failed to seek to {time_s}", file=sys.stderr)
        return 1

    return 0


def cmd_import(args) -> int:
    """Handle the 'import' subcommand: import cues from file or directory."""

    # Determine mode: single file or directory
    if args.file:
        # Single file mode (original behavior)
        return import_single_file(args)
    elif args.dir:
        # Directory mode (new)
        return import_directory(args)
    else:
        print("Error: must specify either --file or --dir", file=sys.stderr)
        return 2


def import_single_file(args) -> int:
    """Import cues from a single JSON file (original behavior)."""
    p = Path(args.file)
    if p.suffix.lower() != ".json":
        print("JSON-only: please pass a Whisper .json file.", file=sys.stderr)
        return 2

    cues = parse_whisper_json(args.file)
    if not cues:
        print("No segments found.", file=sys.stderr)
        return 1

    label = p.stem

    ctx_payload = {
        "daw_slot": args.daw,
        "preset_slot": args.preset,
        "port_id": args.port_id,
        "channel": args.channel,
        "bank_msb": args.msb,
        "bank_lsb": args.lsb,
        "program": args.program,
    }

    if args.dry_run:
        context_id = 123
    else:
        ctx_resp = http_json("POST", f"{args.base}/api/contexts/get_or_create", ctx_payload)
        context_id = int(ctx_resp["context_id"])

        # Label context as filename stem
        http_json("POST", f"{args.base}/api/contexts/{context_id}/label", {"label": label})

    note = args.start_note
    for cue in cues:
        # For single file mode, we still use the old command format (no playlist/index)
        # This preserves backward compatibility
        cmd = make_seek_cmd_legacy(cue.start_s, args.mpv_sock)
        bind_payload = {
            "context_id": context_id,
            "enabled": 1,
            "trig_type": 1,
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
            http_json("POST", f"{args.base}/api/bindings/set", bind_payload)

        note += 1

    print(f"OK: label={label!r} context_id={context_id} cues={len(cues)} start_note={args.start_note}")
    return 0


def import_directory(args) -> int:
    """Import cues from all JSON files in a directory, creating a playlist."""
    dir_path = Path(args.dir)
    if not dir_path.is_dir():
        print(f"Error: {args.dir} is not a directory", file=sys.stderr)
        return 2

    # Parse video extensions
    video_exts = [ext.strip() for ext in args.video_ext.split(',')]

    # Scan directory for video+JSON pairs
    pairs = scan_directory_for_videos(dir_path, video_exts)
    if not pairs:
        print(f"No video/JSON pairs found in {args.dir}", file=sys.stderr)
        return 1

    # Create playlist file
    playlist_name = f"{dir_path.name}.m3u"
    playlist_path = dir_path / playlist_name
    create_playlist(pairs, playlist_path)
    print(f"Created playlist: {playlist_path}")

    # Count total cues
    total_cues = sum(len(pair.cues) for pair in pairs)

    # Create context
    label = dir_path.name
    ctx_payload = {
        "daw_slot": args.daw,
        "preset_slot": args.preset,
        "port_id": args.port_id,
        "channel": args.channel,
        "bank_msb": args.msb,
        "bank_lsb": args.lsb,
        "program": args.program,
    }

    if args.dry_run:
        context_id = 123
    else:
        ctx_resp = http_json("POST", f"{args.base}/api/contexts/get_or_create", ctx_payload)
        context_id = int(ctx_resp["context_id"])
        http_json("POST", f"{args.base}/api/contexts/{context_id}/label", {"label": label})

    # Create bindings for all cues across all videos
    note = args.start_note
    script_path = Path(__file__).absolute()

    for video_idx, pair in enumerate(pairs):
        for cue in pair.cues:
            # Create readable command using the cue subcommand
            cmd = (
                f"{script_path} cue "
                f"--playlist {playlist_path.absolute()} "
                f"--index {video_idx} "
                f"--time {cue.start_s:.3f}"
            )

            # Add optional args if non-default
            if args.mpv_sock != "/run/user/1000/mpv.sock":
                cmd += f" --sock {args.mpv_sock}"
            if args.mpv_bin != "mpv":
                cmd += f" --mpv-bin {args.mpv_bin}"

            bind_payload = {
                "context_id": context_id,
                "enabled": 1,
                "trig_type": 1,
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
                http_json("POST", f"{args.base}/api/bindings/set", bind_payload)

            note += 1

    end_note = note - 1
    print(f"OK: label={label!r} context_id={context_id}")
    print(f"    videos={len(pairs)} cues={total_cues}")
    print(f"    note_range={args.start_note}-{end_note}")
    print(f"    playlist={playlist_path}")

    return 0


def make_seek_cmd_legacy(seconds: float, sock: str) -> str:
    """Legacy command format for backward compatibility (single-file mode)."""
    payload = f'{{ "command": ["seek", {seconds:.3f}, "absolute", "exact"] }}'
    return f"bash -lc 'printf {json.dumps(payload)} | socat - {sock} >/dev/null'"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="VDJ MIDI Mapper: Import cues and control mpv playback"
    )

    subparsers = parser.add_subparsers(dest='command', help='Subcommands')

    # Import subcommand
    import_parser = subparsers.add_parser('import', help='Import cues from JSON file(s)')
    import_parser.add_argument("--base", default="http://127.0.0.1:8765")
    import_parser.add_argument("--file", help="Single Whisper JSON file")
    import_parser.add_argument("--dir", help="Directory containing video+JSON pairs")
    import_parser.add_argument("--video-ext", default="mp4,mkv,webm",
                               help="Comma-separated video extensions (default: mp4,mkv,webm)")
    import_parser.add_argument("--mpv-sock", default="/run/user/1000/mpv.sock")
    import_parser.add_argument("--mpv-bin", default="mpv", help="Path to mpv binary")
    import_parser.add_argument("--daw", type=int, default=0)
    import_parser.add_argument("--preset", type=int, default=0)
    import_parser.add_argument("--port-id", type=int, required=True)
    import_parser.add_argument("--channel", type=int, default=0)
    import_parser.add_argument("--msb", type=int, default=0)
    import_parser.add_argument("--lsb", type=int, default=0)
    import_parser.add_argument("--program", type=int, default=0)
    import_parser.add_argument("--start-note", type=int, required=True)
    import_parser.add_argument("--debounce-ms", type=int, default=80)
    import_parser.add_argument("--require-armed", type=int, default=1)
    import_parser.add_argument("--notify", action="store_true")
    import_parser.add_argument("--dry-run", action="store_true")

    # Cue subcommand
    cue_parser = subparsers.add_parser('cue', help='Control mpv: jump to playlist item and seek')
    cue_parser.add_argument("--playlist", required=True, help="Path to m3u playlist file")
    cue_parser.add_argument("--index", type=int, required=True, help="Playlist item index (0-based)")
    cue_parser.add_argument("--time", type=float, required=True, help="Seek time in seconds")
    cue_parser.add_argument("--sock", default="/run/user/1000/mpv.sock", help="mpv IPC socket path")
    cue_parser.add_argument("--mpv-bin", default="mpv", help="Path to mpv binary")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    if args.command == 'import':
        return cmd_import(args)
    elif args.command == 'cue':
        return cmd_cue(args)
    else:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
