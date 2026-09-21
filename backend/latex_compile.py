"""Biên dịch mã LaTeX do CHÍNH máy chủ sinh ra thành PDF (và PNG nếu có pdftoppm).

An toàn: không bao giờ nhận .tex tuỳ ý từ trình duyệt (tránh \\input file hệ thống);
chạy pdflatex với -no-shell-escape, giới hạn đọc/ghi file, thư mục tạm riêng và timeout.

Riêng MiKTeX (Windows): nếu thiếu gói, MiKTeX có thể bật hộp thoại chờ cài đặt làm treo tiến trình.
Vì vậy ta (1) kiểm tra trước các gói cần thiết, (2) chạy MiKTeX với -disable-installer.
"""
from __future__ import annotations

import base64
import os
import re
import shutil
import subprocess
import tempfile
import threading
from functools import lru_cache
from pathlib import Path

_SLOTS = threading.BoundedSemaphore(int(os.environ.get("LATEX_CONCURRENCY", "2")))
TIMEOUT = float(os.environ.get("LATEX_TIMEOUT", "40"))
NEEDED = ("pgfplots.sty", "standalone.cls", "mathptmx.sty", "amsmath.sty")
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


@lru_cache(maxsize=1)
def tex_available() -> bool:
    return bool(shutil.which("pdflatex"))


@lru_cache(maxsize=1)
def _is_miktex() -> bool:
    try:
        out = subprocess.run(["pdflatex", "--version"], capture_output=True, text=True, timeout=20,
                             creationflags=_NO_WINDOW)
        return "miktex" in (out.stdout + out.stderr).lower()
    except Exception:
        return False


def _kpse(name: str) -> bool:
    kpse = shutil.which("kpsewhich")
    if not kpse:
        return True  # không kiểm tra được thì cứ thử biên dịch
    try:
        out = subprocess.run([kpse, name], capture_output=True, text=True, timeout=20, creationflags=_NO_WINDOW)
        return bool(out.stdout.strip())
    except Exception:
        return True


@lru_cache(maxsize=1)
def _has_vietnam() -> bool:
    return _kpse("vietnam.sty")


def missing_packages() -> list[str]:
    return [n.rsplit(".", 1)[0] for n in NEEDED if not _kpse(n)]


def compile_tex(tex: str, dpi: int = 220) -> dict:
    """Trả về {ok, png_base64?, pdf_base64, note, log}. Không ném lỗi ra ngoài."""
    if not tex_available():
        return {"ok": False, "error": "Máy chưa cài pdflatex (MiKTeX hoặc TeX Live), nên không biên dịch được."}
    miss = missing_packages()
    if miss:
        hint = ("Mở MiKTeX Console → Packages để cài các gói này (hoặc đặt 'Install missing packages on-the-fly' = Always)."
                if _is_miktex() else "Hãy cài các gói này bằng trình quản lý TeX của bạn.")
        return {"ok": False, "error": f"TeX của máy thiếu gói: {', '.join(miss)}.\n{hint}"}
    if not _SLOTS.acquire(timeout=5):
        return {"ok": False, "error": "Máy chủ đang bận biên dịch LaTeX, vui lòng thử lại sau ít giây."}
    try:
        note = None
        if not _has_vietnam():
            # Hình chỉ chứa công thức nên vẫn biên dịch được khi thiếu gói vietnam.
            tex = tex.replace(r"\usepackage[utf8]{vietnam}", r"\usepackage[utf8]{inputenc}")
            note = "Máy chưa có gói vietnam; bản xem trước dùng inputenc thay thế."
        with tempfile.TemporaryDirectory(prefix="arealab_") as tmp:
            d = Path(tmp)
            (d / "figure.tex").write_text(tex, encoding="utf-8")
            env = dict(os.environ)
            env.update({"TEXMFVAR": tmp, "TEXMFCONFIG": tmp,
                        "openin_any": "p", "openout_any": "p", "shell_escape": "f"})
            if os.name != "nt":
                env["HOME"] = tmp
            cmd = ["pdflatex", "-no-shell-escape", "-interaction=nonstopmode", "-halt-on-error"]
            if _is_miktex():
                cmd.append("-disable-installer")
            cmd.append("figure.tex")
            try:
                proc = subprocess.run(cmd, cwd=tmp, env=env, capture_output=True, timeout=TIMEOUT,
                                      stdin=subprocess.DEVNULL, creationflags=_NO_WINDOW)
            except subprocess.TimeoutExpired:
                return {"ok": False, "error": "Biên dịch LaTeX quá thời gian cho phép."}
            pdf = d / "figure.pdf"
            if proc.returncode != 0 or not pdf.exists():
                log = proc.stdout.decode("utf-8", "replace")
                m = re.search(r"^!.*$", log, re.M)
                return {"ok": False, "error": "Biên dịch LaTeX thất bại.", "log": (m.group(0) if m else log[-600:])}
            out = {"ok": True, "pdf_base64": base64.b64encode(pdf.read_bytes()).decode(), "png_base64": None, "note": note}
            if shutil.which("pdftoppm"):
                subprocess.run(["pdftoppm", "-png", "-r", str(dpi), "-singlefile", str(pdf), str(d / "figure")],
                               cwd=tmp, env=env, capture_output=True, timeout=TIMEOUT, creationflags=_NO_WINDOW)
                png = d / "figure.png"
                if png.exists():
                    out["png_base64"] = base64.b64encode(png.read_bytes()).decode()
            return out
    finally:
        _SLOTS.release()
