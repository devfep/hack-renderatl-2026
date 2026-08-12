# One image, two roles: the ADK web server (DigitalOcean) and the harvest (Render cron).
#
# Deliberately free of BuildKit syntax. DigitalOcean App Platform's builder does not enable
# BuildKit, so `RUN --mount=type=cache` and `RUN --mount=type=bind` fail there. Dependency
# caching comes from ordinary layer ordering instead: lockfile first, source second.

FROM python:3.13-slim-trixie AS builder

COPY --from=ghcr.io/astral-sh/uv:0.12.3 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

# Dependencies resolve into their own layer, reused whenever only src/ changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable


FROM python:3.13-slim-trixie

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    HOME=/home/atl

WORKDIR /app
RUN useradd --create-home --uid 10001 atl

COPY --from=builder --chown=atl:atl /app/.venv /app/.venv
COPY --chown=atl:atl src ./src

# harvest writes its GTFS downloads here, and DuckDBStore its database file.
RUN mkdir -p /app/data/raw && chown -R atl:atl /app/data

USER atl

# Bake the DuckDB spatial extension into the image so neither role has to download it on a
# cold start. Both harvest and DuckDBStore run `INSTALL spatial; LOAD spatial;`.
RUN python -c "import duckdb; duckdb.connect().execute('INSTALL spatial; LOAD spatial;')"

EXPOSE 8080

# DigitalOcean injects PORT. Render's cron job overrides this entirely via dockerCommand.
CMD ["sh", "-c", "exec adk web /app/src --host 0.0.0.0 --port ${PORT:-8080}"]
