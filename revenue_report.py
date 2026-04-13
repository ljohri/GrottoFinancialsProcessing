"""Consolidated revenue report across Chase and PayPal accounts.

Produces a full line-item listing of all 2025 income transactions,
clearly flagged by source account, with subtotals by source and category.

Run:
    uv run python revenue_report.py

Outputs:
    output/2025_revenue_consolidated.csv   — machine-readable line items
    output/2025_revenue_consolidated.txt   — formatted text report
"""

import os
import sys

import pandas as pd
from tabulate import tabulate

from anonymize import anonymize
from categorize import categorize
from config import DATA_DIR, OUTPUT_DIR
from load_data import load_all_data
from transform import transform

INCOME_CATEGORIES = {"membership_income", "donation_income"}

_CATEGORY_LABELS = {
    "membership_income": "Membership",
    "donation_income":   "Donation",
}

_SOURCE_LABELS = {
    "chase":  "Chase",
    "paypal": "PayPal",
}


# ---------------------------------------------------------------------------
# Build the consolidated revenue dataframe
# ---------------------------------------------------------------------------

def build_revenue_df(data_dir: str) -> pd.DataFrame:
    raw        = load_all_data(data_dir)
    clean      = transform(raw)
    categorized = categorize(clean)

    revenue = categorized[categorized["category"].isin(INCOME_CATEGORIES)].copy()
    revenue = revenue.sort_values("date").reset_index(drop=True)

    revenue["description_clean"] = revenue["description"].apply(anonymize)
    revenue["source_label"]      = revenue["source"].map(_SOURCE_LABELS).fillna(revenue["source"].str.upper())
    revenue["category_label"]    = revenue["category"].map(_CATEGORY_LABELS)

    return revenue


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _fmt(amount: float) -> str:
    return f"${amount:>10,.2f}"


def _section_header(title: str, width: int = 80) -> str:
    bar = "─" * width
    return f"\n{bar}\n  {title}\n{bar}"


def _build_line_items_table(df: pd.DataFrame) -> str:
    rows = [
        {
            "#":           i + 1,
            "Date":        row["date"].strftime("%m/%d/%Y"),
            "Source":      row["source_label"],
            "Category":    row["category_label"],
            "Amount":      f"${row['amount']:,.2f}",
            "Description": row["description_clean"],
        }
        for i, (_, row) in enumerate(df.iterrows())
    ]
    return tabulate(
        rows,
        headers="keys",
        tablefmt="simple",
        colalign=("right", "left", "left", "left", "right", "left"),
    )


def _build_subtotal_table(df: pd.DataFrame, group_col: str, label_col: str) -> str:
    grouped = (
        df.groupby(group_col)["amount"]
        .agg(count="count", total="sum")
        .reset_index()
        .rename(columns={group_col: label_col})
        .sort_values("total", ascending=False)
    )
    rows = [
        {
            label_col:    row[label_col],
            "Transactions": int(row["count"]),
            "Total":        f"${row['total']:,.2f}",
        }
        for _, row in grouped.iterrows()
    ]
    rows.append({label_col: "TOTAL", "Transactions": int(df.shape[0]), "Total": f"${df['amount'].sum():,.2f}"})
    return tabulate(rows, headers="keys", tablefmt="simple",
                    colalign=("left", "right", "right"))


# ---------------------------------------------------------------------------
# Full report builder
# ---------------------------------------------------------------------------

def generate_report(revenue: pd.DataFrame) -> str:
    lines: list[str] = []

    grand_total   = revenue["amount"].sum()
    chase_total   = revenue.loc[revenue["source"] == "chase",  "amount"].sum()
    paypal_total  = revenue.loc[revenue["source"] == "paypal", "amount"].sum()
    membership_total = revenue.loc[revenue["category"] == "membership_income", "amount"].sum()
    donation_total   = revenue.loc[revenue["category"] == "donation_income",   "amount"].sum()

    # ── Title ──────────────────────────────────────────────────────────────
    lines.append("=" * 80)
    lines.append("  SFBC 2025 — CONSOLIDATED REVENUE REPORT")
    lines.append("  All accounts · All line items")
    lines.append("=" * 80)

    # ── Executive summary ──────────────────────────────────────────────────
    lines.append(_section_header("SUMMARY"))
    summary_rows = [
        {"Account":  "Chase",            "Revenue": _fmt(chase_total)},
        {"Account":  "PayPal",           "Revenue": _fmt(paypal_total)},
        {"Account":  "─────────────────", "Revenue": "────────────"},
        {"Account":  "GRAND TOTAL",      "Revenue": _fmt(grand_total)},
    ]
    lines.append(tabulate(summary_rows, headers="keys", tablefmt="simple",
                           colalign=("left", "right")))

    lines.append("")
    category_rows = [
        {"Category":  "Membership",       "Revenue": _fmt(membership_total)},
        {"Category":  "Donations",        "Revenue": _fmt(donation_total)},
        {"Category":  "─────────────────","Revenue": "────────────"},
        {"Category":  "GRAND TOTAL",      "Revenue": _fmt(grand_total)},
    ]
    lines.append(tabulate(category_rows, headers="keys", tablefmt="simple",
                           colalign=("left", "right")))

    # ── Per-source subtotals ───────────────────────────────────────────────
    lines.append(_section_header("BY SOURCE ACCOUNT"))
    lines.append(_build_subtotal_table(revenue, "source_label", "Source"))

    # ── Per-category subtotals ─────────────────────────────────────────────
    lines.append(_section_header("BY CATEGORY"))
    lines.append(_build_subtotal_table(revenue, "category_label", "Category"))

    # ── Monthly breakdown ──────────────────────────────────────────────────
    lines.append(_section_header("MONTHLY BREAKDOWN BY SOURCE"))
    month_pivot = (
        revenue.assign(month=revenue["date"].dt.strftime("%b"))
               .assign(month_num=revenue["date"].dt.month)
               .groupby(["month_num", "month", "source_label"])["amount"]
               .sum()
               .reset_index()
               .pivot_table(index=["month_num", "month"], columns="source_label",
                             values="amount", aggfunc="sum", fill_value=0.0)
               .reset_index()
    )
    month_pivot.columns.name = None
    month_pivot = month_pivot.rename(columns={"month": "Month"})
    month_pivot = month_pivot.drop(columns=["month_num"])

    numeric_cols = [c for c in month_pivot.columns if c != "Month"]
    month_pivot["Total"] = month_pivot[numeric_cols].sum(axis=1)

    # Format dollar values
    formatted = month_pivot.copy()
    for col in numeric_cols + ["Total"]:
        formatted[col] = formatted[col].apply(lambda v: f"${v:,.2f}")

    # Totals row
    totals = {"Month": "TOTAL"}
    for col in numeric_cols:
        totals[col] = f"${month_pivot[col].sum():,.2f}"
    totals["Total"] = f"${month_pivot['Total'].sum():,.2f}"
    formatted = pd.concat([formatted, pd.DataFrame([totals])], ignore_index=True)

    lines.append(tabulate(formatted, headers="keys", showindex=False,
                           tablefmt="simple", colalign=("left",) + ("right",) * (len(formatted.columns) - 1)))

    # ── Chase line items ───────────────────────────────────────────────────
    chase_df = revenue[revenue["source"] == "chase"]
    lines.append(_section_header(f"CHASE — ALL LINE ITEMS  ({len(chase_df)} transactions)"))
    if chase_df.empty:
        lines.append("  (no Chase revenue transactions)")
    else:
        lines.append(_build_line_items_table(chase_df))
        lines.append(f"\n  Chase Total: {_fmt(chase_total)}")

    # ── PayPal line items ──────────────────────────────────────────────────
    paypal_df = revenue[revenue["source"] == "paypal"]
    lines.append(_section_header(f"PAYPAL — ALL LINE ITEMS  ({len(paypal_df)} transactions)"))
    if paypal_df.empty:
        lines.append("  (no PayPal revenue transactions)")
    else:
        lines.append(_build_line_items_table(paypal_df))
        lines.append(f"\n  PayPal Total: {_fmt(paypal_total)}")

    # ── Grand total footer ─────────────────────────────────────────────────
    lines.append("\n" + "=" * 80)
    lines.append(f"  GRAND TOTAL REVENUE  {_fmt(grand_total)}")
    lines.append(f"  {'Chase':30s}  {_fmt(chase_total)}")
    lines.append(f"  {'PayPal':30s}  {_fmt(paypal_total)}")
    lines.append("=" * 80)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

def export_csv(revenue: pd.DataFrame, path: str) -> None:
    out = revenue[["date", "source_label", "category_label", "amount", "description_clean"]].copy()
    out = out.rename(columns={
        "source_label":      "source",
        "category_label":    "category",
        "description_clean": "description",
    })
    out["date"] = out["date"].dt.strftime("%m/%d/%Y")
    out.to_csv(path, index=False)
    print(f"  CSV saved: {path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    print("=== SFBC 2025 Consolidated Revenue Report ===\n")

    print("[1/3] Loading and processing transactions...")
    revenue = build_revenue_df(DATA_DIR)
    print(f"  Revenue transactions: {len(revenue)}\n")

    if revenue.empty:
        print("No revenue transactions found. Exiting.")
        sys.exit(0)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("[2/3] Generating report...")
    report_text = generate_report(revenue)
    print()

    txt_path = os.path.join(OUTPUT_DIR, "2025_revenue_consolidated.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(report_text)
    print(f"  Report saved: {txt_path}")

    print("[3/3] Exporting CSV...")
    csv_path = os.path.join(OUTPUT_DIR, "2025_revenue_consolidated.csv")
    export_csv(revenue, csv_path)

    print()
    print(report_text)
    print(f"\nDone. Output written to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
