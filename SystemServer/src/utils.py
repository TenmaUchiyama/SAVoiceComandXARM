import json
from pathlib import Path
from typing import Any

SAVE_DIR = Path(__file__).resolve().parent / "saved_grids"
SAVE_DIR.mkdir(exist_ok=True)

GRID_CONFIG_FILENAME = "qr_grid_config.json"


def _normalize_json_data(data: Any) -> Any:
    """Allow both raw Python objects and JSON-in-JSON strings.

    Unity側/手編集で、ファイルが "[...]" のような JSON文字列 になっているケースがあるので
    その場合は1段だけ json.loads して実体に戻す。
    """
    if isinstance(data, str):
        s = data.strip()
        if not s:
            return data
        if s[0] in "[{\"" and s[-1] in "]}\"":
            try:
                return json.loads(s)
            except Exception:
                return data
    return data

def save_grid_to_file(data: Any) -> str:
    """Always overwrite the single grid-config file."""
    save_path = SAVE_DIR / GRID_CONFIG_FILENAME
    data = _normalize_json_data(data)
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return GRID_CONFIG_FILENAME

def load_latest_grid_json():
    """Load the single grid-config file (kept for backward compatibility)."""
    path = SAVE_DIR / GRID_CONFIG_FILENAME
    if not path.is_file():
        return None

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data = _normalize_json_data(data)
    return {"filename": path.name, "data": data}


ROBOT_MARKER_CONFIG_FILENAME = "robot_marker_config.json"

def save_robot_marker_config(data: Any) -> str:
    """Save robot marker relative coordinates config."""
    save_path = SAVE_DIR / ROBOT_MARKER_CONFIG_FILENAME
    data = _normalize_json_data(data)
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return ROBOT_MARKER_CONFIG_FILENAME

def load_robot_marker_config():
    """Load robot marker relative coordinates config."""
    path = SAVE_DIR / ROBOT_MARKER_CONFIG_FILENAME
    if not path.is_file():
        return None

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data = _normalize_json_data(data)
    return {"filename": path.name, "data": data}





