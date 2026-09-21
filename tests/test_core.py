"""Kiểm thử lõi toán học: so sánh với tích phân số độc lập (mpmath) và các giá trị đã biết."""
import mpmath as mp
import pytest
import sympy as sp

from backend.calculator import calculate
from backend.errors import AreaError
from backend.numeric import numeric_fn
from backend.parser import parse_bound, parse_function


def run(f1, f2="0", a=None, b=None, mode="manual"):
    return calculate({"f1": f1, "f2": f2, "a": a, "b": b, "mode": mode})


def brute_area(f1, f2, a, b, cuts=()):
    """Diện tích ∫|f-g| tính độc lập, chia đoạn tại các điểm cho trước."""
    h = numeric_fn(parse_function(f1) - parse_function(f2))
    fn = lambda x: abs(h([float(x)])[0])
    pts = [float(a)] + sorted(cuts) + [float(b)]
    return float(mp.quad(fn, pts))


@pytest.mark.parametrize("f1,f2,exact", [
    ("x^2-4", "0", sp.Rational(32, 3)),
    ("x^3-3x", "x", 8),
    ("x^2", "x+2", sp.Rational(9, 2)),
    ("sqrt(4-x^2)", "0", 2 * sp.pi),
    ("sqrt(x)", "x/2", sp.Rational(4, 3)),
])
def test_known_areas_auto(f1, f2, exact):
    res = run(f1, f2, mode="auto")
    assert res["exact"]
    assert abs(res["area_value"] - float(exact)) < 1e-9


def test_user_example_two_pieces():
    res = run("x^2", "2*x+3/2", "-3", "1")
    root = 1 - sp.sqrt(10) / 2
    assert len(res["intervals"]) == 2
    assert res["exact"]
    assert abs(res["area_value"] - brute_area("x^2", "2x+3/2", -3, 1, [float(root)])) < 1e-8
    assert abs(res["area_value"] - float(sp.Rational(34, 3) + 5 * sp.sqrt(10) / 3)) < 1e-9


def test_abs_kink_is_exact():
    assert abs(run("|x-1|", "2", "-2", "4")["area_value"] - 5) < 1e-9


def test_numeric_roots_flagged_approximate():
    res = run("exp(x)", "x+2", mode="auto")
    assert not res["exact"]
    assert abs(res["area_value"] - brute_area("exp(x)", "x+2", -1.8414056604369606, 1.1461932206205825)) < 1e-8


def test_sin_over_period_uses_absolute_value():
    assert abs(run("sin(x)", "0", "0", "2*pi")["area_value"] - 4) < 1e-9


def test_swapped_bounds_warn():
    res = run("x^2", "0", "2", "0")
    assert res["warnings"] and abs(res["area_value"] - 8 / 3) < 1e-9


@pytest.mark.parametrize("kwargs,code", [
    (dict(f1="x**2+++"), "parse"),
    (dict(f1="1/x", a="-1", b="1"), "domain"),
    (dict(f1="ln x", a="0", b="1"), "domain"),
    (dict(f1="x^2", f2="-1", mode="auto"), "no_intersection"),
    (dict(f1="x^2", f2="2x-1", mode="auto"), "no_region"),
    (dict(f1="sin x", f2="cos x", mode="auto"), "too_many"),
    (dict(f1="x^2", f2="x^2", a="0", b="1"), "identical"),
    (dict(f1="x^2", a="1"), "bounds"),
    (dict(f1="x^2", a="0", b="0"), "no_region"),
])
def test_error_codes(kwargs, code):
    with pytest.raises(AreaError) as e:
        run(**kwargs)
    assert e.value.code == code


@pytest.mark.parametrize("text,expected", [
    ("2x+3", "2*x + 3"), ("sinx", "sin(x)"), ("sin 2x", "sin(2*x)"), ("sin^2 x", "sin(x)**2"),
    ("x²-4", "x**2 - 4"), ("0,5x", "x/2"), ("|x-1|", "Abs(x - 1)"), ("f(x)=x^2", "x**2"),
    ("(x+1)(x-1)", "(x - 1)*(x + 1)"),
])
def test_parser_friendly_input(text, expected):
    assert sp.simplify(parse_function(text) - sp.sympify(expected.replace("Abs", "Abs"), locals={"x": sp.Symbol("x", real=True)})) == 0


@pytest.mark.parametrize("bad", ["", "abc", "9^9^9", "x^999", "__import__('os')", "y+x", "sqrt(-1)", "1/0"])
def test_parser_rejects_dangerous_or_invalid(bad):
    with pytest.raises(AreaError):
        parse_function(bad)


def test_bounds_parser():
    assert parse_bound("pi/2") == sp.pi / 2
    with pytest.raises(AreaError):
        parse_bound("x")


def test_latex_is_generated_for_all_supported_functions():
    for f in ("x^2", "sqrt(x)", "sin(x)", "exp(x)", "ln(x)", "1/x", "|x|", "arctan(x)", "tan(x)"):
        res = run(f, "0", "0.5", "1")
        assert "\\begin{tikzpicture}" in res["pgfplots_code"]
        assert "fill between" in res["pgfplots_code"]
        assert "\\begin{document}" in res["tex_document"]


# ------------------------------------------------------------------ v2
def test_sample_curves_covers_requested_range():
    from backend.calculator import sample_curves
    out = sample_curves({"f1": "x^2", "f2": "2x+3/2", "x0": -100, "x1": 100, "y0": -10, "y1": 400, "n": 400})
    assert len(out["x"]) == 400 and out["x"][0] == -100 and out["x"][-1] == 100
    assert out["g"][0] is not None and abs(out["g"][0] - (-198.5)) < 1e-6  # đường thẳng nằm trong khung
    assert out["f"][200] is not None  # gần x = 0
    with pytest.raises(AreaError):
        sample_curves({"f1": "x^2", "x0": 5, "x1": 1})


def test_sample_curves_breaks_at_asymptote():
    from backend.calculator import sample_curves
    out = sample_curves({"f1": "tan(x)", "f2": "0", "x0": 0, "x1": 3.5, "y0": -5, "y1": 5, "n": 700})
    assert None in out["f"]  # tiệm cận đứng bị ngắt nét, không nối thẳng qua


def test_live_preview_function():
    from backend.calculator import preview_function
    assert preview_function({"text": "sin^2 x + 1/2x"})["latex"].startswith("\\frac{x}{2}")
    assert preview_function({"text": "pi/2", "kind": "bound"})["latex"] == "\\frac{\\pi}{2}"
    with pytest.raises(AreaError):
        preview_function({"text": "x^^2+"})


def test_guide_examples_match_real_parser():
    from backend.guide import build_guide
    g = build_guide()
    rows = [r for grp in g["groups"] for r in grp["rows"]]
    assert len(rows) >= 25
    by = {r["typed"]: r["latex"] for r in rows}
    assert by["x^2"] == by["x**2"] == "x^{2}"
    assert by["ln(x)"] == by["log(x)"] == "\\ln{\\left(x \\right)}"
    # các ví dụ "dễ nhầm" phải thực sự cho kết quả khác với cách gõ đúng
    assert all(m["latex"] != m["fix_latex"] for m in g["mistakes"])


def test_ln_notation_in_results():
    res = run("ln x", "x-1", "0.5", "3")
    assert "\\ln" in res["integral_latex"] and "\\log" not in res["area_latex"]


def test_curve_colors_in_latex():
    res = run("x^2", "2x+3/2", "-3", "1")
    assert "1E4FD6" in res["pgfplots_code"] and "EB5A2A" in res["pgfplots_code"]
    assert "vietnam" in res["tex_document"] and "mathptmx" in res["tex_document"]
