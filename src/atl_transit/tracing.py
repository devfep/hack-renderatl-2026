"""OpenTelemetry tracing into a locally-hosted Arize Phoenix.

Answering one question fans out into several model calls and a Snowflake round trip. Without
tracing, a slow or wrong answer is opaque; with it, every invocation is a waterfall showing
which model was called, how long each leg took, and what the tool actually returned.

Phoenix runs entirely locally with no account and no API key: ``uv run phoenix serve``.
"""

from __future__ import annotations

import os

PHOENIX_ENDPOINT = "http://localhost:6006/v1/traces"
PROJECT = "atl-transit"


def start(endpoint: str | None = None, project: str | None = None) -> object | None:
    """Send ADK's spans to Phoenix. Must be called before the agent is imported.

    Instrumentation patches ADK at import time, so importing the agent first means its spans
    are never captured.

    Args:
        endpoint: OTLP HTTP collector URL. Defaults to ``PHOENIX_ENDPOINT``.
        project: Phoenix project name to group traces under.

    Returns:
        The tracer provider, or None when Phoenix is not installed.
    """
    try:
        from phoenix.otel import register  # noqa: PLC0415 - optional dev dependency
    except ImportError:
        print("phoenix not installed - run: uv sync --all-groups")
        return None
    return register(
        project_name=project or PROJECT,
        endpoint=endpoint or os.environ.get("PHOENIX_ENDPOINT", PHOENIX_ENDPOINT),
        auto_instrument=True,
    )
