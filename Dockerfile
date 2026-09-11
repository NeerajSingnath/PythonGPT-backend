FROM docker:29.7.2-cli AS docker-cli

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    ca-certificates \
    git \
    tini \
    && rm -rf /var/lib/apt/lists/*

COPY --from=docker-cli \
    /usr/local/bin/docker \
    /usr/local/bin/docker

RUN useradd \
    --create-home \
    --uid 10001 \
    --shell /usr/sbin/nologin \
    pythongpt

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app

RUN python -m pip install --upgrade pip \
    && python -m pip install .

RUN mkdir -p \
    /app/workspaces \
    /app/runs \
    && chown -R \
    pythongpt:pythongpt \
    /app/workspaces \
    /app/runs

USER pythongpt

EXPOSE 8000

HEALTHCHECK \
    --interval=30s \
    --timeout=5s \
    --start-period=10s \
    --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).read()"]

ENTRYPOINT ["/usr/bin/tini", "--"]

CMD ["uvicorn","app.main:app", "--host", "0.0.0.0", "--port", "8000"]
