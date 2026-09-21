"""Tiện ích số học: chuyển biểu thức SymPy thành hàm NumPy/mpmath an toàn."""
from __future__ import annotations

import warnings
from typing import Callable

import mpmath as mp
import numpy as np
import sympy as sp

from .parser import X


def numeric_fn(expr: sp.Expr) -> Callable[[np.ndarray], np.ndarray]:
    """Trả về hàm vector hoá. Giá trị không xác định / phức / vô hạn -> NaN."""
    lam = sp.lambdify(X, expr, modules=["numpy"])

    def call(xs) -> np.ndarray:
        xs = np.asarray(xs, dtype=float)
        with np.errstate(all="ignore"), warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                ys = np.asarray(lam(xs))
            except Exception:
                return np.full(xs.shape, np.nan)
        if ys.ndim == 0 or ys.shape != xs.shape:
            ys = np.broadcast_to(ys, xs.shape).copy()
        if np.iscomplexobj(ys):
            ys = np.where(np.abs(ys.imag) < 1e-12, ys.real, np.nan)
        ys = ys.astype(float, copy=True)
        ys[~np.isfinite(ys)] = np.nan
        return ys

    return call


def scalar(fn: Callable[[np.ndarray], np.ndarray], x: float) -> float:
    return float(fn(np.array([x]))[0])


def to_float(expr) -> float:
    return float(sp.N(expr, 30))


def mpf_of(expr) -> mp.mpf:
    return mp.mpf(str(sp.N(expr, 35)))


def kink_points(expr: sp.Expr, a, b) -> list:
    """Điểm gãy của |u(x)| trong (a, b): tại đó u(x) = 0. Cầu phương số phải chia đoạn tại các điểm này."""
    a_f, b_f = to_float(a), to_float(b)
    pts: list[float] = []
    for ab in expr.atoms(sp.Abs):
        try:
            sol = sp.solveset(ab.args[0], X, sp.Interval(a, b))
        except Exception:
            continue
        if isinstance(sol, sp.FiniteSet):
            for s in sol:
                try:
                    v = float(sp.N(s, 30))
                except Exception:
                    continue
                if a_f + 1e-12 < v < b_f - 1e-12 and all(abs(v - q) > 1e-12 for q in pts):
                    pts.append(v)
    return sorted(pts)


def numeric_integral(expr: sp.Expr, a, b) -> mp.mpf:
    """Tích phân số 30 chữ số bằng mpmath (dùng làm kiểm chứng / phương án dự phòng)."""
    with mp.workdps(30):
        fn = sp.lambdify(X, expr, modules="mpmath")
        nodes = [mpf_of(a)] + [mp.mpf(v) for v in kink_points(expr, a, b)] + [mpf_of(b)]
        return mp.quad(fn, nodes)


def fmt_num(v: float, digits: int = 6) -> str:
    """Định dạng số cố định (không dùng ký hiệu khoa học) và bỏ số 0 thừa."""
    if abs(v) < 10 ** (-digits):
        return "0"
    s = f"{v:.{digits}f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s
