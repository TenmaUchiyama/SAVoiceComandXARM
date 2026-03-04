"""
Math utilities for 3D vector operations.
"""
from __future__ import annotations
import math
from typing import Dict, List, Literal, Tuple

# =========================
# Type Aliases
# =========================
Vec3 = Tuple[float, float, float]


# =========================
# Vector Operations
# =========================
def v3(x: List[float]) -> Vec3:
    """List to Vec3 tuple."""
    return (float(x[0]), float(x[1]), float(x[2]))


def sub(a: Vec3, b: Vec3) -> Vec3:
    """Vector subtraction: a - b"""
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def dot(a: Vec3, b: Vec3) -> float:
    """Dot product."""
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a: Vec3, b: Vec3) -> Vec3:
    """Cross product."""
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def norm(a: Vec3) -> float:
    """Vector magnitude."""
    return math.sqrt(dot(a, a))


def normalize(a: Vec3, eps: float = 1e-8) -> Vec3:
    """Normalize vector to unit length."""
    n = norm(a)
    if n < eps:
        return (0.0, 0.0, 0.0)
    return (a[0] / n, a[1] / n, a[2] / n)


def project_xz(a: Vec3) -> Vec3:
    """Project vector onto XZ plane (y=0)."""
    return (a[0], 0.0, a[2])


# =========================
# Frame Basis
# =========================
def make_frame_basis(forward: Vec3, up: Vec3 = (0.0, 1.0, 0.0)) -> Tuple[Vec3, Vec3, Vec3]:
    """
    Create orthonormal basis from forward vector.
    Unity convention: right = cross(up, forward)
    
    Returns:
        (right, up, forward) basis vectors
    """
    f = normalize(forward)
    r = normalize(cross(up, f))
    u = normalize(cross(f, r))  # Re-orthogonalize
    return r, u, f


def world_to_local(p_world: Vec3, origin_world: Vec3, basis_ruf: Tuple[Vec3, Vec3, Vec3]) -> Vec3:
    """
    Transform world position to local coordinates.
    
    Args:
        p_world: Position in world space
        origin_world: Origin of local frame in world space
        basis_ruf: (right, up, forward) basis vectors
        
    Returns:
        Position in local space (x=right, y=up, z=forward)
    """
    r, u, f = basis_ruf
    d = sub(p_world, origin_world)
    return (dot(d, r), dot(d, u), dot(d, f))


# =========================
# Utility Functions
# =========================
def safe_cos_theta(u: Vec3, forward_hat: Vec3, eps: float = 1e-8) -> float:
    """
    Compute cosine of angle between u and forward_hat.
    Returns 1.0 if u is zero (same position as origin).
    """
    nu = norm(u)
    if nu < eps:
        return 1.0
    return dot(u, forward_hat) / nu


def stable_rank(values: Dict[str, float], direction: Literal["asc", "desc"]) -> Dict[str, int]:
    """
    Assign 1-indexed ranks with stable sorting.
    Ties are resolved by object ID for reproducibility.
    """
    items = list(values.items())
    if direction == "asc":
        items_sorted = sorted(items, key=lambda kv: (kv[1], kv[0]))
    else:
        items_sorted = sorted(items, key=lambda kv: (-kv[1], kv[0]))
    return {obj_id: i + 1 for i, (obj_id, _) in enumerate(items_sorted)}


def quadrant_side(l: float, p: float) -> Literal["front", "back", "left", "right"]:
    """
    Determine which quadrant an object is in relative to robot.
    
    Args:
        l: Lateral projection (positive = right)
        p: Forward projection (positive = front)
    """
    if abs(p) >= abs(l):
        return "front" if p >= 0 else "back"
    else:
        return "right" if l >= 0 else "left"
