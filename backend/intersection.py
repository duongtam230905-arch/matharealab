"""Tìm hoành độ giao điểm của hai đồ thị: nghiệm của f(x) = g(x).

Chiến lược (ưu tiên độ chính xác toán học):
  1. Giải chính xác bằng SymPy `solveset` trên miền phù hợp.
  2. Kiểm chứng từng nghiệm bằng số (loại nghiệm ngoại lai).
  3. Quét số học (đổi dấu + cực tiểu của |h|) để bổ sung nghiệm mà bước 1 bỏ sót
     (ví dụ e^x = x + 2). Nghiệm tìm bằng số được đánh dấu exact=False.
"""
from __future__ import annotations

import mpmath as mp
import numpy as np
import sympy as sp

from .models import Boundary
from .numeric import numeric_fn, scalar, to_float
from .parser import X

WINDOW = 40.0          # khi không có cận, quét nghiệm số trong [-40, 40]
SCAN_POINTS = 40001
MERGE_TOL = 1e-9
MAX_ROOTS = 20


def _tidy(expr: sp.Expr) -> sp.Expr:
    try:
        if expr.count_ops() < 80:
            return sp.simplify(expr)
    except Exception:
        pass
    return expr


def _real_value(c: sp.Expr) -> float | None:
    try:
        v = sp.N(c, 30)
        if abs(sp.im(v)) > 1e-20:
            return None
        return float(sp.re(v))
    except Exception:
        return None


def _is_root(hfn, ffn, gfn, r: float) -> bool:
    hv, fv, gv = scalar(hfn, r), scalar(ffn, r), scalar(gfn, r)
    if np.isnan(hv) or np.isnan(fv) or np.isnan(gv):
        return False
    return abs(hv) <= 1e-7 * max(1.0, abs(fv), abs(gv))


def _bisect(hfn, a: float, b: float) -> float | None:
    fa = scalar(hfn, a)
    fb = scalar(hfn, b)
    if np.isnan(fa) or np.isnan(fb):
        return None
    if fa == 0:
        return a
    if fb == 0:
        return b
    if fa * fb > 0:
        return None
    for _ in range(200):
        m = 0.5 * (a + b)
        fm = scalar(hfn, m)
        if np.isnan(fm):
            return None
        if fm == 0:
            return m
        if fa * fm < 0:
            b = m
        else:
            a, fa = m, fm
        if b - a < 1e-15 * max(1.0, abs(a)):
            break
    return 0.5 * (a + b)


def _touch_roots(hfn, xs: np.ndarray, ys: np.ndarray) -> list[float]:
    """Nghiệm bội chẵn (đồ thị tiếp xúc): |h| có cực tiểu bằng 0 mà không đổi dấu."""
    out: list[float] = []
    ay = np.abs(ys)
    with np.errstate(invalid="ignore"):
        cand = np.nonzero((ay[1:-1] < ay[:-2]) & (ay[1:-1] < ay[2:]))[0] + 1
    scale = np.nanmax(ay) if np.isfinite(ay).any() else 1.0
    cand = [i for i in cand if ay[i] < 1e-3 * max(scale, 1.0)][:60]
    for i in cand:
        a, b = xs[i - 1], xs[i + 1]
        for _ in range(100):  # tìm kiếm tam phân trên |h|
            m1, m2 = a + (b - a) / 3, b - (b - a) / 3
            v1, v2 = abs(scalar(hfn, m1)), abs(scalar(hfn, m2))
            if np.isnan(v1) or np.isnan(v2):
                break
            if v1 < v2:
                b = m2
            else:
                a = m1
        r = 0.5 * (a + b)
        v = abs(scalar(hfn, r))
        if not np.isnan(v) and v < 1e-9 * max(1.0, scale):
            out.append(r)
    return out


def scan_roots(h: sp.Expr, f: sp.Expr, g: sp.Expr, lo: float, hi: float, n: int = SCAN_POINTS) -> list[float]:
    """Quét số học nghiệm của h = f - g trên [lo, hi]."""
    if hi - lo < 1e-12:
        return []
    hfn, ffn, gfn = numeric_fn(h), numeric_fn(f), numeric_fn(g)
    xs = np.linspace(lo, hi, n)
    ys = hfn(xs)
    ok = ~np.isnan(ys)
    roots: list[float] = []
    pair = ok[:-1] & ok[1:]
    zero_idx = np.nonzero(ok & (ys == 0.0))[0]
    roots.extend(float(xs[i]) for i in zero_idx)
    with np.errstate(all="ignore"):
        flips = np.nonzero(pair & (ys[:-1] * ys[1:] < 0))[0]
    for i in flips[:400]:
        r = _bisect(hfn, float(xs[i]), float(xs[i + 1]))
        if r is not None and _is_root(hfn, ffn, gfn, r):  # loại đổi dấu do tiệm cận đứng
            roots.append(r)
    for r in _touch_roots(hfn, xs, ys):
        if _is_root(hfn, ffn, gfn, r):
            roots.append(r)
    return roots


def _polish(h: sp.Expr, r0: float) -> sp.Expr:
    """Tinh chỉnh nghiệm số lên ~30 chữ số bằng mpmath; nếu lỗi thì giữ nghiệm float."""
    try:
        with mp.workdps(40):
            fn = sp.lambdify(X, h, modules="mpmath")
            r = mp.findroot(fn, (mp.mpf(r0), mp.mpf(r0) + mp.mpf("1e-9")), tol=1e-30, maxsteps=60)
            if abs(float(r) - r0) < 1e-7:
                return sp.Float(mp.nstr(r, 30), 30)
    except Exception:
        pass
    return sp.Float(r0, 15)


def _rationalize(h: sp.Expr, r: float) -> sp.Expr | None:
    """Nghiệm số có thực sự là số 'đẹp' (hữu tỉ hoặc bội của pi) không? Kiểm chứng bằng SymPy."""
    candidates = []
    try:
        candidates.append(sp.nsimplify(r, rational=True, tolerance=1e-12))
        candidates.append(sp.nsimplify(r, [sp.pi], tolerance=1e-12))
    except Exception:
        return None
    for q in candidates:
        try:
            if q.count_ops() < 12 and sp.simplify(h.subs(X, q)) == 0:
                return q
        except Exception:
            continue
    return None


def _is_identical(h: sp.Expr, lo: float, hi: float) -> bool:
    try:
        if sp.simplify(h) == 0:
            return True
    except Exception:
        pass
    xs = np.linspace(lo, hi, 400)
    ys = numeric_fn(h)(xs)
    fin = ys[~np.isnan(ys)]
    return fin.size > 50 and bool(np.all(np.abs(fin) < 1e-12))


def find_intersections(f: sp.Expr, g: sp.Expr, lo=None, hi=None) -> tuple[list[Boundary], bool]:
    """Trả về (danh sách giao điểm đã sắp xếp, hai hàm có trùng nhau không).

    lo, hi là biểu thức SymPy (chế độ nhập cận) hoặc None (tìm trên cả trục số).
    """
    h = f - g
    manual = lo is not None and hi is not None
    lo_f = to_float(lo) if manual else -WINDOW
    hi_f = to_float(hi) if manual else WINDOW

    if _is_identical(h, lo_f, hi_f):
        return [], True

    hfn, ffn, gfn = numeric_fn(h), numeric_fn(f), numeric_fn(g)
    domain = sp.Interval(lo, hi) if manual else sp.S.Reals

    roots: list[Boundary] = []
    try:
        sol = sp.solveset(h, X, domain)
    except Exception:
        sol = None

    if isinstance(sol, sp.FiniteSet):
        for c in sol:
            val = _real_value(c)
            if val is None:
                continue
            if manual and not (lo_f - 1e-9 <= val <= hi_f + 1e-9):
                continue
            if _is_root(hfn, ffn, gfn, val):
                roots.append(Boundary(val, _tidy(c), True, True))

    # Bổ sung bằng quét số (nghiệm mà solveset không biểu diễn được hoặc bỏ sót)
    for r in scan_roots(h, f, g, lo_f, hi_f):
        if all(abs(r - b.value) > 1e-6 for b in roots):
            nice = _rationalize(h, r)
            if nice is not None:
                roots.append(Boundary(to_float(nice), nice, True, True))
            else:
                roots.append(Boundary(r, _polish(h, r), False, True))

    roots.sort(key=lambda b: b.value)
    merged: list[Boundary] = []
    for b in roots:
        if merged and abs(b.value - merged[-1].value) < MERGE_TOL:
            if b.exact and not merged[-1].exact:
                merged[-1] = b
            continue
        merged.append(b)
    return merged, False
