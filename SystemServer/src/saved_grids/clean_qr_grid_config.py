"""Utility to normalize saved grid config JSON.

This project sometimes ends up with `qr_grid_config.json` saved as a *JSON string*
that itself contains JSON (e.g. "[\r\n  {...}\r\n]"). This script converts it
into a normal JSON file (list/dict) and rewrites with clean formatting.

Run:
  python clean_qr_grid_config.py

Optional:
  python clean_qr_grid_config.py --file qr_grid_config.json
  python clean_qr_grid_config.py --inplace

By default it writes a new file next to the input:
  <name>.clean.json
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def _loads_maybe_json_string(value: Any) -> Any:
    """If `value` is a JSON string that contains JSON, decode one layer."""
    if not isinstance(value, str):
        return value

    s = value.strip()
    if not s:
        return value

    # Heuristic: likely JSON payload.
    if (s[0] in "[{\""):
        try:
            return json.loads(s)
        except Exception:
            return value

    return value


def normalize_file(path: Path) -> Any:
    raw = path.read_text(encoding="utf-8")

    # First parse the file as JSON.
    data = json.loads(raw)

    # If it's a JSON string, parse the inner JSON.
    data = _loads_maybe_json_string(data)

    # If it is still a string, try one more time (handles accidental double-encoding).
    data = _loads_maybe_json_string(data)

    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default="qr_grid_config.json", help="Input file name/path")
    parser.add_argument(
        "--inplace",
        action="store_true",
        help="Overwrite the original file (creates a timestamped .bak first)",
    )

    args = parser.parse_args()

    input_path = Path(args.file)
    if not input_path.is_absolute():
        input_path = Path(__file__).resolve().parent / input_path

    if not input_path.is_file():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    data = normalize_file(input_path)

    # Decide output path.
    if args.inplace:
        backup_path = input_path.with_suffix(input_path.suffix + f".{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak")
        backup_path.write_text(input_path.read_text(encoding="utf-8"), encoding="utf-8")
        output_path = input_path
    else:
        output_path = input_path.with_name(input_path.stem + ".clean" + input_path.suffix)

    with output_path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"✅ Wrote normalized JSON: {output_path}")
    if args.inplace:
        print(f"🧾 Backup created: {backup_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
