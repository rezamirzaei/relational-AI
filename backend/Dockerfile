# ── Stage 1: build ─────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /build

COPY pyproject.toml README.md LICENSE alembic.ini ./
COPY alembic ./alembic
COPY src ./src

RUN pip install --upgrade pip \
    && pip install --prefix=/install .

# ── Stage 2: runtime ──────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV RFI_PROJECT_ROOT=/app

WORKDIR /app

# Copy only the installed packages — no pip, no build tools
COPY --from=builder /install /usr/local
COPY alembic.ini ./
COPY alembic ./alembic
COPY src ./src

RUN groupadd --system rfi \
    && useradd --system --gid rfi --create-home rfi \
    && mkdir -p /app/data \
    && chown -R rfi:rfi /app

USER rfi
EXPOSE 8001

CMD ["sh", "-c", "rfi-manage migrate && rfi-api"]
