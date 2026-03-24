"""Celery tasks for label PDF generation."""

import asyncio
import os
import uuid

from src.workers.celery_app import celery_app


@celery_app.task(name="generate_label_pdf", bind=True, max_retries=3, default_retry_delay=10)
def generate_label_pdf(self, label_id: str) -> dict:
    """
    Generate a PDF for the given label_id using ReportLab.
    Updates the label's label_data with the pdf_path on completion.
    """
    return asyncio.run(_generate_label_pdf_async(label_id))


async def _generate_label_pdf_async(label_id_str: str) -> dict:
    from src.core.config import settings
    from src.db.session import create_standalone_session

    label_id = uuid.UUID(label_id_str)

    engine, session_factory = create_standalone_session()
    try:
        async with session_factory() as db:
            from src.db.repositories.label_repository import LabelRepository
            repo = LabelRepository(db)
            label = await repo.get(label_id)

            if label is None:
                return {"status": "error", "detail": "Label not found"}

            html_content = label.rendered_html or ""
            label_data = label.label_data or {}

            # Build PDF output path
            output_dir = settings.PDF_OUTPUT_DIR
            os.makedirs(output_dir, exist_ok=True)
            pdf_path = os.path.join(output_dir, f"label_{label_id}.pdf")

            _render_pdf(html_content, label_data, pdf_path)

            # Update label_data with pdf_path
            updated_data = dict(label_data)
            updated_data["pdf_path"] = pdf_path
            await repo.update(label, {"label_data": updated_data})
            await db.commit()

            return {"status": "success", "pdf_path": pdf_path}
    finally:
        await engine.dispose()


def _render_pdf(html_content: str, label_data: dict, output_path: str) -> None:
    """Render a complete nutritional label PDF using ReportLab.

    Supports:
    - Mandatory nutritional table (EU 1169/2011 order)
    - Optional per-serving column when nutrition_per_serving is present
    - Ingredients section with allergens in bold
    - Separate allergens block
    - Product footer: manufacturer, net weight, best before, storage, regulation
    """
    from io import BytesIO

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        HRFlowable,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    STEEL_BLUE = colors.HexColor("#2D4A6B")
    LIGHT_GREY = colors.HexColor("#F5F5F5")
    MID_GREY = colors.HexColor("#CCCCCC")
    ALLERGEN_BG = colors.HexColor("#FFFBE6")
    ALLERGEN_BORDER = colors.HexColor("#D4AC0D")

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "LabelTitle",
        parent=styles["Heading1"],
        textColor=STEEL_BLUE,
        fontSize=16,
        spaceAfter=2,
    )
    brand_style = ParagraphStyle(
        "LabelBrand",
        parent=styles["Normal"],
        textColor=colors.HexColor("#555555"),
        fontSize=10,
        spaceAfter=6,
    )
    section_heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        textColor=STEEL_BLUE,
        fontSize=12,
        spaceBefore=6,
        spaceAfter=2,
    )
    styles["Normal"]
    small_style = ParagraphStyle(
        "Small",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.grey,
    )
    info_style = ParagraphStyle(
        "Info",
        parent=styles["Normal"],
        fontSize=9,
        spaceAfter=3,
    )
    allergen_style = ParagraphStyle(
        "Allergen",
        parent=styles["Normal"],
        fontSize=9,
        spaceAfter=3,
        backColor=ALLERGEN_BG,
        borderColor=ALLERGEN_BORDER,
        borderWidth=1,
        borderPadding=4,
        leading=13,
    )

    story = []

    product = label_data.get("product") or {}
    nutrition_100g = label_data.get("nutrition_per_100g") or {}
    nutrition_srv = label_data.get("nutrition_per_serving")  # May be None
    serving_size_g = label_data.get("serving_size_g")
    regulation = label_data.get("regulation") or "Reglamento (UE) nº 1169/2011"

    # ---- Product title ----
    product_name = product.get("name") or ""
    brand = product.get("brand") or ""
    story.append(Paragraph(product_name, title_style))
    if brand:
        story.append(Paragraph(brand, brand_style))
    story.append(HRFlowable(width="100%", thickness=1, color=STEEL_BLUE, spaceAfter=6))

    # ---- Nutritional table ----
    if nutrition_100g:
        story.append(Paragraph("Información Nutricional", section_heading_style))

        has_serving = nutrition_srv is not None and serving_size_g is not None

        # Column subtitle row
        if has_serving:
            subtitle_text = f"Por 100 g / Por porción ({int(float(serving_size_g))} g)"
        else:
            subtitle_text = "Por 100 g"
        story.append(Paragraph(subtitle_text, small_style))
        story.append(Spacer(1, 0.2 * cm))

        def fmt(val, suffix: str = "") -> str:
            if val is None:
                return "—"
            if isinstance(val, float) and val == int(val):
                return f"{int(val)}{suffix}"
            return f"{val}{suffix}"

        def energy_str(kj, kcal) -> str:
            return f"{fmt(kj)} kJ / {fmt(kcal)} kcal"

        # Header row
        if has_serving:
            header = ["Nutriente", "Por 100 g", f"Por porción\n({int(float(serving_size_g))} g)"]
            col_widths = [8.5 * cm, 3.5 * cm, 3.5 * cm]
        else:
            header = ["Nutriente", "Por 100 g"]
            col_widths = [11.5 * cm, 4 * cm]

        table_data = [header]

        # Field definitions in EU mandatory order
        # Each tuple: (label, field_key_100g, is_sub_row, is_energy_combined)
        field_rows = [
            ("Energía", "energy", False, True),
            ("Grasas", "fat_g", False, False),
            ("  de las cuales ácidos grasos saturados", "saturated_fat_g", True, False),
            ("Hidratos de carbono", "carbohydrates_g", False, False),
            ("  de los cuales azúcares", "sugars_g", True, False),
            ("Fibra alimentaria", "fiber_g", True, False),  # only if present
            ("Proteínas", "protein_g", False, False),
            ("Sal", "salt_g", False, False),
        ]

        # Track which rows are sub-rows for styling
        sub_row_indices = []  # 1-based relative to table_data
        energy_row_index = 1  # header is 0, energy is 1

        for label_text, field_key, is_sub, is_energy in field_rows:
            if field_key == "fiber_g" and nutrition_100g.get("fiber_g") is None:
                continue  # Skip fiber if not declared

            row_index = len(table_data)

            if is_energy:
                val_100g = energy_str(
                    nutrition_100g.get("energy_kj"),
                    nutrition_100g.get("energy_kcal"),
                )
                if has_serving:
                    val_srv = energy_str(
                        nutrition_srv.get("energy_kj"),
                        nutrition_srv.get("energy_kcal"),
                    )
                    table_data.append([label_text, val_100g, val_srv])
                else:
                    table_data.append([label_text, val_100g])
            else:
                val_100g_raw = nutrition_100g.get(field_key)
                if field_key == "salt_g" and val_100g_raw is None:
                    # Fallback: try to compute salt from sodium if not in nutrition_100g
                    sodium = (product.get("sodium_mg") or
                              label_data.get("regulatory_data", {}).get("sodium_mg"))
                    if sodium is not None:
                        val_100g_raw = round(float(sodium) * 2.5 / 1000, 3)

                val_str = fmt(val_100g_raw, " g")
                if has_serving:
                    val_srv_raw = nutrition_srv.get(field_key)
                    srv_str = fmt(val_srv_raw, " g")
                    table_data.append([label_text, val_str, srv_str])
                else:
                    table_data.append([label_text, val_str])

            if is_sub:
                sub_row_indices.append(row_index)

        table = Table(table_data, colWidths=col_widths)

        # Build table style commands
        ts_cmds = [
            # Header row style
            ("BACKGROUND", (0, 0), (-1, 0), STEEL_BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ("TOPPADDING", (0, 0), (-1, 0), 6),
            # Data rows
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
            ("GRID", (0, 0), (-1, -1), 0.4, MID_GREY),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("TOPPADDING", (0, 1), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
            # Right-align value columns
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
            # Energy row: thick bottom border
            ("LINEBELOW", (0, energy_row_index), (-1, energy_row_index), 2, colors.black),
            ("FONTNAME", (0, energy_row_index), (-1, energy_row_index), "Helvetica-Bold"),
        ]

        # Sub-row indentation style
        for idx in sub_row_indices:
            ts_cmds.append(("FONTNAME", (0, idx), (0, idx), "Helvetica-Oblique"))
            ts_cmds.append(("TEXTCOLOR", (0, idx), (0, idx), colors.HexColor("#333333")))

        table.setStyle(TableStyle(ts_cmds))
        story.append(table)
        story.append(Spacer(1, 0.4 * cm))

    # ---- Allergens block ----
    allergens = product.get("allergens")
    if allergens:
        story.append(Paragraph(
            f"<b>Contiene:</b> <b>{allergens}</b>",
            allergen_style,
        ))
        story.append(Spacer(1, 0.3 * cm))

    # ---- Ingredients ----
    ingredients = product.get("ingredients")
    if ingredients:
        story.append(Paragraph("Ingredientes", section_heading_style))
        # Bold allergen terms within ingredients text
        ingredients_display = ingredients
        if allergens:
            for term in [a.strip() for a in allergens.split(",")]:
                if term and term.lower() in ingredients_display.lower():
                    idx_pos = ingredients_display.lower().find(term.lower())
                    original = ingredients_display[idx_pos: idx_pos + len(term)]
                    ingredients_display = ingredients_display.replace(
                        original, f"<b>{original}</b>", 1
                    )
        story.append(Paragraph(ingredients_display, info_style))
        story.append(Spacer(1, 0.3 * cm))

    # ---- Product footer information ----
    footer_items = []
    if product.get("net_weight"):
        footer_items.append(f"<b>Peso neto:</b> {product['net_weight']}")
    if product.get("manufacturer"):
        footer_items.append(f"<b>Fabricante:</b> {product['manufacturer']}")
    if product.get("best_before"):
        footer_items.append(f"<b>Consumir preferentemente antes de:</b> {product['best_before']}")
    if product.get("storage_conditions"):
        footer_items.append(f"<b>Condiciones de conservación:</b> {product['storage_conditions']}")
    if product.get("country_of_origin"):
        footer_items.append(f"<b>País de origen:</b> {product['country_of_origin']}")

    if footer_items:
        story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GREY, spaceBefore=4, spaceAfter=4))
        for item_text in footer_items:
            story.append(Paragraph(item_text, info_style))

    # ---- Regulation reference ----
    story.append(Spacer(1, 0.4 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GREY, spaceAfter=4))
    story.append(Paragraph(regulation, small_style))

    doc.build(story)
    with open(output_path, "wb") as f:
        f.write(buffer.getvalue())
