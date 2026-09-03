# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base

# Keep Python output unbuffered so logs show up immediately in `docker logs`
# instead of getting stuck in a buffer — a small thing that saves real
# debugging time in production.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ .

# Run as a non-root user — a real reliability/security practice, not
# just box-ticking: it limits blast radius if the container is compromised.
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

ENV APP_ENV=production \
    PORT=8080

EXPOSE 8080

# HEALTHCHECK is what lets `docker ps` and orchestrators (ECS, k8s, Compose)
# know the container is actually serving, not just that the process exists.
# This is the exact mechanism the broken-deployment scenario breaks.
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request,sys; \
    sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2).status == 200 else 1)"

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--access-logfile", "-", "app:app"]
