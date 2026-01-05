#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen
from zlib import crc32


@dataclass
class Cue:
    start_s: float
    end_s: float
    text: str


def hash_to_slots(filename_stem: str) -> tuple[int, int]:
    """Convert filename to deterministic daw_slot/preset_slot.

    Uses CRC32 hash to map to slots:
    - daw_slot: 0-11 (4 bits)
    - preset_slot: 0-15 (4 bits)

    Gives 192 unique combinations without UI changes.
    """
    h = crc32(filename_stem.encode("utf-8")) & 0xFFFFFFFF
    daw_slot = (h >> 4) & 0x0B  # 0-11 (DAW has only 12 slots in UI)
    preset_slot = h & 0x0F       # 0-15
    return daw_slot, preset_slot


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


def make_seek_cmd(seconds: float, sock: str) -> str:
    # IMPORTANT: pipeline requires a shell. We invoke bash explicitly so your backend
    # can run it in argv mode (no EXEC_USE_SHELL needed).
    payload = f'{{ "command": ["seek", {seconds:.3f}, "absolute", "exact"] }}'
    # json.dumps makes the printf argument safely quoted for bash
    return f"bash -lc 'printf {json.dumps(payload)} | socat - {sock} >/dev/null'"


def main() -> int:
    ap = argparse.ArgumentParser(description="Import Whisper JSON segments into MIDI Mapper bindings.")
    ap.add_argument("--base", default="http://127.0.0.1:8765")
    ap.add_argument("--file", required=True, help="Whisper .json (segments[].start/end/text)")
    ap.add_argument("--mpv-sock", default="/run/user/1000/mpv.sock")
    ap.add_argument("--daw", type=int, default=None, help="DAW slot 0-11 (default: auto from filename hash)")
    ap.add_argument("--preset", type=int, default=None, help="Preset slot 0-15 (default: auto from filename hash)")
    ap.add_argument("--port-id", type=int, required=True)
    ap.add_argument("--channel", type=int, default=0)
    ap.add_argument("--msb", type=int, default=0)
    ap.add_argument("--lsb", type=int, default=0)
    ap.add_argument("--program", type=int, default=0)
    ap.add_argument("--start-note", type=int, required=True)
    ap.add_argument("--debounce-ms", type=int, default=80)
    ap.add_argument("--require-armed", type=int, default=1)
    ap.add_argument("--notify", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    p = Path(args.file)
    if p.suffix.lower() != ".json":
        print("JSON-only: please pass a Whisper .json file.", file=sys.stderr)
        return 2

    cues = parse_whisper_json(args.file)
    if not cues:
        print("No segments found.", file=sys.stderr)
        return 1

    label = p.stem

    # Determine daw_slot and preset_slot
    if args.daw is None or args.preset is None:
        # Auto-assign from filename hash
        auto_daw, auto_preset = hash_to_slots(p.stem)
        daw_slot = args.daw if args.daw is not None else auto_daw
        preset_slot = args.preset if args.preset is not None else auto_preset
        print(f"Auto-assigned slots from filename: daw={daw_slot}, preset={preset_slot}")
    else:
        daw_slot = args.daw
        preset_slot = args.preset

    ctx_payload = {
        "daw_slot": daw_slot,
        "preset_slot": preset_slot,
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
        cmd = make_seek_cmd(cue.start_s, args.mpv_sock)
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


if __name__ == "__main__":
    raise SystemExit(main())
