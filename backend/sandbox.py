"""Chạy phép tính SymPy trong tiến trình riêng có giới hạn thời gian.

Vì sao cần: solve/integrate của SymPy có thể chạy rất lâu hoặc ngốn RAM với biểu thức lạ.
Nếu chạy trong chính tiến trình web, một yêu cầu xấu sẽ làm treo toàn bộ trang.
Ở đây mỗi yêu cầu chạy trong một worker (đã nạp sẵn SymPy); quá hạn thì tiêu diệt worker
và trả lỗi thân thiện.
"""
from __future__ import annotations

import concurrent.futures as cf
import multiprocessing as mp
import os
import threading
from concurrent.futures.process import BrokenProcessPool

from .errors import AreaError

WORKERS = int(os.environ.get("WORKERS", "2"))
TIMEOUT = float(os.environ.get("CALC_TIMEOUT", "30"))

_lock = threading.Lock()
_pool: cf.ProcessPoolExecutor | None = None


def _init_worker() -> None:
    limit = os.environ.get("WORKER_MEM_MB")
    if limit:
        try:
            import resource
            b = int(limit) * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (b, b))
        except Exception:
            pass
    from . import calculator  # noqa: F401  (nạp sẵn SymPy để lần gọi đầu không bị chậm)


def _get_pool() -> cf.ProcessPoolExecutor:
    global _pool
    with _lock:
        if _pool is None:
            _pool = cf.ProcessPoolExecutor(max_workers=WORKERS, mp_context=mp.get_context("spawn"),
                                           initializer=_init_worker)
        return _pool


def _kill_pool() -> None:
    global _pool
    with _lock:
        pool, _pool = _pool, None
    if pool is None:
        return
    for proc in list(getattr(pool, "_processes", {}).values()):
        try:
            proc.terminate()
        except Exception:
            pass
    pool.shutdown(wait=False, cancel_futures=True)


def run_isolated(fn, *args, timeout: float = TIMEOUT):
    """Chạy fn(*args) trong worker. AreaError của worker được ném lại nguyên vẹn."""
    last: Exception | None = None
    for _ in range(2):  # thử lại một lần nếu worker bị tiêu diệt do yêu cầu khác quá hạn
        try:
            return _get_pool().submit(fn, *args).result(timeout=timeout)
        except cf.TimeoutError:
            _kill_pool()
            raise AreaError("timeout", "Phép tính mất quá nhiều thời gian.\nHãy thử biểu thức đơn giản hơn hoặc nhập cận cụ thể.")
        except BrokenProcessPool as exc:
            _kill_pool()
            last = exc
    raise AreaError("internal", "Máy chủ tính toán đang khởi động lại, vui lòng thử lại.", detail=str(last))


def shutdown() -> None:
    _kill_pool()
