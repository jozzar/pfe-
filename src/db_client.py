"""Database ingestion helpers for MASI historical prices using PostgreSQL.

Expected environment variables:
    DB_USER
    DB_PASSWORD
    DB_HOST
    DB_PORT
    DB_NAME

The table and column names are configurable through function arguments.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

load_dotenv()

DEFAULT_DATE_COLUMN = "date"
DEFAULT_CLOSE_COLUMN = "close"
DEFAULT_TABLE_NAME = "masi_prices"


class DataIngestionError(RuntimeError):
    """Raised when MASI price data cannot be fetched or validated."""


@dataclass(frozen=True)
class DatabaseSettings:
    """Connection settings for a PostgreSQL database."""

    user: str
    password: str
    host: str
    port: str
    name: str

    @classmethod
    def from_env(cls) -> "DatabaseSettings":
        """Load database credentials from environment variables."""
        user = os.getenv("DB_USER", "postgres")
        password = os.getenv("DB_PASSWORD", "postgres")
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "5432")
        name = os.getenv("DB_NAME", "masi_db")

        return cls(user=user, password=password, host=host, port=port, name=name)

    @property
    def url(self) -> str:
        """Construct a SQLAlchemy database URL."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


def get_db_engine(settings: DatabaseSettings | None = None) -> Engine:
    """Create a SQLAlchemy engine from explicit settings or environment vars."""
    resolved_settings = settings or DatabaseSettings.from_env()
    try:
        return create_engine(resolved_settings.url)
    except Exception as exc:
        raise DataIngestionError(f"Failed to create database engine: {exc}")


def fetch_masi_prices(
    *,
    table_name: str = DEFAULT_TABLE_NAME,
    date_column: str = DEFAULT_DATE_COLUMN,
    close_column: str = DEFAULT_CLOSE_COLUMN,
    engine: Engine | None = None,
    start_date: str | pd.Timestamp | None = None,
    end_date: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Fetch daily MASI closing prices from PostgreSQL.

    Parameters
    ----------
    table_name:
        Database table containing historical MASI observations.
    date_column:
        Name of the date column in ``table_name``.
    close_column:
        Name of the closing-price column in ``table_name``.
    engine:
        Optional preconfigured SQLAlchemy engine.
    start_date, end_date:
        Optional inclusive date filters.

    Returns
    -------
    pandas.DataFrame
        Clean DataFrame indexed by date with one float column named ``close``.
    """
    db_engine = engine or get_db_engine()
    
    query = f"SELECT {date_column}, {close_column} FROM {table_name}"
    conditions = []
    params = {}

    if start_date is not None:
        conditions.append(f"{date_column} >= :start_date")
        params["start_date"] = pd.Timestamp(start_date).date()
    if end_date is not None:
        conditions.append(f"{date_column} <= :end_date")
        params["end_date"] = pd.Timestamp(end_date).date()

    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += f" ORDER BY {date_column} ASC"

    try:
        with db_engine.connect() as conn:
            df = pd.read_sql(text(query), conn, params=params)
    except Exception as exc:
        raise DataIngestionError(
            f"Failed to fetch MASI prices from table '{table_name}': {exc}"
        )

    return clean_price_frame(
        df,
        date_column=date_column,
        close_column=close_column,
    )


def clean_price_frame(
    records: Iterable[Mapping[str, Any]] | pd.DataFrame,
    *,
    date_column: str = DEFAULT_DATE_COLUMN,
    close_column: str = DEFAULT_CLOSE_COLUMN,
) -> pd.DataFrame:
    """Validate and standardize raw MASI records into a modelling DataFrame."""
    df = records.copy() if isinstance(records, pd.DataFrame) else pd.DataFrame(records)

    if df.empty:
        raise DataIngestionError("No MASI price records were returned.")

    required_columns = {date_column, close_column}
    missing_columns = required_columns.difference(df.columns)
    if missing_columns:
        raise DataIngestionError(
            "MASI price data is missing required column(s): "
            + ", ".join(sorted(missing_columns))
            + "."
        )

    clean_df = df.loc[:, [date_column, close_column]].copy()
    clean_df.rename(
        columns={date_column: "date", close_column: "close"},
        inplace=True,
    )

    clean_df["date"] = pd.to_datetime(clean_df["date"], errors="coerce")
    clean_df["close"] = pd.to_numeric(clean_df["close"], errors="coerce")
    clean_df.dropna(subset=["date", "close"], inplace=True)

    if clean_df.empty:
        raise DataIngestionError(
            "MASI price records were present, but no valid date/close rows remained."
        )

    clean_df.sort_values("date", inplace=True)
    clean_df.drop_duplicates(subset="date", keep="last", inplace=True)
    clean_df.set_index("date", inplace=True)
    clean_df.index.name = "date"

    if len(clean_df) < 3:
        raise DataIngestionError(
            "At least 3 valid MASI observations are required for time-series work."
        )

    return clean_df.astype({"close": "float64"})


def upload_masi_prices(
    df: pd.DataFrame,
    *,
    table_name: str = DEFAULT_TABLE_NAME,
    engine: Engine | None = None,
) -> None:
    """Upload MASI price records to PostgreSQL.

    Parameters
    ----------
    df:
        DataFrame containing at least a 'close' column and a date index.
    table_name:
        Target database table.
    engine:
        Optional preconfigured SQLAlchemy engine.
    """
    if df.empty:
        return

    db_engine = engine or get_db_engine()
    
    # Prepare records for PostgreSQL
    records = df.reset_index().copy()
    records["date"] = pd.to_datetime(records["date"]).dt.date

    try:
        with db_engine.connect() as conn:
            # Create table if it doesn't exist, otherwise append
            records.to_sql(table_name, conn, if_exists="append", index=False)
            # Optional: Add primary key/unique constraint if needed here
    except Exception as exc:
        raise DataIngestionError(f"Failed to upload data to '{table_name}': {exc}")


if __name__ == "__main__":
    try:
        prices = fetch_masi_prices()
        print(prices.head())
        print(f"Fetched {len(prices):,} MASI observations.")
    except Exception as e:
        print(f"Database error: {e}")
