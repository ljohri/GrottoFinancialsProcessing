"""Compute summary statistics and export the Markdown budget report."""

import os
from datetime import date

import pandas as pd
from tabulate import tabulate

from anonymize import anonymize
from config import ANALYSIS_END, ANALYSIS_START, DATA_DIR, REPORT_PERIOD_LABEL
from expense_notes import lookup_note

MAJOR_EXPENSE_THRESHOLD = 50.0


# ---------------------------------------------------------------------------
# Computation helpers
# ---------------------------------------------------------------------------

def _anonymize_df_descriptions(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["description"] = df["description"].apply(anonymize)
    return df


def generate_report(df: pd.DataFrame, expense_notes: dict | None = None) -> dict:
    """Compute all summary totals and breakdown tables from a categorized dataframe."""
    expense_notes = expense_notes or {}

    # Exclude internal transfers from all financial calculations
    financial = df[df["category"] != "internal_transfer"].copy()

    membership_df = financial[financial["category"] == "membership_income"]
    donations_df  = financial[financial["category"] == "donation_income"]
    expenses_df   = financial[financial["category"] == "expense"]
    paypal_fees_df = financial[financial["category"] == "paypal_fee"]

    total_membership  = membership_df["amount"].sum()
    total_donations   = donations_df["amount"].sum()
    total_expenses    = abs(expenses_df["amount"].sum())
    total_paypal_fees = abs(paypal_fees_df["amount"].sum())
    net_income = (total_membership + total_donations) - (total_expenses + total_paypal_fees)

    # PayPal-specific summary
    paypal_income_df   = financial[(financial["category"] == "membership_income") & (financial["source"] == "paypal")]
    paypal_donation_df = financial[(financial["category"] == "donation_income")   & (financial["source"] == "paypal")]
    paypal_gross_total = paypal_income_df["amount"].sum() + paypal_donation_df["amount"].sum()
    paypal_net         = paypal_gross_total - total_paypal_fees

    # --- Monthly income breakdown ---
    MONTH_ORDER = {
        "January": 1, "February": 2, "March": 3, "April": 4,
        "May": 5, "June": 6, "July": 7, "August": 8,
        "September": 9, "October": 10, "November": 11, "December": 12,
    }

    income_monthly = (
        membership_df.groupby("month_name")["amount"].sum()
        .rename("Membership")
        .to_frame()
        .join(donations_df.groupby("month_name")["amount"].sum().rename("Donations"), how="outer")
        .fillna(0.0)
    )
    income_monthly["Total"] = income_monthly["Membership"] + income_monthly["Donations"]
    income_monthly = income_monthly.reset_index().rename(columns={"month_name": "Month"})
    income_monthly["_sort"] = income_monthly["Month"].map(MONTH_ORDER)
    income_monthly = income_monthly.sort_values("_sort").drop(columns="_sort")
    income_monthly[["Membership", "Donations", "Total"]] = income_monthly[
        ["Membership", "Donations", "Total"]
    ].map(lambda x: f"${x:,.2f}")
    income_monthly = pd.concat(
        [income_monthly, pd.DataFrame(
            [["**TOTAL**", f"${total_membership:,.2f}", f"${total_donations:,.2f}",
              f"${total_membership + total_donations:,.2f}"]],
            columns=income_monthly.columns)],
        ignore_index=True,
    )

    # --- Monthly expense breakdown ---
    expense_monthly = (
        expenses_df.groupby("month_name")["amount"]
        .agg(lambda s: abs(s.sum()))
        .reset_index()
        .rename(columns={"month_name": "Month", "amount": "Expenses"})
    )
    expense_monthly["_sort"] = expense_monthly["Month"].map(MONTH_ORDER)
    expense_monthly = expense_monthly.sort_values("_sort").drop(columns="_sort")
    expense_monthly["Expenses"] = expense_monthly["Expenses"].map(lambda x: f"${x:,.2f}")
    expense_monthly = pd.concat(
        [expense_monthly, pd.DataFrame(
            [["**TOTAL**", f"${total_expenses:,.2f}"]],
            columns=expense_monthly.columns)],
        ignore_index=True,
    )

    # --- All itemized expenses (anonymized) ---
    expense_items = expenses_df[["date", "description", "amount"]].copy()
    expense_items = _anonymize_df_descriptions(expense_items)
    expense_items["amount"] = expense_items["amount"].map(lambda x: f"${abs(x):,.2f}")
    expense_items["date"]   = expense_items["date"].dt.strftime("%Y-%m-%d")
    expense_items = expense_items.sort_values("date")
    expense_items.columns = ["Date", "Description", "Amount"]

    # --- Major expenses with notes ---
    major_mask = expenses_df["amount"].abs() >= MAJOR_EXPENSE_THRESHOLD
    major_df   = expenses_df[major_mask].copy()
    major_df   = _anonymize_df_descriptions(major_df)

    major_rows = []
    for _, row in major_df.sort_values("date").iterrows():
        note_match = lookup_note(row["description"], expense_notes)
        note_text  = note_match["note"] if note_match else ""
        major_rows.append({
            "Date":        row["date"].strftime("%Y-%m-%d"),
            "Description": row["description"],
            "Amount":      f"${abs(row['amount']):,.2f}",
            "Note":        note_text,
        })
    major_expenses_df = pd.DataFrame(major_rows)

    # --- Zelle payments out (separate breakdown, anonymized) ---
    zelle_out = expenses_df[
        expenses_df["description"].str.contains("Zelle payment to", case=False, na=False)
    ].copy()
    zelle_out = _anonymize_df_descriptions(zelle_out)
    zelle_rows = []
    for _, row in zelle_out.sort_values("date").iterrows():
        note_match = lookup_note(row["description"], expense_notes)
        note_text  = note_match["note"] if note_match else ""
        zelle_rows.append({
            "Date":        row["date"].strftime("%Y-%m-%d"),
            "Description": row["description"],
            "Amount":      f"${abs(row['amount']):,.2f}",
            "Note":        note_text,
        })
    zelle_out_df = pd.DataFrame(zelle_rows)

    # --- Internal transfers list ---
    transfers = df[df["category"] == "internal_transfer"][["date", "description", "amount", "source"]].copy()
    transfers["amount"] = transfers["amount"].map(lambda x: f"${x:,.2f}")
    transfers["date"]   = transfers["date"].dt.strftime("%Y-%m-%d")
    transfers.columns   = ["Date", "Description", "Amount", "Source"]

    return {
        "total_membership":  total_membership,
        "total_donations":   total_donations,
        "total_expenses":    total_expenses,
        "total_paypal_fees": total_paypal_fees,
        "net_income":        net_income,
        "paypal_gross":      paypal_gross_total,
        "paypal_net":        paypal_net,
        "income_monthly":    income_monthly,
        "expense_monthly":   expense_monthly,
        "expense_items":     expense_items,
        "major_expenses":    major_expenses_df,
        "zelle_out":         zelle_out_df,
        "transfers":         transfers,
        "paypal_has_2025_data": paypal_gross_total > 0 or total_paypal_fees > 0,
        "period_label": REPORT_PERIOD_LABEL,
        "analysis_start": ANALYSIS_START,
        "analysis_end": ANALYSIS_END,
    }


# ---------------------------------------------------------------------------
# Markdown export
# ---------------------------------------------------------------------------

def _df_to_md(df: pd.DataFrame) -> str:
    return tabulate(df, headers="keys", tablefmt="pipe", showindex=False)


def export_markdown(
    report_data: dict,
    fidelity_data: dict,
    investment_data: dict,
    out_path: str,
) -> None:
    """Write the full budget report to a Markdown file."""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    r  = report_data
    f  = fidelity_data
    inv = investment_data or {}
    generated = date.today().strftime("%B %d, %Y")

    pl = r["period_label"]
    inv_year = ANALYSIS_END.year  # calendar row / labels for Fidelity investment-income xlsx
    lines = [
        f"# SFBC {pl} Budget Report",
        "",
        f"_Generated: {generated}_",
        "",
        "---",
        "",
        "## Summary",
        "",
    ]

    summary_rows = [
        ["Membership Income", f"${r['total_membership']:,.2f}"],
        ["Donations",         f"${r['total_donations']:,.2f}"],
        ["Total Income",      f"${r['total_membership'] + r['total_donations']:,.2f}"],
        ["Expenses",          f"${r['total_expenses']:,.2f}"],
        ["PayPal Fees",       f"${r['total_paypal_fees']:,.2f}"],
        ["Total Outflows",    f"${r['total_expenses'] + r['total_paypal_fees']:,.2f}"],
        ["**Net Income**",    f"**${r['net_income']:,.2f}**"],
    ]
    lines.append(tabulate(summary_rows, headers=["Metric", "Amount"], tablefmt="pipe"))
    lines += [
        "",
        "![Income vs Expenses](chart_income_vs_expenses.png)",
        "",
        "---", "", "## Income Breakdown", "", "### Monthly Income", "",
    ]
    lines.append(_df_to_md(r["income_monthly"]))
    lines += ["", "![Monthly Cash Flow](chart_monthly_cashflow.png)"]

    # --- Expense Breakdown ---
    lines += ["", "---", "", "## Expense Breakdown", "", "### Monthly Expenses", ""]
    lines.append(_df_to_md(r["expense_monthly"]))
    lines += ["", "![Expense Breakdown](chart_expense_breakdown.png)"]

    lines += ["", "### Major Expenses (>$50) with Notes", ""]
    if not r["major_expenses"].empty:
        lines.append(_df_to_md(r["major_expenses"]))
    else:
        lines.append("_No major expenses found._")

    lines += ["", "### Zelle Payments Out", ""]
    if not r["zelle_out"].empty:
        lines.append(_df_to_md(r["zelle_out"]))
    else:
        lines.append("_No outgoing Zelle payments._")

    lines += ["", "### All Itemized Expenses", ""]
    lines.append(_df_to_md(r["expense_items"]))

    # --- PayPal Summary ---
    lines += ["", "---", "", "## PayPal Summary", ""]
    if r["paypal_has_2025_data"]:
        paypal_rows = [
            ["Gross Received", f"${r['paypal_gross']:,.2f}"],
            ["Fees",           f"${r['total_paypal_fees']:,.2f}"],
            ["Net",            f"${r['paypal_net']:,.2f}"],
        ]
        lines.append(tabulate(paypal_rows, headers=["Item", "Amount"], tablefmt="pipe"))
    else:
        a0, a1 = r["analysis_start"], r["analysis_end"]
        lines += [
            "> **Note:** No completed PayPal income was found for this period (or amounts net to zero).",
            f"> Check `{os.path.join(DATA_DIR, 'paypal.CSV')}` has **Completed** rows with dates from "
            f"{a0} through {a1}.",
        ]

    # --- Fidelity Investments ---
    lines += ["", "---", "", "## Fidelity Investments", ""]
    if f and f["total_value"] > 0:
        lines.append(f"**Account:** {f['account_number']}")
        lines.append(f"**Current Portfolio Value:** ${f['total_value']:,.2f}")
        lines += [""]

        # Annual performance from xlsx
        if inv:
            perf_rows = [
                [f"Beginning Balance (Jan 1, {inv_year})",  f"${inv['beginning_balance']:,.2f}"],
                ["Market Change",                    f"${inv['market_change']:+,.2f}"],
                ["Dividends",                        f"${inv['dividends']:,.2f}"],
                [f"Ending Balance (Dec 31, {inv_year})",    f"${inv['ending_balance']:,.2f}"],
                ["**Total Return ($)**",             f"**${inv['total_return']:+,.2f}**"],
                ["**Total Return (%)**",             f"**{inv['return_pct']:+.2f}%**"],
            ]
            lines += [f"### {inv_year} Annual Performance", ""]
            lines.append(tabulate(perf_rows, headers=["Metric", "Value"], tablefmt="pipe"))
            lines += [""]

        holdings = f["holdings"].copy()
        holdings["current_value"]          = holdings["current_value"].map(lambda x: f"${x:,.2f}")
        holdings["last_price"]             = holdings["last_price"].map(lambda x: f"${x:,.2f}" if x > 0 else "—")
        holdings["total_gain_loss_dollar"] = holdings["total_gain_loss_dollar"].map(
            lambda x: f"+${x:,.2f}" if x >= 0 else f"-${abs(x):,.2f}")
        holdings["total_gain_loss_pct"]    = holdings["total_gain_loss_pct"].map(lambda x: f"{x:+.2f}%")
        holdings["percent_of_account"]     = holdings["percent_of_account"].map(lambda x: f"{x:.2f}%")

        display_cols = ["symbol", "description", "last_price", "current_value",
                        "total_gain_loss_dollar", "total_gain_loss_pct", "percent_of_account"]
        holdings_display = holdings[display_cols].rename(columns={
            "symbol": "Symbol", "description": "Description",
            "last_price": "Last Price", "current_value": "Current Value",
            "total_gain_loss_dollar": "Total G/L $", "total_gain_loss_pct": "Total G/L %",
            "percent_of_account": "Allocation",
        })
        lines += ["### Holdings", ""]
        lines.append(_df_to_md(holdings_display))
    else:
        lines.append("> Fidelity data not available.")

    # --- Notes ---
    lines += [
        "", "---", "", "## Notes", "",
        "- **Internal transfers excluded:** PayPal <-> Chase ACH transfers are detected and",
        "  excluded from all income/expense totals to avoid double-counting.",
        f"- **Date range:** Only transactions with posting dates from **{r['analysis_start']}** "
        f"through **{r['analysis_end']}** (inclusive) are included.",
        "- **PayPal fees:** PayPal processing fees are tracked separately and excluded from income.",
        "- **Income classification:** Donations are detected by keywords in the transaction",
        "  description (e.g. donation, benevity). Other positive credits are treated as membership income.",
        "- **Major expenses:** Expenses >= $50 are listed with notes in the Major Expenses section.",
        "- **Name redaction:** Personal names in transaction descriptions have been anonymized.",
        "- **Fidelity:** Portfolio positions are as of the CSV export date and are not mixed",
        "  into operating income or expense figures.",
        "",
    ]

    if not r["transfers"].empty:
        lines += ["### Internal Transfers (Excluded)", ""]
        lines.append(_df_to_md(r["transfers"]))
        lines.append("")

    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))

    print(f"  Report written to {out_path}")
