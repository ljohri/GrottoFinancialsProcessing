"""Generate summary charts and save them to the output directory."""

import os

import matplotlib
matplotlib.use("Agg")  # non-interactive backend for headless environments

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

from config import REPORT_PERIOD_LABEL

MONTH_ORDER = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def _dollar_fmt(x, _pos):
    return f"${x:,.0f}"


def generate_charts(df: pd.DataFrame, out_dir: str, expense_notes: dict | None = None) -> list[str]:
    """Generate bar, line, and pie charts. Returns list of saved file paths."""
    os.makedirs(out_dir, exist_ok=True)
    financial = df[df["category"] != "internal_transfer"].copy()
    saved = []

    # ------------------------------------------------------------------
    # 1. Bar chart: Total Income vs Total Expenses
    # ------------------------------------------------------------------
    membership = financial[financial["category"] == "membership_income"]["amount"].sum()
    donations = financial[financial["category"] == "donation_income"]["amount"].sum()
    expenses = abs(financial[financial["category"] == "expense"]["amount"].sum())
    paypal_fees = abs(financial[financial["category"] == "paypal_fee"]["amount"].sum())

    fig, ax = plt.subplots(figsize=(8, 5))
    categories = ["Membership\nIncome", "Donations", "Expenses", "PayPal\nFees"]
    values = [membership, donations, expenses, paypal_fees]
    colors = ["#2ecc71", "#27ae60", "#e74c3c", "#c0392b"]
    bars = ax.bar(categories, values, color=colors, width=0.5, edgecolor="white", linewidth=1.5)

    for bar, val in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 20,
            f"${val:,.0f}",
            ha="center", va="bottom", fontsize=10, fontweight="bold",
        )

    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_dollar_fmt))
    ax.set_title(f"SFBC {REPORT_PERIOD_LABEL} — Income vs Expenses", fontsize=14, fontweight="bold", pad=12)
    ax.set_ylabel("Amount (USD)")
    ax.spines[["top", "right"]].set_visible(False)
    ax.yaxis.grid(True, linestyle="--", alpha=0.5)
    ax.set_axisbelow(True)
    fig.tight_layout()

    path1 = os.path.join(out_dir, "chart_income_vs_expenses.png")
    fig.savefig(path1, dpi=150)
    plt.close(fig)
    saved.append(path1)
    print(f"  Chart saved: {path1}")

    # ------------------------------------------------------------------
    # 2. Line chart: Monthly net cash flow
    # ------------------------------------------------------------------
    income_by_month = (
        financial[financial["category"].isin(["membership_income", "donation_income"])]
        .groupby("month_name")["amount"]
        .sum()
    )
    outflow_by_month = (
        financial[financial["category"].isin(["expense", "paypal_fee"])]
        .groupby("month_name")["amount"]
        .agg(lambda s: abs(s.sum()))
    )

    all_months = [m for m in MONTH_ORDER if m in income_by_month.index or m in outflow_by_month.index]
    if all_months:
        income_vals = [income_by_month.get(m, 0.0) for m in all_months]
        outflow_vals = [outflow_by_month.get(m, 0.0) for m in all_months]
        net_vals = [i - o for i, o in zip(income_vals, outflow_vals)]
        x = range(len(all_months))
        short_months = [m[:3] for m in all_months]

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(x, income_vals, marker="o", color="#2ecc71", linewidth=2, label="Income")
        ax.plot(x, outflow_vals, marker="s", color="#e74c3c", linewidth=2, label="Outflows")
        ax.bar(x, net_vals, alpha=0.25, color=["#2ecc71" if v >= 0 else "#e74c3c" for v in net_vals],
               label="Net", zorder=1)
        ax.axhline(0, color="gray", linewidth=0.8, linestyle="--")

        ax.set_xticks(list(x))
        ax.set_xticklabels(short_months)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(_dollar_fmt))
        ax.set_title(f"SFBC {REPORT_PERIOD_LABEL} — Monthly Cash Flow", fontsize=14, fontweight="bold", pad=12)
        ax.set_ylabel("Amount (USD)")
        ax.legend()
        ax.spines[["top", "right"]].set_visible(False)
        ax.yaxis.grid(True, linestyle="--", alpha=0.4)
        ax.set_axisbelow(True)
        fig.tight_layout()

        path2 = os.path.join(out_dir, "chart_monthly_cashflow.png")
        fig.savefig(path2, dpi=150)
        plt.close(fig)
        saved.append(path2)
        print(f"  Chart saved: {path2}")

    # ------------------------------------------------------------------
    # 3. Pie chart: Expense breakdown — use Expense Notes short labels where available
    # ------------------------------------------------------------------
    from expense_notes import lookup_note, _normalize_key  # noqa: E402

    expense_rows = financial[financial["category"] == "expense"].copy()
    if not expense_rows.empty:
        def _group_expense(desc: str) -> str:
            # First: try expense notes short label
            if expense_notes:
                match = lookup_note(desc, expense_notes)
                if match:
                    return match["short_label"]
            # Fallback keyword grouping
            d = desc.lower()
            if "cleverwaiver" in d:
                return "CleverWaiver (Waivers)"
            if "dreamhost" in d:
                return "DreamHost (Web Hosting)"
            if "cavesim" in d:
                return "Cavesim"
            if "ncrc" in d or "national cave" in d:
                return "NCRC Training"
            if "speleolog" in d or "nss" in d or "western region" in d:
                return "NSS / Western Region"
            if "zelle" in d:
                return "Zelle Payments Out"
            if "check" in d:
                return "Check Payments"
            return "Other"

        expense_rows["group"] = expense_rows["description"].apply(_group_expense)
        pie_data = (
            expense_rows.groupby("group")["amount"]
            .agg(lambda s: abs(s.sum()))
            .sort_values(ascending=False)
        )

        fig, ax = plt.subplots(figsize=(8, 6))
        wedge_props = {"edgecolor": "white", "linewidth": 1.5}
        wedges, texts, autotexts = ax.pie(
            pie_data.values,
            labels=pie_data.index,
            autopct="%1.1f%%",
            startangle=140,
            wedgeprops=wedge_props,
            pctdistance=0.82,
        )
        for at in autotexts:
            at.set_fontsize(9)
        ax.set_title(f"SFBC {REPORT_PERIOD_LABEL} — Expense Breakdown", fontsize=14, fontweight="bold", pad=12)
        fig.tight_layout()

        path3 = os.path.join(out_dir, "chart_expense_breakdown.png")
        fig.savefig(path3, dpi=150)
        plt.close(fig)
        saved.append(path3)
        print(f"  Chart saved: {path3}")

    return saved
