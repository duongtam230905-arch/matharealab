"""Bộ hướng dẫn gõ hàm số.

Cột "hiển thị" được TÍNH bằng chính bộ đọc biểu thức của hệ thống (parser.py),
nên hướng dẫn không bao giờ lệch so với cách web thực sự hiểu.
"""
from __future__ import annotations

from functools import lru_cache

import sympy as sp

from .formatting import tex
from .parser import parse_function

_GROUPS = [
    ("Phép tính cơ bản", [
        ("2*x+3", "Dấu * là phép nhân."),
        ("2x+3", "Số viết liền biến cũng được hiểu là nhân, có thể bỏ dấu *."),
        ("x/2", "Dấu / là phép chia."),
        ("(x+1)/(x-2)", "Tử hoặc mẫu có nhiều số hạng thì phải đặt trong ngoặc."),
        ("(x+1)(x-1)", "Hai ngoặc đứng cạnh nhau là nhân."),
    ]),
    ("Luỹ thừa", [
        ("x^2", "Dấu ^ là mũ: x^2 nghĩa là x bình phương."),
        ("x**2", "Dấu ** cũng là mũ (cách viết của Python), kết quả giống x^2."),
        ("x^3-2x+1", "Đa thức bậc ba."),
        ("x^(1/2)", "Số mũ là phân số hoặc nhiều ký tự thì đặt trong ngoặc."),
        ("2^x", "Hàm mũ cơ số 2."),
        ("e^x", "Hàm mũ cơ số e (số Euler)."),
    ]),
    ("Căn và giá trị tuyệt đối", [
        ("sqrt(x)", "Căn bậc hai. Luôn có ngoặc: sqrt(x)."),
        ("sqrt(4-x^2)", "Biểu thức dưới căn đặt trong ngoặc."),
        ("|x-1|", "Giá trị tuyệt đối viết bằng hai gạch đứng."),
        ("abs(x-1)", "Hoặc dùng abs(...), kết quả giống nhau."),
    ]),
    ("Lượng giác (đơn vị radian)", [
        ("sin(x)", "sin, cos, tan, cot; góc tính bằng radian."),
        ("cos(2x)", "Đối số có nhiều ký tự thì đặt trong ngoặc."),
        ("sin(x)^2", "Bình phương của sin x."),
        ("tan(x)", "Tiếp tuyến; đồ thị có tiệm cận đứng."),
        ("sin(pi*x)", "pi là số π ≈ 3,14159."),
    ]),
    ("Mũ và logarit", [
        ("exp(x)", "Hàm mũ e^x."),
        ("ln(x)", "Logarit tự nhiên (cơ số e)."),
        ("log(x)", "Cũng là logarit tự nhiên, giống ln(x)."),
        ("lg(x)", "Logarit thập phân (cơ số 10)."),
        ("log(x)/log(2)", "Logarit cơ số 2: dùng công thức đổi cơ số."),
    ]),
    ("Hằng số", [
        ("pi", "Số π."),
        ("2*pi", "Dùng được cả trong ô cận, ví dụ b = 2*pi."),
        ("e", "Số e ≈ 2,71828."),
    ]),
]

# (gõ, giải thích, cách gõ đúng nếu muốn nghĩa khác)
_MISTAKES = [
    ("x2", "x2 được hiểu là x nhân 2, không phải x bình phương.", "x^2"),
    ("1/2x", "Được hiểu là (1/2)·x. Muốn 1/(2x) thì phải đặt ngoặc.", "1/(2x)"),
    ("sin x^2", "Được hiểu là sin(x²). Muốn (sin x)² thì viết sin(x)^2.", "sin(x)^2"),
    ("e^2x", "Được hiểu là e²·x. Muốn e mũ 2x thì đặt ngoặc.", "e^(2x)"),
    ("2^x+1", "Cộng 1 sau khi tính 2^x. Muốn 2^(x+1) thì đặt ngoặc.", "2^(x+1)"),
]

TIPS = [
    "Ô cận a, b cũng gõ được số như -3, 1/2, pi/2, sqrt(2), e.",
    "Dấu phẩy thập phân kiểu Việt Nam được chấp nhận: 0,5x giống 0.5x.",
    "Không cần gõ f(x)= hay y=; nếu bạn dán cả chuỗi 'y=x^2' thì web vẫn đọc được.",
    "Chỉ dùng biến x. Chữ hoa hay chữ thường đều được.",
]


def _tex(text: str) -> str:
    return tex(parse_function(text))


@lru_cache(maxsize=1)
def build_guide() -> dict:
    groups = [
        {"title": title, "rows": [{"typed": t, "latex": _tex(t), "note": note} for t, note in rows]}
        for title, rows in _GROUPS
    ]
    mistakes = [
        {"typed": t, "latex": _tex(t), "note": note, "fix": fix, "fix_latex": _tex(fix)}
        for t, note, fix in _MISTAKES
    ]
    return {"ok": True, "groups": groups, "mistakes": mistakes, "tips": TIPS}
