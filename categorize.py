"""Assign a category to each transaction row."""

import pandas as pd

# Keywords that identify a PayPal → Chase (or vice-versa) internal transfer in Chase rows
_INTERNAL_TRANSFER_CHASE_TYPES = {"ACH_DEBIT", "ACH_CREDIT"}
_INTERNAL_TRANSFER_DESC_KEYWORDS = ["paypal", "paypalsi"]

# Keywords that identify donation income (case-insensitive)
_DONATION_KEYWORDS = [
    "donation",
    "donate",
    "benevity",
    "amer online giv",
    "america gives",
    "giv1",
    "fcauses",
]

# Dollar threshold above which an unlabelled income is treated as a donation
_DONATION_AMOUNT_THRESHOLD = 100.0


def _classify_row(row: pd.Series) -> str:
    source: str = row["source"]
    amount: float = row["amount"]
    desc: str = str(row["description"]).lower()
    chase_type: str = str(row.get("chase_type", "")).upper()

    # --- PayPal fee rows (already split by load_paypal) ---
    if source == "paypal_fee":
        return "paypal_fee"

    # --- Internal transfers (PayPal ↔ Chase ACH) ---
    if source == "chase":
        if chase_type in _INTERNAL_TRANSFER_CHASE_TYPES and any(
            kw in desc for kw in _INTERNAL_TRANSFER_DESC_KEYWORDS
        ):
            return "internal_transfer"

    if source == "paypal":
        if any(kw in desc for kw in ["transfer", "bank deposit", "withdrawal", "general withdrawal"]):
            return "internal_transfer"

    # --- Expenses: any negative amount (Chase debits) ---
    if amount < 0:
        return "expense"

    # --- Donation income: keyword match or large one-off amount ---
    if any(kw in desc for kw in _DONATION_KEYWORDS) or amount > _DONATION_AMOUNT_THRESHOLD:
        return "donation_income"

    # --- Default: membership income (Zelle/PayPal membership payments) ---
    return "membership_income"


def categorize(df: pd.DataFrame) -> pd.DataFrame:
    """Return df with a new 'category' column applied to every row."""
    df = df.copy()
    df["category"] = df.apply(_classify_row, axis=1)

    # Summary for transparency
    counts = df["category"].value_counts().to_dict()
    print("  Category counts:", counts)

    return df
