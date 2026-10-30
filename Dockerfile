FROM python:3.12-alpine3.23@sha256:a4ad86fc2eaa4f9a5c3153776c9fb56e502dbd8e23dfa855d164308f376a6dd2 AS builder

COPY --from=ghcr.io/astral-sh/uv:0.13.0 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY src ./src

RUN uv sync --frozen --no-dev --no-editable --python /usr/local/bin/python3


FROM python:3.12-alpine3.23@sha256:a4ad86fc2eaa4f9a5c3153776c9fb56e502dbd8e23dfa855d164308f376a6dd2 AS runtime

# Correções de segurança do sistema base; pip e setuptools não são usados em runtime.
RUN apk upgrade --no-cache \
    && addgroup -S -g 10001 nexo \
    && adduser -S -u 10001 -G nexo -h /home/nexo nexo \
    && python -m pip uninstall -y pip setuptools wheel >/dev/null 2>&1 || true \
    && rm -rf /usr/local/lib/python3.12/ensurepip /usr/local/lib/python3.12/site-packages/pip* \
       /usr/local/lib/python3.12/site-packages/setuptools* /usr/local/lib/python3.12/site-packages/wheel* \
       /usr/local/bin/pip* /root/.cache

WORKDIR /app

COPY --from=builder --chown=nexo:nexo /app/.venv /app/.venv
COPY --chown=nexo:nexo alembic.ini ./alembic.ini
COPY --chown=nexo:nexo migrations ./migrations
COPY --chown=nexo:nexo scripts/entrypoint.sh ./scripts/entrypoint.sh

USER nexo

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_ENV=local \
    APP_HOST=0.0.0.0 \
    APP_PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live')"

ENTRYPOINT ["sh", "scripts/entrypoint.sh"]
