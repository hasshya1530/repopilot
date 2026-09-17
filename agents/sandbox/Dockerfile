FROM python:3.12-slim

RUN pip install --no-cache-dir pytest

RUN useradd \
    --create-home \
    --shell /usr/sbin/nologin \
    sandbox

WORKDIR /workspace

RUN chown sandbox:sandbox /workspace

USER sandbox

ENTRYPOINT []
