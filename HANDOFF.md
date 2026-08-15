# Handoff

Paste this into a fresh session to pick the project up.

---

## What this is

**Atlanta Transit Agent** — a conversational agent that answers questions about MARTA service
and Atlanta's transit equity, built solo for Hack RenderATL 2026 (12 Aug 2026).

**It won Best Use of Atlanta Open Data (1st) and Render Workflows (3rd).**

Repo: https://github.com/devfep/hack-renderatl-2026

## Live deployments (all verified up)

| What | URL |
|---|---|
| App (CopilotKit + A2UI) | https://atl-transit-ui-duzrs.ondigitalocean.app |
| Traces (Arize Phoenix) | https://atl-transit-phoenix-mi8iu.ondigitalocean.app |
| Agent API (ADK dev UI) | https://atl-transit-wra5i.ondigitalocean.app/dev-ui/ |

Three DigitalOcean apps, one Render Workflow (`atl-transit-harvest`), one Snowflake account.
All specs are committed: `.do/app.yaml`, `.do/ui.yaml`, `.do/phoenix.yaml`, `render.yaml`.

## The finding

Joining the City of Atlanta's **Communities of Concern 2025** layer to MARTA's schedule:

- Inside a Community of Concern: 464 stops, median **41** weekday trips per stop
- Everywhere else: 6,549 stops, median **40**
- Correlation between car-free households and service: **+0.27** (positive)

So MARTA broadly allocates service toward need. But two areas lag at comparable need:
**Ivan Hill** (31.0% carless, 30 trips) and **Bankhead Courts / Bolton** (34.4% carless, 20
trips), against **Campbellton Road** (31.7% carless, 80 trips). A 4x spread inside the city's
own high-need areas.

## Architecture

Three models, three jobs, deliberately no overlap:

- **Gemini** (Google ADK 2.6.3) orchestrates conversation and tool choice. Never writes SQL.
- **Snowflake Cortex** over its REST API does all reasoning *about data*: question to SQL,
  rows back to prose.
- **Gemma 4** (`gemma-4-31b-it`) writes one plain-English brief per Community of Concern
  during the harvest. Offline, off the demo path.

A **Render Workflow** harvests MARTA GTFS (2.4M stop times) plus two City of Atlanta ArcGIS
layers, aggregates to 49k frequency rows, spatially joins stops to NPU and CoC polygons, fans
15 Gemma briefs out in parallel, validates, and loads Snowflake. 4m17s in-process becomes
1m56s as a workflow; 19 tasks per run.

## Key files

| Path | |
|---|---|
| `src/atl_transit/harvest.py` | Fetch, aggregate, spatial join, validate, load |
| `src/atl_transit/store.py` | Store adapter: DuckDB locally, Snowflake deployed |
| `src/atl_transit/cortex.py` | Cortex REST client + the SCHEMA prompt |
| `src/atl_transit/agent.py` | ADK agent, three tools, source citations |
| `src/atl_transit/gemma.py` | Gemma briefs + defensive output extraction |
| `src/atl_transit/workflow.py` | Render Workflow task definitions |
| `atl-ui/` | Next.js + CopilotKit frontend; `agent/main.py` is the AG-UI bridge |
| `evals/` | ADK eval set and criteria |
| `CONTEXT.md`, `docs/adr/` | Glossary and decisions |

## Conventions

- Python 3.13, `uv`, `ruff` 0.13 (pinned low because render_sdk caps it), `ty`, pytest
- 40 tests, 4/4 evals passing; a git `pre-push` hook runs lint + types + tests
- Direct pushes to `main` are allowed in this repo via `.claude/allow-main-push`
- Commit messages: imperative, no Co-Authored-By trailer
- Store defaults to DuckDB so the repo runs with no credentials; `ATL_STORE=snowflake` deployed

## Gotchas that cost real time

1. **Gemini free tier is 20 requests/day/model.** Billing is now enabled; don't let it lapse.
2. **DigitalOcean's builder has no BuildKit.** No `RUN --mount` in any Dockerfile.
3. **Snowflake returns `Decimal`**, which ADK cannot serialise. `agent.jsonable()` handles it.
4. **Gemma 4 reasons out loud.** Never give it a word-count constraint; it loops to MAX_TOKENS.
5. **`.dockerignore` must exclude nested `.venv`**, or the host venv overwrites the container's.
6. **Render Blueprints cannot declare Workflows.** Created via `render workflows create`.
7. **The model is env-overridable (`GEMINI_MODEL`)** because capacity 503s happen.

## Known limitations (be honest about these)

- **Measures service at stops that exist.** Says nothing about areas with no stop at all.
  This is the biggest gap and the most valuable next build.
- Scheduled service only. No reliability or on-time performance.
- The MARTA-wide median of **40 is hardcoded** in `gemma.py`'s prompt rather than computed.
  Fix this if the data is refreshed.
- Phoenix has no auth and no persistent disk; traces vanish on restart.
- MARTA is a separate authority from the City of Atlanta. Different levers.

## Open threads

1. **Coverage analysis** is the natural next build and closes the main limitation: which
   populated areas have no stop within walking distance. Needs a population or parcel layer
   joined to the existing stop geometry.
2. **Accessibility**: 40% of MARTA stops publish no wheelchair information at all. The field
   is already harvested and never surfaced. A rider planning a trip cannot use "unknown".
3. **Compute the network median** rather than hardcoding 40 in `gemma.py`'s prompt.
4. Someone with City of Atlanta ties asked to talk at the awards ceremony but contact details
   were never exchanged. If they surface, the question worth asking is whether coverage is
   more useful to them than frequency.

## What I'd want from a fresh session

State the goal, then work in this style: verify facts against live data before asserting them,
push back when a premise looks wrong, and keep the lint/type/test gate green.
