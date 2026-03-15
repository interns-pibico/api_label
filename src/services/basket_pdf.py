"""Generate a shopping-basket budget report PDF using ReportLab."""

from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

PDF_DIR = Path("/tmp/api_label_pdfs/baskets")

STEEL_BLUE = colors.HexColor("#2D4A6B")
ACCENT_RED = colors.HexColor("#CB4154")
LIGHT_GREY = colors.HexColor("#F7F8FA")
BORDER_GREY = colors.HexColor("#E2E8F0")
WHITE = colors.white
DARK_TEXT = colors.HexColor("#1A1A2E")
MUTED_TEXT = colors.HexColor("#64748B")
GREEN = colors.HexColor("#16a34a")


def generate_basket_pdf(
    basket_id: str,
    basket_name: str,
    username: str,
    items: list[dict],
) -> str:
    """
    Generate a budget-style PDF for a shopping basket.

    Each item shows: product, supermarket, price, discount, expiry.
    A summary total is shown at the bottom.
    """
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    output_path = PDF_DIR / f"basket_{basket_id}.pdf"

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
    )

    styles = getSampleStyleSheet()
    page_width = A4[0] - 3.6 * cm  # usable width

    # ── Styles ────────────────────────────────────────────────────────────────

    s_title = ParagraphStyle(
        "s_title", parent=styles["Normal"],
        fontSize=16, textColor=WHITE, fontName="Helvetica-Bold",
    )
    s_subtitle = ParagraphStyle(
        "s_subtitle", parent=styles["Normal"],
        fontSize=9, textColor=colors.HexColor("#B0C4DE"),
    )
    s_section = ParagraphStyle(
        "s_section", parent=styles["Normal"],
        fontSize=10, textColor=STEEL_BLUE, fontName="Helvetica-Bold",
        spaceBefore=14, spaceAfter=6,
    )
    s_header = ParagraphStyle(
        "s_header", parent=styles["Normal"],
        fontSize=8, textColor=WHITE, fontName="Helvetica-Bold",
    )
    s_cell = ParagraphStyle(
        "s_cell", parent=styles["Normal"],
        fontSize=8, textColor=DARK_TEXT, leading=11,
    )
    s_cell_bold = ParagraphStyle(
        "s_cell_bold", parent=styles["Normal"],
        fontSize=8, textColor=DARK_TEXT, fontName="Helvetica-Bold", leading=11,
    )
    s_price = ParagraphStyle(
        "s_price", parent=styles["Normal"],
        fontSize=8, textColor=DARK_TEXT, fontName="Helvetica-Bold",
        alignment=TA_RIGHT, leading=11,
    )
    s_discount = ParagraphStyle(
        "s_discount", parent=styles["Normal"],
        fontSize=8, textColor=GREEN, fontName="Helvetica-Bold", leading=11,
    )
    s_no_offer = ParagraphStyle(
        "s_no_offer", parent=styles["Normal"],
        fontSize=8, textColor=MUTED_TEXT, leading=11,
    )
    s_total_label = ParagraphStyle(
        "s_total_label", parent=styles["Normal"],
        fontSize=11, textColor=WHITE, fontName="Helvetica-Bold",
    )
    s_total_value = ParagraphStyle(
        "s_total_value", parent=styles["Normal"],
        fontSize=14, textColor=WHITE, fontName="Helvetica-Bold",
        alignment=TA_RIGHT,
    )
    s_disclaimer = ParagraphStyle(
        "s_disclaimer", parent=styles["Normal"],
        fontSize=7, textColor=MUTED_TEXT, alignment=TA_CENTER, spaceBefore=10,
    )
    s_items_count = ParagraphStyle(
        "s_items_count", parent=styles["Normal"],
        fontSize=8, textColor=MUTED_TEXT, alignment=TA_RIGHT, spaceAfter=4,
    )

    story = []
    now = datetime.now()

    # ── Header banner ─────────────────────────────────────────────────────────
    header_data = [
        [Paragraph(f"Presupuesto: {basket_name}", s_title)],
        [Paragraph(
            f"Usuario: {username}  |  Fecha: {now.strftime('%d/%m/%Y %H:%M')}",
            s_subtitle,
        )],
    ]
    header_table = Table(header_data, colWidths=[page_width])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), STEEL_BLUE),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, 0), 14),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 14),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.4 * cm))

    # ── Items count ───────────────────────────────────────────────────────────
    story.append(Paragraph(
        f"{len(items)} producto{'s' if len(items) != 1 else ''} en la cesta",
        s_items_count,
    ))

    # ── Column widths ─────────────────────────────────────────────────────────
    # Producto | Supermercado | Precio | Dto. | Expira
    col_w = [
        page_width * 0.32,  # Producto
        page_width * 0.20,  # Supermercado
        page_width * 0.15,  # Precio
        page_width * 0.15,  # Descuento
        page_width * 0.18,  # Expira
    ]

    # ── Table header ──────────────────────────────────────────────────────────
    table_data = [[
        Paragraph("Producto", s_header),
        Paragraph("Supermercado", s_header),
        Paragraph("Precio", s_header),
        Paragraph("Dto.", s_header),
        Paragraph("Expira", s_header),
    ]]

    # ── Table rows ────────────────────────────────────────────────────────────
    total = 0.0
    has_prices = False

    for item in items:
        product_name = item.get("product_name", "—")
        barcode = item.get("barcode", "")
        best = item.get("best_offer")

        # Product cell: name + barcode on second line
        product_text = f"<b>{product_name}</b>"
        if barcode:
            product_text += f"<br/><font size='6' color='#64748B'>EAN: {barcode}</font>"

        if best:
            price = best.get("price", 0)
            total += price
            has_prices = True

            supermarket = best.get("supermarket", "—")
            discount = best.get("discount_percent")
            original = best.get("original_price")

            # Price cell: show original crossed out + offer price
            if original and discount:
                price_text = (
                    f"<font size='6' color='#64748B'>"
                    f"<strike>{original:.2f} \u20ac</strike></font><br/>"
                    f"<b>{price:.2f} \u20ac</b>"
                )
            else:
                price_text = f"<b>{price:.2f} \u20ac</b>"

            # Discount cell
            if discount:
                discount_text = f"-{discount:.0f}%"
                discount_style = s_discount
            else:
                discount_text = "—"
                discount_style = s_no_offer

            # Expiry: use scraped_at as reference date
            scraped_at = best.get("scraped_at", "")
            if scraped_at and hasattr(scraped_at, "strftime"):
                expiry_text = scraped_at.strftime("%d/%m/%Y")
            elif scraped_at:
                expiry_text = str(scraped_at)[:10]
            else:
                expiry_text = "—"

            table_data.append([
                Paragraph(product_text, s_cell),
                Paragraph(supermarket, s_cell),
                Paragraph(price_text, s_price),
                Paragraph(discount_text, discount_style),
                Paragraph(expiry_text, s_cell),
            ])
        else:
            # No offer found
            table_data.append([
                Paragraph(product_text, s_cell),
                Paragraph("—", s_no_offer),
                Paragraph("—", s_no_offer),
                Paragraph("—", s_no_offer),
                Paragraph("—", s_no_offer),
            ])

    # ── Build table ───────────────────────────────────────────────────────────
    main_table = Table(table_data, colWidths=col_w, repeatRows=1)

    table_styles = [
        # Header row
        ("BACKGROUND", (0, 0), (-1, 0), STEEL_BLUE),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        # All cells
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        # Borders
        ("LINEBELOW", (0, 0), (-1, 0), 1, STEEL_BLUE),
        ("LINEBELOW", (0, 1), (-1, -1), 0.5, BORDER_GREY),
    ]

    # Zebra striping
    for i in range(1, len(table_data)):
        if i % 2 == 0:
            table_styles.append(("BACKGROUND", (0, i), (-1, i), LIGHT_GREY))

    main_table.setStyle(TableStyle(table_styles))
    story.append(main_table)

    # ── Total ─────────────────────────────────────────────────────────────────
    if has_prices:
        story.append(Spacer(1, 0.3 * cm))
        items_with_price = sum(
            1 for it in items if it.get("best_offer")
        )
        total_data = [[
            Paragraph(
                f"TOTAL ESTIMADO ({items_with_price} producto"
                f"{'s' if items_with_price != 1 else ''})",
                s_total_label,
            ),
            Paragraph(f"{total:.2f} \u20ac", s_total_value),
        ]]
        total_table = Table(total_data, colWidths=[page_width * 0.65, page_width * 0.35])
        total_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), STEEL_BLUE),
            ("LEFTPADDING", (0, 0), (-1, -1), 14),
            ("RIGHTPADDING", (0, 0), (-1, -1), 14),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(total_table)

    # ── Disclaimer ────────────────────────────────────────────────────────────
    story.append(Paragraph(
        "Precios capturados en las fechas indicadas. "
        "Verifica antes de comprar. Los precios pueden variar en tienda.",
        s_disclaimer,
    ))

    doc.build(story)
    return str(output_path)
