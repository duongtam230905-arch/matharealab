"""Điều phối toàn bộ quy trình: nhập hàm -> giao điểm -> miền -> tích phân -> hình -> LaTeX.

`calculate(payload)` là hàm thuần (dict vào, dict ra) nên có thể chạy trong tiến trình
riêng có giới hạn thời gian (xem sandbox.py) và dễ mở rộng sang thể tích tròn xoay,
độ dài đường cong... bằng cách thêm module tương tự.
"""
from __future__ import annotations

import sympy as sp

from . import graph as graph_mod
from . import latex_generator, steps as steps_mod
from .domain import check_domain
from .errors import MSG_NO_INTERSECTION, MSG_NO_REGION, AreaError
from .formatting import bound_latex, diff_latex, pair_label, tex, value_latex
from .integration import integrate_piece
from .intersection import MAX_ROOTS, find_intersections
from .models import Boundary, Solution
from .numeric import fmt_num, numeric_fn, to_float
from .parser import X, expr_to_input, parse_bound, parse_function
from .regions import build_pieces

MAX_PIECES = 60

PIPELINE_LABELS = {
    "parse": "Đã phân tích hàm số",
    "intersections": "Đã tìm giao điểm",
    "region": "Đã xác định miền cần tính",
    "integral": "Đã tính tích phân",
    "graph": "Đã tạo đồ thị",
    "latex": "Đã sinh mã LaTeX",
}


class _Stage:
    def __init__(self) -> None:
        self.current = "parse"
        self.done: list[dict] = []

    def start(self, key: str) -> None:
        self.current = key

    def finish(self, key: str) -> None:
        self.done.append({"key": key, "label": PIPELINE_LABELS[key]})


def _clean(text) -> str | None:
    if text is None:
        return None
    text = str(text).strip()
    return text or None


def _root_info(f: sp.Expr, b: Boundary, letter: str) -> dict:
    """Thông tin một giao điểm: hoành độ, tung độ (chính xác nếu có) và nhãn."""
    y_val = float(numeric_fn(f)(__import__("numpy").array([b.value]))[0])
    y_expr = None
    if b.exact:
        try:
            y_expr = sp.simplify(f.subs(X, b.expr))
            if y_expr.has(sp.zoo) or y_expr.has(sp.nan):
                y_expr = None
        except Exception:
            y_expr = None
    y_tex = tex(y_expr) if y_expr is not None else fmt_num(y_val, 4)
    x_tex = bound_latex(b)
    return {
        "label": letter,
        "x": b.value, "y": y_val,
        "x_latex": x_tex, "y_latex": y_tex,
        "x_input": expr_to_input(b.expr) if b.exact else repr(b.value),
        "exact": b.exact,
        "point_latex": rf"{letter}\left({x_tex},\,{y_tex}\right)",
        "text": f"{letter}({fmt_num(b.value, 3)}; {fmt_num(y_val, 3)})",
        "tex": pair_label(b, y_tex, y_val, letter),
    }


def _letters(n: int) -> list[str]:
    base = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return [base[i % 26] + (str(i // 26) if i >= 26 else "") for i in range(n)]


def _boundary_from(expr: sp.Expr) -> Boundary:
    return Boundary(to_float(expr), expr, True, False)


def _resolve_region(payload: dict, f: sp.Expr, g: sp.Expr, warnings: list[str]):
    mode = payload.get("mode", "manual")
    a_txt, b_txt = _clean(payload.get("a")), _clean(payload.get("b"))

    if mode == "manual" and bool(a_txt) != bool(b_txt):
        raise AreaError("bounds", "Hãy nhập đủ cả hai cận a và b, hoặc để trống cả hai để hệ thống tự tìm giao điểm.")
    if mode == "manual" and not a_txt:
        mode = "auto"
        warnings.append("Chưa nhập cận nên hệ thống tự tìm giao điểm và lấy các giao điểm làm cận.")

    if mode == "manual":
        lo, hi = parse_bound(a_txt), parse_bound(b_txt)
        if to_float(lo) > to_float(hi):
            lo, hi = hi, lo
            warnings.append("Cận a lớn hơn b nên hệ thống đã đổi chỗ hai cận.")
        if abs(to_float(hi) - to_float(lo)) < 1e-12:
            raise AreaError("no_region", MSG_NO_REGION, detail="a = b")
        return mode, lo, hi
    return "auto", None, None


def _solve(payload: dict, stage: _Stage) -> tuple[Solution, list[dict]]:
    warnings: list[str] = []
    stage.start("parse")
    f = parse_function(payload.get("f1", ""))
    g = parse_function(_clean(payload.get("f2")) or "0")
    is_ox = g == 0
    mode, lo_expr, hi_expr = _resolve_region(payload, f, g, warnings)
    stage.finish("parse")

    # ---- giao điểm
    stage.start("intersections")
    if mode == "manual":
        roots, identical = find_intersections(f, g, lo_expr, hi_expr)
    else:
        roots, identical = find_intersections(f, g)
    if identical:
        raise AreaError("identical", "Hai đồ thị trùng nhau nên không tạo thành miền hình phẳng (diện tích bằng 0).")
    if mode == "auto":
        if not roots:
            raise AreaError("no_intersection", MSG_NO_INTERSECTION)
        if len(roots) > MAX_ROOTS:
            raise AreaError("too_many", "Hai đồ thị có quá nhiều giao điểm (có thể vô hạn).\n"
                            "Hãy chuyển sang chế độ nhập cận a, b.")
        if len(roots) == 1:
            raise AreaError("no_region", MSG_NO_REGION, detail="Chỉ có một giao điểm nên chưa tạo thành miền kín")
    elif len(roots) > MAX_PIECES:
        raise AreaError("too_many", "Trong đoạn đã chọn có quá nhiều giao điểm.\nHãy chọn đoạn [a, b] ngắn hơn.")
    stage.finish("intersections")

    # ---- miền
    stage.start("region")
    if mode == "manual":
        lo_b, hi_b = _boundary_from(lo_expr), _boundary_from(hi_expr)
        inner = [r for r in roots if lo_b.value + 1e-9 < r.value < hi_b.value - 1e-9]
        inside = [r for r in roots if lo_b.value - 1e-9 <= r.value <= hi_b.value + 1e-9]
        breakpoints = [lo_b] + inner + [hi_b]
    else:
        lo_b, hi_b = roots[0], roots[-1]
        inside = roots
        breakpoints = roots
    check_domain(f, "f", lo_b.expr, hi_b.expr, lo_b.value, hi_b.value)
    check_domain(g, "g", lo_b.expr, hi_b.expr, lo_b.value, hi_b.value)
    pieces = build_pieces(f, g, breakpoints)
    if not pieces:
        raise AreaError("no_region", MSG_NO_REGION)
    # Có thể build_pieces đã thêm mốc mới (nghiệm bị bỏ sót): cập nhật danh sách mốc
    bps = [pieces[0].lo] + [p.hi for p in pieces]
    stage.finish("region")

    # ---- tích phân
    stage.start("integral")
    for p in pieces:
        integrate_piece(p, warnings)
    exact = all(p.exact for p in pieces)
    total_value = sum(p.area_value for p in pieces)
    if exact:
        try:
            total = sp.simplify(sum((p.area for p in pieces), sp.S.Zero))
        except Exception:
            total = sum((p.area for p in pieces), sp.S.Zero)
    else:
        total = sp.Float(total_value, 20)
        warnings.append("Kết quả là giá trị gần đúng vì có giao điểm/tích phân không biểu diễn được bằng công thức đóng.")
    if any(p.area_value < -1e-9 for p in pieces):
        warnings.append("Phát hiện diện tích âm ở một khoảng; hãy kiểm tra lại cận.")
    stage.finish("integral")

    sol = Solution(f=f, g=g, is_ox=is_ox, mode=mode, lo=bps[0], hi=bps[-1], intersections=inside,
                   breakpoints=bps, pieces=pieces, total=total, total_value=total_value,
                   exact=exact, warnings=warnings)
    return sol, [_root_info(f, b, L) for b, L in zip(inside, _letters(len(inside)))]


def calculate(payload: dict) -> dict:
    stage = _Stage()
    try:
        sol, points = _solve(payload, stage)

        stage.start("graph")
        view = graph_mod.compute_view(sol)
        graph_data = graph_mod.build_graph(sol, view, points)
        stage.finish("graph")

        stage.start("latex")
        tex_out = latex_generator.generate(sol, view, points)
        steps = steps_mod.build_steps(sol)
        stage.finish("latex")
    except AreaError as err:
        if err.stage is None:
            err.stage = stage.current
        err.done = None
        raise
    return _to_response(sol, points, graph_data, tex_out, steps, stage)


def _fn_info(text: str, expr: sp.Expr) -> dict:
    return {"input": text, "latex": tex(expr), "sympy": sp.sstr(expr)}


def _to_response(sol: Solution, points, graph_data, tex_out, steps, stage: _Stage) -> dict:
    intervals = []
    for i, p in enumerate(sol.pieces, 1):
        names = ("f", "g") if p.upper == "f" else ("g", "f")
        intervals.append({
            "index": i,
            "lo": {"latex": bound_latex(p.lo), "value": p.lo.value, "exact": p.lo.exact},
            "hi": {"latex": bound_latex(p.hi), "value": p.hi.value, "exact": p.hi.exact},
            "upper": names[0], "lower": names[1],
            "upper_latex": tex(p.upper_expr), "lower_latex": tex(p.lower_expr),
            "integrand_latex": tex(p.integrand),
            "integral_latex": rf"\int_{{{bound_latex(p.lo)}}}^{{{bound_latex(p.hi)}}}\left({diff_latex(p.upper_expr, p.lower_expr)}\right)dx",
            "area_latex": value_latex(p.area, p.exact, p.area_value),
            "area_decimal": fmt_num(p.area_value, 8),
            "exact": p.exact,
            "test": {"x": p.test_x, "f": p.test_f, "g": p.test_g},
        })
    total_latex = value_latex(sol.total, sol.exact, sol.total_value)
    pieces_formula = ("S=" + "+".join(f"S_{{{i}}}" for i in range(1, len(sol.pieces) + 1))) if len(sol.pieces) > 1 else None
    return {
        "ok": True,
        "mode": sol.mode,
        "is_ox": sol.is_ox,
        "functions": {"f": _fn_info("", sol.f), "g": _fn_info("", sol.g)},
        "bounds": {
            "a": {"latex": bound_latex(sol.lo), "value": sol.lo.value, "input": expr_to_input(sol.lo.expr) if sol.lo.exact else repr(sol.lo.value)},
            "b": {"latex": bound_latex(sol.hi), "value": sol.hi.value, "input": expr_to_input(sol.hi.expr) if sol.hi.exact else repr(sol.hi.value)},
        },
        "intersections": points,
        "breakpoints": [{"latex": bound_latex(b), "value": b.value, "exact": b.exact} for b in sol.breakpoints],
        "intervals": intervals,
        "area": sp.sstr(sol.total) if sol.exact else fmt_num(sol.total_value, 10),
        "area_latex": total_latex,
        "area_decimal": fmt_num(sol.total_value, 8),
        "area_value": sol.total_value,
        "exact": sol.exact,
        "integral_latex": steps_mod.abs_formula(sol),
        "pieces_formula_latex": pieces_formula,
        "graph_data": graph_data,
        "tikz_code": tex_out["tikz"],
        "pgfplots_code": tex_out["pgfplots"],
        "tex_document": tex_out["document"],
        "tex_document_tikz": tex_out.get("document_tikz"),
        "latex_note": tex_out["note"],
        "steps": steps,
        "warnings": sol.warnings,
        "pipeline": stage.done,
    }


def list_intersections(payload: dict) -> dict:
    """Chức năng 'Tự động tìm giao điểm': trả về các giao điểm để người dùng chọn làm cận."""
    stage = _Stage()
    try:
        f = parse_function(payload.get("f1", ""))
        g = parse_function(_clean(payload.get("f2")) or "0")
        roots, identical = find_intersections(f, g)
    except AreaError as err:
        if err.stage is None:
            err.stage = stage.current
        raise
    if identical:
        raise AreaError("identical", "Hai đồ thị trùng nhau nên không có giao điểm riêng lẻ.", stage="intersections")
    if not roots:
        raise AreaError("no_intersection", MSG_NO_INTERSECTION, stage="intersections")
    if len(roots) > MAX_ROOTS:
        raise AreaError("too_many", "Hai đồ thị có quá nhiều giao điểm (có thể vô hạn).\nHãy tự nhập cận a, b.",
                        stage="intersections")
    pts = [_root_info(f, b, L) for b, L in zip(roots, _letters(len(roots)))]
    return {"ok": True, "intersections": pts, "is_ox": g == 0,
            "suggested": {"a": pts[0]["x_input"], "b": pts[-1]["x_input"]} if len(pts) >= 2 else None}


def sample_curves(payload: dict) -> dict:
    """Lấy mẫu f, g trên [x0, x1] (dùng khi người học zoom/kéo đồ thị)."""
    import math
    f = parse_function(payload.get("f1", ""))
    g = parse_function(_clean(payload.get("f2")) or "0")
    try:
        x0, x1 = float(payload["x0"]), float(payload["x1"])
        y0, y1 = float(payload.get("y0", -10)), float(payload.get("y1", 10))
        n = int(payload.get("n", 1500))
    except (KeyError, TypeError, ValueError):
        raise AreaError("range", "Khoảng lấy mẫu không hợp lệ.")
    if not all(map(math.isfinite, (x0, x1, y0, y1))) or not x1 > x0 or (x1 - x0) > 1e7:
        raise AreaError("range", "Khoảng lấy mẫu không hợp lệ.")
    n = max(50, min(n, 3000))
    return {"ok": True, **graph_mod.sample_curves(f, g, x0, x1, y0, y1, n)}


def preview_function(payload: dict) -> dict:
    """Xem trước công thức ngay khi người học đang gõ: trả về LaTeX của biểu thức đã đọc."""
    text = payload.get("text", "")
    kind = payload.get("kind", "fn")
    expr = parse_bound(text) if kind == "bound" else parse_function(text)
    return {"ok": True, "latex": tex(expr), "sympy": sp.sstr(expr)}
