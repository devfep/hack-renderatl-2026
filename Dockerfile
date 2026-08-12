# Serves the ADK agent, and also runs the harvest when started with a different command.
# One image, two entrypoints, so the web app and the scheduled harvest can never drift apart.
#
# Deliberately plain Docker syntax: no `RUN --mount` cache or bind mounts. Those require
# BuildKit, which DigitalOcean App Platform's builder does not enable, and the build fails
# there while succeeding locally where Docker Desktop turns BuildKit on by default.
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Dependencies resolve from the lockfile alone, so this layer survives source edits.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY README.md ./
COPY src/ ./src/
RUN uv sync --locked --no-dev


FROM python:3.13-slim-bookworm AS runtime

RUN useradd --create-home --uid 10001 app
WORKDIR /app

COPY --from=builder --chown=app:app /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    ATL_STORE=snowflake \
    PORT=8080

USER app

# Bake the DuckDB spatial extension in. Otherwise every cold start downloads it, adding ~35s
# and making each scheduled harvest depend on DuckDB's extension CDN staying up.
RUN python -c "import duckdb; duckdb.connect().execute('INSTALL spatial; LOAD spatial;')"

# Decline ADK's usage telemetry at build time. The server injects the stored consent into the
# Web UI's bootstrap config, and an absent choice makes every first-time visitor answer a
# Google data-collection dialog before they can use the app. Declining on their behalf is the
# right default: nobody visiting a public demo should be opted into anything.
RUN adk telemetry disable

EXPOSE 8080

# DigitalOcean and Render both inject PORT; bind 0.0.0.0 or the platform sees no listener.
CMD ["sh", "-c", "adk web src --host 0.0.0.0 --port ${PORT}"]
