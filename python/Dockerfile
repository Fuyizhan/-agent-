FROM python:3.12-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build
COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    APP_HOST=0.0.0.0 \
    APP_PORT=8000 \
    UPLOAD_DIR=/app/uploads
WORKDIR /app
COPY --from=builder /install /usr/local
COPY src/ ./src/
COPY data/ ./data/
RUN mkdir -p /app/uploads
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
