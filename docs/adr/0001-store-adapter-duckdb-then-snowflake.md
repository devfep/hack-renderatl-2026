# Store adapter: DuckDB locally, Snowflake in the deployed app

The agent reaches harvested data through a single Store adapter interface. DuckDB
backs it locally; Snowflake backs it once credentials are working. We build and
demo against DuckDB first and switch the adapter afterwards.

## Context

Snowflake is worth a prize track and makes the Render Workflow legitimate — a
harvest that fetches, normalises, loads and validates has real failure modes, which
is a far better Workflows story than refreshing a cache. But a brand-new trial
account is an unknown quantity on a same-day deadline: provisioning, auth, MFA and
region-gated Cortex features are all discovered rather than known.

Wiring the agent directly to Snowflake would put an unproven dependency on the
demo's critical path. If it fails at 18:00 there is no submission at all.

## Consequences

Snowflake failing costs us one prize track instead of the entire project. The price
is one indirection we would not otherwise write, and the discipline of keeping the
DuckDB path working rather than deleting it once Snowflake is live.

The adapter boundary is deliberately narrow — parameterised SQL in, rows out. Any
Cortex-specific capability lives behind its own seam, so it cannot quietly become
load-bearing for the core demo.
