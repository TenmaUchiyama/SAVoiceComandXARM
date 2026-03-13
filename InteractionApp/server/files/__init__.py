"""
files — Grid / Robot 設定ファイルの保存・読み込み管理。
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any, List, Optional, Tuple


def _normalize_json_data(data: Any) -> Any:
    """JSON-in-JSON 文字列を 1 段だけパースする。"""
    if isinstance(data, str):
        s = data.strip()
        if s and s[0] in "[{\"" and s[-1] in "]}\"":
            try:
                return json.loads(s)
            except Exception:
                pass
    return data


class FileManager:
    """Grid / Robot config ファイル管理。"""

    def __init__(self, save_dir: Path):
        self.save_dir = save_dir
        self.save_dir.mkdir(parents=True, exist_ok=True)

    # === Grid ===
    _GRID_MANUAL = "qr_grid_config_manual.json"

    def list_grids(self) -> List[Path]:
        files = list(self.save_dir.glob("qr_grid_config*.json"))
        return sorted(
            files,
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

    def list_grid_names(self) -> List[str]:
        return [p.name for p in self.list_grids()]

    def save_grid(self, data: Any, filename: Optional[str] = None) -> Path:
        data = _normalize_json_data(data)
        if filename and filename.endswith(".json") and "qr_grid_config" in filename:
            path = self.save_dir / filename
        else:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            path = self.save_dir / f"qr_grid_config_{ts}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return path

    def load_grid(self, name: Optional[str] = None) -> Tuple[str, Any]:
        target = self._resolve(name, self.list_grids, "grid")
        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)
        return target.name, _normalize_json_data(data)

    # === Robot ===
    def list_robots(self) -> List[Path]:
        files = list(self.save_dir.glob("qr_robot_config*.json"))
        return sorted(
            files,
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

    def list_robot_names(self) -> List[str]:
        return [p.name for p in self.list_robots()]

    def save_robot(self, data: Any, filename: Optional[str] = None) -> Path:
        data = _normalize_json_data(data)
        if filename and filename.endswith(".json") and "qr_robot_config" in filename:
            path = self.save_dir / filename
        else:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            path = self.save_dir / f"qr_robot_config_{ts}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return path

    def load_robot(self, name: Optional[str] = None) -> Tuple[str, Any]:
        target = self._resolve(name, self.list_robots, "robot")
        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)
        return target.name, _normalize_json_data(data)

    # === helper ===
    def _resolve_grid_latest(self) -> Path:
        """「最新」= まず qr_grid_config_manual.json があればそれ、なければ mtime で最新。"""
        manual = self.save_dir / self._GRID_MANUAL
        if manual.exists():
            return manual
        files = self.list_grids()
        if not files:
            raise FileNotFoundError(f"No saved grid files in {self.save_dir}")
        return files[0]

    def _resolve(self, name: Optional[str], list_fn, kind: str) -> Path:
        if name and name != "latest":
            p = self.save_dir / name
            if not p.exists():
                raise FileNotFoundError(f"{kind} file not found: {p}")
            return p
        if kind == "grid":
            return self._resolve_grid_latest()
        files = list_fn()
        if not files:
            raise FileNotFoundError(f"No saved {kind} files in {self.save_dir}")
        return files[0]
