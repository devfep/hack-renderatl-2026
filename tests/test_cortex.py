"""Cortex reply handling: models wrap SQL in prose and fences, and we have to execute it."""

from __future__ import annotations

import pytest

from atl_transit.cortex import SCHEMA, Cortex, CortexError, strip_sql


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("SELECT 1", "SELECT 1"),
        ("```sql\nSELECT 1\n```", "SELECT 1"),
        ("```SQL\nSELECT 1\n```", "SELECT 1"),
        ("```\nSELECT 1\n```", "SELECT 1"),
        ("  SELECT 1;  ", "SELECT 1"),
        ("```sql\nSELECT 1;\n```", "SELECT 1"),
        ("SELECT a\nFROM b\nWHERE c = 1", "SELECT a\nFROM b\nWHERE c = 1"),
    ],
)
def test_strip_sql_yields_executable_sql(raw: str, expected: str) -> None:
    assert strip_sql(raw) == expected


def test_cortex_requires_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing credentials must fail loudly at construction, not at demo time."""
    monkeypatch.delenv("SF_ACCOUNT", raising=False)
    monkeypatch.delenv("SF_PAT", raising=False)
    with pytest.raises(CortexError, match="SF_ACCOUNT"):
        Cortex()


def test_base_url_uses_the_account_identifier() -> None:
    cortex = Cortex(account="myorg-myacct", token="tok")  # noqa: S106 - test fixture, not a secret
    assert cortex.base_url == "https://myorg-myacct.snowflakecomputing.com"


def test_schema_warns_against_the_division_trap() -> None:
    """A model that divides MEDIAN_WEEKDAY_TRIPS by STOP_COUNT reports fabricated numbers."""
    assert "Never divide" in SCHEMA
    assert "NEIGHBORHOODS" in SCHEMA
