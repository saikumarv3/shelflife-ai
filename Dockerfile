FROM python:3.12-slim AS builder

WORKDIR /app
RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

FROM python:3.12-slim

WORKDIR /app
COPY --from=builder /app /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

EXPOSE 8000
CMD ["sh", "-c", "gunicorn api.main:app -k uvicorn.workers.UvicornWorker --workers ${API_WORKERS:-2} --bind 0.0.0.0:8000 --timeout 120"]
