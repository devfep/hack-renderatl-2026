"""Brief extraction: Gemma 4 reasons out loud, so the answer has to be found, not assumed.

Every case here is real output observed from gemma-4-31b-it during the build.
"""

from __future__ import annotations

import pytest

from atl_transit.gemma import best_sentence

BRIEF = (
    "In Vine City, 49.2% of households have no vehicle, 38.8% live below the poverty line, "
    "and the median weekday bus trips per stop is 62.0, compared to a MARTA-wide median of 40."
)


def test_plain_answer_passes_through() -> None:
    assert best_sentence(BRIEF) == BRIEF


def test_quoted_then_echoed_answer_is_returned_once() -> None:
    """Gemma often emits the sentence quoted and then repeats it bare."""
    assert best_sentence(f'"{BRIEF}" {BRIEF}') == BRIEF


def test_draft_label_is_stripped() -> None:
    assert best_sentence(f"Draft 3:* {BRIEF}") == BRIEF


def test_reasoning_preamble_is_skipped() -> None:
    noise = "Okay. Let me think about this. The prompt says one sentence. "
    assert best_sentence(noise + BRIEF) == BRIEF


def test_decimals_do_not_split_the_sentence() -> None:
    """A naive sentence splitter truncates at '34.4%'; the brief must survive intact."""
    text = "In Bankhead, 34.4% of households have no vehicle and 34.1% are below poverty."
    assert best_sentence(text) == text


@pytest.mark.parametrize(
    "commentary",
    [
        "is factual, simply stating the numbers is more neutral).",
        "Wait, that phrasing might be seen as slightly editorial and non-standard.",
        "",
        "Sure.",
    ],
)
def test_commentary_yields_no_brief(commentary: str) -> None:
    """Better an empty brief than the model's private reasoning shown to a resident."""
    assert best_sentence(commentary) == ""
