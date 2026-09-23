FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /opt/repopilot

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen

RUN useradd \
    --create-home \
    --shell /usr/sbin/nologin \
    sandbox

RUN chown -R sandbox:sandbox /opt/repopilot

ENV PATH="/opt/repopilot/.venv/bin:$PATH"

USER sandbox

WORKDIR /workspace

ENTRYPOINT []
