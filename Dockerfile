# Single stage, pure Python. The frontend is a static file with no build step
# (TO-22), so there is no Node stage and no node_modules to fail to install on
# a reviewer's machine.
FROM python:3.12-slim

# Pinned by digest, not `:latest`. TO-05 spends a paragraph arguing that a
# "-latest" alias drifts and that the drift then masquerades as a change you
# made yourself; that argument does not stop applying at the build boundary.
COPY --from=ghcr.io/astral-sh/uv@sha256:606e70c71c852d03f611b1e56a195d08648507018a7057fab82c4974c4eae105 /uv /usr/local/bin/uv

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
COPY datasets/ datasets/

ENV DB_PATH=/app/data/app.db
EXPOSE 8000
# server.main is the only module that imports both apps: chatbot at /, console at
# /console, one process so the console's cache invalidation reaches the chatbot.
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
