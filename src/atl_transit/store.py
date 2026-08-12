"""The Store: the queryable home of harvested Atlanta transit data.

Two backings sit behind one narrow interface, per ADR-0001. DuckDB runs locally with no
credentials; Snowflake runs once credentials work. The agent never learns which it got.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Protocol

import duckdb
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas

Row = tuple[Any, ...]


class Store(Protocol):
    """A queryable collection of harvested transit tables."""

    def query(self, sql: str) -> tuple[list[str], list[Row]]:
        """Run a read-only query.

        Args:
            sql: A single SELECT statement.

        Returns:
            The column names, and the rows they describe.
        """
        ...

    def load_frame(self, frame: Any, table: str) -> int:  # noqa: ANN401
        """Replace a table's contents with a pandas DataFrame.

        Args:
            frame: The DataFrame to write. Columns are uppercased by the caller.
            table: Destination table name.

        Returns:
            The number of rows written.
        """
        ...


class DuckDBStore:
    """A Store backed by a local DuckDB file. Needs no credentials."""

    def __init__(self, path: str) -> None:
        """Open (creating if absent) the DuckDB file at ``path``."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._con = duckdb.connect(path)
        self._con.execute("INSTALL spatial; LOAD spatial;")

    def query(self, sql: str) -> tuple[list[str], list[Row]]:
        """Run a read-only query. See :meth:`Store.query`."""
        cur = self._con.execute(sql)
        names = [d[0] for d in cur.description or []]
        return names, cur.fetchall()

    def load_frame(self, frame: Any, table: str) -> int:  # noqa: ANN401
        """Replace ``table`` with ``frame``. See :meth:`Store.load_frame`."""
        self._con.register("_incoming", frame)
        self._con.execute(f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM _incoming")
        self._con.unregister("_incoming")
        return len(frame)


class SnowflakeStore:
    """A Store backed by Snowflake, authenticated with a programmatic access token."""

    def __init__(self) -> None:
        """Connect using the SF_* environment variables."""
        self._con = snowflake.connector.connect(
            account=_require("SF_ACCOUNT"),
            user=_require("SF_USER"),
            password=_require("SF_PAT"),
            warehouse=os.environ.get("SF_WAREHOUSE", "COMPUTE_WH"),
            database=os.environ.get("SF_DATABASE", "ATL"),
            schema=os.environ.get("SF_SCHEMA", "PUBLIC"),
            role=os.environ.get("SF_ROLE", "ACCOUNTADMIN"),
        )

    def query(self, sql: str) -> tuple[list[str], list[Row]]:
        """Run a read-only query. See :meth:`Store.query`."""
        cur = self._con.cursor()
        cur.execute(sql)
        names = [d[0] for d in cur.description or []]
        return names, cur.fetchall()

    def load_frame(self, frame: Any, table: str) -> int:  # noqa: ANN401
        """Replace ``table`` with ``frame``. See :meth:`Store.load_frame`."""
        ok, _chunks, nrows, _out = write_pandas(
            self._con,
            frame,
            table,
            auto_create_table=True,
            overwrite=True,
            quote_identifiers=False,
        )
        if not ok:
            msg = f"write_pandas failed for table {table}"
            raise RuntimeError(msg)
        return nrows


def _require(name: str) -> str:
    """Read an environment variable, failing loudly when it is missing."""
    value = os.environ.get(name)
    if not value:
        msg = f"{name} is not set. Copy .env.example to .env and fill it in."
        raise RuntimeError(msg)
    return value


def open_store() -> Store:
    """Open the Store named by ``ATL_STORE``, defaulting to DuckDB.

    Returns:
        A DuckDB-backed Store unless ``ATL_STORE=snowflake``.
    """
    backend = os.environ.get("ATL_STORE", "duckdb").strip().lower()
    if backend == "snowflake":
        return SnowflakeStore()
    if backend == "duckdb":
        return DuckDBStore(os.environ.get("ATL_DUCKDB_PATH", "data/atl.duckdb"))
    msg = f"Unknown ATL_STORE={backend!r}. Use 'duckdb' or 'snowflake'."
    raise RuntimeError(msg)
