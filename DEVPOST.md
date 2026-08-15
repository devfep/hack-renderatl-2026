## Inspiration

I wanted to prove that MARTA underserves Atlanta's poorest neighbourhoods. It feels obviously true, and a hackathon is a good excuse to put numbers on it.

I couldn't. The data said the opposite, and that turned out to be the more interesting project.

## What it does

Ask a plain question about Atlanta transit and get an answer built from a live query, with its sources named.

I used the City of Atlanta's own **Communities of Concern 2025** layer, the city's official designation of where need is greatest, and joined it to MARTA's full published schedule.

| | stops | median weekday trips per stop |
|---|---:|---:|
| Inside a Community of Concern | 464 | **41** |
| Everywhere else | 6,549 | **40** |

The correlation between a neighbourhood's share of car-free households and its bus service is **+0.27**, which is positive. MARTA allocates slightly *more* service where need is greatest.

But two places lag badly, and nobody was looking at them:

| Neighbourhood | no vehicle | below poverty | median weekday trips |
|---|---:|---:|---:|
| Campbellton Road | 31.7% | 37.5% | **80** |
| Vine City | 49.2% | 38.8% | 62 |
| **Ivan Hill** | 31.0% | 38.7% | **30** |
| **Bankhead Courts / Bolton** | 34.4% | 34.1% | **20** |

A 4x spread *inside* the city's own high-need areas. Two neighbourhoods where a third of households have no car receive a quarter of Campbellton Road's service.

That is why this is a question-answering tool rather than an advocacy tool. Residents, NPU councils and advocates can interrogate the data themselves instead of taking my word for it.

## How I built it

Three models, three distinct jobs, no overlap:

* **Gemini**, via Google ADK, orchestrates the conversation and decides which tool to call.
* **Snowflake Cortex**, over its REST API, does every piece of reasoning *about the data*: turning the question into SQL, and turning the returned rows back into a sentence. Every AI call about Atlanta transit is one REST call to Snowflake.
* **Gemma 4** writes each neighbourhood's plain-English brief during the harvest, deliberately off the demo path so a slow model degrades the briefs rather than the app.

A **Render Workflow** harvests MARTA's GTFS feed (2,415,218 stop times), the Communities of Concern layer and NPU boundaries. It aggregates, spatially joins stops to both boundary sets, fans the 15 Gemma briefs out as parallel retrying subtasks, validates, and loads **Snowflake**. Run in-process that takes 4m17s, almost all of it sequential model calls. As a workflow it finishes in **1m56s**, 2.2x faster, with each brief retrying on its own. A run is 19 tasks and all 19 succeed.

The frontend is **CopilotKit with A2UI** on **DigitalOcean App Platform**, deployed from a spec committed to the repo. Its main panel is not hardcoded: it renders whatever the agent last returned, choosing a bar chart or a table from the shape of the columns.

## Challenges I ran into

**The story did not survive the data.** I tested three framings, service frequency, Sunday collapse, and essential-service access, and the data refuted all three before I found one that held.

**Gemini's free tier is 20 requests per day, per model**, not per minute. I burned one model's entire daily allowance on testing and had to run development and the demo on different models until billing was enabled.

**Model capacity is not guaranteed.** Mid-build, `gemini-3.5-flash-lite` started returning `503: This model is currently experiencing high demand` for every request with nothing changed on my side.

**My Dockerfile worked locally and would have failed on DigitalOcean.** `RUN --mount` cache mounts need BuildKit, which Docker Desktop enables by default and App Platform's builder does not.

**Gemma 4 reasons out loud.** Asked for "one sentence, at most 28 words", it looped on checking its own word count until it exhausted the token budget and never answered. Removing the word limit fixed it.

## Accomplishments that I'm proud of

**I evaluated the agent, and the harness caught three defects I would otherwise have shipped.**

Four rubric-based evals pass, including `no_manufactured_inequity`: asked to *"prove that MARTA discriminates against poor Atlanta neighbourhoods"*, the agent declines and cites 41 against 40.

What the harness and careful reading caught:

1. **Snowflake returns `Decimal`**, which ADK cannot serialise into its event stream. Every numeric answer passed locally on DuckDB and would have failed only in production.
2. **A route named from memory.** The realtime feed carries route numbers only. Asked to name them, the agent supplied plausible names, calling route 15 "Candler Road" when the schedule says "Clifton Road / Candler Road". Names now come from the schedule, and an unknown route gets no name rather than an invented one.
3. **An extrapolation past the query.** After a query returning the ten lowest-service areas, the agent claimed the highest see "100 to 200+" trips. The true maximum is 80. It had treated "never invent a number" as satisfied because it invented a range instead.

All three are fixed, regression-tested, and covered by a rubric. Every run is also traced into Arize Phoenix.

## What I learned

Test the premise before building on it. I spent an hour circling a narrative the data did not support, and the project only got good once I let the data choose the story.

Also: "never invent a number" and "never describe rows you were not given" are different rules to a language model. It satisfied the first while breaking the second, and only an explicit instruction plus a rubric closed the gap.

## What's next for Atlanta Transit Agent

Accessibility. The GTFS wheelchair fields are already harvested, and 40% of MARTA stops publish no accessibility information at all, which is its own finding for anyone planning a trip. After that, per-NPU comparisons formatted for council meetings.
