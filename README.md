# SFBC Budget Report Generator

Generates a structured annual budget report for the **San Francisco Bay Chapter (SFBC)**
from Chase, PayPal, and Fidelity financial exports.

Outputs: `output/2025_budget_report.md`, `.pdf`, and `.docx` — all with embedded charts.

---

## Requirements

- **Python 3.13+** managed by [uv](https://github.com/astral-sh/uv)

Install dependencies:

```bash
uv sync
```

Or add them fresh:

```bash
uv add pandas numpy matplotlib python-dateutil tabulate fpdf2 openpyxl python-docx
```

---

## Running the Report

```bash
uv run python main.py
```

All output is written to `output/`.

---

## Input Files

Place all source files in `docs/input_docs/2025/` before running.

### 1. Chase Bank Activity CSV

**Filename pattern:** `Chase9010_Activity_*.CSV`
(e.g. `Chase9010_Activity_20260319.CSV`)

**How to export:**
1. Log in to chase.com → Accounts → Checking account
2. Click **Download Account Activity**
3. Select date range: **Jan 1 – Dec 31, 2025**
4. Format: **CSV**
5. Save to `docs/input_docs/2025/`

**Expected columns:**
```
Details, Posting Date, Description, Amount, Type, Balance, Check or Slip #
```

**Notes:**
- Positive `Amount` = credit (income); negative = debit (expense)
- Zelle payments received appear with `Type` = `PARTNERFI_TO_CHASE` or `QUICKPAY_CREDIT`
- Zelle payments sent appear with `Type` = `CHASE_TO_PARTNERFI` or `QUICKPAY_DEBIT`
- PayPal↔Chase ACH transfers are automatically detected and excluded from totals

---

### 2. PayPal Activity CSV

**Filename:** `paypal.CSV`

**How to export:**
1. Log in to paypal.com → Activity → All Transactions
2. Set date range: **Jan 1 – Dec 31, 2025**
3. Click **Download** → select **CSV** format
4. Rename the file to `paypal.CSV`
5. Save to `docs/input_docs/2025/`

**Expected columns (key ones):**
```
Date, Time, TimeZone, Name, Type, Status, Currency, Gross, Fee, Net, ...
```

**Notes:**
- Only `Status == Completed` transactions are processed
- `Gross` (positive) = income received; `Fee` (negative) = PayPal processing fee
- Fee rows are split out and tracked separately as `paypal_fee` category
- Make sure the export covers the full calendar year 2025; partial exports will
  produce a note in the report flagging missing data

---

### 3. Fidelity Portfolio Positions CSV

**Filename pattern:** `Fidelity Portfolio_Positions_*.csv`
(e.g. `Fidelity Portfolio_Positions_Mar-19-2026.csv`)

**How to export:**
1. Log in to fidelity.com → Portfolio → Positions
2. Click the **Download** icon (top-right of positions table)
3. Select **CSV**
4. Save to `docs/input_docs/2025/`

**Expected columns:**
```
Account Number, Account Name, Symbol, Description, Quantity, Last Price,
Last Price Change, Current Value, Today's Gain/Loss Dollar, ...
Total Gain/Loss Dollar, Total Gain/Loss Percent, Percent Of Account,
Cost Basis Total, Average Cost Basis, Type
```

**Notes:**
- The file contains a multi-paragraph disclaimer footer after the position rows;
  the parser automatically discards it
- Dollar signs (`$`), plus signs (`+`), and percent signs (`%`) in numeric columns
  are stripped automatically
- This section appears **separately** from operating income/expenses — it is never
  mixed into the income or expense totals

---

### 4. Fidelity Investment Income XLSX

**Filename pattern:** `Investment_income*.xlsx`
(e.g. `Investment_income_balance_detail 2.xlsx`)

**How to export:**
1. Log in to fidelity.com → Portfolio → Performance & Analysis → Investment Income
2. Set **Account**: Corporation (or the relevant account)
3. Set **Time period**: Custom → Jan 1 2025 – Dec 31 2025
4. Set **Frequency**: Yearly
5. Click **Export** → Excel (`.xlsx`)
6. Save to `docs/input_docs/2025/`

**Expected structure:**
```
Row 1-4: Title/header text (ignored)
Row 5:   Column headers: Yearly | Beginning balance | Market change |
                         Dividends | Interest | Deposits | Withdrawals |
                         Net advisory fees | Ending balance
Row 6+:  One row per year (e.g. "2025(As of ...)")
```

**Data extracted for the 2025 Annual Performance table:**
| Field | Description |
|---|---|
| Beginning balance | Portfolio value on Jan 1, 2025 |
| Market change | Capital appreciation/depreciation |
| Dividends | Dividend income received |
| Ending balance | Portfolio value on Dec 31, 2025 |
| Total Return ($) | Market change + Dividends |
| Total Return (%) | Total return ÷ Beginning balance |

---

### 5. Expense Notes (optional)

**Filename:** `docs/input_docs/2025/Expense Notes.txt`

Provides human-readable annotations for major expenses. These notes appear in:
- The **Major Expenses** table in all report formats
- The **Zelle Payments Out** breakdown
- The **expense pie chart** labels (first line of each note is used as the label)

**Format:**
```
<exact transaction description from Chase CSV> :
<short note / brief description>

<next transaction description>:
<note>
```

**Example:**
```
 Online Payment 25091919723 To Western Region of the National Speleolog 06/11 :
 WCC Funds

 Zelle payment to RON MILLER JPM99bsjkkc6:
 SPAR related expense for the trainer
```

**Rules:**
- Matching is done by substring — the description key does not need to be exact,
  but should be distinctive enough to avoid false matches
- Blocks are separated by one or more blank lines
- Leading/trailing whitespace and trailing colons on the description line are ignored
- The note text (second line) is used as the **short label** in the pie chart

---

## Name Redaction

Personal names appearing in transaction descriptions are automatically anonymized
before being written to any output file:

| Original | Redacted |
|---|---|
| `Avik` | `A***` |
| `RON MILLER` | `R***` |
| `Zelle payment to Jane Smith ABC123` | `Zelle payment to J*** ABC123` |

To add additional known names, edit the `_STATIC_REPLACEMENTS` list in `anonymize.py`.
Dynamic redaction of Zelle "payment to" names is handled automatically for any name
not in the static list.

---

## Output Files

All outputs are written to the `output/` directory:

| File | Description |
|---|---|
| `2025_budget_report.md` | Markdown report with relative image links |
| `2025_budget_report.pdf` | Self-contained PDF with embedded charts |
| `2025_budget_report.docx` | Word document with embedded charts |
| `chart_income_vs_expenses.png` | Bar chart: income vs expenses |
| `chart_monthly_cashflow.png` | Line chart: monthly income, outflows, net |
| `chart_expense_breakdown.png` | Pie chart: expense categories |

---

## Report Sections

1. **Summary** — top-level income, expense, and net income totals
2. **Income Breakdown** — monthly membership income and donations table
3. **Expense Breakdown** — monthly totals, major expenses with notes, Zelle payments out, full itemized list
4. **PayPal Summary** — gross received, fees, net
5. **Fidelity Investments** — 2025 annual performance (gains in $ and %), current holdings table
6. **Notes** — methodology, filters applied, name redaction policy
7. **Internal Transfers (Excluded)** — appendix listing all detected PayPal↔Chase transfers

---

## Project Structure

```
sfbc_accounts/
├── main.py              — entry point
├── load_data.py         — CSV loading and normalization
├── transform.py         — date parsing, amount cleaning, 2025 filter
├── categorize.py        — transaction categorization
├── anonymize.py         — personal name redaction
├── expense_notes.py     — Expense Notes.txt parser
├── fidelity.py          — Fidelity CSV + Investment Income xlsx parser
├── charts.py            — matplotlib chart generation
├── report.py            — Markdown report export
├── pdf_export.py        — PDF report export (fpdf2)
├── docx_export.py       — Word document export (python-docx)
├── pyproject.toml       — uv project and dependency config
├── docs/
│   └── input_docs/
│       └── 2025/
│           ├── Chase9010_Activity_*.CSV
│           ├── paypal.CSV
│           ├── Fidelity Portfolio_Positions_*.csv
│           ├── Investment_income*.xlsx
│           └── Expense Notes.txt
└── output/
    ├── 2025_budget_report.md
    ├── 2025_budget_report.pdf
    ├── 2025_budget_report.docx
    └── chart_*.png
```
