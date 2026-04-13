"""Clean and normalize the unified dataframe: parse dates, amounts, add year/month, filter by analysis dates."""

import pandas as pd

from config import ANALYSIS_END, ANALYSIS_START


def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Return a cleaned dataframe filtered to `ANALYSIS_START`–`ANALYSIS_END` (inclusive) from config / `.env`."""
    df = df.copy()

    # Parse dates — PayPal and Chase both use MM/DD/YYYY
    df["date"] = pd.to_datetime(df["date"], format="%m/%d/%Y", errors="coerce")

    # Drop rows where date could not be parsed
    bad_dates = df["date"].isna().sum()
    if bad_dates:
        print(f"  Warning: dropped {bad_dates} row(s) with unparseable dates")
    df = df.dropna(subset=["date"])

    # Parse amounts — strip commas, then coerce to float
    df["amount"] = (
        df["amount"]
        .astype(str)
        .str.replace(",", "", regex=False)
        .str.strip()
    )
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

    bad_amounts = df["amount"].isna().sum()
    if bad_amounts:
        print(f"  Warning: dropped {bad_amounts} row(s) with unparseable amounts")
    df = df.dropna(subset=["amount"])

    # Add calendar helpers
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["month_name"] = df["date"].dt.strftime("%B")

    d = df["date"].dt.date
    mask = (d >= ANALYSIS_START) & (d <= ANALYSIS_END)
    df_out = df[mask].copy()
    print(
        f"  Rows after date filter {ANALYSIS_START}–{ANALYSIS_END}: "
        f"{len(df_out)} (from {len(df)} total)"
    )

    return df_out.reset_index(drop=True)
