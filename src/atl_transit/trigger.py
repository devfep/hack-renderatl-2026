"""The scheduled entrypoint: start the harvest workflow, or run it inline if there isn't one.

Render Workflows has no native scheduling, so a cron job starts the run. Falling back to an
inline harvest means the schedule keeps working before the Workflow service exists, and keeps
working if it is ever removed.
"""

from __future__ import annotations

import os
import sys

from render_sdk import Render

from atl_transit.harvest import main as harvest_main

TASK = "harvest"


def main() -> int:
    """Start the harvest, preferring the workflow when one is configured.

    Returns:
        A process exit code.
    """
    slug = os.environ.get("RENDER_WORKFLOW_SLUG", "").strip()
    if not slug or not os.environ.get("RENDER_API_KEY"):
        print("no workflow configured - running the harvest inline")
        return harvest_main()

    print(f"starting workflow task {slug}/{TASK}")
    run = Render().workflows.start_task(f"{slug}/{TASK}", ["cron"])
    print(f"started: {run}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
