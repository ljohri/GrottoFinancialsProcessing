"""Load and normalize Chase, PayPal, and PayPal-fee CSV data into a unified dataframe."""

import glob
import os

import pandas as pd


def load_chase(path: str) -> pd.DataFrame:
    """Read a Chase activity CSV and return normalized rows.

    Chase CSVs have a trailing comma on each data row, which makes pandas
    shift all column values by one unless index_col=False is specified.
    """
    df = pd.read_csv(path, index_col=False)
    df = df.rename(columns={
        "Posting Date": "date",
        "Description": "description",
        "Amount": "amount",
        "Type": "chase_type",
    })
    df["source"] = "chase"
    return df[["date", "description", "amount", "source", "chase_type"]].copy()


def load_paypal(path: str) -> pd.DataFrame:
    """Read a PayPal activity CSV and return two rows per transaction:
    one for the gross received amount and one for the fee.
    Only Completed transactions are included.
    """
    df = pd.read_csv(path, quotechar='"')

    # Normalize column names (PayPal export has quoted headers)
    df.columns = [c.strip().strip('"') for c in df.columns]

    # Keep only completed transactions
    df = df[df["Status"].str.strip() == "Completed"].copy()

    if df.empty:
        return pd.DataFrame(columns=["date", "description", "amount", "source", "chase_type"])

    def clean_money(series: pd.Series) -> pd.Series:
        return (
            series.astype(str)
            .str.replace(",", "", regex=False)
            .str.replace('"', "", regex=False)
            .str.strip()
        )

    df["_gross"] = pd.to_numeric(clean_money(df["Gross"]), errors="coerce").fillna(0.0)
    df["_fee"] = pd.to_numeric(clean_money(df["Fee"]), errors="coerce").fillna(0.0)
    df["_name"] = df["Name"].fillna("").astype(str).str.strip()
    df["_type"] = df["Type"].fillna("").astype(str).str.strip()

    # Income rows (gross received — positive)
    income = df[df["_gross"] > 0][["Date", "_name", "_type", "_gross"]].copy()
    income = income.rename(columns={"Date": "date", "_name": "description", "_gross": "amount"})
    income["description"] = income["description"] + " (" + income["_type"] + ")"
    income["source"] = "paypal"
    income["chase_type"] = ""
    income = income[["date", "description", "amount", "source", "chase_type"]]

    # Fee rows (fees are negative in PayPal export; store as negative so categorize treats them as expense)
    fees = df[df["_fee"] != 0][["Date", "_name", "_type", "_fee"]].copy()
    fees = fees.rename(columns={"Date": "date", "_name": "description", "_fee": "amount"})
    fees["description"] = "PayPal Fee - " + fees["description"] + " (" + fees["_type"] + ")"
    fees["source"] = "paypal_fee"
    fees["chase_type"] = ""
    fees = fees[["date", "description", "amount", "source", "chase_type"]]

    return pd.concat([income, fees], ignore_index=True)


def load_all_data(data_dir: str) -> pd.DataFrame:
    """Load all Chase and PayPal CSVs from data_dir into a single unified dataframe."""
    frames = []

    # Chase: match any Chase*.CSV (case-insensitive extension)
    for path in glob.glob(os.path.join(data_dir, "Chase*.CSV")) + glob.glob(
        os.path.join(data_dir, "Chase*.csv")
    ):
        print(f"  Loading Chase: {os.path.basename(path)}")
        frames.append(load_chase(path))

    # PayPal
    paypal_path = os.path.join(data_dir, "paypal.CSV")
    if not os.path.exists(paypal_path):
        paypal_path = os.path.join(data_dir, "paypal.csv")
    if os.path.exists(paypal_path):
        print(f"  Loading PayPal: {os.path.basename(paypal_path)}")
        frames.append(load_paypal(paypal_path))
    else:
        print("  Warning: paypal.CSV not found")

    if not frames:
        raise FileNotFoundError(f"No Chase or PayPal CSV files found in {data_dir}")

    return pd.concat(frames, ignore_index=True)
