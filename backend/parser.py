"""Chuẩn hoá và đọc biểu thức người dùng nhập.

Mục tiêu: cho phép gõ tự nhiên (`2x+3`, `x^2`, `sinx`, `sqrt x`, `|x-1|`, `0,5x`)
nhưng vẫn an toàn: KHÔNG bao giờ eval chuỗi thô. Chuỗi được tách thành token,
mọi tên phải nằm trong danh sách cho phép, rồi mới chuyển cho SymPy.
"""
from __future__ import annotations

import re
from typing import NamedTuple

import sympy as sp
from sympy.parsing.sympy_parser import parse_expr, standard_transformations

from .errors import MSG_PARSE, AreaError

# Biến duy nhất của bài toán. `real=True` để SymPy hiểu sqrt(x**2) = |x|, giải trên R...
X = sp.Symbol("x", real=True)

MAX_LEN = 200
MAX_TOKENS = 150
MAX_EXPONENT_LITERAL = 100

_LG = sp.Lambda(sp.Symbol("t"), sp.log(sp.Symbol("t")) / sp.log(10))

# Tên hàm cho phép. Ghi chú: log và ln đều là logarit tự nhiên; lg là log cơ số 10.
_FUNCS = {
    "sin": sp.sin, "cos": sp.cos, "tan": sp.tan, "cot": sp.cot, "sec": sp.sec, "csc": sp.csc,
    "tg": sp.tan, "cotg": sp.cot,
    "asin": sp.asin, "acos": sp.acos, "atan": sp.atan,
    "arcsin": sp.asin, "arccos": sp.acos, "arctan": sp.atan, "arctg": sp.atan,
    "sinh": sp.sinh, "cosh": sp.cosh, "tanh": sp.tanh,
    "exp": sp.exp, "log": sp.log, "ln": sp.log, "lg": _LG,
    "sqrt": sp.sqrt, "cbrt": sp.cbrt, "abs": sp.Abs,
}
_CONSTS = {"pi": sp.pi, "e": sp.E}
_NAMES = set(_FUNCS) | set(_CONSTS) | {"x"}
_MAX_NAME = max(len(n) for n in _NAMES)

_LOCALS = {**_FUNCS, **_CONSTS, "x": X}
_GLOBALS = {
    "Integer": sp.Integer, "Float": sp.Float, "Rational": sp.Rational,
    "Symbol": sp.Symbol, "Function": sp.Function,
}

NUM, VAR, CONST, FUNC, OP, LP, RP, COMMA = "NUM", "VAR", "CONST", "FUNC", "OP", "LP", "RP", "COMMA"


class Tok(NamedTuple):
    kind: str
    text: str


def _fail(detail: str) -> AreaError:
    return AreaError("parse", MSG_PARSE, detail=detail)


# ---------------------------------------------------------------- chuẩn hoá chuỗi
_UNICODE = {
    "²": "**2", "³": "**3", "−": "-", "–": "-", "—": "-", "×": "*", "·": "*", "⋅": "*",
    "÷": "/", "√": "sqrt", "π": "pi", "^": "**", "（": "(", "）": ")",
}
_PREFIX = re.compile(r"^\s*(?:[fgy]\s*(?:\(\s*x\s*\))?\s*=)\s*")


def normalize(text: str) -> str:
    if not isinstance(text, str):
        raise _fail("Đầu vào không phải chuỗi")
    text = text.strip()
    if not text:
        raise _fail("Biểu thức rỗng")
    if len(text) > MAX_LEN:
        raise _fail("Biểu thức quá dài")
    text = text.lower()
    text = _PREFIX.sub("", text)  # cho phép dán "f(x)=x^2" hoặc "y=x^2"
    for k, v in _UNICODE.items():
        text = text.replace(k, v)
    # |u| -> abs(u)  (chỉ hỗ trợ một tầng, đủ dùng cho chương trình phổ thông)
    for _ in range(6):
        new = re.sub(r"\|([^|]*)\|", r"abs(\1)", text)
        if new == text:
            break
        text = new
    if "|" in text:
        raise _fail("Dấu | không cân đối")
    # Dấu phẩy thập phân kiểu Việt Nam: 0,5 -> 0.5 (bỏ qua nếu có log(a, b))
    if "log(" not in text:
        text = re.sub(r"(?<=\d),(?=\d)", ".", text)
    return text


_TOKEN_RE = re.compile(r"\s*(?:(\d+\.\d*|\.\d+|\d+)|([a-z]+)|(\*\*|[+\-*/])|(\()|(\))|(,))")


def _segment(name: str) -> list[str] | None:
    """Tách 'sinx' -> ['sin', 'x'], 'xsinx' -> ['x','sin','x']. Ưu tiên ít mảnh nhất."""
    if name in _NAMES:
        return [name]
    n = len(name)
    best: list[list[str] | None] = [None] * (n + 1)
    best[0] = []
    for i in range(1, n + 1):
        for j in range(max(0, i - _MAX_NAME), i):
            piece = name[j:i]
            if best[j] is not None and piece in _NAMES:
                cand = best[j] + [piece]
                if best[i] is None or len(cand) < len(best[i]):
                    best[i] = cand
    return best[n]


def tokenize(text: str) -> list[Tok]:
    toks: list[Tok] = []
    pos = 0
    while pos < len(text):
        m = _TOKEN_RE.match(text, pos)
        if not m or m.end() == pos:
            raise _fail(f"Ký tự không hợp lệ gần vị trí {pos}: {text[pos:pos + 5]!r}")
        pos = m.end()
        num, name, op, lp, rp, comma = m.groups()
        if num is not None:
            toks.append(Tok(NUM, num))
        elif name is not None:
            parts = _segment(name)
            if parts is None:
                raise _fail(f"Không nhận ra '{name}'")
            for p in parts:
                kind = VAR if p == "x" else CONST if p in _CONSTS else FUNC
                toks.append(Tok(kind, p))
        elif op is not None:
            toks.append(Tok(OP, op))
        elif lp is not None:
            toks.append(Tok(LP, "("))
        elif rp is not None:
            toks.append(Tok(RP, ")"))
        else:
            toks.append(Tok(COMMA, ","))
    if len(toks) > MAX_TOKENS:
        raise _fail("Biểu thức quá dài")
    return toks


# ---------------------------------------------------------------- hàm không ngoặc
def _match_paren(toks: list[Tok], i: int) -> int:
    depth = 0
    for j in range(i, len(toks)):
        if toks[j].kind == LP:
            depth += 1
        elif toks[j].kind == RP:
            depth -= 1
            if depth == 0:
                return j
    raise _fail("Thiếu dấu đóng ngoặc")


def _read_atom(toks: list[Tok], i: int, allow_sign: bool = False) -> tuple[list[Tok], int]:
    """Đọc một 'nguyên tử': số, biến, hằng, nhóm ngoặc hoặc lời gọi hàm không ngoặc."""
    if i >= len(toks):
        raise _fail("Thiếu đối số của hàm")
    t = toks[i]
    if allow_sign and t.kind == OP and t.text in "+-":
        atom, j = _read_atom(toks, i + 1)
        return [t] + atom, j
    if t.kind == LP:
        j = _match_paren(toks, i)
        inner = _apply_functions(toks[i + 1:j])
        return [t] + inner + [toks[j]], j + 1
    if t.kind in (NUM, VAR, CONST):
        return [t], i + 1
    if t.kind == FUNC:
        return _read_func(toks, i)
    raise _fail("Biểu thức không hợp lệ")


def _read_arg(toks: list[Tok], i: int) -> tuple[list[Tok], int]:
    """Đối số của hàm viết không ngoặc: `sin 2x`, `sqrt x`, `cos x^2`."""
    atom, j = _read_atom(toks, i)
    out = list(atom)
    while j < len(toks):
        t = toks[j]
        if t.kind == OP and t.text == "**":
            exp, j = _read_atom(toks, j + 1, allow_sign=True)
            out += [t] + exp
        elif t.kind in (VAR, CONST) and out[-1].kind in (NUM, VAR, CONST):
            out.append(t)
            j += 1
        else:
            break
    return out, j


def _read_func(toks: list[Tok], i: int) -> tuple[list[Tok], int]:
    fn = toks[i]
    j = i + 1
    if j < len(toks) and toks[j].kind == LP:  # sin(...) - dạng chuẩn
        k = _match_paren(toks, j)
        inner = _apply_functions(toks[j + 1:k])
        return [fn, toks[j]] + inner + [toks[k]], k + 1
    exp: list[Tok] = []
    if j < len(toks) and toks[j].kind == OP and toks[j].text == "**":  # sin^2 x
        exp, j = _read_atom(toks, j + 1, allow_sign=True)
    arg, j = _read_arg(toks, j)
    group = [fn, Tok(LP, "(")] + arg + [Tok(RP, ")")]
    if exp:
        group = [Tok(LP, "(")] + group + [Tok(RP, ")"), Tok(OP, "**")] + exp
    return group, j


def _apply_functions(toks: list[Tok]) -> list[Tok]:
    out: list[Tok] = []
    i = 0
    while i < len(toks):
        if toks[i].kind == FUNC:
            group, i = _read_func(toks, i)
            out.extend(group)
        elif toks[i].kind == LP:
            j = _match_paren(toks, i)
            out += [toks[i]] + _apply_functions(toks[i + 1:j]) + [toks[j]]
            i = j + 1
        else:
            out.append(toks[i])
            i += 1
    return out


# ---------------------------------------------------------------- nhân ngầm
def _needs_mul(a: Tok, b: Tok) -> bool:
    left = a.kind in (NUM, VAR, CONST, RP)
    right = b.kind in (VAR, CONST, FUNC, LP) or (b.kind == NUM and a.kind != NUM)
    return left and right


def _insert_mult(toks: list[Tok]) -> list[Tok]:
    out: list[Tok] = []
    for t in toks:
        if out and _needs_mul(out[-1], t):
            out.append(Tok(OP, "*"))
        out.append(t)
    return out


def _guard(toks: list[Tok]) -> None:
    """Chặn các biểu thức có thể làm treo máy chủ (tháp luỹ thừa, số mũ khổng lồ)."""
    for i, t in enumerate(toks):
        if t.kind == OP and t.text == "**" and i + 1 < len(toks) and toks[i + 1].kind == NUM:
            try:
                if float(toks[i + 1].text) > MAX_EXPONENT_LITERAL:
                    raise _fail("Số mũ quá lớn")
            except ValueError:
                raise _fail("Số mũ không hợp lệ")
        if (t.kind == OP and t.text == "**" and 1 <= i and i + 3 < len(toks)
                and toks[i - 1].kind == NUM and toks[i + 1].kind == NUM
                and toks[i + 2].text == "**" and toks[i + 3].kind == NUM):
            raise _fail("Tháp luỹ thừa số quá lớn")
    if len(toks) and toks[-1].kind in (OP, COMMA):
        raise _fail("Biểu thức kết thúc bằng toán tử")


def _to_source(toks: list[Tok]) -> str:
    parts = []
    for t in toks:
        if t.kind == NUM and "." in t.text:
            parts.append(f"Rational('{t.text}')")  # giữ chính xác 0.5 = 1/2
        else:
            parts.append(t.text)
    return " ".join(parts)


# ---------------------------------------------------------------- API công khai
def _parse(text: str) -> sp.Expr:
    toks = tokenize(normalize(text))
    toks = _insert_mult(_apply_functions(toks))
    _guard(toks)
    source = _to_source(toks)
    try:
        expr = parse_expr(
            source,
            local_dict=dict(_LOCALS),
            global_dict=dict(_GLOBALS),
            transformations=standard_transformations,
            evaluate=True,
        )
    except AreaError:
        raise
    except MemoryError:
        raise _fail("Biểu thức quá lớn")
    except Exception as exc:  # SyntaxError, TypeError, ...
        raise _fail(f"{type(exc).__name__}: {exc}") from exc
    expr = sp.sympify(expr)
    if not isinstance(expr, sp.Expr):
        raise _fail("Kết quả không phải biểu thức số")
    if expr.has(sp.I) or expr.has(sp.zoo) or expr.has(sp.nan) or expr.has(sp.oo) or expr.has(-sp.oo):
        raise _fail("Biểu thức chứa số phức hoặc giá trị vô hạn")
    return expr


def parse_function(text: str) -> sp.Expr:
    """Đọc hàm số y = f(x). Chỉ cho phép biến x."""
    expr = _parse(text)
    extra = expr.free_symbols - {X}
    if extra:
        names = ", ".join(sorted(str(s) for s in extra))
        raise _fail(f"Biến lạ: {names}")
    return expr


def parse_bound(text: str) -> sp.Expr:
    """Đọc một cận tích phân: số thực như -3, 1/2, pi/2, sqrt(2), e."""
    expr = _parse(text)
    if expr.free_symbols:
        raise AreaError("bound", "Cận tích phân phải là một số thực (ví dụ -3, 1/2, pi/2).",
                        detail="Cận chứa biến x")
    try:
        val = complex(sp.N(expr, 30))
    except (TypeError, ValueError):
        raise AreaError("bound", "Cận tích phân phải là một số thực (ví dụ -3, 1/2, pi/2).")
    if abs(val.imag) > 1e-12:
        raise AreaError("bound", "Cận tích phân phải là một số thực (ví dụ -3, 1/2, pi/2).")
    return expr


def expr_to_input(expr: sp.Expr) -> str:
    """Chuỗi có thể nhập lại vào ô nhập liệu (dùng khi bấm chọn giao điểm làm cận)."""
    return sp.sstr(expr)
