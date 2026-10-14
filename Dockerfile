FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app
COPY docker ./docker

RUN chmod +x /srv/app/docker/start-api.sh /srv/app/docker/start-worker.sh \
    && useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /srv/app

USER appuser

EXPOSE 8000

CMD ["./docker/start-api.sh"]
