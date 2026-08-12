"""AG-UI bridge for the Atlanta transit agent.

The agent, its instruction and its three tools all come from the `atl_transit` package, so
this frontend and the ADK deployment answer with exactly the same logic. Nothing about the
domain lives here - this file only exposes the agent over AG-UI, and starts tracing.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

# Order matters: instrumentation patches ADK at import time, so tracing has to start before
# anything pulls ADK in. Imports below this line are deliberately not at the top of the file.
from atl_transit import tracing  # noqa: E402

tracing.start()

import uvicorn  # noqa: E402
from ag_ui_adk import ADKAgent, add_adk_fastapi_endpoint  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from google.adk.agents import LlmAgent  # noqa: E402

from atl_transit.agent import (  # noqa: E402
    INSTRUCTION,
    ask_transit,
    live_vehicles,
    run_sql,
)

root_agent = LlmAgent(
    name="atl_transit",
    model=os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite"),
    description="Answers questions about MARTA service and Atlanta transit equity.",
    instruction=INSTRUCTION,
    tools=[ask_transit, run_sql, live_vehicles],
)

adk_agent = ADKAgent(
    adk_agent=root_agent,
    app_name="atl_transit",
    user_id="rider",
    use_in_memory_services=True,
)

app = FastAPI(title="Atlanta Transit Agent")
add_adk_fastapi_endpoint(app, adk_agent, path="/")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))  # noqa: S104
