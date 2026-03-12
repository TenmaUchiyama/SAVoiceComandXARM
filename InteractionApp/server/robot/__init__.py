"""
robot — ロボット制御モジュール。

本番用は SystemServer/src/XARmOperator.py を import して使う。
SDK が無い環境ではモックに自動フォールバック。
"""

from __future__ import annotations

import logging
from typing import Union

from debug import debug_log

log = logging.getLogger("unified_debug")

# Adapter (本番) を先に試し、ダメならフラグだけ立てる
_HAS_ADAPTER = False
try:
    from robot.adapter import XArmAdapter, HAS_OPERATOR
    _HAS_ADAPTER = HAS_OPERATOR
except Exception:
    _HAS_ADAPTER = False
    XArmAdapter = None  # type: ignore

from robot.mock import XArmMock

# 型エイリアス (どちらのインスタンスも同じ I/F)
RobotArm = Union["XArmAdapter", XArmMock]


def create_arm(*, mock: bool = False, ip: str = "192.168.1.199") -> RobotArm:
    """環境に応じてアームインスタンスを生成。"""
    if mock or not _HAS_ADAPTER:
        if not _HAS_ADAPTER and not mock:
            debug_log.warn("robot", "XArm SDK / XArmOperator が見つかりません — mock モードで起動")
        return XArmMock()
    return XArmAdapter(ip=ip)  # type: ignore
