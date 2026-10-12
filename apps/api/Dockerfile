FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.11.28 /uv /uvx /bin/
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY src ./src
COPY alembic.ini ./
COPY alembic ./alembic
RUN uv sync --frozen --no-dev && useradd --create-home appuser
USER appuser
ENV PATH="/app/.venv/bin:$PATH"
CMD ["sh", "-c", "uvicorn opportunity_platform.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
