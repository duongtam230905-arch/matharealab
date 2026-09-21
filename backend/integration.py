"""Tính tích phân từng đoạn: ưu tiên kết quả chính xác, kiểm chứng và dự phòng bằng số."""
from __future__ import annotations

import sympy as sp

from .models import Piece
from .numeric import numeric_integral
from .parser import X

REL_TOL = 1e-9


def _tidy(expr: sp.Expr) -> sp.Expr:
    try:
        if expr.count_ops() < 250:
            return sp.simplify(expr)
    except Exception:
        pass
    return expr


def _bad(v: sp.Expr) -> bool:
    return v.has(sp.zoo) or v.has(sp.nan) or v.has(sp.oo) or v.has(-sp.oo) or v.has(sp.I) or v.has(sp.Integral)


def integrate_piece(piece: Piece, warnings: list[str]) -> None:
    """Điền piece.integrand / area / exact / antiderivative."""
    expr = sp.simplify(piece.upper_expr - piece.lower_expr) if piece.upper_expr.count_ops() < 120 \
        else piece.upper_expr - piece.lower_expr
    piece.integrand = expr

    lo, hi = piece.lo, piece.hi
    numeric = numeric_integral(expr, lo.expr, hi.expr)
    numeric_f = float(numeric)

    exact_val = None
    F = None
    if lo.exact and hi.exact:
        try:
            F = sp.integrate(expr, X)
            if _bad(F):
                F = None
        except Exception:
            F = None
        if F is not None:
            try:
                cand = _tidy(F.subs(X, hi.expr) - F.subs(X, lo.expr))
                if not _bad(cand) and abs(complex(sp.N(cand, 25)).imag) < 1e-15:
                    diff = abs(float(sp.re(sp.N(cand, 25))) - numeric_f)
                    if diff <= REL_TOL * max(1.0, abs(numeric_f)):
                        exact_val = cand
                    else:
                        warnings.append("Nguyên hàm tính được không khớp với tích phân số; dùng giá trị số.")
            except Exception:
                exact_val = None
        if exact_val is None:
            try:  # thử tích phân xác định trực tiếp
                cand = _tidy(sp.integrate(expr, (X, lo.expr, hi.expr)))
                if not _bad(cand):
                    diff = abs(float(sp.re(sp.N(cand, 25))) - numeric_f)
                    if diff <= REL_TOL * max(1.0, abs(numeric_f)):
                        exact_val = cand
            except Exception:
                exact_val = None

    if exact_val is not None:
        piece.area = exact_val
        piece.area_value = float(sp.re(sp.N(exact_val, 25)))
        piece.exact = True
        piece.antiderivative = F
    else:
        piece.area = sp.Float(str(numeric), 25)
        piece.area_value = numeric_f
        piece.exact = False
        piece.antiderivative = None
