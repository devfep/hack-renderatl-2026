"""Tool results must survive JSON serialisation, whichever Store produced them."""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal

import pytest

from atl_transit.agent import jsonable


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (Decimal("20.0"), 20.0),
        (Decimal(81), 81.0),
        (Decimal("34.4"), 34.4),
        (date(2026, 8, 12), "2026-08-12"),
        # Naive on purpose: a driver hands back exactly this, tzinfo or not.
        (datetime(2026, 8, 12, 14, 30), "2026-08-12T14:30:00"),  # noqa: DTZ001
        (40, 40),
        ("Vine City", "Vine City"),
        (None, None),
    ],
)
def test_values_become_json_safe(raw: object, expected: object) -> None:
    assert jsonable(raw) == expected


def test_snowflake_style_row_serialises() -> None:
    """Snowflake returns Decimal for numerics; ADK serialises tool results to JSON.

    Without coercion this raises TypeError and the agent returns nothing at all.
    """
    row = [Decimal("20.0"), "Collier Heights", Decimal("24.3"), None]
    assert json.dumps([jsonable(v) for v in row]) == '[20.0, "Collier Heights", 24.3, null]'


def test_raw_decimal_row_is_not_serialisable() -> None:
    """Guards the premise: without jsonable this genuinely fails, so the test has teeth."""
    with pytest.raises(TypeError, match="Decimal"):
        json.dumps([Decimal("20.0")])
