"""Harvest: pull Atlanta transit and equity data from source, then load it into the Store.

The heavy join happens locally in DuckDB. Only compact, answerable tables reach the Store,
so the agent never queries the 2.4M-row stop_times feed directly.
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path
from typing import Any

import duckdb
import requests

from atl_transit.gemma import write_briefs
from atl_transit.store import open_store

GTFS_URL = "https://itsmarta.com/google_transit_feed/google_transit.zip"

# MARTA returns 403 to the default python-requests agent.
USER_AGENT = {"User-Agent": "atl-transit-harvest/1.0 (Hack RenderATL 2026)"}

COC_URL = (
    "https://services2.arcgis.com/zLeajbicrDRLQcny/arcgis/rest/services/"
    "Communities_of_Concern_2025/FeatureServer/4/query"
    "?where=1%3D1&outFields=*&f=geojson"
)

NPU_URL = (
    "https://gis.atlantaga.gov/dpcd/rest/services/AdministrativeArea/GeopoliticalArea/"
    "MapServer/2/query?where=1%3D1&outFields=*&outSR=4326&f=geojson"
)

VEHICLES_URL = "https://gtfs-rt.itsmarta.com/TMGTFSRealTimeWebService/vehicle/vehiclepositions.pb"

GTFS_MEMBERS = ("stop_times", "trips", "stops", "calendar", "routes")

DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


def download(url: str, dest: Path, timeout: int = 120) -> Path:
    """Fetch ``url`` to ``dest``, streaming so large feeds do not sit in memory.

    Args:
        url: Source URL.
        dest: Destination path; parent directories are created.
        timeout: Per-request timeout in seconds.

    Returns:
        The path written.

    Raises:
        requests.HTTPError: If the source returns a non-2xx status.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, timeout=timeout, stream=True, headers=USER_AGENT) as response:
        response.raise_for_status()
        with dest.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1 << 16):
                handle.write(chunk)
    return dest


def fetch_sources(workdir: Path) -> None:
    """Download the GTFS feed and both boundary layers into ``workdir``."""
    archive = download(GTFS_URL, workdir / "gtfs.zip")
    with zipfile.ZipFile(archive) as bundle:
        for member in GTFS_MEMBERS:
            bundle.extract(f"{member}.txt", workdir / "gtfs")
    download(COC_URL, workdir / "coc.geojson")
    download(NPU_URL, workdir / "npu.geojson")


def _connect(workdir: Path) -> duckdb.DuckDBPyConnection:
    """Open an in-memory DuckDB with the GTFS text files and boundary layers registered."""
    con = duckdb.connect()
    con.execute("INSTALL spatial; LOAD spatial;")
    for member in GTFS_MEMBERS:
        path = workdir / "gtfs" / f"{member}.txt"
        con.execute(
            f"CREATE VIEW {member} AS SELECT * FROM read_csv_auto('{path}', all_varchar=true)"
        )
    con.execute(f"CREATE TABLE coc AS SELECT * FROM ST_Read('{workdir / 'coc.geojson'}')")
    con.execute(f"CREATE TABLE npu AS SELECT * FROM ST_Read('{workdir / 'npu.geojson'}')")
    return con


def build_tables(workdir: Path, *, enrich: bool = True) -> dict[str, Any]:
    """Aggregate the raw feed into the four tables the agent answers from.

    Args:
        workdir: Directory populated by :func:`fetch_sources`.
        enrich: Whether to write Gemma briefs in-line. The Render Workflow sets this
            False and fans the briefs out as parallel subtasks instead.

    Returns:
        Table name to DataFrame, with columns already uppercased for the Store.
    """
    con = _connect(workdir)
    day_counts = ", ".join(f"COUNT(*) FILTER (WHERE c.{day} = '1') AS {day}" for day in DAYS)
    con.execute(f"""
        CREATE TABLE trips_per_stop AS
        SELECT st.stop_id, {day_counts}
        FROM stop_times st
        JOIN trips t USING (trip_id)
        JOIN calendar c ON c.service_id = t.service_id
        GROUP BY st.stop_id
    """)
    unpivot = " UNION ALL ".join(
        f"SELECT stop_id, '{day}' AS service_day, {day} AS trip_count FROM trips_per_stop"
        for day in DAYS
    )
    con.execute(f"CREATE TABLE stop_frequency AS {unpivot}")
    con.execute("""
        CREATE TABLE stops_located AS
        SELECT s.stop_id, s.stop_name,
               CAST(s.stop_lat AS DOUBLE) AS lat, CAST(s.stop_lon AS DOUBLE) AS lon,
               s.wheelchair_boarding,
               npu.NAME AS npu,
               coc.Name AS coc_name, coc.COC_Tier AS coc_tier,
               coc.Neighborhoods AS coc_neighborhoods,
               coc.p_NoVehicleAvailable AS pct_no_vehicle,
               coc.p_BelowPovertyLine AS pct_poverty
        FROM stops s
        LEFT JOIN npu ON ST_Contains(npu.geom, ST_Point(CAST(s.stop_lon AS DOUBLE),
                                                        CAST(s.stop_lat AS DOUBLE)))
        LEFT JOIN coc ON ST_Contains(coc.geom, ST_Point(CAST(s.stop_lon AS DOUBLE),
                                                        CAST(s.stop_lat AS DOUBLE)))
    """)
    frames = {
        "STOPS": con.execute("SELECT * FROM stops_located").df(),
        "STOP_FREQUENCY": con.execute("SELECT * FROM stop_frequency WHERE trip_count > 0").df(),
        "ROUTES": con.execute("""
            SELECT route_id, route_short_name, route_long_name,
                   CAST(route_type AS INTEGER) AS route_type
            FROM routes
        """).df(),
        "COC_AREA": con.execute("""
            SELECT c.Name AS coc_name, c.Neighborhoods AS neighborhoods, c.COC_Tier AS coc_tier,
                   c.p_NoVehicleAvailable AS pct_no_vehicle,
                   c.p_BelowPovertyLine AS pct_poverty,
                   c.p_PublicTransitCommute AS pct_transit_commute,
                   COUNT(s.stop_id) AS stop_count,
                   MEDIAN(f.trip_count) AS median_weekday_trips
            FROM coc c
            LEFT JOIN stops_located s ON s.coc_name = c.Name
            LEFT JOIN stop_frequency f
                   ON f.stop_id = s.stop_id AND f.service_day = 'monday'
            GROUP BY 1, 2, 3, 4, 5, 6
        """).df(),
    }
    for frame in frames.values():
        frame.columns = [c.upper() for c in frame.columns]
    if enrich:
        frames["COC_AREA"] = write_briefs(frames["COC_AREA"])
    return frames


def validate(frames: dict[str, Any]) -> None:
    """Fail the harvest if any table came back implausible.

    Args:
        frames: Output of :func:`build_tables`.

    Raises:
        RuntimeError: If a table is empty or far smaller than the feed implies.
    """
    minimums = {"STOPS": 5000, "STOP_FREQUENCY": 5000, "ROUTES": 50, "COC_AREA": 10}
    for table, floor in minimums.items():
        rows = len(frames[table])
        if rows < floor:
            msg = f"{table} has {rows} rows, expected at least {floor}. Refusing to load."
            raise RuntimeError(msg)


def main() -> int:
    """Run the whole harvest and load it into the configured Store.

    Returns:
        A process exit code.
    """
    workdir = Path("data/raw")
    print("fetching sources...")
    fetch_sources(workdir)
    print("building tables...")
    frames = build_tables(workdir)
    validate(frames)
    store = open_store()
    for table, frame in frames.items():
        rows = store.load_frame(frame, table)
        print(f"  loaded {table:<16} {rows:>7} rows")
    print("harvest complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
