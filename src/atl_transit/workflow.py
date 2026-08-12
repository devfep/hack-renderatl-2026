"""The harvest as a Render Workflow.

Running the harvest in-process takes about four minutes, almost all of it fifteen sequential
Gemma calls. As a workflow the briefs fan out as independent subtasks that run in parallel and
retry individually, so one flaky model call no longer costs the whole run.

Blueprints do not yet support Workflows, so the service itself is created in the Render
dashboard against this module. The task definitions are the part that lives in code.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pandas as pd
from render_sdk import Retry, Workflows

from atl_transit.gemma import brief_for
from atl_transit.harvest import build_tables, fetch_sources, validate
from atl_transit.store import open_store

WORKDIR = Path("data/raw")

# The upstream feeds are public endpoints with no SLA, so fetching retries hardest.
NETWORK_RETRY = Retry(max_retries=5, wait_duration_ms=3000, backoff_scaling=2.0)
MODEL_RETRY = Retry(max_retries=3, wait_duration_ms=2000, backoff_scaling=2.0)

app = Workflows(default_retry=Retry(max_retries=2, wait_duration_ms=1000), default_timeout=900)


@app.task(retry=NETWORK_RETRY, timeout_seconds=900)
def load_core_tables() -> dict[str, int]:
    """Download the feeds, aggregate them, and load every table except the briefs.

    Returns:
        Row counts per table, so a truncated upstream feed is visible in the run log.
    """
    fetch_sources(WORKDIR)
    frames = build_tables(WORKDIR, enrich=False)
    validate(frames)
    store = open_store()
    return {table: store.load_frame(frame, table) for table, frame in frames.items()}


@app.task(timeout_seconds=120)
def list_areas() -> list[dict[str, Any]]:
    """Read back the Communities of Concern that need a brief.

    Returns:
        One entry per area, carrying just the figures Gemma needs.
    """
    columns, rows = open_store().query(
        "SELECT COC_NAME, NEIGHBORHOODS, PCT_NO_VEHICLE, PCT_POVERTY, MEDIAN_WEEKDAY_TRIPS "
        "FROM COC_AREA"
    )
    index = {name: position for position, name in enumerate(columns)}
    return [
        {
            "coc_name": row[index["COC_NAME"]],
            "neighborhoods": row[index["NEIGHBORHOODS"]],
            "pct_no_vehicle": float(row[index["PCT_NO_VEHICLE"]] or 0),
            "pct_poverty": float(row[index["PCT_POVERTY"]] or 0),
            "median_trips": float(row[index["MEDIAN_WEEKDAY_TRIPS"]] or 0),
        }
        for row in rows
    ]


@app.task(retry=MODEL_RETRY, timeout_seconds=180)
def write_area_brief(area: dict[str, Any]) -> dict[str, str]:
    """Write one neighbourhood's brief. This is the task that fans out.

    Args:
        area: One entry from :func:`list_areas`.

    Returns:
        The area's key and its brief, empty if Gemma produced nothing usable.
    """
    return {"coc_name": area["coc_name"], "brief": brief_for(area)}


@app.task(timeout_seconds=300)
def store_briefs(briefs: list[dict[str, str]]) -> dict[str, int]:
    """Attach the fanned-out briefs to COC_AREA.

    Args:
        briefs: Results from every :func:`write_area_brief` subtask.

    Returns:
        How many areas were written and how many received a usable brief.
    """
    columns, rows = open_store().query("SELECT * FROM COC_AREA")
    frame = pd.DataFrame(rows, columns=pd.Index(columns))
    by_name = {b["coc_name"]: b["brief"] for b in briefs}
    frame["BRIEF"] = frame["COC_NAME"].map(by_name).fillna("")
    written = open_store().load_frame(frame, "COC_AREA")
    return {"areas": written, "with_brief": int((frame["BRIEF"] != "").sum())}


@app.task(timeout_seconds=3600)
async def harvest(_trigger: str = "cron") -> dict[str, Any]:
    """Run the whole harvest: load the tables, then fan the briefs out in parallel.

    Args:
        _trigger: Ignored; present so a cron job can record why the run started.

    Returns:
        Row counts from the load and how many briefs were written.
    """
    counts = await load_core_tables()
    areas = await list_areas()
    briefs = await asyncio.gather(*[write_area_brief(area) for area in areas])
    stored = await store_briefs(list(briefs))
    return {"tables": counts, "briefs": stored}


if __name__ == "__main__":
    app.start()
