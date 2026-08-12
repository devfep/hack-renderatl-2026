"""Harvest behaviour: validation refuses to load data that would silently break the agent."""

from __future__ import annotations

import pandas as pd
import pytest

from atl_transit.harvest import validate


def _frames(**overrides: int) -> dict[str, pd.DataFrame]:
    """Build a set of plausible frames, with row counts overridable per table."""
    sizes = {"STOPS": 7000, "STOP_FREQUENCY": 49000, "ROUTES": 86, "COC_AREA": 15}
    sizes.update(overrides)
    return {name: pd.DataFrame({"x": range(n)}) for name, n in sizes.items()}


def test_validate_accepts_a_realistic_harvest() -> None:
    validate(_frames())


@pytest.mark.parametrize(
    ("table", "rows"),
    [("STOPS", 12), ("STOP_FREQUENCY", 40), ("ROUTES", 3), ("COC_AREA", 0)],
)
def test_validate_rejects_a_truncated_table(table: str, rows: int) -> None:
    """A partial upstream feed must fail the harvest, not quietly load a subset."""
    with pytest.raises(RuntimeError, match=table):
        validate(_frames(**{table: rows}))


def test_validate_names_the_offending_table_and_counts() -> None:
    """The error has to say which table and how short it was, or debugging it is guesswork."""
    with pytest.raises(RuntimeError, match=r"ROUTES has 3 rows, expected at least 50"):
        validate(_frames(ROUTES=3))
