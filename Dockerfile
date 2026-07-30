# Single stage, pure Python. The frontend is a static file with no build step
# (TO-24), so there is no Node stage and no node_modules to fail to install on
# a reviewer's machine.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock ./
COPY packages/ packages/
COPY apps/ apps/
RUN uv sync --frozen --no-dev

# Baked into the image on purpose: the corpus is a build-time artifact, and the
# running container must never need to reach lumalabs.ai.
COPY corpus/ corpus/
COPY scripts/ scripts/

ENV DB_PATH=/app/data/app.db
EXPOSE 8000
CMD ["uvicorn", "ask_luma.main:app", "--host", "0.0.0.0", "--port", "8000"]
