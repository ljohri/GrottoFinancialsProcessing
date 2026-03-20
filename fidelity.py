"""Parse Fidelity Portfolio Positions CSV and Investment Income xlsx."""

import glob
import os
import re

import openpyxl
import pandas as pd


def _clean_money(value) -> float:
    """Strip $, +, commas from a value and return float. Returns 0.0 if unparseable."""
    if pd.isna(value):
        return 0.0
    s = str(value).replace("$", "").replace("+", "").replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return 0.0


def _clean_percent(value) -> float:
    """Strip %, + from a value and return float. Returns 0.0 if unparseable."""
    if pd.isna(value):
        return 0.0
    s = str(value).replace("%", "").replace("+", "").strip()
    try:
        return float(s)
    except ValueError:
        return 0.0


def analyze_fidelity(path: str) -> dict:
    """Parse a Fidelity positions CSV and return a summary dict.

    Handles:
    - Dollar-sign prefixed numeric columns (Current Value, Last Price, etc.)
    - Footer disclaimer rows after the position data
    - Missing / money-market rows with sparse data
    """
    # Read a generous number of rows; we'll drop footer rows below.
    # index_col=False prevents column-shift caused by trailing commas in data rows.
    df = pd.read_csv(path, nrows=20, index_col=False)

    # Keep only rows that have a non-empty Symbol column and are actual fund rows
    # (footer rows have NaN or empty Symbol after the data block)
    df = df[df["Symbol"].notna()].copy()
    df = df[df["Symbol"].str.strip() != ""].copy()
    # Drop rows whose Symbol looks like a sentence fragment (footer bleed-through)
    df = df[~df["Symbol"].str.contains(r"\s{3,}", regex=True)].copy()

    if df.empty:
        return {"holdings": pd.DataFrame(), "total_value": 0.0, "account_number": "N/A"}

    account_number = str(df["Account Number"].iloc[0]) if "Account Number" in df.columns else "N/A"

    # Clean numeric columns
    df["current_value"] = df["Current Value"].apply(_clean_money)
    df["last_price"] = df["Last Price"].apply(_clean_money)
    df["total_gain_loss_dollar"] = df["Total Gain/Loss Dollar"].apply(_clean_money)
    df["total_gain_loss_pct"] = df["Total Gain/Loss Percent"].apply(_clean_percent)
    df["percent_of_account"] = df["Percent Of Account"].apply(_clean_percent)
    df["cost_basis"] = df["Cost Basis Total"].apply(_clean_money)

    quantity_raw = df["Quantity"].astype(str).str.strip()
    df["quantity"] = pd.to_numeric(quantity_raw, errors="coerce").fillna(0.0)

    # Build clean holdings table
    holdings = df[
        ["Symbol", "Description", "quantity", "last_price", "current_value",
         "total_gain_loss_dollar", "total_gain_loss_pct", "percent_of_account", "cost_basis"]
    ].copy()
    holdings = holdings.rename(columns={
        "Symbol": "symbol",
        "Description": "description",
    })

    total_value = holdings["current_value"].sum()

    # Recompute allocation if Percent Of Account is missing/zero for all rows
    if holdings["percent_of_account"].sum() == 0 and total_value > 0:
        holdings["percent_of_account"] = (holdings["current_value"] / total_value * 100).round(2)

    print(f"  Fidelity account: {account_number}, total value: ${total_value:,.2f}")
    print(f"  Holdings: {len(holdings)} position(s)")

    return {
        "holdings": holdings,
        "total_value": total_value,
        "account_number": account_number,
    }


def find_fidelity_path(data_dir: str) -> str | None:
    """Return the first Fidelity positions CSV found in data_dir, or None."""
    patterns = [
        os.path.join(data_dir, "Fidelity Portfolio_Positions_*.csv"),
        os.path.join(data_dir, "Fidelity*.csv"),
    ]
    for pattern in patterns:
        matches = glob.glob(pattern)
        if matches:
            return matches[0]
    return None


def find_investment_income_path(data_dir: str) -> str | None:
    """Return the first Investment Income xlsx found in data_dir, or None."""
    patterns = [
        os.path.join(data_dir, "Investment_income*.xlsx"),
        os.path.join(data_dir, "Investment-Income*.xlsx"),
        os.path.join(data_dir, "Investment*.xlsx"),
    ]
    for pattern in patterns:
        matches = glob.glob(pattern)
        if matches:
            return matches[0]
    return None


def analyze_investment_income(path: str, target_year: int = 2025) -> dict:
    """Parse a Fidelity Investment Income xlsx and return annual performance for target_year.

    Expected xlsx structure (rows 5-7 after headers):
        Row 5: header  → Yearly | Beginning balance | Market change | Dividends | ... | Ending balance
        Row 6: 2026 partial data
        Row 7: 2025 full-year data
        Row 8: Totals

    Returns a dict with:
        year, beginning_balance, market_change, dividends, ending_balance,
        total_return, return_pct
    """
    if not path or not os.path.exists(path):
        return {}

    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active

    header_row_idx = None
    col_map: dict[str, int] = {}

    all_rows = list(ws.iter_rows(values_only=True))

    # Find the header row (contains "Yearly" or "Beginning balance")
    for i, row in enumerate(all_rows):
        row_vals = [str(v).strip().lower() if v is not None else "" for v in row]
        if "yearly" in row_vals or "beginning balance" in row_vals:
            header_row_idx = i
            for j, v in enumerate(row):
                if v is not None:
                    col_map[str(v).strip().lower()] = j
            break

    if header_row_idx is None:
        print("  Warning: could not find Investment Income header row")
        return {}

    # Find the row matching target_year
    result = {}
    for row in all_rows[header_row_idx + 1:]:
        first_cell = str(row[0]).strip() if row[0] is not None else ""
        if str(target_year) in first_cell:
            def _get(col_name: str) -> float:
                idx = col_map.get(col_name.lower())
                if idx is None:
                    return 0.0
                val = row[idx]
                if val is None:
                    return 0.0
                try:
                    return float(str(val).replace(",", "").replace("$", "").strip())
                except (ValueError, TypeError):
                    return 0.0

            beginning = _get("beginning balance")
            market_change = _get("market change")
            dividends = _get("dividends")
            ending = _get("ending balance")
            total_return = market_change + dividends
            return_pct = (total_return / beginning * 100) if beginning != 0 else 0.0

            result = {
                "year": target_year,
                "beginning_balance": beginning,
                "market_change": market_change,
                "dividends": dividends,
                "ending_balance": ending,
                "total_return": total_return,
                "return_pct": return_pct,
            }
            print(
                f"  Investment income {target_year}: "
                f"return ${total_return:,.2f} ({return_pct:.2f}%)"
            )
            break

    if not result:
        print(f"  Warning: no investment income row found for {target_year}")

    return result
