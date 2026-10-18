FROM python:3.11-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /build

COPY pyproject.toml .
COPY src ./src
COPY proto ./proto
COPY tools ./tools

RUN pip install --no-cache-dir . && python tools/generate_protos.py

FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH="/app/src"

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY --from=builder /build/src ./src
COPY --from=builder /build/proto ./proto

RUN groupadd --system app && useradd --system --gid app --create-home app \
    && mkdir -p /app/data \
    && chown -R app:app /app

USER app

CMD ["python", "-m", "integrity_analytics.main"]