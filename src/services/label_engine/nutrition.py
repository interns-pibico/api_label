"""NutritionLabelGenerator — Conforme al Reglamento (UE) nº 1169/2011."""

from src.services.label_engine.base import BaseLabelGenerator

TRANSLATIONS = {
    "es": {
        "nutrition_facts": "Información Nutricional",
        "per_100g": "Por 100 g",
        "per_serving": "Por porción",
        "serving_label": "Por porción ({size} g)",
        "energy": "Energía",
        "fat": "Grasas",
        "saturated_fat": "de las cuales ácidos grasos saturados",
        "carbohydrates": "Hidratos de carbono",
        "sugars": "de los cuales azúcares",
        "fiber": "Fibra alimentaria",
        "protein": "Proteínas",
        "salt": "Sal",
        "regulation": "Reglamento (UE) nº 1169/2011",
        "ingredients": "Ingredientes",
        "allergens": "Contiene",
        "net_weight": "Peso neto",
        "manufacturer": "Fabricante",
        "best_before": "Consumir preferentemente antes de",
        "storage": "Condiciones de conservación",
        "country_of_origin": "País de origen",
        "error_missing": "Campo obligatorio ausente o nulo",
        "error_salt_or_sodium": (
            "Se requiere 'salt_g' o 'sodium_mg' (se calcula automáticamente)"
        ),
    },
    "en": {
        "nutrition_facts": "Nutrition Facts",
        "per_100g": "Per 100 g",
        "per_serving": "Per serving",
        "serving_label": "Per serving ({size} g)",
        "energy": "Energy",
        "fat": "Fat",
        "saturated_fat": "of which saturates",
        "carbohydrates": "Carbohydrate",
        "sugars": "of which sugars",
        "fiber": "Fibre",
        "protein": "Protein",
        "salt": "Salt",
        "regulation": "Regulation (EU) No 1169/2011",
        "ingredients": "Ingredients",
        "allergens": "Contains",
        "net_weight": "Net weight",
        "manufacturer": "Manufacturer",
        "best_before": "Best before",
        "storage": "Storage conditions",
        "country_of_origin": "Country of origin",
        "error_missing": "Required field missing or null",
        "error_salt_or_sodium": (
            "Either 'salt_g' or 'sodium_mg' is required (salt_g is auto-calculated)"
        ),
    },
}

# Mandatory nutritional fields per EU 1169/2011 (excluding salt — handled separately)
REQUIRED_FIELDS_NO_SALT = [
    "energy_kj",
    "energy_kcal",
    "fat_g",
    "saturated_fat_g",
    "carbohydrates_g",
    "sugars_g",
    "protein_g",
]

OPTIONAL_FIELDS = [
    "fiber_g",
    "sodium_mg",
    "serving_size_g",
    "ingredients",
    "allergens",
    "net_weight",
    "manufacturer",
    "best_before",
    "storage_conditions",
    "country_of_origin",
]

# CSS embedded in the label HTML
_LABEL_CSS = """
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
        font-family: Arial, Helvetica, sans-serif;
        max-width: 860px;
        margin: 0 auto;
        padding: 16px;
        color: #1a1a1a;
        font-size: 14px;
        line-height: 1.4;
    }
    .product-header { margin-bottom: 12px; }
    .product-name { font-size: 1.25em; font-weight: bold; color: #2D4A6B; }
    .product-brand { color: #555; font-size: 0.9em; margin-top: 2px; }

    /* Two-column layout: table left, info right */
    .label-body {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 16px;
        align-items: start;
    }
    @media (max-width: 520px) {
        .label-body { grid-template-columns: 1fr; }
    }

    .nutrition-block { border: 2px solid #1a1a1a; padding: 8px 10px; }
    .nutrition-title {
        font-size: 1.3em;
        font-weight: bold;
        border-bottom: 8px solid #1a1a1a;
        padding-bottom: 4px;
        margin-bottom: 4px;
    }
    .nutrition-subtitle {
        font-size: 0.78em;
        color: #333;
        margin-bottom: 6px;
        border-bottom: 1px solid #aaa;
        padding-bottom: 3px;
    }
    table.nutrition-table {
        width: 100%;
        border-collapse: collapse;
    }
    table.nutrition-table thead tr {
        border-bottom: 4px solid #1a1a1a;
    }
    table.nutrition-table th {
        font-size: 0.78em;
        font-weight: bold;
        text-align: right;
        padding: 3px 2px;
        white-space: nowrap;
    }
    table.nutrition-table th:first-child { text-align: left; }
    table.nutrition-table td {
        padding: 3px 2px;
        font-size: 0.85em;
        border-bottom: 1px solid #ddd;
        vertical-align: middle;
    }
    table.nutrition-table td:not(:first-child) {
        text-align: right;
        font-weight: bold;
        white-space: nowrap;
    }
    tr.energy-row td { border-bottom: 4px solid #1a1a1a; font-weight: bold; }
    tr.sub-row td:first-child { padding-left: 16px; }
    tr.fiber-row td { border-bottom: 1px solid #ccc; }
    tr.last-row td { border-bottom: none; }

    .label-info { display: flex; flex-direction: column; gap: 10px; }
    .info-block p { margin-bottom: 5px; font-size: 0.85em; }
    .info-block strong { font-weight: bold; }
    .allergens-block {
        border: 1px solid #aaa;
        padding: 6px 8px;
        background: #fffbe6;
        border-radius: 3px;
        font-size: 0.85em;
    }
    .allergens-block .allergen-label { font-weight: bold; }
    .regulation-note {
        color: #777;
        font-size: 0.72em;
        margin-top: 12px;
        border-top: 1px solid #ddd;
        padding-top: 6px;
    }
"""


def _compute_salt(rd: dict) -> float | None:
    """Return salt_g from rd, computing from sodium_mg if needed."""
    if rd.get("salt_g") is not None:
        return float(rd["salt_g"])
    if rd.get("sodium_mg") is not None:
        return round(float(rd["sodium_mg"]) * 2.5 / 1000, 3)
    return None


def _serving_value(value_per_100g, serving_size_g: float) -> float:
    """Scale a per-100g nutritional value to the given serving size."""
    return round(float(value_per_100g) * serving_size_g / 100, 2)


class NutritionLabelGenerator(BaseLabelGenerator):
    """Generador de etiquetas nutricionales conforme al Reglamento (UE) nº 1169/2011."""

    REGULATION_VERSION = "EU_1169_2011_v1"

    # ------------------------------------------------------------------
    # validate_data
    # ------------------------------------------------------------------
    def validate_data(self, regulatory_data: dict) -> list[str]:
        """Validate regulatory_data against EU 1169/2011 requirements.

        Returns a list of error messages in Spanish. Empty list = valid.
        Special rule: salt_g OR sodium_mg must be present (not both required).
        """
        errors: list[str] = []

        for field in REQUIRED_FIELDS_NO_SALT:
            if regulatory_data.get(field) is None:
                errors.append(
                    f"Campo obligatorio ausente o nulo: '{field}'"
                )

        # Salt rule: accept salt_g OR sodium_mg
        has_salt = regulatory_data.get("salt_g") is not None
        has_sodium = regulatory_data.get("sodium_mg") is not None
        if not has_salt and not has_sodium:
            errors.append(
                "Se requiere 'salt_g' o 'sodium_mg'. "
                "Si sólo se proporciona 'sodium_mg', el valor de sal se calcula "
                "automáticamente como sodium_mg × 2,5 / 1000."
            )

        return errors

    # ------------------------------------------------------------------
    # generate_json
    # ------------------------------------------------------------------
    def generate_json(self, product_data: dict, lang: str = "es") -> dict:
        """Return a structured JSON representation of the label.

        Automatically computes salt_g from sodium_mg when needed.
        Adds nutrition_per_serving dict when serving_size_g is present.
        """
        rd = product_data.get("regulatory_data") or {}
        t = TRANSLATIONS.get(lang, TRANSLATIONS["es"])

        salt_g = _compute_salt(rd)
        serving_size_g = rd.get("serving_size_g")

        nutrition_per_100g: dict = {
            "energy_kj": rd.get("energy_kj"),
            "energy_kcal": rd.get("energy_kcal"),
            "fat_g": rd.get("fat_g"),
            "saturated_fat_g": rd.get("saturated_fat_g"),
            "carbohydrates_g": rd.get("carbohydrates_g"),
            "sugars_g": rd.get("sugars_g"),
            "fiber_g": rd.get("fiber_g"),  # None if not declared
            "protein_g": rd.get("protein_g"),
            "salt_g": salt_g,
        }

        result: dict = {
            "label_type": "nutrition_eu",
            "regulation": t["regulation"],
            "regulation_version": self.REGULATION_VERSION,
            "language": lang,
            "product": {
                "name": product_data.get("name"),
                "brand": product_data.get("brand"),
                "barcode": product_data.get("barcode"),
                "net_weight": rd.get("net_weight"),
                "manufacturer": rd.get("manufacturer"),
                "best_before": rd.get("best_before"),
                "storage_conditions": rd.get("storage_conditions"),
                "country_of_origin": rd.get("country_of_origin"),
                "ingredients": rd.get("ingredients"),
                "allergens": rd.get("allergens"),
            },
            "nutrition_per_100g": nutrition_per_100g,
        }

        # Add per-serving block only when serving_size_g is declared
        if serving_size_g is not None:
            result["serving_size_g"] = float(serving_size_g)
            per_serving: dict = {}
            for key, val in nutrition_per_100g.items():
                if val is not None:
                    per_serving[key] = _serving_value(val, float(serving_size_g))
                else:
                    per_serving[key] = None
            result["nutrition_per_serving"] = per_serving

        return result

    # ------------------------------------------------------------------
    # generate_html
    # ------------------------------------------------------------------
    def generate_html(self, product_data: dict, lang: str = "es") -> str:
        """Generate a complete HTML label conforming to EU 1169/2011.

        - 2 columns by default (Nutriente | Por 100 g)
        - 3 columns when serving_size_g is present
        - Fiber row shown only if fiber_g is declared
        - Allergens highlighted in bold within ingredients and separate block
        - Product information block at bottom
        """
        rd = product_data.get("regulatory_data") or {}
        t = TRANSLATIONS.get(lang, TRANSLATIONS["es"])

        name = product_data.get("name", "")
        brand = product_data.get("brand", "")

        salt_g = _compute_salt(rd)
        fiber_g = rd.get("fiber_g")
        serving_size_g = rd.get("serving_size_g")
        has_serving = serving_size_g is not None

        def fmt(val, suffix: str = "") -> str:
            if val is None:
                return "—"
            v = round(float(val), 1)
            if v == int(v):
                return f"{int(v)}{suffix}"
            return f"{v}{suffix}"

        def per_100(field: str) -> str:
            return fmt(rd.get(field), " g") if field != "energy" else ""

        def per_srv(val_100g) -> str:
            if val_100g is None:
                return "—"
            sv = round(_serving_value(val_100g, float(serving_size_g)), 1)
            if sv == int(sv):
                return f"{int(sv)} g"
            return f"{sv} g"

        # Energy values
        energy_kj = rd.get("energy_kj")
        energy_kcal = rd.get("energy_kcal")
        energy_100g = f"{fmt(energy_kj)} kJ / {fmt(energy_kcal)} kcal"
        if has_serving:
            energy_srv_kj = _serving_value(energy_kj, float(serving_size_g)) if energy_kj is not None else None
            energy_srv_kcal = _serving_value(energy_kcal, float(serving_size_g)) if energy_kcal is not None else None
            energy_srv = f"{fmt(energy_srv_kj)} kJ / {fmt(energy_srv_kcal)} kcal"

        fat_g = rd.get("fat_g")
        sat_fat_g = rd.get("saturated_fat_g")
        carbs_g = rd.get("carbohydrates_g")
        sugars_g = rd.get("sugars_g")
        protein_g = rd.get("protein_g")

        # Build table header
        if has_serving:
            serving_col_label = t["serving_label"].format(size=int(float(serving_size_g)))
            header_html = (
                f"<thead><tr>"
                f"<th></th>"
                f"<th>{t['per_100g']}</th>"
                f"<th>{serving_col_label}</th>"
                f"</tr></thead>"
            )
        else:
            header_html = (
                f"<thead><tr>"
                f"<th></th>"
                f"<th>{t['per_100g']}</th>"
                f"</tr></thead>"
            )

        def row(label: str, val_100g_str: str, val_srv_str: str = "", css_class: str = "") -> str:
            cls = f' class="{css_class}"' if css_class else ""
            if has_serving:
                return f"<tr{cls}><td>{label}</td><td>{val_100g_str}</td><td>{val_srv_str}</td></tr>"
            return f"<tr{cls}><td>{label}</td><td>{val_100g_str}</td></tr>"

        # Build rows in mandatory EU order
        rows: list[str] = []

        # 1. Energy (thick bottom border — EU requirement)
        rows.append(row(
            t["energy"],
            energy_100g,
            energy_srv if has_serving else "",
            css_class="energy-row",
        ))

        # 2. Fat
        rows.append(row(
            t["fat"],
            fmt(fat_g, " g"),
            per_srv(fat_g) if has_serving else "",
        ))

        # 3. Saturated fat (sub-row)
        rows.append(row(
            f"&nbsp;&nbsp;{t['saturated_fat']}",
            fmt(sat_fat_g, " g"),
            per_srv(sat_fat_g) if has_serving else "",
            css_class="sub-row",
        ))

        # 4. Carbohydrates
        rows.append(row(
            t["carbohydrates"],
            fmt(carbs_g, " g"),
            per_srv(carbs_g) if has_serving else "",
        ))

        # 5. Sugars (sub-row)
        rows.append(row(
            f"&nbsp;&nbsp;{t['sugars']}",
            fmt(sugars_g, " g"),
            per_srv(sugars_g) if has_serving else "",
            css_class="sub-row",
        ))

        # 6. Fiber — ONLY if declared (optional field)
        if fiber_g is not None:
            rows.append(row(
                t["fiber"],
                fmt(fiber_g, " g"),
                per_srv(fiber_g) if has_serving else "",
                css_class="fiber-row",
            ))

        # 7. Protein
        rows.append(row(
            t["protein"],
            fmt(protein_g, " g"),
            per_srv(protein_g) if has_serving else "",
        ))

        # 8. Salt (last mandatory row — no bottom border)
        rows.append(row(
            t["salt"],
            fmt(salt_g, " g"),
            per_srv(salt_g) if has_serving else "",
            css_class="last-row",
        ))

        rows_html = "\n    ".join(rows)

        # Build product information block
        info_parts: list[str] = []

        # Ingredients with allergens highlighted in bold
        ingredients_raw = rd.get("ingredients")
        allergens_raw = rd.get("allergens")

        if ingredients_raw:
            ingredients_display = ingredients_raw
            if allergens_raw:
                # Highlight each individual allergen term in bold within ingredients text
                for allergen_term in [a.strip() for a in allergens_raw.split(",")]:
                    if allergen_term and allergen_term.lower() in ingredients_display.lower():
                        # Case-insensitive replacement with bold
                        idx = ingredients_display.lower().find(allergen_term.lower())
                        original = ingredients_display[idx: idx + len(allergen_term)]
                        ingredients_display = ingredients_display.replace(
                            original, f"<strong>{original}</strong>", 1
                        )
            info_parts.append(
                f"<p><strong>{t['ingredients']}:</strong> {ingredients_display}</p>"
            )

        # Separate allergens block
        allergens_block = ""
        if allergens_raw:
            allergens_block = (
                f'<div class="allergens-block">'
                f'<span class="allergen-label">{t["allergens"]}: </span>'
                f"<strong>{allergens_raw}</strong>"
                f"</div>"
            )

        if rd.get("net_weight"):
            info_parts.append(
                f"<p><strong>{t['net_weight']}:</strong> {rd['net_weight']}</p>"
            )
        if rd.get("manufacturer"):
            info_parts.append(
                f"<p><strong>{t['manufacturer']}:</strong> {rd['manufacturer']}</p>"
            )
        if rd.get("best_before"):
            info_parts.append(
                f"<p><strong>{t['best_before']}:</strong> {rd['best_before']}</p>"
            )
        if rd.get("storage_conditions"):
            info_parts.append(
                f"<p><strong>{t['storage']}:</strong> {rd['storage_conditions']}</p>"
            )
        if rd.get("country_of_origin"):
            info_parts.append(
                f"<p><strong>{t['country_of_origin']}:</strong> {rd['country_of_origin']}</p>"
            )

        info_block = ""
        if info_parts:
            info_block = (
                '<div class="info-block">\n'
                + "\n".join(info_parts)
                + "\n</div>"
            )

        html = f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{name} — {t["nutrition_facts"]}</title>
  <style>{_LABEL_CSS}</style>
</head>
<body>

  <div class="product-header">
    <div class="product-name">{name}</div>
    {"" if not brand else f'<div class="product-brand">{brand}</div>'}
  </div>

  <div class="label-body">
    <div class="nutrition-block">
      <div class="nutrition-title">{t["nutrition_facts"]}</div>
      <div class="nutrition-subtitle">
        {t["per_100g"]}{"" if not has_serving else f" / {t['serving_label'].format(size=int(float(serving_size_g)))}"}
      </div>
      <table class="nutrition-table">
        {header_html}
        <tbody>
      {rows_html}
        </tbody>
      </table>
    </div>

    <div class="label-info">
      {allergens_block}
      {info_block}
    </div>
  </div>

  <p class="regulation-note">{t["regulation"]}</p>

</body>
</html>"""

        return html
