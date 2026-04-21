FROM python:3.12-slim AS builder
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY packages/vellic_flags /packages/vellic_flags
RUN uv pip install --system --no-cache /packages/vellic_flags
COPY admin/pyproject.toml .
RUN uv pip install --system --no-cache ".[dev]"

FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*
RUN groupadd --gid 1001 appuser && useradd --uid 1001 --gid 1001 --no-create-home appuser
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
RUN rm -f /usr/local/bin/uv /usr/local/bin/uvx
RUN pip install --no-cache-dir --upgrade "pip>=25.3"
COPY admin/app/ ./app/
COPY admin/static/ ./static/
COPY worker/app/prompts/presets/ ./presets/
USER appuser
EXPOSE 8001
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
