from __future__ import annotations

import sys
from pathlib import Path


# Allow importing from <repo>/SystemServer/src regardless of where you run this.
SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
	sys.path.insert(0, str(SRC_DIR))

from XARmOperator import XArmOperator


def _parse_xy(line: str) -> tuple[int, int] | None:
	parts = line.strip().replace(",", " ").split()
	if len(parts) != 2:
		return None
	try:
		x = int(parts[0])
		y = int(parts[1])
	except ValueError:
		return None
	return x, y


def main() -> int:
	op = XArmOperator()  # IP default is inside XArmOperator
	ok, msg = op.connect()
	if not ok:
		print(f"connect failed: {msg}")
		return 1

	try:
		print("Enter: 'x y' (e.g. 0 3), 'o' (open), 'c' (close), 'q' (quit)")
		while True:
			try:
				line = input("> ").strip()
			except (EOFError, KeyboardInterrupt):
				print()
				return 0

			if not line:
				continue

			cmd = line.lower()
			if cmd in {"q", "quit", "exit"}:
				return 0
			if cmd in {"o", "open"}:
				ok, msg = op.open_gripper()
				print(f"open_gripper: ok={ok}, msg={msg}")
				continue
			if cmd in {"c", "close"}:
				ok, msg = op.close_gripper()
				print(f"close_gripper: ok={ok}, msg={msg}")
				continue
			if cmd in {"h", "help", "?"}:
				print("Commands: x y | o/open | c/close | q/quit")
				continue

			parsed = _parse_xy(line)
			if parsed is None:
				print("Invalid input. Example: 0 3  (or o/c/q)")
				continue

			x, y = parsed
			ok, msg = op.pick_at(x, y)
			print(f"pick_at({x},{y}): ok={ok}, msg={msg}")
	finally:
		op.disconnect()


if __name__ == "__main__":
	raise SystemExit(main())
