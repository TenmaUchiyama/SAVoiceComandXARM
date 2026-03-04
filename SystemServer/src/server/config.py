"""
Server configuration and initialization.
"""
import os
from typing import Optional

# =========================
# Environment Helpers
# =========================
def _env_flag(name: str, default: bool = True) -> bool:
    """Parse boolean environment variable."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off", ""}


# =========================
# Configuration
# =========================
XARM_ENABLE = _env_flag("XARM_ENABLE", default=True)
XARM_IP = os.getenv("XARM_IP", "192.168.1.199")

# LLM input mode: "coordinate" or "feature"
LLM_INPUT_MODE = os.getenv("LLM_INPUT_MODE", "coordinate").lower()
if LLM_INPUT_MODE not in ["coordinate", "feature"]:
    print(f"⚠️ Invalid LLM_INPUT_MODE='{LLM_INPUT_MODE}', defaulting to 'coordinate'")
    LLM_INPUT_MODE = "coordinate"


# =========================
# Robot Initialization
# =========================
_XARM_IMPORT_ERROR: Optional[Exception] = None

try:
    from XARmOperator import XArmOperator
except ModuleNotFoundError as e:
    XArmOperator = None  # type: ignore[assignment]
    _XARM_IMPORT_ERROR = e


def create_robot():
    """Create robot operator instance if available."""
    if XArmOperator is None:
        return None
    if not XARM_ENABLE:
        return None
    return XArmOperator(ip=XARM_IP)


def get_xarm_import_error() -> Optional[Exception]:
    """Get XArm import error if any."""
    return _XARM_IMPORT_ERROR


# Global robot instance
robot = create_robot()
