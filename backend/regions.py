"""Chia miền thành các đoạn nhỏ và xác định hàm trên / hàm dưới ở mỗi đoạn.

Trên mỗi đoạn giữa hai mốc liên tiếp, f - g không đổi dấu (vì các mốc đã gồm mọi nghiệm
của f = g). Do đó chỉ cần xét dấu tại một điểm thử; ta lấy nhiều điểm để phát hiện
nghiệm bị bỏ sót, nếu có thì quét lại đoạn đó.
"""
from __future__ import annotations

import numpy as np
import sympy as sp

from .intersection import scan_roots
from .models import Boundary, Piece
from .numeric import numeric_fn, to_float

MIN_LEN = 1e-9


def _sample_signs(hfn, lo: float, hi: float, n: int = 9):
    ts = lo + (hi - lo) * (np.arange(1, n + 1) / (n + 1))
    return ts, hfn(ts)


def build_pieces(f: sp.Expr, g: sp.Expr, points: list[Boundary]) -> list[Piece]:
    h = f - g
    hfn, ffn, gfn = numeric_fn(h), numeric_fn(f), numeric_fn(g)
    pts = sorted(points, key=lambda b: b.value)

    # Vòng tinh chỉnh: nếu trên một đoạn h đổi dấu thì còn nghiệm chưa được tìm thấy
    for _ in range(2):
        extra: list[Boundary] = []
        for a, b in zip(pts, pts[1:]):
            if b.value - a.value < MIN_LEN:
                continue
            _, hs = _sample_signs(hfn, a.value, b.value)
            hs = hs[~np.isnan(hs)]
            scale = max(1e-12, float(np.max(np.abs(hs)))) if hs.size else 1.0
            if hs.size and (hs.max() > 1e-9 * scale) and (hs.min() < -1e-9 * scale):
                for r in scan_roots(h, f, g, a.value, b.value, n=8001):
                    if a.value + 1e-7 < r < b.value - 1e-7:
                        extra.append(Boundary(r, sp.Float(r, 15), False, True))
        if not extra:
            break
        pts = sorted(pts + extra, key=lambda b: b.value)

    pieces: list[Piece] = []
    for a, b in zip(pts, pts[1:]):
        if b.value - a.value < MIN_LEN:
            continue
        ts, hs = _sample_signs(hfn, a.value, b.value)
        valid = ~np.isnan(hs)
        mid = (a.value + b.value) / 2
        # Điểm thử: điểm mẫu có |h| lớn nhất cho dấu đáng tin nhất
        k = int(np.nanargmax(np.abs(hs))) if valid.any() else 4
        x0 = float(ts[k])
        fx, gx = float(ffn(np.array([x0]))[0]), float(gfn(np.array([x0]))[0])
        f_on_top = (fx - gx) >= 0
        pieces.append(Piece(
            lo=a, hi=b,
            upper="f" if f_on_top else "g",
            upper_expr=f if f_on_top else g,
            lower_expr=g if f_on_top else f,
            test_x=x0, test_f=fx, test_g=gx,
        ))
    return pieces
