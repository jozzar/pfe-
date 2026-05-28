"""Supabase data ingestion helpers for MASI historical prices.

Expected environment variables:
    SUPABASE_URL
    SUPABASE_KEY

The table and column names are configurable through function arguments so this
module can work with your current warehouse schema without code changes.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Iterable, Mapping

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

if TYPE_CHECKING:
    from supabase import Client
else:
    Client = Any


DEFAULT_DATE_COLUMN = "date"
DEFAULT_CLOSE_COLUMN = "close"
DEFAULT_TABLE_NAME = "masi_prices"


class DataIngestionError(RuntimeError):
    """Raised when MASI price data cannot be fetched or validated."""


@dataclass(frozen=True)
class SupabaseSettings:
    """Connection settings for a Supabase project."""

    url: str
    key: str

    @classmethod
    def from_env(cls) -> "SupabaseSettings":
        """Load Supabase credentials from environment variables."""
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")

        missing = [
            name
            for name, value in (("SUPABASE_URL", url), ("SUPABASE_KEY", key))
            if not value
        ]
        if missing:
            raise DataIngestionError(
                "Missing Supabase environment variable(s): "
                + ", ".join(missing)
                + "."
            )

        return cls(url=str(url), key=str(key))


def get_supabase_client(settings: SupabaseSettings | None = None) -> Client:
    """Create a Supabase client from explicit settings or environment vars."""
    resolved_settings = settings or SupabaseSettings.from_env()

    try:
        from supabase import create_client

        return create_client(resolved_settings.url, resolved_settings.key)
    except ImportError as exc:
        raise DataIngestionError(
            "The 'supabase' package is required. Install it with: "
            "python -m pip install supabase"
        ) from exc
    except Exception as exc:  # pragma: no cover - depends on external client
        raise DataIngestionError("Failed to create Supabase client.") from exc


def fetch_masi_prices(
    *,
    table_name: str = DEFAULT_TABLE_NAME,
    date_column: str = DEFAULT_DATE_COLUMN,
    close_column: str = DEFAULT_CLOSE_COLUMN,
    client: Client | None = None,
    start_date: str | pd.Timestamp | None = None,
    end_date: str | pd.Timestamp | None = None,
    page_size: int = 1_000,
) -> pd.DataFrame:
    """Fetch daily MASI closing prices from Supabase.

    Parameters
    ----------
    table_name:
        Supabase table containing historical MASI observations.
    date_column:
        Name of the date column in ``table_name``.
    close_column:
        Name of the closing-price column in ``table_name``.
    client:
        Optional preconfigured Supabase client. If omitted, credentials are read
        from ``SUPABASE_URL`` and ``SUPABASE_KEY``.
    start_date, end_date:
        Optional inclusive date filters.
    page_size:
        Number of rows per Supabase request. Pagination is handled internally.

    Returns
    -------
    pandas.DataFrame
        Clean DataFrame indexed by date with one float column named ``close``.
    """
    if page_size <= 0:
        raise ValueError("page_size must be a positive integer.")

    supabase = client or get_supabase_client()
    selected_columns = f"{date_column},{close_column}"
    rows: list[Mapping[str, Any]] = []
    offset = 0

    try:
        while True:
            query = (
                supabase.table(table_name)
                .select(selected_columns)
                .order(date_column, desc=False)
                .range(offset, offset + page_size - 1)
            )

            if start_date is not None:
                query = query.gte(date_column, _format_date_filter(start_date))
            if end_date is not None:
                query = query.lte(date_column, _format_date_filter(end_date))

            response = query.execute()
            batch = response.data or []
            rows.extend(batch)

            if len(batch) < page_size:
                break
            offset += page_size
    except Exception as exc:  # pragma: no cover - depends on network/db state
        raise DataIngestionError(
            f"Failed to fetch MASI prices from Supabase table '{table_name}'."
        ) from exc

    return clean_price_frame(
        rows,
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
    client: Client | None = None,
) -> None:
    """Upload MASI price records to Supabase.

    Parameters
    ----------
    df:
        DataFrame containing at least a 'close' column and a date index.
    table_name:
        Target Supabase table.
    client:
        Optional preconfigured Supabase client.
    """
    if df.empty:
        return

    supabase = client or get_supabase_client()
    
    # Prepare records for Supabase (list of dicts)
    records = df.reset_index().copy()
    records["date"] = records["date"].dt.strftime("%Y-%m-%d")
    data = records.to_dict(orient="records")

    try:
        # Using upsert to handle duplicates if the table has a unique constraint on date
        supabase.table(table_name).upsert(data).execute()
    except Exception as exc:
        raise DataIngestionError(f"Failed to upload data to '{table_name}': {exc}")


def _format_date_filter(value: str | pd.Timestamp) -> str:
    """Format dates for Supabase/PostgREST filters."""
    timestamp = pd.Timestamp(value)
    if pd.isna(timestamp):
        raise ValueError(f"Invalid date filter value: {value!r}")
    return timestamp.date().isoformat()


if __name__ == "__main__":
    prices = fetch_masi_prices()
    print(prices.head())
    print(f"Fetched {len(prices):,} MASI observations.")
