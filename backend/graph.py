"""Dữ liệu đồ thị cho frontend (Plotly) và khung nhìn dùng chung với bộ sinh LaTeX."""
from __future__ import annotations

import math

import numpy as np

from .models import Solution
from .numeric import numeric_fn

N_CURVE = 1800
N_REGION = 240


def nice_step(span: float, target: int = 8) -> float:
    """Bước chia 'đẹp' (1, 2, 5 x 10^k) sao cho có khoảng `target` vạch trên `span`."""
    if span <= 0:
        return 1.0
    raw = span / target
    mag = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 2.5, 5, 10):
        if raw <= m * mag:
            return m * mag
    return 10 * mag


def nice_bounds(lo: float, hi: float, step: float) -> tuple[float, float]:
    return math.floor(lo / step + 1e-9) * step, math.ceil(hi / step - 1e-9) * step


def compute_view(sol: Solution) -> dict:
    lo, hi = sol.lo.value, sol.hi.value
    width = max(hi - lo, 1e-6)
    pad = max(0.3 * width, 0.5 if width >= 0.5 else width)
    ffn, gfn = numeric_fn(sol.f), numeric_fn(sol.g)
    xs = np.linspace(lo, hi, 600)
    ys = np.concatenate([ffn(xs), gfn(xs)])
    ys = ys[~np.isnan(ys)]
    ymin = min(0.0, float(ys.min())) if ys.size else -1.0
    ymax = max(0.0, float(ys.max())) if ys.size else 1.0
    span = (ymax - ymin) or 1.0
    return {
        "xmin": lo - pad, "xmax": hi + pad,
        "ymin": ymin - 0.18 * span, "ymax": ymax + 0.18 * span,
    }


def defined_range(fn, x0: float, x1: float) -> tuple[float, float]:
    """Đoạn [u, v] ⊂ [x0, x1] mà hàm có giá trị (dùng để giới hạn miền vẽ trong TikZ)."""
    xs = np.linspace(x0, x1, 3001)
    ok = ~np.isnan(fn(xs))
    if not ok.any():
        return x0, x1
    return float(xs[ok][0]), float(xs[ok][-1])


def _clean(arr: np.ndarray, cap: float, yspan: float) -> list:
    """Chuyển mảng thành list JSON: NaN -> None, ngắt nét ở tiệm cận đứng."""
    y = arr.copy()
    y[np.abs(y) > cap] = np.nan
    big = 2 * yspan
    with np.errstate(invalid="ignore"):
        flip = (y[:-1] * y[1:] < 0) & (np.abs(y[:-1]) > big) & (np.abs(y[1:]) > big)
    y[1:][flip] = np.nan
    return [None if np.isnan(v) else round(float(v), 6) for v in y]


def sample_curves(f, g, x0: float, x1: float, y0: float, y1: float, n: int = N_CURVE) -> dict:
    """Lấy mẫu hai đồ thị trên [x0, x1]. Frontend gọi lại hàm này (qua /api/sample) mỗi khi
    người học zoom/kéo, nhờ đó đường cong luôn phủ kín khung nhìn, không bao giờ bị cụt."""
    ffn, gfn = numeric_fn(f), numeric_fn(g)
    xs = np.linspace(x0, x1, n)
    yspan = max(y1 - y0, 1e-9)
    cap = 6 * yspan + max(abs(y0), abs(y1))
    return {
        "x": [round(float(v), 6) for v in xs],
        "f": _clean(ffn(xs), cap, yspan),
        "g": _clean(gfn(xs), cap, yspan),
    }


def build_graph(sol: Solution, view: dict, points: list[dict]) -> dict:
    ffn, gfn = numeric_fn(sol.f), numeric_fn(sol.g)
    width = view["xmax"] - view["xmin"]
    # Lấy mẫu rộng gấp 3 lần khung nhìn ban đầu để kéo/zoom nhẹ vẫn không thấy đầu mút
    curves = sample_curves(sol.f, sol.g, view["xmin"] - width, view["xmax"] + width, view["ymin"], view["ymax"])

    regions = []
    for p in sol.pieces:
        rx = np.linspace(p.lo.value, p.hi.value, N_REGION)
        up = numeric_fn(p.upper_expr)(rx)
        low = numeric_fn(p.lower_expr)(rx)
        regions.append({
            "x": [round(float(v), 6) for v in np.concatenate([rx, rx[::-1]])],
            "y": [round(float(v), 6) for v in np.concatenate([up, low[::-1]])],
        })

    verticals = []
    for label, b in (("a", sol.lo), ("b", sol.hi)):
        vals = [float(v[0]) for v in (ffn(np.array([b.value])), gfn(np.array([b.value])))]
        far = max(vals + [0.0], key=abs)
        verticals.append({"label": label, "x": b.value, "y0": 0.0, "y1": far})

    return {
        "view": view,
        "x": curves["x"],
        "f": curves["f"],
        "g": curves["g"],
        "regions": regions,
        "points": points,
        "verticals": verticals,
        "is_ox": sol.is_ox,
    }
