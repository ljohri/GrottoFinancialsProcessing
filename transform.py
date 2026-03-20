"""Clean and normalize the unified dataframe: parse dates, amounts, add year/month, filter to 2025."""

import pandas as pd


def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Return a cleaned dataframe filtered to 2025 transactions only."""
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

    # Filter to 2025 only
    df_2025 = df[df["year"] == 2025].copy()
    print(f"  Rows after 2025 filter: {len(df_2025)} (from {len(df)} total)")

    return df_2025.reset_index(drop=True)
