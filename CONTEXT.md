# Atlanta Civic Data Agent

A conversational agent that answers natural-language questions about Atlanta public
transit data, rendering its answers as generated UI rather than text. Built for Hack
RenderATL 2026.

## Language

### Domain

**Harvest**:
The scheduled ingestion of a public dataset from its source into our own store.
_Avoid_: Sync, scrape, ETL, refresh

**Service Frequency**:
The number of transit trips serving a given stop over a given period. The primary
measure behind every equity claim the agent makes.
_Avoid_: Headway, service level

**Transit Desert**:
An inhabited area whose Service Frequency falls below the threshold needed to reach
essential services by transit. A conclusion the data supports, never a field in it.
_Avoid_: Underserved area, transit gap

**Stop**:
A single boarding location. The unit that Service Frequency is measured against.

**Route**:
A named public-facing transit line. One Route serves many Stops.

**Trip**:
One scheduled traversal of a Route at a specific time. Counting Trips per Stop
yields Service Frequency.

### Protocols

These three are routinely confused with one another. They are not interchangeable.

**A2UI**:
Google's Agent-to-UI spec. The agent emits declarative UI blueprints; the client
renders them with its own components. This is how our answers become interfaces.
_Avoid_: Generative UI, AG-UI, A2A

**AG-UI**:
CopilotKit's Agent-User Interaction protocol. The transport carrying events between
our agent and the frontend. Complementary to A2UI, which rides on top of it.
_Avoid_: A2UI, CopilotKit protocol

**A2A**:
Google's Agent-to-Agent protocol, for delegation between separate agents.
Deliberately unused — we run a single agent. Named here only to keep it distinct
from A2UI.
_Avoid_: Using it as a synonym for A2UI

### Storage

**Store**:
The queryable home of harvested data, reached through one adapter interface so the
backing engine can change without touching the agent.
_Avoid_: Database, warehouse, cache
