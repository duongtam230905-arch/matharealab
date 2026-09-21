"""API FastAPI + phục vụ giao diện tĩnh.

Chạy:  uvicorn backend.main:app --reload
"""
from __future__ import annotations

import hashlib
import json
import logging
from collections import OrderedDict
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import calculator
from .errors import AreaError
from .examples import EXAMPLES
from .guide import build_guide
from .latex_compile import compile_tex, tex_available
from .sandbox import run_isolated

log = logging.getLogger("arealab")
ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"

app = FastAPI(title="AreaLab", version="0.1.0",
              description="Công cụ trực quan hóa và tính diện tích hình phẳng bằng tích phân.")
app.add_middleware(GZipMiddleware, minimum_size=1024)


# ------------------------------------------------------------------ schema
class CalcRequest(BaseModel):
    f1: str = Field(..., max_length=200, description="Hàm số f(x), ví dụ x^2")
    f2: str = Field("0", max_length=200, description="Hàm số g(x); mặc định 0 (trục Ox)")
    a: Optional[str] = Field(None, max_length=60)
    b: Optional[str] = Field(None, max_length=60)
    mode: Literal["manual", "auto"] = "manual"

    def payload(self) -> dict:
        """Chỉ các trường ảnh hưởng tới phép tính (bỏ `variant` của yêu cầu xem trước)."""
        return {k: v for k, v in self.model_dump().items() if k in ("f1", "f2", "a", "b", "mode")}

    def key(self) -> str:
        blob = json.dumps(self.payload(), sort_keys=True, ensure_ascii=False)
        return hashlib.sha1(blob.encode()).hexdigest()


# ------------------------------------------------------------------ bộ nhớ đệm nhỏ (LRU)
class _Cache:
    def __init__(self, size: int = 64):
        self.size, self.data = size, OrderedDict()

    def get(self, k):
        if k in self.data:
            self.data.move_to_end(k)
            return self.data[k]
        return None

    def put(self, k, v):
        self.data[k] = v
        self.data.move_to_end(k)
        while len(self.data) > self.size:
            self.data.popitem(last=False)


_cache = _Cache()


def _error_response(err: AreaError, status: int = 400) -> JSONResponse:
    if err.code == "timeout":
        status = 504
    return JSONResponse(status_code=status, content={"ok": False, "error": err.to_dict()})


def _compute(req: CalcRequest) -> dict:
    hit = _cache.get(req.key())
    if hit is not None:
        return hit
    result = run_isolated(calculator.calculate, req.payload())
    _cache.put(req.key(), result)
    return result


# ------------------------------------------------------------------ API
@app.post("/api/calculate")
def api_calculate(req: CalcRequest):
    try:
        return _compute(req)
    except AreaError as err:
        return _error_response(err)
    except Exception:  # lỗi không lường trước: ghi log, trả thông điệp chung
        log.exception("calculate failed")
        return JSONResponse(status_code=500, content={"ok": False, "error": {
            "code": "internal", "message": "Đã xảy ra lỗi khi tính toán. Vui lòng thử lại với biểu thức khác.",
            "detail": None, "stage": None}})


@app.post("/api/intersections")
def api_intersections(req: CalcRequest):
    try:
        return run_isolated(calculator.list_intersections, req.payload())
    except AreaError as err:
        return _error_response(err)
    except Exception:
        log.exception("intersections failed")
        return JSONResponse(status_code=500, content={"ok": False, "error": {
            "code": "internal", "message": "Không thể tìm giao điểm lúc này.", "detail": None, "stage": None}})


class PreviewRequest(CalcRequest):
    variant: Literal["pgfplots", "tikz"] = "pgfplots"


@app.post("/api/latex/preview")
def api_latex_preview(req: PreviewRequest):
    """Biên dịch pdflatex trên máy chủ. Chỉ biên dịch mã do chính máy chủ sinh từ tham số."""
    try:
        result = _compute(req)
    except AreaError as err:
        return _error_response(err)
    key = "tex_document_tikz" if req.variant == "tikz" else "tex_document"
    tex = result.get(key)
    if not tex:
        return JSONResponse(status_code=422, content={"ok": False, "error": {
            "code": "latex", "message": result.get("latex_note") or "Không có mã LaTeX để xem trước.",
            "detail": None, "stage": "latex"}})
    out = compile_tex(tex)
    if not out.get("ok"):
        return JSONResponse(status_code=200, content=out)
    return out


class SampleRequest(BaseModel):
    f1: str = Field(..., max_length=200)
    f2: str = Field("0", max_length=200)
    x0: float
    x1: float
    y0: float = -10.0
    y1: float = 10.0
    n: int = 1500


@app.post("/api/sample")
def api_sample(req: SampleRequest):
    """Lấy mẫu lại hai đồ thị theo khung nhìn hiện tại để zoom/kéo không bao giờ bị cụt."""
    try:
        return run_isolated(calculator.sample_curves, req.model_dump(), timeout=15)
    except AreaError as err:
        return _error_response(err)
    except Exception:
        log.exception("sample failed")
        return JSONResponse(status_code=500, content={"ok": False, "error": {
            "code": "internal", "message": "Không lấy mẫu được đồ thị.", "detail": None, "stage": None}})


class ParseRequest(BaseModel):
    text: str = Field("", max_length=200)
    kind: Literal["fn", "bound"] = "fn"


@app.post("/api/parse")
def api_parse(req: ParseRequest):
    """Xem trước công thức ngay khi người học đang gõ."""
    try:
        return run_isolated(calculator.preview_function, req.model_dump(), timeout=8)
    except AreaError as err:
        return _error_response(err)
    except Exception:
        return JSONResponse(status_code=500, content={"ok": False, "error": {
            "code": "internal", "message": "Chưa xem trước được.", "detail": None, "stage": None}})


@app.get("/api/guide")
def api_guide():
    return build_guide()


@app.get("/api/examples")
def api_examples():
    return {"examples": EXAMPLES}


@app.get("/api/health")
def api_health():
    return {"status": "ok", "pdflatex": tex_available()}


# ------------------------------------------------------------------ giao diện
app.mount("/static", StaticFiles(directory=str(FRONTEND / "static")), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(FRONTEND / "index.html")
