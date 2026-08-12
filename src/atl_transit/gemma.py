"""Gemma 4: batch enrichment during harvest.

Gemma turns each Community of Concern's raw percentages into one plain sentence a resident
would actually read. This runs offline in the harvest, never on the demo path, so a slow or
failing model degrades the briefs rather than the app.
"""

from __future__ import annotations

import os
import re
from typing import Any

import requests

MODEL = os.environ.get("GEMMA_MODEL", "gemma-4-31b-it")
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

# Word-count constraints send Gemma into an unbounded self-checking loop that exhausts the
# token budget before it answers. State the facts, ask for prose, impose no counting task.
BRIEF_PROMPT = """\
Facts about an Atlanta neighbourhood:
- Name: {neighborhoods}
- Households with no vehicle: {pct_no_vehicle}%
- Below poverty line: {pct_poverty}%
- Median weekday bus trips per stop: {median_trips}
- Median weekday bus trips per stop across all of MARTA: 40

Restate these as one short, factual, neutral sentence for a resident reading a transit
report. Do not editorialise or recommend anything.

Answer immediately, with no preamble and no reasoning."""


MIN_WORDS = 8
MIN_DIGITS = 4
COMMENTARY = ("i ", "the prompt", "let", "wait", "okay", "sure", "here", "one more", "is ")
# Gemma labels its attempts ("Draft 3:", "Final answer:") before the sentence itself.
LABEL = re.compile(
    r"^(?:draft|final|answer|option|version|attempt)\s*\d*\s*:?\s*\*?\s*", re.IGNORECASE
)


def best_sentence(raw: str) -> str:
    """Pull the one usable sentence out of a reasoning model's reply.

    Gemma 4 volunteers commentary and often echoes its answer twice, once quoted. The first
    complete sentence of at least :data:`MIN_WORDS` words is reliably the answer.

    Args:
        raw: The model's full reply.

    Returns:
        A single clean sentence, or '' if the model never produced one.
    """
    text = " ".join(raw.replace("\r", "").split())
    quoted = re.search(r'"([^"]{40,})"', text)
    if quoted:
        text = quoted.group(1)
    # Split only where punctuation is followed by whitespace, so "34.4%" stays intact.
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        cleaned = LABEL.sub("", sentence.strip().lstrip("*-#| ").strip()).strip()
        if _is_brief(cleaned):
            return cleaned
    return ""


def _is_brief(candidate: str) -> bool:
    """Judge whether a sentence is the answer rather than the model's commentary.

    A real brief always cites at least two figures, which reliably separates it from
    self-narration like "is factual, simply stating the numbers is more neutral".
    """
    if len(candidate.split()) < MIN_WORDS:
        return False
    if len(re.findall(r"\d", candidate)) < MIN_DIGITS:
        return False
    return not candidate.lower().startswith(COMMENTARY)


def brief_for(row: dict[str, Any], timeout: int = 60) -> str:
    """Write one neighbourhood brief. The unit the Render Workflow fans out.

    Args:
        row: Keys ``neighborhoods``, ``pct_no_vehicle``, ``pct_poverty``,
            ``median_trips``.
        timeout: Request timeout in seconds.

    Returns:
        One plain sentence, or '' if Gemma never produced one.
    """
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        return ""
    return _one_brief(row, api_key, timeout)


def _one_brief(row: dict[str, Any], api_key: str, timeout: int) -> str:
    """Ask Gemma for a single neighbourhood brief, returning '' if it declines."""
    response = requests.post(
        ENDPOINT.format(model=MODEL),
        params={"key": api_key},
        json={
            "contents": [{"parts": [{"text": BRIEF_PROMPT.format(**row)}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 8192},
        },
        timeout=timeout,
    )
    response.raise_for_status()
    parts = response.json()["candidates"][0]["content"]["parts"]
    return best_sentence(" ".join(p.get("text", "") for p in parts))


def write_briefs(frame: Any, timeout: int = 60) -> Any:  # noqa: ANN401
    """Add a BRIEF column to the COC_AREA frame, one plain sentence per area.

    Best-effort: any area Gemma cannot describe gets an empty brief rather than failing the
    harvest, because a missing sentence is survivable and a failed harvest is not.

    Args:
        frame: The COC_AREA DataFrame, with columns already uppercased.
        timeout: Per-request timeout in seconds.

    Returns:
        The same frame with a BRIEF column added.
    """
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        frame["BRIEF"] = ""
        return frame
    briefs = []
    for record in frame.to_dict("records"):
        row = {
            "neighborhoods": record.get("NEIGHBORHOODS"),
            "pct_no_vehicle": record.get("PCT_NO_VEHICLE"),
            "pct_poverty": record.get("PCT_POVERTY"),
            "median_trips": record.get("MEDIAN_WEEKDAY_TRIPS"),
        }
        try:
            briefs.append(_one_brief(row, api_key, timeout))
        except (requests.RequestException, KeyError, IndexError) as exc:
            print(f"  brief failed for {row['neighborhoods']}: {exc}")
            briefs.append("")
    frame["BRIEF"] = briefs
    return frame
