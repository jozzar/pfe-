"""Signal-processing utilities for ACF fundamental value estimation."""

from __future__ import annotations

from typing import Literal

import pandas as pd


DEFAULT_CLOSE_COLUMN = "close"
DEFAULT_FUNDAMENTAL_COLUMN = "fundamental_value"
DEFAULT_CYCLE_COLUMN = "hp_cycle"
DEFAULT_HP_LAMBDA_DAILY = 129_600.0


class SignalProcessingError(RuntimeError):
    """Raised when price signals cannot be transformed for modelling."""


def add_hp_fundamental_value(
    prices: pd.DataFrame,
    *,
    close_column: str = DEFAULT_CLOSE_COLUMN,
    fundamental_column: str = DEFAULT_FUNDAMENTAL_COLUMN,
    cycle_column: str | None = DEFAULT_CYCLE_COLUMN,
    lamb: float = DEFAULT_HP_LAMBDA_DAILY,
    drop_missing: bool = True,
) -> pd.DataFrame:
    """Append the HP-filter trend used as the unobserved fundamental price.

    The Chen et al. 2-type framework requires a fundamental value ``p_t^f``.
    Here, ``p_t^f`` is proxied by the smoothed HP-filter trend of MASI closing
    prices.

    Parameters
    ----------
    prices:
        DataFrame containing a numeric MASI closing-price series.
    close_column:
        Name of the observed price column ``p_t``.
    fundamental_column:
        Output column for the HP trend, interpreted as ``p_t^f``.
    cycle_column:
        Optional output column for the HP cyclical component. Pass ``None`` to
        omit it.
    lamb:
        Hodrick-Prescott smoothing parameter. ``129600`` is a common daily-data
        starting point; tune it as part of robustness checks.
    drop_missing:
        Whether to drop rows with missing/non-numeric close prices before
        filtering.

    Returns
    -------
    pandas.DataFrame
        Copy of ``prices`` with ``fundamental_column`` and optionally
        ``cycle_column`` added.
    """
    price_series = _extract_price_series(
        prices,
        close_column=close_column,
        drop_missing=drop_missing,
    )

    try:
        from statsmodels.tsa.filters.hp_filter import hpfilter

        cycle, trend = hpfilter(price_series, lamb=lamb)
    except ImportError as exc:
        raise SignalProcessingError(
            "The 'statsmodels' package is required for HP filtering. Install it "
            "with: python -m pip install statsmodels"
        ) from exc
    except Exception as exc:
        raise SignalProcessingError("HP filtering failed for MASI prices.") from exc

    output = prices.copy()
    output[fundamental_column] = trend.reindex(output.index)
    if cycle_column is not None:
        output[cycle_column] = cycle.reindex(output.index)

    if drop_missing:
        required = [close_column, fundamental_column]
        if cycle_column is not None:
            required.append(cycle_column)
        output.dropna(subset=required, inplace=True)

    return output


def calculate_fundamental_value(
    prices: pd.DataFrame | pd.Series,
    *,
    close_column: str = DEFAULT_CLOSE_COLUMN,
    lamb: float = DEFAULT_HP_LAMBDA_DAILY,
    return_component: Literal["trend", "cycle"] = "trend",
) -> pd.Series:
    """Return the HP-filter trend or cycle for a MASI closing-price series."""
    if isinstance(prices, pd.Series):
        price_series = _clean_series(prices)
    else:
        price_series = _extract_price_series(
            prices,
            close_column=close_column,
            drop_missing=True,
        )

    try:
        from statsmodels.tsa.filters.hp_filter import hpfilter

        cycle, trend = hpfilter(price_series, lamb=lamb)
    except ImportError as exc:
        raise SignalProcessingError(
            "The 'statsmodels' package is required for HP filtering. Install it "
            "with: python -m pip install statsmodels"
        ) from exc
    except Exception as exc:
        raise SignalProcessingError("HP filtering failed for MASI prices.") from exc

    if return_component == "trend":
        trend.name = DEFAULT_FUNDAMENTAL_COLUMN
        return trend

    cycle.name = DEFAULT_CYCLE_COLUMN
    return cycle


def _extract_price_series(
    prices: pd.DataFrame,
    *,
    close_column: str,
    drop_missing: bool,
) -> pd.Series:
    """Validate a DataFrame and return a clean numeric price series."""
    if close_column not in prices.columns:
        raise SignalProcessingError(
            f"Input DataFrame must contain a '{close_column}' column."
        )

    series = pd.to_numeric(prices[close_column], errors="coerce")
    if drop_missing:
        series = series.dropna()
    elif series.isna().any():
        raise SignalProcessingError(
            f"Column '{close_column}' contains missing or non-numeric values."
        )

    return _clean_series(series)


def _clean_series(series: pd.Series) -> pd.Series:
    """Validate the minimum requirements for HP filtering."""
    if series.empty:
        raise SignalProcessingError("Cannot HP-filter an empty price series.")

    clean_series = pd.to_numeric(series, errors="coerce").dropna().astype("float64")
    if len(clean_series) < 3:
        raise SignalProcessingError(
            "At least 3 valid observations are required for HP filtering."
        )

    if not clean_series.index.is_monotonic_increasing:
        clean_series = clean_series.sort_index()

    clean_series.name = series.name or DEFAULT_CLOSE_COLUMN
    return clean_series


if __name__ == "__main__":
    from db_client import fetch_masi_prices

    masi_prices = fetch_masi_prices()
    masi_with_fundamental = add_hp_fundamental_value(masi_prices)
    print(masi_with_fundamental.head())
