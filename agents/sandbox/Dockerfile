FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN useradd \
    --create-home \
    --shell /usr/sbin/nologin \
    sandbox

WORKDIR /workspace

USER sandbox

ENTRYPOINT []
