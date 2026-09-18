FROM ghcr.io/astral-sh/uv:0.8.22 AS uv
FROM python:3.12-slim-bookworm AS development
COPY --from=uv /uv /usr/local/bin/uv
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv UV_LINK_MODE=copy PATH="/opt/venv/bin:$PATH"
WORKDIR /app
RUN useradd --create-home --uid 10001 app && mkdir /opt/venv && chown app:app /app /opt/venv
COPY --chown=app:app backend/pyproject.toml backend/uv.lock ./
USER app
RUN uv sync --frozen
COPY --chown=app:app backend/ ./
CMD ["uv", "run", "--frozen", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
