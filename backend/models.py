"""Các cấu trúc dữ liệu dùng chung giữa các bước tính toán."""
from __future__ import annotations

from dataclasses import dataclass, field

import sympy as sp


@dataclass
class Boundary:
    """Một mốc trên trục hoành: cận a/b hoặc hoành độ giao điểm.

    exact=False nghĩa là giá trị chỉ là nghiệm gần đúng (tìm bằng phương pháp số).
    """
    value: float
    expr: sp.Expr
    exact: bool = True
    is_root: bool = False  # có phải hoành độ giao điểm của hai đồ thị không


@dataclass
class Piece:
    """Một đoạn [lo, hi] mà trên đó một hàm luôn nằm trên hàm còn lại."""
    lo: Boundary
    hi: Boundary
    upper: str  # 'f' hoặc 'g'
    upper_expr: sp.Expr
    lower_expr: sp.Expr
    test_x: float = 0.0
    test_f: float = 0.0
    test_g: float = 0.0
    integrand: sp.Expr | None = None
    area: sp.Expr | None = None
    area_value: float = 0.0
    exact: bool = True
    antiderivative: sp.Expr | None = None


@dataclass
class Solution:
    f: sp.Expr
    g: sp.Expr
    is_ox: bool
    mode: str  # 'manual' | 'auto'
    lo: Boundary
    hi: Boundary
    intersections: list[Boundary] = field(default_factory=list)  # chỉ những giao điểm nằm trong [lo, hi]
    breakpoints: list[Boundary] = field(default_factory=list)  # a, các giao điểm bên trong, b
    pieces: list[Piece] = field(default_factory=list)
    total: sp.Expr | None = None
    total_value: float = 0.0
    exact: bool = True
    warnings: list[str] = field(default_factory=list)
