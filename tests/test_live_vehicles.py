"""Live vehicle answers must name routes from the schedule, never from the model's memory.

The realtime feed carries only route numbers. Asked to name them, a model supplies plausible
and subtly wrong names - observed live: route 15 called "Candler Road" when the schedule says
"Clifton Road / Candler Road".
"""

from __future__ import annotations

import pytest

from atl_transit import agent


@pytest.fixture
def feed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Two vehicles, one on a route the schedule knows and one on a route it does not."""
    monkeypatch.setattr(
        agent,
        "vehicle_positions",
        lambda: [
            {"vehicle_id": "1", "route_id": "15", "lat": 33.8, "lon": -84.3, "bearing": 90.0},
            {"vehicle_id": "2", "route_id": "999", "lat": 33.7, "lon": -84.4, "bearing": 10.0},
        ],
    )
    monkeypatch.setattr(
        agent, "_route_names", lambda: {"15": "Clifton Road / Candler Road", "12": "Howell Mill"}
    )


@pytest.mark.usefixtures("feed")
def test_known_route_gets_its_scheduled_name() -> None:
    result = agent.live_vehicles()
    assert result["vehicles"][0]["route_name"] == "Clifton Road / Candler Road"


@pytest.mark.usefixtures("feed")
def test_unknown_route_gets_no_invented_name() -> None:
    """An empty name is correct; a guessed one is the bug this prevents."""
    assert agent.live_vehicles()["vehicles"][1]["route_name"] == ""


@pytest.mark.usefixtures("feed")
def test_result_tells_the_model_not_to_invent_names() -> None:
    assert "Never name a route" in agent.live_vehicles()["note"]


@pytest.mark.usefixtures("feed")
def test_vehicle_count_reports_the_whole_feed_not_the_sample() -> None:
    assert agent.live_vehicles()["vehicle_count"] == 2


def test_feed_failure_degrades_to_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom() -> list[dict[str, object]]:
        msg = "connection reset"
        raise ConnectionError(msg)

    monkeypatch.setattr(agent, "vehicle_positions", boom)
    assert "connection reset" in agent.live_vehicles()["error"]
