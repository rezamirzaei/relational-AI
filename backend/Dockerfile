FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV RFI_PROJECT_ROOT=/app

WORKDIR /app

COPY pyproject.toml README.md alembic.ini ./
COPY alembic ./alembic
COPY src ./src

RUN groupadd --system rfi \
    && useradd --system --gid rfi --create-home rfi \
    && mkdir -p /app/data \
    && pip install --upgrade pip \
    && pip install . \
    && chown -R rfi:rfi /app

USER rfi
EXPOSE 8001

CMD ["sh", "-c", "rfi-manage migrate && rfi-api"]
