"""Sinh lời giải từng bước (Tab 'Các bước giải').

Mỗi bước gồm: tiêu đề, đề bài gợi ý (prompt), gợi ý (hint) và lời giải (blocks).
Chế độ học tập chỉ hiện prompt trước; hint và lời giải mở dần theo yêu cầu.
Chuỗi văn bản có thể chứa $...$ (công thức nội dòng) - frontend hiển thị bằng KaTeX.
"""
from __future__ import annotations

import sympy as sp

from .formatting import bound_latex, diff_latex, tex, value_latex
from .models import Solution
from .numeric import fmt_num


def T(content: str) -> dict:
    return {"type": "text", "content": content}


def M(content: str) -> dict:
    return {"type": "math", "content": content}


def _abs_formula(sol: Solution) -> str:
    a, b = bound_latex(sol.lo), bound_latex(sol.hi)
    inner = tex(sol.f) if sol.is_ox else diff_latex(sol.f, sol.g)
    return rf"S=\int_{{{a}}}^{{{b}}}\left|{inner}\right|\,dx"


def abs_formula(sol: Solution) -> str:
    return _abs_formula(sol)


def build_steps(sol: Solution) -> list[dict]:
    steps: list[dict] = []
    F, G = tex(sol.f), tex(sol.g)
    a, b = bound_latex(sol.lo), bound_latex(sol.hi)
    approx_any = any(not r.exact for r in sol.intersections)

    # ---- Bước 1: giao điểm
    h = sp.simplify(sol.f - sol.g)
    eq = rf"{F}=0" if sol.is_ox else rf"{F}={G}"
    blocks = [T("Hoành độ giao điểm là nghiệm của phương trình:"), M(eq)]
    if not sol.is_ox and h != 0:
        blocks.append(M(rf"\iff {tex(h)}=0"))
    if sol.mode == "manual":
        blocks.append(T(f"Cận đã cho là $a={a}$ và $b={b}$ nên chỉ xét các nghiệm thuộc $[a;\\,b]$."))
    if sol.intersections:
        roots = r",\qquad ".join(rf"x={bound_latex(r)}" for r in sol.intersections)
        blocks.append(T("Các nghiệm tìm được:"))
        blocks.append(M(roots))
        if approx_any:
            blocks.append(T("Có nghiệm không biểu diễn được bằng công thức đóng, hệ thống dùng nghiệm gần đúng (30 chữ số thập phân)."))
    else:
        blocks.append(T("Phương trình không có nghiệm trong đoạn này, nên hai đồ thị không cắt nhau trên $[a;\\,b]$."))
    steps.append({
        "id": "s1",
        "title": "Bước 1. Tìm giao điểm với trục Ox" if sol.is_ox else "Bước 1. Tìm giao điểm của hai đồ thị",
        "prompt": "Giải phương trình $f(x)=0$ để tìm hoành độ giao điểm." if sol.is_ox
        else "Giải phương trình $f(x)=g(x)$ để tìm hoành độ giao điểm của hai đồ thị.",
        "hint": "Chuyển vế để được $f(x)-g(x)=0$, giải phương trình rồi kiểm tra nghiệm thuộc tập xác định.",
        "blocks": blocks,
    })

    # ---- Bước 2: miền
    pts = " < ".join(bound_latex(p) for p in sol.breakpoints)
    blocks = [M(rf"{a}\le x\le {b}")]
    if sol.mode == "auto":
        blocks.insert(0, T("Không cho cận nên miền được giới hạn bởi các giao điểm ngoài cùng của hai đồ thị."))
    if len(sol.breakpoints) > 2:
        blocks.append(T("Các giao điểm nằm trong miền chia đoạn này thành các khoảng nhỏ; các mốc chia miền là:"))
        blocks.append(M(pts))
    steps.append({
        "id": "s2", "title": "Bước 2. Xác định miền cần tính",
        "prompt": "Xác định đoạn $[a;\\,b]$ và các mốc chia miền.",
        "hint": "Các mốc chia miền gồm hai cận và mọi giao điểm nằm giữa chúng, sắp xếp tăng dần.",
        "blocks": blocks,
    })

    # ---- Bước 3: hàm trên / dưới
    blocks = []
    for i, p in enumerate(sol.pieces, 1):
        lo, hi = bound_latex(p.lo), bound_latex(p.hi)
        blocks.append(T(
            f"Khoảng {i}: $[{lo};\\,{hi}]$. Lấy $x_0={fmt_num(p.test_x, 4)}$ thì "
            f"$f(x_0)={fmt_num(p.test_f, 4)}$, $g(x_0)={fmt_num(p.test_g, 4)}$."))
        if sol.is_ox:
            blocks.append(M(r"f(x)\ge 0" if p.upper == "f" else r"f(x)\le 0"))
            blocks.append(T("Đồ thị nằm phía trên trục Ox." if p.upper == "f" else "Đồ thị nằm phía dưới trục Ox."))
        else:
            blocks.append(M(r"f(x)\ge g(x)" if p.upper == "f" else r"g(x)\ge f(x)"))
    steps.append({
        "id": "s3",
        "title": "Bước 3. Xác định hàm trên và hàm dưới",
        "prompt": "Trên từng khoảng, đồ thị nào nằm phía trên?",
        "hint": "Trên mỗi khoảng $f(x)-g(x)$ không đổi dấu, nên chỉ cần thử một điểm bất kỳ của khoảng.",
        "blocks": blocks,
    })

    # ---- Bước 4: lập tích phân
    blocks = [M(_abs_formula(sol))]
    if len(sol.pieces) == 1:
        p = sol.pieces[0]
        blocks.append(T("Vì trên đoạn này một hàm luôn nằm trên hàm còn lại nên có thể bỏ dấu giá trị tuyệt đối:"))
        blocks.append(M(rf"S=\int_{{{bound_latex(p.lo)}}}^{{{bound_latex(p.hi)}}}\left({diff_latex(p.upper_expr, p.lower_expr)}\right)dx"))
    else:
        blocks.append(T("Tách theo các mốc chia miền để bỏ dấu giá trị tuyệt đối:"))
        blocks.append(M("S=" + "+".join(f"S_{{{i}}}" for i in range(1, len(sol.pieces) + 1))))
        for i, p in enumerate(sol.pieces, 1):
            blocks.append(M(rf"S_{{{i}}}=\int_{{{bound_latex(p.lo)}}}^{{{bound_latex(p.hi)}}}\left({diff_latex(p.upper_expr, p.lower_expr)}\right)dx"))
    steps.append({
        "id": "s4", "title": "Bước 4. Lập tích phân",
        "prompt": "Viết công thức diện tích bằng tích phân (chú ý bỏ dấu giá trị tuyệt đối).",
        "hint": "$S=\\int_a^b [f_{\\text{trên}}(x)-f_{\\text{dưới}}(x)]\\,dx$ trên từng khoảng.",
        "blocks": blocks,
    })

    # ---- Bước 5: tính
    blocks = []
    many = len(sol.pieces) > 1
    for i, p in enumerate(sol.pieces, 1):
        name = f"S_{{{i}}}" if many else "S"
        lo, hi = bound_latex(p.lo), bound_latex(p.hi)
        val = value_latex(p.area, p.exact, p.area_value)
        integral = rf"\int_{{{lo}}}^{{{hi}}}\left({tex(p.integrand)}\right)dx"
        if p.exact and p.antiderivative is not None:
            blocks.append(M(rf"\int \left({tex(p.integrand)}\right)dx={tex(p.antiderivative)}+C"))
            blocks.append(M(rf"{name}={integral}={val}"))
        elif p.exact:
            blocks.append(M(rf"{name}={integral}={val}"))
        else:
            blocks.append(M(rf"{name}={integral}\approx {val}"))
            blocks.append(T("Tích phân này không có nguyên hàm sơ cấp hoặc có cận gần đúng nên được tính bằng phương pháp số."))
    total = value_latex(sol.total, sol.exact, sol.total_value)
    if many:
        sums = "+".join(f"S_{{{i}}}" for i in range(1, len(sol.pieces) + 1))
        blocks.append(M(rf"S={sums}=\boxed{{{total}}}" if sol.exact else rf"S={sums}\approx\boxed{{{total}}}"))
    else:
        blocks.append(M(rf"S=\boxed{{{total}}}" if sol.exact else rf"S\approx\boxed{{{total}}}"))
    if sol.exact:
        blocks.append(T(f"Giá trị thập phân: $S\\approx {fmt_num(sol.total_value, 6)}$ (đơn vị diện tích)."))
    steps.append({
        "id": "s5", "title": "Bước 5. Tính kết quả",
        "prompt": "Tính từng tích phân rồi cộng lại.",
        "hint": "Tìm nguyên hàm $F(x)$, tính $F(b)-F(a)$ trên từng khoảng, cuối cùng cộng các diện tích.",
        "blocks": blocks,
    })
    return steps
