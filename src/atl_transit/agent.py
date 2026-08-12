"""The ADK agent: Gemini orchestrates the conversation, Snowflake Cortex reasons about data.

Gemini decides *which* question is being asked and how to present the answer. It never writes
SQL itself unless Cortex is unreachable - every claim about Atlanta transit is produced by a
Cortex REST call against harvested data.
"""

from __future__ import annotations

import os
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from google.adk.agents import Agent

from atl_transit.cortex import SCHEMA, Cortex, CortexError
from atl_transit.realtime import vehicle_positions
from atl_transit.store import open_store

MAX_ROWS = 50

INSTRUCTION = """\
You answer questions about Atlanta's MARTA transit network and how its service relates to the
neighbourhoods the City of Atlanta has formally designated Communities of Concern.

Always call `ask_transit` to answer any factual question. Never invent a number, and never
answer from memory - the data is the only source of truth.

When you present an answer:
- Lead with the direct answer and the specific numbers.
- Name the neighbourhood or route in plain English, not by ID.
- If the data shows no meaningful difference, say so. Do not manufacture a problem that is not
  there. MARTA's median weekday service is roughly equal inside and outside Communities of
  Concern, and saying so honestly is a correct answer.
- Offer one natural follow-up question the data could also answer.

Use `run_sql` only if `ask_transit` reports that Cortex is unavailable.
Use `live_vehicles` when asked what is happening right now."""


def jsonable(value: Any) -> Any:  # noqa: ANN401 - accepts whatever a driver returns
    """Convert a database value into something the ADK event stream can serialise.

    Snowflake returns ``Decimal`` for numeric columns and ``date``/``datetime`` for temporal
    ones, none of which are JSON-serialisable. DuckDB returns plain floats, so this only bites
    against the deployed Store.

    Args:
        value: A single cell from a query result.

    Returns:
        The value as a JSON-safe primitive.
    """
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    return value


def _render(columns: list[str], rows: list[tuple[Any, ...]]) -> str:
    """Render rows as a compact text table for a model to read."""
    header = " | ".join(columns)
    body = "\n".join(" | ".join("" if v is None else str(v) for v in row) for row in rows)
    return f"{header}\n{body}"


def ask_transit(question: str) -> dict[str, Any]:
    """Answer a question about Atlanta transit using harvested MARTA and equity data.

    Snowflake Cortex turns the question into SQL, the Store runs it, and Cortex turns the
    resulting rows back into a plain-language answer.

    Args:
        question: A natural-language question about MARTA stops, routes, service frequency,
            or Atlanta's Communities of Concern.

    Returns:
        The plain-language answer, the SQL that produced it, and the rows themselves so the
        interface can render a table or chart.
    """
    try:
        cortex = Cortex()
        sql = cortex.write_sql(question)
    except CortexError as exc:
        return {"error": f"Cortex unavailable: {exc}", "schema": SCHEMA}
    try:
        columns, rows = open_store().query(sql)
    except Exception as exc:  # noqa: BLE001 - surface any driver error to the model
        return {"error": f"Query failed: {exc}", "sql": sql, "schema": SCHEMA}
    capped = rows[:MAX_ROWS]
    summary = cortex.summarise(question, _render(columns, capped))
    return {
        "summary": summary,
        "sql": sql,
        "columns": columns,
        "rows": [[jsonable(v) for v in r] for r in capped],
        "row_count": len(rows),
    }


def run_sql(sql: str) -> dict[str, Any]:
    """Run a SQL query directly against the Store. Use only if Cortex is unavailable.

    Args:
        sql: A single SELECT statement against STOPS, STOP_FREQUENCY, ROUTES or COC_AREA.

    Returns:
        The column names and rows, or an error message.
    """
    try:
        columns, rows = open_store().query(sql)
    except Exception as exc:  # noqa: BLE001 - surface any driver error to the model
        return {"error": str(exc), "schema": SCHEMA}
    return {
        "columns": columns,
        "rows": [[jsonable(v) for v in r] for r in rows[:MAX_ROWS]],
        "row_count": len(rows),
    }


def live_vehicles() -> dict[str, Any]:
    """Report where MARTA vehicles are right now, from the live GTFS-realtime feed.

    Returns:
        The number of vehicles currently reporting and a sample of their positions.
    """
    try:
        vehicles = vehicle_positions()
    except Exception as exc:  # noqa: BLE001 - the live feed is best-effort
        return {"error": f"Live feed unavailable: {exc}"}
    return {"vehicle_count": len(vehicles), "vehicles": vehicles[:MAX_ROWS]}


root_agent = Agent(
    name="atl_transit",
    # gemini-2.5-* is retired for new keys. The free tier allows only 20 requests per day
    # PER MODEL, so development and the demo deliberately run on different models.
    model=os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite"),
    description="Answers questions about MARTA service and Atlanta transit equity.",
    instruction=INSTRUCTION,
    tools=[ask_transit, run_sql, live_vehicles],
)
