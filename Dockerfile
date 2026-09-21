# AreaLab: FastAPI + SymPy + TeX Live (pdflatex) để xem trước hình LaTeX trên máy chủ.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 WORKERS=2

# pgfplots nằm trong texlive-pictures; gói vietnam nằm trong texlive-lang-other;
# mathptmx (Times) cần texlive-fonts-recommended; poppler-utils cung cấp pdftoppm.
RUN apt-get update && apt-get install -y --no-install-recommends \
        texlive-latex-base texlive-latex-extra texlive-pictures \
        texlive-fonts-recommended texlive-lang-other poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./backend
COPY frontend ./frontend

EXPOSE 8000
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
