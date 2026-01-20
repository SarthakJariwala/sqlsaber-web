# Stage 1: Build the frontend files
FROM node:24-bookworm-slim AS node-builder
RUN nodejs -v && npm -v
WORKDIR /code
COPY . /code
RUN mkdir -p /code/static
RUN npm install
RUN npm run build

# Stage 2: Runtime image with Python dependencies
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Reset the entrypoint, don't invoke `uv`
ENTRYPOINT []

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
ENV VIRTUAL_ENV="/code/.venv"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV DEBUG=0

RUN apt-get update \
    && apt-get install -y \
    curl \
    libpq-dev \
    && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
    && rm -rf /var/lib/apt/lists/*

RUN addgroup --system django \
    && adduser --system --ingroup django --home /code django

ENV HOME=/code

WORKDIR /code

COPY pyproject.toml uv.lock /code/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project --no-dev --frozen

COPY --chown=django:django . /code
COPY --from=node-builder --chown=django:django /code/frontend/dist /code/frontend/dist

RUN DEBUG=False python ./manage.py collectstatic --noinput --settings=sqlsaber_web.settings_production
RUN chown django:django -R static

USER django

COPY --chown=django:django docker_startup.sh /start
RUN chmod +x /start
CMD /start
