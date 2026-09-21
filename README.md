# AreaLab – Tính diện tích hình phẳng bằng tích phân

Nhập hàm → nhập cận / tìm giao điểm → phân tích miền → tính diện tích → vẽ hình → xuất mã LaTeX (PGFPlots/TikZ).

## Chạy trên máy

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn backend.main:app --reload                       # mở http://127.0.0.1:8000
pytest                                                   # chạy kiểm thử
```

Xem trước hình LaTeX cần `pdflatex` và `pdftoppm` (TeX Live + poppler). Thiếu chúng thì mọi tính năng khác vẫn chạy,
riêng khung xem trước báo "chưa cài pdflatex".

## Triển khai lên Render (Docker)

1. Đẩy thư mục này lên GitHub.
2. Render → New → Blueprint → chọn repo (dùng `render.yaml`) hoặc New Web Service → Runtime: Docker.
3. Ảnh Docker cài sẵn TeX Live (pgfplots, gói `vietnam`, `mathptmx`) nên dung lượng lớn (~1 GB); build lần đầu mất vài phút.
4. Gói free (512 MB RAM) dễ thiếu bộ nhớ khi SymPy và pdflatex cùng chạy; nên dùng gói Starter.

Biến môi trường: `WORKERS` (số tiến trình tính toán, mặc định 2), `CALC_TIMEOUT` (giây, mặc định 30),
`LATEX_TIMEOUT`, `LATEX_CONCURRENCY`, `WORKER_MEM_MB` (giới hạn RAM mỗi worker, tuỳ chọn).

## Kiến trúc

```text
backend/
  main.py            FastAPI: /api/calculate, /api/intersections, /api/sample (lấy mẫu lại khi zoom), /api/parse (xem trước khi gõ),
                     /api/guide, /api/latex/preview, /api/examples, /api/health
  guide.py           bộ hướng dẫn gõ hàm (cột 'hiển thị' tính bằng chính parser)
  calculator.py      điều phối: parse -> giao điểm -> miền -> tích phân -> đồ thị -> LaTeX -> các bước
  parser.py          chuẩn hoá & đọc biểu thức an toàn (không eval chuỗi thô)
  intersection.py    giải f=g: solveset chính xác + quét số (đổi dấu, nghiệm bội chẵn) + kiểm chứng
  domain.py          kiểm tra hàm xác định/liên tục trên miền
  regions.py         chia miền, xác định hàm trên/dưới, phát hiện nghiệm bị bỏ sót
  integration.py     tích phân chính xác, đối chiếu tích phân số 30 chữ số, dự phòng số
  graph.py           dữ liệu đồ thị cho Plotly
  latex_generator.py sinh PGFPlots, TikZ thuần, tài liệu standalone (pdflatex + gói vietnam)
  latex_compile.py   biên dịch mã do chính máy chủ sinh ra -> PDF/PNG (không nhận .tex tuỳ ý)
  steps.py           lời giải từng bước, gợi ý cho chế độ học tập
  sandbox.py         chạy tính toán trong tiến trình riêng có timeout
  examples.py        thư viện ví dụ (sau này dùng để tạo bài tập tự động)
frontend/            index.html + static/{css,js} (Plotly.js, KaTeX, không cần bước build)
tests/               kiểm thử lõi toán học và API
```

Mở rộng: thêm module mới (ví dụ `volume.py` cho thể tích tròn xoay) theo mẫu
`hàm thuần dict -> dict`, đăng ký endpoint trong `main.py`, tái sử dụng `parser`, `intersection`, `domain`, `latex_generator`.

## Tuỳ chỉnh thông tin liên hệ

Sửa file `frontend/static/js/site-config.js` (tên thầy, Facebook, Zalo, số điện thoại). Nút nổi "Liên hệ" và
chân trang tự cập nhật. **Nhớ thay `facebookUrl` bằng đường link trang Facebook thật.**

## Xem trước hình LaTeX

Mặc định web dựng bản xem trước nhanh bằng SVG ngay trong trình duyệt (không cần TeX) và có nút "Mở trong Overleaf".
Nếu máy chủ có `pdflatex`, xuất hiện thêm nút "Biên dịch thật bằng pdflatex". Với MiKTeX (Windows), nếu thiếu gói
(pgfplots, standalone...) hãy mở MiKTeX Console -> Packages để cài; web sẽ báo rõ gói còn thiếu thay vì bị treo.

## Quy ước nhập

`x^2`, `2x+3`, `sqrt(x)`, `|x-1|`, `sin(x)` (radian), `exp(x)`, `e^x`, `ln(x)`; `log(x)` cũng là logarit tự nhiên,
`lg(x)` là log₁₀. Dấu phẩy thập phân kiểu Việt Nam (`0,5x`) được chấp nhận.
