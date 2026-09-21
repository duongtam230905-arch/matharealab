"""Lỗi nghiệp vụ: mọi lỗi người dùng có thể gặp đều đi qua AreaError.

Thông điệp (message) được viết sẵn bằng tiếng Việt để frontend hiển thị nguyên văn.
"""
from __future__ import annotations

MSG_PARSE = "Không thể đọc biểu thức.\nVui lòng kiểm tra lại hàm số."
MSG_DOMAIN = "Hàm số không xác định trên miền đang xét."
MSG_NO_REGION = "Không xác định được miền hình phẳng cần tính.\nHãy kiểm tra cận hoặc giao điểm."
MSG_NO_INTERSECTION = "Không tìm thấy giao điểm thực giữa hai đồ thị."


class AreaError(Exception):
    """Lỗi có mã (code), thông điệp thân thiện và chi tiết kỹ thuật tuỳ chọn.

    `stage` cho biết lỗi xảy ra ở bước nào của quy trình (parse, intersections, ...),
    để giao diện đánh dấu đúng bước bị dừng.
    """

    def __init__(self, code: str, message: str, detail: str | None = None, stage: str | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail
        self.stage = stage

    # Cần thiết để ném lỗi qua ranh giới tiến trình (ProcessPoolExecutor).
    def __reduce__(self):
        return (AreaError, (self.code, self.message, self.detail, self.stage))

    def to_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "detail": self.detail, "stage": self.stage}
