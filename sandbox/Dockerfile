FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_NO_CACHE_DIR=1

RUN python -m pip install --upgrade pip \
    && python -m pip install \
        pytest \
        ruff \
        mypy

RUN useradd \
    --create-home \
    --uid 10001 \
    --shell /usr/sbin/nologin \
    sandbox

WORKDIR /workspace

USER sandbox

CMD ["python", "--version"]