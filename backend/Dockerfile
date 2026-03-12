FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md alembic.ini ./
COPY alembic ./alembic
COPY src ./src

RUN groupadd --system rfi \
    && useradd --system --gid rfi --create-home rfi \
    && pip install --upgrade pip \
    && pip install . \
    && chown -R rfi:rfi /app

USER rfi
EXPOSE 8000

CMD ["sh", "-c", "rfi-manage migrate && rfi-api"]
