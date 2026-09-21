"""Kiểm tra hàm số xác định và liên tục trên đoạn [lo, hi]."""
from __future__ import annotations

import numpy as np
import sympy as sp
from sympy.calculus.util import continuous_domain

from .errors import MSG_DOMAIN, AreaError
from .numeric import numeric_fn
from .parser import X


def check_domain(expr: sp.Expr, name: str, lo, hi, lo_f: float, hi_f: float) -> None:
    """Ném AreaError nếu `expr` không xác định (hoặc gián đoạn) tại một điểm nào đó của [lo, hi].

    Hai lớp kiểm tra bổ trợ nhau:
      - Ký hiệu: continuous_domain của SymPy bắt được tiệm cận đứng nằm giữa các mẫu.
      - Số học: lấy mẫu dày để bắt căn/log của số âm, giá trị phức, NaN.
    """
    if expr.is_number:  # hàm hằng luôn hợp lệ
        return
    xs = np.linspace(lo_f, hi_f, 1601)
    ys = numeric_fn(expr)(xs)
    if np.isnan(ys).any():
        bad = xs[np.isnan(ys)][0]
        raise AreaError("domain", MSG_DOMAIN,
                        detail=f"{name}(x) không xác định tại x ≈ {bad:.4g}")
    try:
        interval = sp.Interval(lo, hi)
        cd = continuous_domain(expr, X, interval)
        ok = interval.is_subset(cd)
        if ok is False:
            raise AreaError("domain", MSG_DOMAIN,
                            detail=f"{name}(x) gián đoạn hoặc không xác định trong [{lo}, {hi}]")
    except AreaError:
        raise
    except Exception:
        pass  # SymPy không kết luận được: dựa vào kiểm tra số ở trên
