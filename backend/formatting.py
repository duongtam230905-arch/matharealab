"""Định dạng LaTeX / số thập phân cho kết quả trả về giao diện."""
from __future__ import annotations

import sympy as sp

from .models import Boundary
from .numeric import fmt_num


def tex(expr: sp.Expr) -> str:
    """LaTeX của biểu thức; logarit tự nhiên hiển thị là \\ln (quy ước sách giáo khoa Việt Nam)."""
    return sp.latex(expr, ln_notation=True)


def bound_latex(b: Boundary) -> str:
    """Cận/giao điểm: dạng chính xác nếu có, ngược lại số thập phân."""
    if b.exact:
        return tex(b.expr)
    return fmt_num(b.value, 6)


def value_latex(expr: sp.Expr, exact: bool, value: float) -> str:
    return tex(expr) if exact else fmt_num(value, 6)


def diff_latex(upper: sp.Expr, lower: sp.Expr) -> str:
    """u(x) - v(x), đóng ngoặc v khi cần: x^2-\\left(2x+\\frac32\\right)."""
    if lower == 0:
        return tex(upper)
    low = tex(lower)
    if lower.is_Add or lower.could_extract_minus_sign():
        low = rf"\left({low}\right)"
    return f"{tex(upper)}-{low}"


def pair_label(b: Boundary, y_latex: str, y_value: float, letter: str) -> str:
    """Nhãn điểm cho hình vẽ LaTeX: A(x, y). Chỉ giữ dạng chính xác khi là số hữu tỉ, còn lại làm tròn."""
    x_tex = bound_latex(b) if (b.exact and b.expr.is_Rational) else fmt_num(b.value, 3)
    y_tex = y_latex if len(y_latex) <= 8 and "sqrt" not in y_latex and "frac" not in y_latex or y_latex.lstrip("-").isdigit() \
        else fmt_num(y_value, 3)
    return f"{letter}({x_tex},\\,{y_tex})"
