# Handoff

Paste this into a fresh session to pick the project up.

---

## What this is

**Atlanta Transit Agent** — a conversational agent that answers questions about MARTA service
and Atlanta's transit equity, built solo for Hack RenderATL 2026 (12 Aug 2026).

**It won Best Use of Atlanta Open Data (1st) and Render Workflows (3rd).**

Repo: https://github.com/devfep/hack-renderatl-2026

## Deployments (torn down 15 Aug 2026)

The three DigitalOcean apps were destroyed after judging. **App Platform has no free tier for
services** — the free tier covers static sites only — so the demo was costing $49/month:

| App | Slug | $/mo |
|---|---|---:|
| `atl-transit` (agent API) | `apps-s-1vcpu-1gb` | 12 |
| `atl-transit-ui` | `apps-s-1vcpu-2gb` | 25 |
| `atl-transit-phoenix` | `apps-s-1vcpu-1gb` | 12 |

Two of those are *professional*-tier slugs that cost more than the basic equivalent at identical
specs (`apps-s-1vcpu-1gb` $12 vs `basic-xs` $10; `apps-s-1vcpu-2gb` $25 vs `basic-s` $20). Use
the basic slugs if this is ever redeployed.

Nothing was actually paid: the 12-15 Aug usage came to $3.72 and was fully offset by a "Credit
for using DigitalOcean at MLH Hackathons" line, leaving an August balance of $0.00. The $49/month
above is list price, not out-of-pocket. A credit is finite and dated where a free tier is not, so
check the remaining balance and its expiry before assuming a redeploy is free.

The Render Workflow (`atl-transit-harvest`) was deleted the same day. It cost nothing at rest —
it bills per run — but it held env-var copies of the credentials, so it went with everything else.
The `atl-harvest-trigger` cron in `render.yaml` was never applied in the first place.

Recreating it is the `render workflows create` command in the README's Deploying section. Note
the CLI cannot *delete* a workflow: `render workflows` has no delete subcommand and `render
services delete` resolves only `srv-`/`crn-` IDs, not `wfl-`. Use the dashboard.

All specs are committed and reproduce the deployments exactly (verified by diff against the live
specs before deletion): `.do/app.yaml`, `.do/ui.yaml`, `.do/phoenix.yaml`, `render.yaml`.

**Redeploying costs money from the first minute.** Before pointing anyone at a public URL again,
note that the UI is unauthenticated: anyone with the link drives Gemini calls and Snowflake Cortex
queries on your account, with no cap. Set a Google Cloud budget and a Snowflake resource monitor
first.

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

1. **Gemini free tier is 20 requests/day/model.** Billing was enabled during the build, which
   also means an exposed key bills you; see Credentials below.
2. **DigitalOcean's builder has no BuildKit.** No `RUN --mount` in any Dockerfile.
3. **Snowflake returns `Decimal`**, which ADK cannot serialise. `agent.jsonable()` handles it.
4. **Gemma 4 reasons out loud.** Never give it a word-count constraint; it loops to MAX_TOKENS.
5. **`.dockerignore` must exclude nested `.venv`**, or the host venv overwrites the container's.
6. **Render Blueprints cannot declare Workflows.** Created via `render workflows create`.
7. **The model is env-overridable (`GEMINI_MODEL`)** because capacity 503s happen.

## Credentials

Nothing sensitive is or was committed — `.gitignore` covers `.env` and `.env.*`, and `git
ls-files` confirms only `.env.example` is tracked. The local `.env` and `atl-ui/.env` still hold
the working values.

Destroying the apps removed the only public path to these keys but did not invalidate them, so
the two that could bill were revoked at the provider:

| Credential | Where | Status | Why it mattered |
|---|---|---|---|
| `GOOGLE_API_KEY` | Google AI Studio | Revoked | Billing enabled — pay-as-you-go, no cap |
| `SF_PAT` | Snowflake, `ACCOUNTADMIN` | Revoked | Cortex bills per token; the role can do anything |
| `COPILOTKIT_LICENSE_TOKEN`, `INTELLIGENCE_API_KEY` | CopilotKit Cloud | Left alone | Free tier, self-expires 2026-09-11 |

CopilotKit needed no action: `npx copilotkit@latest license list` reports a free-tier, 5-seat
license expiring 2026-09-11, so no payment method sits behind it and it revokes itself. Both keys
were server-side only — `next.config.ts` bakes a derived `"true"`/`"false"` into the client
bundle, never the token. The license belongs to the `RenderATL MLH Hackathon` org, where this
account is not an admin; `dashboard.operations.copilotkit.ai` is the place to rotate if ever
needed, and the CLI has no read-only listing for the project-scoped Intelligence key.

The values in the local `.env` and `atl-ui/.env` are therefore dead for Google and Snowflake.
Any redeploy needs fresh ones.

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
