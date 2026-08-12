"""Snowflake Cortex over its REST API.

Every piece of reasoning *about the data* happens here: turning a rider's question into SQL,
and turning the resulting rows back into a sentence. Each is one POST to Snowflake.
"""

from __future__ import annotations

import os
import re

import requests

CHAT_PATH = "/api/v2/cortex/v1/chat/completions"

SCHEMA = """\
STOPS(STOP_ID, STOP_NAME, LAT, LON, WHEELCHAIR_BOARDING, NPU, COC_NAME, COC_TIER,
      COC_NEIGHBORHOODS, PCT_NO_VEHICLE, PCT_POVERTY)
  -- one row per MARTA stop. NPU is a City of Atlanta planning unit letter ('A'..'Z') and is
  -- NULL for stops outside city limits. COC_* columns are non-NULL only for stops inside one
  -- of Atlanta's 15 official Communities of Concern; PCT_NO_VEHICLE is the share of households
  -- there with no car.
STOP_FREQUENCY(STOP_ID, SERVICE_DAY, TRIP_COUNT)
  -- scheduled trips serving a stop on a given day. SERVICE_DAY is lowercase 'monday'..'sunday'.
  -- Use SERVICE_DAY='monday' for a typical weekday.
ROUTES(ROUTE_ID, ROUTE_SHORT_NAME, ROUTE_LONG_NAME, ROUTE_TYPE)
  -- ROUTE_TYPE: 0=streetcar, 1=heavy rail, 3=bus.
COC_AREA(COC_NAME, NEIGHBORHOODS, COC_TIER, PCT_NO_VEHICLE, PCT_POVERTY,
         PCT_TRANSIT_COMMUTE, STOP_COUNT, MEDIAN_WEEKDAY_TRIPS, BRIEF)
  -- BRIEF is a one-sentence plain-English summary of the area, written during the harvest.
  -- Select it whenever the question is about a specific neighbourhood, and quote it verbatim.
  -- one row per Community of Concern. COC_NAME is an internal code like 'NSA H01' - NEVER show
  -- it to a user. ALWAYS select NEIGHBORHOODS instead, which holds the real place names
  -- ('Vine City', 'Mechanicsville'). MEDIAN_WEEKDAY_TRIPS is ALREADY a
  -- per-stop figure: the median Monday TRIP_COUNT across the stops in that area. Never divide
  -- it by STOP_COUNT. STOP_COUNT is only how many stops the area contains.
  -- PCT_* columns are percentages already (49.2 means 49.2%), never fractions.

For network-wide context: the median stop has about 40 weekday trips, and median service
inside and outside Communities of Concern is roughly equal (41 vs 40)."""

SQL_PROMPT = """\
You are a SQL expert. Write ONE query answering the question, against this schema:

{schema}

Rules:
- Return only SQL. No markdown fences, no explanation, no trailing semicolon.
- Use only the tables and columns above.
- Prefer SERVICE_DAY='monday' when the question says "weekday" or does not specify a day.
- Always LIMIT to at most 50 rows unless the question asks for a single aggregate.

Question: {question}"""

ANSWER_PROMPT = """\
A rider asked: {question}

This data answers it:
{rows}

Reply in at most three sentences, plainly, for someone who does not read SQL. Quote the
specific numbers. If the data shows no meaningful difference, say so plainly rather than
implying a problem exists."""


class CortexError(RuntimeError):
    """Raised when Snowflake Cortex cannot be reached or refuses a request."""


class Cortex:
    """A thin client over Snowflake's Cortex inference REST endpoint."""

    def __init__(self, account: str | None = None, token: str | None = None) -> None:
        """Configure from the SF_* environment variables unless overridden.

        Args:
            account: The ``<org>-<account>`` identifier. Defaults to ``SF_ACCOUNT``.
            token: A programmatic access token. Defaults to ``SF_PAT``.

        Raises:
            CortexError: If neither argument nor environment supplies a value.
        """
        self.account = account or os.environ.get("SF_ACCOUNT", "")
        self.token = token or os.environ.get("SF_PAT", "")
        self.model = os.environ.get("SF_CORTEX_MODEL", "claude-sonnet-4-5")
        if not self.account or not self.token:
            msg = "SF_ACCOUNT and SF_PAT must be set to use Cortex."
            raise CortexError(msg)

    @property
    def base_url(self) -> str:
        """The account's Snowflake REST base URL."""
        return f"https://{self.account}.snowflakecomputing.com"

    def complete(self, prompt: str, timeout: int = 60) -> str:
        """Run one inference request.

        Args:
            prompt: The user message to send.
            timeout: Request timeout in seconds.

        Returns:
            The model's reply text.

        Raises:
            CortexError: If Snowflake returns an error or an unexpected payload.
        """
        response = requests.post(
            f"{self.base_url}{CHAT_PATH}",
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "X-Snowflake-Authorization-Token-Type": "PROGRAMMATIC_ACCESS_TOKEN",
            },
            json={"model": self.model, "messages": [{"role": "user", "content": prompt}]},
            timeout=timeout,
        )
        if not response.ok:
            msg = f"Cortex returned {response.status_code}: {response.text[:300]}"
            raise CortexError(msg)
        try:
            return response.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError) as exc:
            msg = f"Unexpected Cortex payload: {response.text[:300]}"
            raise CortexError(msg) from exc

    def write_sql(self, question: str) -> str:
        """Turn a natural-language question into a single SQL query.

        Args:
            question: The rider's question.

        Returns:
            One SQL statement, stripped of fences and trailing punctuation.
        """
        raw = self.complete(SQL_PROMPT.format(schema=SCHEMA, question=question))
        return strip_sql(raw)

    def summarise(self, question: str, rows: str) -> str:
        """Turn query results back into a plain-language answer.

        Args:
            question: The original question.
            rows: A rendered table of results.

        Returns:
            A short answer suitable for a non-technical reader.
        """
        return self.complete(ANSWER_PROMPT.format(question=question, rows=rows)).strip()


def strip_sql(raw: str) -> str:
    """Remove markdown fences and trailing semicolons from a model's SQL reply.

    Args:
        raw: The model's raw reply.

    Returns:
        Bare SQL.
    """
    text = raw.strip()
    fenced = re.match(r"^```(?:sql)?\s*(.*?)\s*```$", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1)
    return text.strip().rstrip(";").strip()
