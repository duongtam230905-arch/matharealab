"""Sinh mã LaTeX (PGFPlots và TikZ thuần) cho hình miền phẳng.

Bảng màu và tiền đề dùng pdflatex + gói vietnam (hỗ trợ tiếng Việt), phông Times (mathptmx).
Hình chỉ chứa công thức nên không phụ thuộc vào phông chữ tiếng Việt.
"""
from __future__ import annotations

import sympy as sp

from .graph import defined_range, nice_bounds, nice_step
from .models import Solution
from .numeric import fmt_num, numeric_fn
from .parser import X


class LatexUnsupported(Exception):
    """Biểu thức có hàm chưa thể chuyển sang cú pháp toán của pgf."""


# --------------------------------------------------------------------------- bộ in biểu thức pgf
class PgfPrinter:
    """Chuyển biểu thức SymPy sang cú pháp toán của PGF/TikZ.

    - pgfplots: dùng `trig format plots=rad`, nên sin(x) giữ nguyên.
    - tikz: sin/cos/tan mặc định theo độ, phải viết sin((u) r).
    - asin/acos/atan của pgf trả về độ nên bọc rad(...).
    Mọi mảng con đều được đóng ngoặc để không phụ thuộc thứ tự ưu tiên toán tử.
    """

    def __init__(self, tikz: bool):
        self.tikz = tikz
        self.var = r"\x" if tikz else "x"

    def __call__(self, e: sp.Expr) -> str:
        if e == X or (e.is_Symbol and e.name == "x"):
            return self.var
        if e.is_Integer:
            return str(int(e)) if e >= 0 else f"({int(e)})"
        if e.is_Rational:
            return f"({e.p}/{e.q})"
        if e.is_Float:
            return f"({float(e):.10g})"
        if e == sp.pi:
            return "pi"
        if e == sp.E:
            return "e"
        if e.is_Add:
            return self._add(e)
        if e.is_Mul:
            return self._mul(e)
        if e.is_Pow:
            return self._pow(e)
        return self._func(e)

    def _add(self, e):
        terms = sp.Add.make_args(e)
        out = ""
        for i, t in enumerate(terms):
            neg = t.could_extract_minus_sign()
            s = self(-t) if neg else self(t)
            if i == 0:
                out = f"-{s}" if neg else s
            else:
                out += f" - {s}" if neg else f" + {s}"
        return f"({out})"

    def _prod(self, n):
        c, rest = n.as_coeff_Mul()
        parts = []
        if c not in (1, -1):
            parts.append(self(c))
        if rest != 1:
            parts.extend(self(a) for a in sp.Mul.make_args(rest))
        s = "*".join(parts) if parts else "1"
        return f"-{s}" if c == -1 else s

    def _mul(self, e):
        n, d = sp.fraction(e)
        ns = self._prod(n)
        if d == 1:
            return f"({ns})"
        return f"(({ns})/({self(d)}))"

    def _pow(self, e):
        base, ex = e.as_base_exp()
        if base == sp.E:
            return f"exp({self(ex)})"
        if ex == sp.S.Half:
            return f"sqrt({self(base)})"
        if ex == -sp.S.Half:
            return f"(1/sqrt({self(base)}))"
        if ex.is_Integer and ex < 0:
            return f"(1/({self(sp.Pow(base, -ex))}))"
        if ex.is_Integer:
            return f"({self(base)})^{int(ex)}"
        return f"({self(base)})^({self(ex)})"

    def _trig(self, name, arg):
        a = self(arg)
        return f"{name}(({a}) r)" if self.tikz else f"{name}({a})"

    def _func(self, e):
        f = e.func
        if f in (sp.sin, sp.cos, sp.tan):
            return self._trig(f.__name__, e.args[0])
        if f == sp.cot:
            return f"(1/{self._trig('tan', e.args[0])})"
        if f == sp.sec:
            return f"(1/{self._trig('cos', e.args[0])})"
        if f == sp.csc:
            return f"(1/{self._trig('sin', e.args[0])})"
        if f in (sp.asin, sp.acos, sp.atan):
            return f"rad({f.__name__}({self(e.args[0])}))"
        if f in (sp.sinh, sp.cosh, sp.tanh):
            return f"{f.__name__}({self(e.args[0])})"
        if f == sp.exp:
            return f"exp({self(e.args[0])})"
        if f == sp.log and len(e.args) == 1:
            return f"ln({self(e.args[0])})"
        if f == sp.Abs:
            return f"abs({self(e.args[0])})"
        raise LatexUnsupported(str(e))


# --------------------------------------------------------------------------- hằng và tiền đề
COLORS = r"""\definecolor{navy}{HTML}{1C2E58}
\definecolor{navylight}{HTML}{A9B8CE}
\definecolor{shadowgray}{HTML}{D7D7D7}
\definecolor{curvef}{HTML}{1E4FD6}
\definecolor{curveg}{HTML}{EB5A2A}"""

REQ_PGFPLOTS = r"""% Cần trong phần tiền đề (preamble):
%   \usepackage{tikz}
%   \usepackage{pgfplots}
%   \pgfplotsset{compat=1.18}
%   \usepgfplotslibrary{fillbetween}"""

REQ_TIKZ = r"""% Cần trong phần tiền đề (preamble):
%   \usepackage{tikz}"""

PREAMBLE = r"""\documentclass[border=10pt]{standalone}
\usepackage[utf8]{vietnam}
\usepackage{mathptmx}
\usepackage{amsmath}
\usepackage{tikz}
\usetikzlibrary{calc}
\usepackage{pgfplots}
\pgfplotsset{compat=1.18}
\usepgfplotslibrary{fillbetween}
"""


def n(v: float) -> str:
    return fmt_num(float(v), 5)


def _ticks(lo: float, hi: float, step: float) -> list[str]:
    out = []
    k = int(round(lo / step))
    while k * step <= hi + 1e-9:
        v = k * step
        if abs(v) > 1e-9:
            out.append(n(v))
        k += 1
    return out


def _lbl(text: str) -> str:
    return text


# --------------------------------------------------------------------------- PGFPlots
def pgfplots_code(sol: Solution, view: dict, points: list[dict]) -> str:
    pr = PgfPrinter(tikz=False)
    fe, ge = pr(sol.f), pr(sol.g)

    sx = nice_step(view["xmax"] - view["xmin"])
    sy = nice_step(view["ymax"] - view["ymin"])
    xmin, xmax = nice_bounds(view["xmin"], view["xmax"], sx)
    ymin, ymax = nice_bounds(view["ymin"], view["ymax"], sy)
    yr = ymax - ymin
    fd = defined_range(numeric_fn(sol.f), xmin, xmax)
    gd = defined_range(numeric_fn(sol.g), xmin, xmax)

    L = [REQ_PGFPLOTS, COLORS, r"\begin{tikzpicture}", r"\begin{axis}["]
    opts = [
        "width=11cm, height=8cm",
        "axis lines=middle, axis line style={navy, thick}",
        "xlabel={$x$}, ylabel={$y$}",
        "xlabel style={at={(current axis.right of origin)}, anchor=west}",
        "ylabel style={at={(current axis.above origin)}, anchor=south}",
        f"xmin={n(xmin)}, xmax={n(xmax)}, ymin={n(ymin)}, ymax={n(ymax)}",
        f"xtick distance={n(sx)}, ytick distance={n(sy)}",
        "grid=major, grid style={shadowgray, very thin}",
        "trig format plots=rad",
        "samples=300",
        "unbounded coords=jump",
        f"restrict y to domain={n(ymin - yr)}:{n(ymax + yr)}",
        "legend pos=north east, legend style={draw=none, fill=white, fill opacity=0.85, text opacity=1, font=\\small}",
    ]
    L.append("    " + ",\n    ".join(opts) + ",")
    L.append("]")

    L.append("% --- Đồ thị hai hàm số ---")
    L.append(f"\\addplot[name path=F, curvef, very thick, domain={n(fd[0])}:{n(fd[1])}] {{{fe}}};")
    L.append("\\addlegendentry{$y=f(x)$}")
    L.append(f"\\addplot[name path=G, curveg, very thick, domain={n(gd[0])}:{n(gd[1])}] {{{ge}}};")
    L.append("\\addlegendentry{$y=g(x)$}" if not sol.is_ox else "\\addlegendentry{$y=0$}")

    L.append("% --- Miền hình phẳng ---")
    for p in sol.pieces:
        L.append("\\addplot[navylight, fill=navylight, fill opacity=0.6, draw=none, forget plot] "
                 f"fill between[of=F and G, soft clip={{domain={n(p.lo.value)}:{n(p.hi.value)}}}];")

    L.append("% --- Các đường x = a, x = b ---")
    for v in (sol.lo, sol.hi):
        top = _top_y(sol, v.value)
        L.append(f"\\draw[dashed, navy, thick] (axis cs:{n(v.value)},0) -- (axis cs:{n(v.value)},{n(top)});")
    if sol.mode == "manual":
        L.append(f"\\node[above left, font=\\small, navy] at (axis cs:{n(sol.lo.value)},0) {{$a$}};")
        L.append(f"\\node[above right, font=\\small, navy] at (axis cs:{n(sol.hi.value)},0) {{$b$}};")

    if points:
        L.append("% --- Giao điểm ---")
    for i, pt in enumerate(points):
        pos = "above left" if i % 2 else "above right"
        L.append(f"\\node[circle, fill=navy, inner sep=1.6pt] at (axis cs:{n(pt['x'])},{n(pt['y'])}) {{}};")
        L.append(f"\\node[{pos}, font=\\footnotesize, navy, fill=white, fill opacity=0.8, text opacity=1, inner sep=1.5pt] at (axis cs:{n(pt['x'])},{n(pt['y'])}) {{${pt['tex']}$}};")

    L += [r"\end{axis}", r"\end{tikzpicture}"]
    return "\n".join(L) + "\n"


def _top_y(sol: Solution, x: float) -> float:
    ys = [float(numeric_fn(e)(__import__("numpy").array([x]))[0]) for e in (sol.f, sol.g)]
    return max(ys + [0.0], key=abs)


# --------------------------------------------------------------------------- TikZ thuần
def tikz_code(sol: Solution, view: dict, points: list[dict]) -> str:
    pr = PgfPrinter(tikz=True)
    fe, ge = pr(sol.f), pr(sol.g)

    sx = nice_step(view["xmax"] - view["xmin"])
    sy = nice_step(view["ymax"] - view["ymin"])
    xmin, xmax = nice_bounds(view["xmin"], view["xmax"], sx)
    ymin, ymax = nice_bounds(view["ymin"], view["ymax"], sy)
    ux = min(max(11.0 / (xmax - xmin), 0.25), 3.0)
    uy = min(max(7.5 / (ymax - ymin), 0.25), 3.0)
    yhi, ylo = n(ymax + sy), n(ymin - sy)

    def clamp(e: str) -> str:  # tránh lỗi "Dimension too large" ở gần tiệm cận
        return f"max(min({e}, {yhi}), {ylo})"

    fd = defined_range(numeric_fn(sol.f), xmin, xmax)
    gd = defined_range(numeric_fn(sol.g), xmin, xmax)

    L = [REQ_TIKZ, COLORS, f"\\begin{{tikzpicture}}[x={n(ux)}cm, y={n(uy)}cm, line cap=round, line join=round]"]
    L.append("  % Lưới")
    L.append(f"  \\draw[shadowgray, very thin, xstep={n(sx)}, ystep={n(sy)}] ({n(xmin)},{n(ymin)}) grid ({n(xmax)},{n(ymax)});")
    L.append("  \\begin{scope}")
    L.append(f"    \\clip ({n(xmin)},{n(ymin)}) rectangle ({n(xmax)},{n(ymax)});")
    L.append("    % Miền hình phẳng")
    for p in sol.pieces:
        up, low = pr(p.upper_expr), pr(p.lower_expr)
        a, b = n(p.lo.value), n(p.hi.value)
        L.append(f"    \\fill[navylight, fill opacity=0.6] plot[domain={a}:{b}, samples=120] (\\x, {{{clamp(up)}}})")
        L.append(f"      -- plot[domain={b}:{a}, samples=120] (\\x, {{{clamp(low)}}}) -- cycle;")
    L.append("    % Đồ thị")
    L.append(f"    \\draw[curvef, very thick, domain={n(fd[0])}:{n(fd[1])}, samples=300] plot (\\x, {{{clamp(fe)}}});")
    L.append(f"    \\draw[curveg, very thick, domain={n(gd[0])}:{n(gd[1])}, samples=300] plot (\\x, {{{clamp(ge)}}});")
    L.append("  \\end{scope}")
    L.append("  % Trục tọa độ")
    L.append(f"  \\draw[->, navy, thick] ({n(xmin)},0) -- ({n(xmax)},0) node[right] {{$x$}};")
    L.append(f"  \\draw[->, navy, thick] (0,{n(ymin)}) -- (0,{n(ymax)}) node[above] {{$y$}};")
    L.append("  \\node[below left, font=\\small, navy] at (0,0) {$O$};")
    xt, yt = _ticks(xmin, xmax, sx), _ticks(ymin, ymax, sy)
    L.append(f"  \\foreach \\t in {{{','.join(xt)}}} \\draw[navy] (\\t,2pt) -- (\\t,-2pt) node[below, font=\\footnotesize] {{$\\t$}};")
    L.append(f"  \\foreach \\t in {{{','.join(yt)}}} \\draw[navy] (2pt,\\t) -- (-2pt,\\t) node[left, font=\\footnotesize] {{$\\t$}};")
    L.append("  % Các đường x = a, x = b")
    for v in (sol.lo, sol.hi):
        L.append(f"  \\draw[dashed, navy, thick] ({n(v.value)},0) -- ({n(v.value)},{n(_top_y(sol, v.value))});")
    if sol.mode == "manual":
        L.append(f"  \\node[above left, font=\\small, navy] at ({n(sol.lo.value)},0) {{$a$}};")
        L.append(f"  \\node[above right, font=\\small, navy] at ({n(sol.hi.value)},0) {{$b$}};")
    if points:
        L.append("  % Giao điểm")
    for i, pt in enumerate(points):
        pos = "above left" if i % 2 else "above right"
        L.append(f"  \\fill[navy] ({n(pt['x'])},{n(pt['y'])}) circle (1.8pt);")
        L.append(f"  \\node[{pos}, font=\\footnotesize, navy, fill=white, fill opacity=0.8, text opacity=1, inner sep=1.5pt] at ({n(pt['x'])},{n(pt['y'])}) {{${pt['tex']}$}};")
    gname = "$y=0$" if sol.is_ox else "$y=g(x)$"
    L.append(f"  \\node[anchor=north west, align=left, font=\\small, fill=white, fill opacity=0.85, text opacity=1, inner sep=3pt] "
             f"at ({n(xmin)},{n(ymax)}) {{\\textcolor{{curvef}}{{$y=f(x)$}}\\\\ \\textcolor{{curveg}}{{{gname}}}}};")
    L.append(r"\end{tikzpicture}")
    return "\n".join(L) + "\n"


def full_document(picture: str) -> str:
    """Tài liệu standalone biên dịch được bằng pdflatex (Overleaf: chọn compiler pdfLaTeX)."""
    return PREAMBLE + "\\begin{document}\n" + picture + "\\end{document}\n"


def generate(sol: Solution, view: dict, points: list[dict]) -> dict:
    """Trả về mã LaTeX; nếu hàm chưa hỗ trợ xuất TikZ thì trả về None kèm ghi chú."""
    try:
        pgf = pgfplots_code(sol, view, points)
        tikz = tikz_code(sol, view, points)
    except LatexUnsupported as exc:
        return {"pgfplots": None, "tikz": None, "document": None, "note": f"Chưa hỗ trợ xuất TikZ cho biểu thức: {exc}"}
    return {"pgfplots": pgf, "tikz": tikz, "document": full_document(pgf), "document_tikz": full_document(tikz), "note": None}
