"""SFBC 2025 Budget Report — main entry point.

Run:
    uv run python main.py
"""

import os

from categorize import categorize
from charts import generate_charts
from config import (
    ANALYSIS_END,
    ANALYSIS_START,
    DATA_DIR,
    OUTPUT_DIR,
    REPORT_PERIOD_LABEL,
)
from docx_export import export_docx
from expense_notes import load_expense_notes
from fidelity import (analyze_fidelity, analyze_investment_income,
                      find_fidelity_path, find_investment_income_path)
from load_data import load_all_data
from pdf_export import export_pdf
from report import export_markdown, generate_report
from transform import transform

NOTES_PATH  = os.path.join(DATA_DIR, "Expense Notes.txt")
REPORT_MD   = os.path.join(OUTPUT_DIR, "2025_budget_report.md")
REPORT_PDF  = f"{OUTPUT_DIR}/2025_budget_report.pdf"
REPORT_DOCX = f"{OUTPUT_DIR}/2025_budget_report.docx"


def main() -> None:
    print(f"=== SFBC {REPORT_PERIOD_LABEL} Budget Report Generator ===\n")

    # --- Expense notes ---
    print("[0/6] Loading expense notes...")
    expense_notes = load_expense_notes(NOTES_PATH)
    print(f"  Loaded {len(expense_notes)} expense note(s)\n")

    # --- Load ---
    print("[1/6] Loading source data...")
    data = load_all_data(DATA_DIR)
    print(f"  Raw rows loaded: {len(data)}\n")

    # --- Transform ---
    print(
        f"[2/6] Transforming and filtering to {ANALYSIS_START}–{ANALYSIS_END} "
        f"({REPORT_PERIOD_LABEL})..."
    )
    clean = transform(data)
    print()

    # --- Categorize ---
    print("[3/6] Categorizing transactions...")
    categorized = categorize(clean)
    print()

    # --- Charts (before report so notes influence pie labels) ---
    print("[4/6] Generating charts...")
    chart_paths = generate_charts(categorized, OUTPUT_DIR, expense_notes=expense_notes)
    print()

    # --- Report data ---
    print("[5/6] Computing report figures...")
    report_data = generate_report(categorized, expense_notes=expense_notes)
    print(f"  Membership income : ${report_data['total_membership']:,.2f}")
    print(f"  Donations         : ${report_data['total_donations']:,.2f}")
    print(f"  Expenses          : ${report_data['total_expenses']:,.2f}")
    print(f"  PayPal fees       : ${report_data['total_paypal_fees']:,.2f}")
    print(f"  Net income        : ${report_data['net_income']:,.2f}")
    print()

    # --- Fidelity positions ---
    print("[5b] Analyzing Fidelity positions...")
    fidelity_path = find_fidelity_path(DATA_DIR)
    fidelity_data = analyze_fidelity(fidelity_path) if fidelity_path else {
        "holdings": None, "total_value": 0.0, "account_number": "N/A"
    }

    # --- Investment income xlsx ---
    print("[5c] Analyzing investment income...")
    inv_path = find_investment_income_path(DATA_DIR)
    investment_data = (
        analyze_investment_income(inv_path, target_year=ANALYSIS_END.year)
        if inv_path
        else {}
    )
    print()

    # --- Export ---
    print("[6/6] Exporting reports...")
    export_markdown(report_data, fidelity_data, investment_data, REPORT_MD)
    export_pdf(report_data, fidelity_data, investment_data, OUTPUT_DIR, REPORT_PDF)
    export_docx(report_data, fidelity_data, investment_data, OUTPUT_DIR, REPORT_DOCX)
    print()

    print("=== Done ===")
    print(f"Markdown : {REPORT_MD}")
    print(f"PDF      : {REPORT_PDF}")
    print(f"DOCX     : {REPORT_DOCX}")
    if chart_paths:
        print("Charts   :")
        for p in chart_paths:
            print(f"  {p}")


if __name__ == "__main__":
    main()
