"""PDF report with repeatable headers, wrapped text and automatic page breaks."""
from datetime import datetime, timezone
import io
from pathlib import Path
from xml.sax.saxutils import escape
from .calculations import calculate
from .project import boq_rows


def make_pdf(name, records, rates, currency, review=None):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
    fonts = Path(__file__).resolve().parents[1] / "assets" / "fonts"
    if "CQSans" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("CQSans", str(fonts / "DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont("CQSansBold", str(fonts / "DejaVuSans-Bold.ttf")))
    styles = getSampleStyleSheet()
    for key in ["Normal", "BodyText", "Title", "Heading1", "Heading2"]:
        styles[key].fontName = "CQSansBold" if key in ("Title", "Heading1", "Heading2") else "CQSans"
    styles.add(ParagraphStyle(name="SmallCQ", fontName="CQSans", fontSize=8, leading=11, spaceAfter=4))
    styles["BodyText"].fontSize = 9
    styles["BodyText"].leading = 13
    styles["Heading1"].textColor = colors.HexColor("#0c6148")
    styles["Heading2"].textColor = colors.HexColor("#0c6148")
    def p(text, style="BodyText"):
        # Core PDF fonts cover English and Latin text. Keep all XML escaped.
        text = str(text).replace("×", " x ").replace("π", "pi").replace("−", "-").replace("³", "3").replace("²", "2")
        return Paragraph(escape(text), styles[style])

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=42, rightMargin=42,
                            topMargin=48, bottomMargin=44, title=f"{name} | Civil QuantEstimate")
    story = [p("CIVIL QUANTESTIMATE", "Heading1"), p(name, "Title"),
             p("Quantity takeoff and material schedule", "Heading2"),
             p(datetime.now(timezone.utc).strftime("Generated %d %b %Y, %H:%M UTC"), "SmallCQ"),
             p("Preliminary estimate. Check dimensions, material assumptions and specifications before procurement. Prices are user-entered; labour, taxes and overheads are excluded."), Spacer(1, 14)]
    rows = boq_rows(records, rates)
    if rows:
        table_data = [[p(t, "SmallCQ") for t in ["Material / unit", "Order qty", f"Rate ({currency})", f"Amount ({currency})"]]]
        for row in rows:
            table_data.append([p(row["Material / unit"], "SmallCQ"), p(f"{row['Order quantity']:,.4f}", "SmallCQ"),
                               p(f"{row['Your unit rate']:,.2f}" if row["Your unit rate"] else "Unpriced", "SmallCQ"),
                               p(f"{row['Material amount']:,.2f}" if row["Material amount"] is not None else "-", "SmallCQ")])
        table = Table(table_data, colWidths=[205, 83, 90, 133], repeatRows=1, hAlign="LEFT")
        table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e0f4ea")),
                                   ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f8f7")]),
                                   ("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                                   ("TOPPADDING", (0, 0), (-1, -1), 7)]))
        story.extend([table, Spacer(1, 9), p(f"Priced-material subtotal: {currency} {sum(r['Material amount'] or 0 for r in rows):,.2f}")])
        if any(r["Your unit rate"] is None for r in rows):
            story.append(p("Incomplete cost estimate: one or more materials are unpriced."))
        story.append(p("Whole cement bags are rounded up after aggregation by bag size; bricks are rounded per takeoff.", "SmallCQ"))
    for index, record in enumerate(records, 1):
        result = calculate(record["module"], record["inputs"])
        story.append(KeepTogether([Spacer(1, 14), p(f"{index:02}. {record['label']} - {record['module']}", "Heading2")]))
        story.append(p("INPUTS", "SmallCQ"))
        for key, value in record["inputs"].items():
            story.append(p(f"{key}: {value}", "SmallCQ"))
        story.append(p("CALCULATED RESULTS", "SmallCQ"))
        for key, value in {**result["metrics"], **result["materials"]}.items():
            story.append(p(f"{key}: {value:,.4f}", "SmallCQ"))
        for line in result["formulas"] + result["notes"]:
            story.append(p(line, "SmallCQ"))
    if review:
        story.extend([Spacer(1, 18), p("AI review - advisory", "Heading2")])
        story.append(p(f"Reviewed takeoff ID: {review['record_id']}. The review applies to that submitted snapshot only.", "SmallCQ"))
        for line in review["answer"].splitlines():
            if line.strip():
                story.append(p(line.lstrip("# "), "BodyText"))
        for source in review.get("sources", []):
            story.append(p(f"[{source['id']}] {source['filename']}, page {source['page']}: {source['text']}", "SmallCQ"))
    def footer(canvas, doc):
        canvas.setStrokeColor(colors.HexColor("#36d99b"))
        canvas.line(42, 34, A4[0] - 42, 34)
        canvas.setFont("CQSans", 8)
        canvas.setFillColor(colors.HexColor("#456158"))
        canvas.drawString(42, 22, "Civil QuantEstimate | Preliminary quantity estimate")
        canvas.drawRightString(A4[0] - 42, 22, f"Page {doc.page}")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
