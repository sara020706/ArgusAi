FROM python:3.11-slim

LABEL maintainer="argus"
LABEL description="Argus insider threat detection — API server"

WORKDIR /app

COPY pyproject.toml .
COPY argus/ ./argus/

RUN pip install --no-cache-dir -e ".[api,ml]"

RUN useradd -m -u 1000 argus && chown -R argus:argus /app
USER argus

VOLUME ["/app/data"]

ENV ARGUS_DB_PATH=/app/data/argus.db
ENV ARGUS_PORT=8000
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["python", "-m", "argus.api.server"]
