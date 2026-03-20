"""Generate a PDF version of the SFBC 2025 Budget Report with embedded charts."""

import os
from datetime import date

from fpdf import FPDF, XPos, YPos

# ---------------------------------------------------------------------------
# Styling constants
# ---------------------------------------------------------------------------
FONT = "Helvetica"
C_DARK       = (30, 30, 30)
C_ACCENT     = (41, 98, 155)
C_SUBHEAD    = (60, 100, 160)
C_ROW_ALT    = (240, 245, 252)
C_ROW_WHITE  = (255, 255, 255)
C_HDR_BG     = (41, 98, 155)
C_HDR_FG     = (255, 255, 255)
C_RULE       = (180, 180, 180)
C_POS        = (30, 130, 76)
C_NEG        = (180, 30, 30)
C_NOTE_BG    = (255, 252, 230)

PAGE_W   = 210
MARGIN   = 14
CW       = PAGE_W - 2 * MARGIN   # content width


def _safe(text) -> str:
    """Encode to latin-1, replacing unsupported Unicode chars with ASCII equivalents."""
    s = str(text) if text is not None else ""
    replacements = {
        "\u2022": "-", "\u2014": "--", "\u2013": "-",
        "\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"',
        "\u2190": "<-", "\u2192": "->", "\u2194": "<->",
        "\u00b7": ".", "\u00a0": " ",
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    return s.encode("latin-1", errors="replace").decode("latin-1")


class BudgetPDF(FPDF):
    def __init__(self):
        super().__init__("P", "mm", "A4")
        self.set_margins(MARGIN, MARGIN, MARGIN)
        self.set_auto_page_break(auto=True, margin=18)
        self._generated = date.today().strftime("%B %d, %Y")

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font(FONT, "I", 8)
        self.set_text_color(*C_RULE)
        self.cell(0, 5, "SFBC 2025 Budget Report", align="L")
        self.set_xy(MARGIN, self.get_y())
        self.cell(0, 5, f"Page {self.page_no()}", align="R",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(*C_RULE)
        self.set_line_width(0.2)
        self.line(MARGIN, self.get_y(), PAGE_W - MARGIN, self.get_y())
        self.ln(2)

    def footer(self):
        self.set_y(-12)
        self.set_font(FONT, "I", 7)
        self.set_text_color(*C_RULE)
        self.cell(0, 6, _safe(f"Generated {self._generated}  |  Confidential"), align="C")

    # ------------------------------------------------------------------
    # Layout helpers
    # ------------------------------------------------------------------
    def _rule(self, top_pad: int = 2, bottom_pad: int = 3):
        self.ln(top_pad)
        self.set_draw_color(*C_RULE)
        self.set_line_width(0.3)
        self.line(MARGIN, self.get_y(), PAGE_W - MARGIN, self.get_y())
        self.ln(bottom_pad)

    def _h2(self, text: str):
        self.ln(4)
        self.set_font(FONT, "B", 13)
        self.set_text_color(*C_ACCENT)
        self.cell(0, 8, _safe(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self._rule(top_pad=1)

    def _h3(self, text: str):
        self.ln(2)
        self.set_font(FONT, "B", 10)
        self.set_text_color(*C_SUBHEAD)
        self.cell(0, 6, _safe(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def _body(self, text: str):
        self.set_font(FONT, "", 9)
        self.set_text_color(*C_DARK)
        self.multi_cell(0, 5, _safe(text))

    def _note_box(self, text: str):
        """Render a shaded note paragraph."""
        self.set_fill_color(*C_NOTE_BG)
        self.set_font(FONT, "I", 8.5)
        self.set_text_color(*C_DARK)
        self.multi_cell(0, 5, _safe(text), fill=True)
        self.ln(1)

    def _kv(self, label: str, value: str, bold_value: bool = False,
             value_color: tuple | None = None):
        self.set_font(FONT, "", 9)
        self.set_text_color(*C_DARK)
        self.cell(72, 6, _safe(label))
        style = "B" if bold_value else ""
        self.set_font(FONT, style, 9)
        if value_color:
            self.set_text_color(*value_color)
        self.cell(0, 6, _safe(value), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        if value_color:
            self.set_text_color(*C_DARK)

    def _table(self, headers: list, rows: list, col_widths: list,
               alignments: list | None = None, wrap_last: bool = False):
        alignments = alignments or (["L"] * len(headers))
        row_h = 6

        self.set_font(FONT, "B", 8)
        self.set_fill_color(*C_HDR_BG)
        self.set_text_color(*C_HDR_FG)
        for h, w, a in zip(headers, col_widths, alignments):
            self.cell(w, row_h + 1, _safe(h), border=0, align=a, fill=True)
        self.ln()

        self.set_text_color(*C_DARK)
        for r_idx, row in enumerate(rows):
            is_total = str(row[0]).upper().replace("*", "").strip().startswith("TOTAL")
            if is_total:
                self.set_fill_color(*C_HDR_BG)
                self.set_text_color(*C_HDR_FG)
                self.set_font(FONT, "B", 8)
            elif r_idx % 2 == 0:
                self.set_fill_color(*C_ROW_ALT)
                self.set_font(FONT, "", 8)
            else:
                self.set_fill_color(*C_ROW_WHITE)
                self.set_font(FONT, "", 8)

            if wrap_last and len(row) > 0:
                # Print all columns except last normally, then multi_cell for last
                for cell_val, w, a in zip(row[:-1], col_widths[:-1], alignments[:-1]):
                    self.cell(w, row_h, _safe(cell_val), border=0, align=a, fill=True)
                # Save x position for potential wrap
                last_x = self.get_x()
                last_y = self.get_y()
                self.multi_cell(col_widths[-1], row_h, _safe(row[-1]),
                                border=0, align=alignments[-1], fill=True)
                # Ensure we're at the start of next line after multi_cell
                self.set_x(MARGIN)
            else:
                for cell_val, w, a in zip(row, col_widths, alignments):
                    self.cell(w, row_h, _safe(cell_val), border=0, align=a, fill=True)
                self.ln()

        self.set_text_color(*C_DARK)
        self.ln(2)

    def _embed_chart(self, path: str, caption: str, w: float = CW):
        if not os.path.exists(path):
            return
        x = MARGIN + (CW - w) / 2
        self.image(path, x=x, w=w)
        self.set_font(FONT, "I", 7.5)
        self.set_text_color(*C_RULE)
        self.cell(0, 5, _safe(caption), align="C",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2)


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------

def export_pdf(
    report_data: dict,
    fidelity_data: dict,
    investment_data: dict,
    chart_dir: str,
    out_path: str,
) -> None:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    r   = report_data
    f   = fidelity_data
    inv = investment_data or {}
    pdf = BudgetPDF()

    # ---- Cover / title ------------------------------------------------
    pdf.add_page()
    pdf.ln(10)
    pdf.set_font(FONT, "B", 26)
    pdf.set_text_color(*C_ACCENT)
    pdf.cell(0, 12, "SFBC", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font(FONT, "B", 18)
    pdf.cell(0, 10, "2025 Budget Report", align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font(FONT, "", 10)
    pdf.set_text_color(*C_RULE)
    pdf.cell(0, 7, f"San Francisco Bay Chapter  |  Generated {pdf._generated}",
             align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(6)
    pdf.set_draw_color(*C_ACCENT)
    pdf.set_line_width(0.8)
    pdf.line(MARGIN, pdf.get_y(), PAGE_W - MARGIN, pdf.get_y())
    pdf.ln(8)

    # ---- Summary --------------------------------------------------------
    pdf._h2("Summary")
    total_income = r["total_membership"] + r["total_donations"]
    total_out    = r["total_expenses"] + r["total_paypal_fees"]
    net          = r["net_income"]

    summary_rows = [
        ["Membership Income",  f"${r['total_membership']:,.2f}"],
        ["Donations",          f"${r['total_donations']:,.2f}"],
        ["Total Income",       f"${total_income:,.2f}"],
        ["Expenses",           f"${r['total_expenses']:,.2f}"],
        ["PayPal Fees",        f"${r['total_paypal_fees']:,.2f}"],
        ["Total Outflows",     f"${total_out:,.2f}"],
        ["NET INCOME",         f"${net:,.2f}"],
    ]
    pdf._table(["Metric", "Amount"], summary_rows,
               [120, CW - 120], ["L", "R"])
    pdf._embed_chart(os.path.join(chart_dir, "chart_income_vs_expenses.png"),
                     "Figure 1 - Income vs Expenses", w=CW * 0.80)

    # ---- Income breakdown -----------------------------------------------
    pdf._h2("Income Breakdown")
    pdf._h3("Monthly Income")
    im = r["income_monthly"].copy()
    im["Month"] = im["Month"].str.replace("**", "", regex=False)
    pdf._table(["Month", "Membership", "Donations", "Total"],
               im.values.tolist(),
               [50, 45, 45, CW - 140],
               ["L", "R", "R", "R"])
    pdf._embed_chart(os.path.join(chart_dir, "chart_monthly_cashflow.png"),
                     "Figure 2 - Monthly Cash Flow", w=CW)

    # ---- Expense breakdown ----------------------------------------------
    pdf._h2("Expense Breakdown")
    pdf._h3("Monthly Expenses")
    em = r["expense_monthly"].copy()
    em["Month"] = em["Month"].str.replace("**", "", regex=False)
    pdf._table(["Month", "Expenses"], em.values.tolist(),
               [120, CW - 120], ["L", "R"])
    pdf._embed_chart(os.path.join(chart_dir, "chart_expense_breakdown.png"),
                     "Figure 3 - Expense Breakdown by Category", w=CW * 0.72)

    # Major expenses with notes
    pdf._h3("Major Expenses (>$50) with Notes")
    if not r["major_expenses"].empty:
        me = r["major_expenses"]
        date_w  = 24
        amt_w   = 24
        note_w  = 56
        desc_w  = CW - date_w - amt_w - note_w
        pdf._table(
            ["Date", "Description", "Amount", "Note"],
            me.values.tolist(),
            [date_w, desc_w, amt_w, note_w],
            ["L", "L", "R", "L"],
            wrap_last=True,
        )

    # Zelle out breakdown
    pdf._h3("Zelle Payments Out")
    if not r["zelle_out"].empty:
        zo = r["zelle_out"]
        date_w  = 24
        amt_w   = 24
        note_w  = 60
        desc_w  = CW - date_w - amt_w - note_w
        pdf._table(
            ["Date", "Description", "Amount", "Note"],
            zo.values.tolist(),
            [date_w, desc_w, amt_w, note_w],
            ["L", "L", "R", "L"],
            wrap_last=True,
        )
    else:
        pdf._body("No outgoing Zelle payments in 2025.")

    # All itemized
    pdf._h3("All Itemized Expenses")
    ei = r["expense_items"]
    desc_w = CW - 26 - 32
    pdf._table(["Date", "Description", "Amount"],
               ei.values.tolist(),
               [26, desc_w, 32],
               ["L", "L", "R"])

    # ---- PayPal summary -------------------------------------------------
    pdf._h2("PayPal Summary")
    if r["paypal_has_2025_data"]:
        paypal_rows = [
            ["Gross Received", f"${r['paypal_gross']:,.2f}"],
            ["Fees",           f"${r['total_paypal_fees']:,.2f}"],
            ["Net",            f"${r['paypal_net']:,.2f}"],
        ]
        pdf._table(["Item", "Amount"], paypal_rows,
                   [120, CW - 120], ["L", "R"])
    else:
        pdf._body(
            "Note: The paypal.CSV export on file contains 2026 transactions. "
            "PayPal 2025 figures are $0.00."
        )

    # ---- Fidelity investments -------------------------------------------
    pdf._h2("Fidelity Investments")
    if f and f["total_value"] > 0:
        pdf._kv("Account:", f["account_number"])
        pdf._kv("Current Portfolio Value:", f"${f['total_value']:,.2f}", bold_value=True)
        pdf.ln(3)

        # Annual performance table
        if inv:
            pdf._h3("2025 Annual Investment Performance")
            ret    = inv["total_return"]
            ret_pct = inv["return_pct"]
            v_color = C_POS if ret >= 0 else C_NEG
            perf_rows = [
                ["Beginning Balance (Jan 1, 2025)",  f"${inv['beginning_balance']:,.2f}"],
                ["Market Change",                    f"${inv['market_change']:+,.2f}"],
                ["Dividends",                        f"${inv['dividends']:,.2f}"],
                ["Ending Balance (Dec 31, 2025)",    f"${inv['ending_balance']:,.2f}"],
                ["Total Return ($)",                 f"${ret:+,.2f}"],
                ["Total Return (%)",                 f"{ret_pct:+.2f}%"],
            ]
            pdf._table(["Metric", "Value"], perf_rows,
                       [120, CW - 120], ["L", "R"])

        # Holdings
        pdf._h3("Current Holdings")
        holdings = f["holdings"].copy()
        holdings["current_value"]          = holdings["current_value"].map(lambda x: f"${x:,.2f}")
        holdings["last_price"]             = holdings["last_price"].map(
            lambda x: f"${x:,.2f}" if x > 0 else "-")
        holdings["total_gain_loss_dollar"] = holdings["total_gain_loss_dollar"].map(
            lambda x: f"+${x:,.2f}" if x >= 0 else f"-${abs(x):,.2f}")
        holdings["total_gain_loss_pct"]    = holdings["total_gain_loss_pct"].map(
            lambda x: f"{x:+.2f}%")
        holdings["percent_of_account"]     = holdings["percent_of_account"].map(
            lambda x: f"{x:.2f}%")

        sym_w = 18; price_w = 22; val_w = 26
        gl_d_w = 24; gl_p_w = 20; alloc_w = 18
        desc_w = CW - sym_w - price_w - val_w - gl_d_w - gl_p_w - alloc_w
        fid_rows = holdings[[
            "symbol", "description", "last_price", "current_value",
            "total_gain_loss_dollar", "total_gain_loss_pct", "percent_of_account"
        ]].values.tolist()
        pdf._table(
            ["Symbol", "Description", "Price", "Value", "G/L $", "G/L %", "Alloc"],
            fid_rows,
            [sym_w, desc_w, price_w, val_w, gl_d_w, gl_p_w, alloc_w],
            ["L", "L", "R", "R", "R", "R", "R"],
        )
    else:
        pdf._body("Fidelity data not available.")

    # ---- Notes ----------------------------------------------------------
    pdf._h2("Notes")
    notes = [
        "Internal transfers excluded: PayPal <-> Chase ACH transfers are detected and "
        "excluded from all income/expense totals to avoid double-counting.",
        "2025 filter: Only transactions with a posting date in calendar year 2025 are included.",
        "PayPal fees: PayPal processing fees are tracked separately and excluded from income.",
        "Donation threshold: Credits above $100 (or matching donation keywords) are classified as donations.",
        "Major expenses: Expenses >= $50 are listed with annotated notes in the Major Expenses section.",
        "Name redaction: Personal names in transaction descriptions have been anonymized.",
        "Fidelity: Portfolio positions are as of the CSV export date and are not mixed "
        "into operating income or expense figures.",
    ]
    for note in notes:
        pdf.set_font(FONT, "", 8.5)
        pdf.set_text_color(*C_DARK)
        pdf.cell(5, 5, "-")
        pdf.multi_cell(0, 5, _safe(note))
        pdf.ln(1)

    # Internal transfers appendix
    if not r["transfers"].empty:
        pdf._h3("Internal Transfers (Excluded)")
        tf = r["transfers"]
        date_w = 24; src_w = 20; amt_w = 24
        desc_w2 = CW - date_w - src_w - amt_w
        pdf._table(
            ["Date", "Description", "Amount", "Source"],
            tf.values.tolist(),
            [date_w, desc_w2, amt_w, src_w],
            ["L", "L", "R", "L"],
        )

    pdf.output(out_path)
    print(f"  PDF written to {out_path}")
