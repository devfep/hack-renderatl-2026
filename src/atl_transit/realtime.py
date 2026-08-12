"""MARTA's live GTFS-realtime feed. No API key, no signup - an anonymous GET returning protobuf."""

from __future__ import annotations

from typing import Any

import requests
from google.transit import gtfs_realtime_pb2

from atl_transit.harvest import USER_AGENT, VEHICLES_URL


def vehicle_positions(timeout: int = 20) -> list[dict[str, Any]]:
    """Fetch every MARTA vehicle currently reporting a position.

    Args:
        timeout: Request timeout in seconds.

    Returns:
        One entry per vehicle with its route, coordinates and bearing.

    Raises:
        requests.HTTPError: If the feed returns a non-2xx status.
    """
    response = requests.get(VEHICLES_URL, timeout=timeout, headers=USER_AGENT)
    response.raise_for_status()
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(response.content)
    vehicles = []
    for entity in feed.entity:
        if not entity.HasField("vehicle"):
            continue
        vehicle = entity.vehicle
        vehicles.append(
            {
                "vehicle_id": vehicle.vehicle.id,
                "route_id": vehicle.trip.route_id,
                "lat": round(vehicle.position.latitude, 5),
                "lon": round(vehicle.position.longitude, 5),
                "bearing": round(vehicle.position.bearing, 1),
            }
        )
    return vehicles
