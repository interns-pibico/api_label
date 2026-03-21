"""CosmeticLabelGenerator — Conforme al Reglamento (CE) nº 1223/2009."""

from src.services.label_engine.base import BaseLabelGenerator

TRANSLATIONS = {
    "es": {
        "title": "Etiqueta de Producto Cosmético",
        "responsible": "Responsable UE",
        "net_content": "Contenido neto",
        "batch": "Nº de lote",
        "function": "Función",
        "pao": "PAO",
        "pao_months": "{months}M",
        "ingredients_inci": "Ingredientes (INCI)",
        "warnings": "Advertencias",
        "usage": "Modo de empleo",
        "storage": "Condiciones de conservación",
        "origin": "País de fabricación",
        "regulation": "Reglamento (CE) nº 1223/2009",
        "error_missing": "Campo obligatorio ausente: {field}",
    },
    "en": {
        "title": "Cosmetic Product Label",
        "responsible": "EU Responsible Person",
        "net_content": "Net content",
        "batch": "Batch No.",
        "function": "Function",
        "pao": "PAO",
        "pao_months": "{months}M",
        "ingredients_inci": "Ingredients (INCI)",
        "warnings": "Warnings",
        "usage": "Directions for use",
        "storage": "Storage conditions",
        "origin": "Country of manufacture",
        "regulation": "Regulation (EC) No 1223/2009",
        "error_missing": "Required field missing: {field}",
    },
}

REQUIRED_FIELDS = [
    "nombre",
    "responsable_ue",
    "contenido_neto",
    "ingredientes_inci",
    "numero_lote",
    "funcion_producto",
    "pao_meses",
]


class CosmeticLabelGenerator(BaseLabelGenerator):
    """Generate cosmetic product labels per EC Regulation 1223/2009 (Art. 19)."""

    REGULATION_VERSION = "CE_1223_2009_v1"

    def validate_data(self, regulatory_data: dict) -> list[str]:
        t = TRANSLATIONS.get("es", TRANSLATIONS["es"])
        errors = []
        for field in REQUIRED_FIELDS:
            val = regulatory_data.get(field)
            if val is None or (isinstance(val, str) and not val.strip()):
                errors.append(t["error_missing"].format(field=field))
        return errors

    def generate_json(self, product_data: dict, lang: str = "es") -> dict:
        rd = product_data.get("regulatory_data", {})
        return {
            "regulation_version": self.REGULATION_VERSION,
            "product_name": product_data.get("name", ""),
            "brand": product_data.get("brand", ""),
            "responsible_eu": rd.get("responsable_ue", ""),
            "net_content": rd.get("contenido_neto", ""),
            "batch_number": rd.get("numero_lote", ""),
            "function": rd.get("funcion_producto", ""),
            "pao_months": rd.get("pao_meses"),
            "ingredients_inci": rd.get("ingredientes_inci", ""),
            "warnings": rd.get("advertencias", ""),
            "usage_instructions": rd.get("modo_empleo", ""),
            "storage_conditions": rd.get("condiciones_conservacion", ""),
            "country_of_manufacture": rd.get("pais_fabricacion", ""),
        }

    def generate_html(self, product_data: dict, lang: str = "es") -> str:
        t = TRANSLATIONS.get(lang, TRANSLATIONS["es"])
        rd = product_data.get("regulatory_data", {})

        name = product_data.get("name", "")
        brand = product_data.get("brand", "")
        barcode = product_data.get("barcode", "")

        responsable = rd.get("responsable_ue", "")
        contenido = rd.get("contenido_neto", "")
        lote = rd.get("numero_lote", "")
        funcion = rd.get("funcion_producto", "")
        pao = rd.get("pao_meses", "")
        inci = rd.get("ingredientes_inci", "")
        advertencias = rd.get("advertencias", "")
        modo_empleo = rd.get("modo_empleo", "")
        conservacion = rd.get("condiciones_conservacion", "")
        pais = rd.get("pais_fabricacion", "")

        # Build INCI list formatted
        inci_html = ""
        if inci:
            inci_items = [i.strip() for i in inci.replace("\n", ",").split(",") if i.strip()]
            inci_html = ", ".join(f"<span>{_esc(i)}</span>" for i in inci_items)

        # Optional sections
        warnings_block = ""
        if advertencias:
            warnings_block = f"""
            <div class="cos-warnings">
                <div class="cos-section-title">{_esc(t['warnings'])}</div>
                <p>{_esc(advertencias)}</p>
            </div>"""

        usage_block = ""
        if modo_empleo:
            usage_block = f"""
            <div class="cos-usage">
                <div class="cos-section-title">{_esc(t['usage'])}</div>
                <p>{_esc(modo_empleo)}</p>
            </div>"""

        storage_block = ""
        if conservacion:
            storage_block = f"""
            <div class="cos-storage">
                <div class="cos-section-title">{_esc(t['storage'])}</div>
                <p>{_esc(conservacion)}</p>
            </div>"""

        origin_block = ""
        if pais:
            origin_block = f"""
            <div class="cos-origin">
                <strong>{_esc(t['origin'])}:</strong> {_esc(pais)}
            </div>"""

        barcode_block = ""
        if barcode:
            barcode_block = f'<div class="cos-barcode"><strong>EAN:</strong> {_esc(barcode)}</div>'

        pao_display = t["pao_months"].format(months=pao) if pao else ""

        return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_esc(name)} — {_esc(t['title'])}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-size: 11pt; color: #333; line-height: 1.5; }}
.cos-label {{ max-width: 520px; margin: 1rem auto; padding: 1.5rem; border: 2px solid #333; border-radius: 8px; }}
.cos-header {{ text-align: center; margin-bottom: 1rem; padding-bottom: 0.75rem; border-bottom: 2px solid #333; }}
.cos-title {{ font-size: 1.1rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }}
.cos-brand {{ font-size: 0.85rem; color: #666; margin-top: 2px; }}
.cos-columns {{ display: flex; gap: 1.25rem; }}
.cos-col-left {{ flex: 1; }}
.cos-col-right {{ flex: 1; }}
.cos-field {{ margin-bottom: 0.6rem; }}
.cos-field-label {{ font-size: 0.75rem; color: #888; text-transform: uppercase; letter-spacing: 0.3px; }}
.cos-field-value {{ font-weight: 500; }}
.cos-pao {{ display: inline-flex; align-items: center; gap: 6px; }}
.cos-pao-icon {{ display: inline-flex; align-items: center; justify-content: center; width: 28px; height: 28px; border: 2px solid #333; border-radius: 4px; font-size: 0.7rem; font-weight: 700; }}
.cos-section-title {{ font-size: 0.8rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.3px; margin-bottom: 0.3rem; color: #555; }}
.cos-inci {{ margin-top: 1rem; padding-top: 0.75rem; border-top: 1px solid #ccc; }}
.cos-inci p {{ font-size: 0.8rem; line-height: 1.6; }}
.cos-warnings {{ margin-top: 0.75rem; padding: 0.5rem; background: #fff3cd; border-radius: 4px; }}
.cos-warnings p {{ font-size: 0.8rem; }}
.cos-usage {{ margin-top: 0.75rem; }}
.cos-usage p {{ font-size: 0.8rem; }}
.cos-storage {{ margin-top: 0.5rem; }}
.cos-storage p {{ font-size: 0.8rem; }}
.cos-origin {{ margin-top: 0.5rem; font-size: 0.8rem; }}
.cos-barcode {{ margin-top: 0.5rem; font-size: 0.8rem; }}
.cos-footer {{ margin-top: 1rem; padding-top: 0.5rem; border-top: 1px solid #ccc; text-align: center; font-size: 0.7rem; color: #999; }}
@media (max-width: 520px) {{
  .cos-columns {{ flex-direction: column; gap: 0.5rem; }}
  .cos-label {{ margin: 0.5rem; padding: 1rem; }}
}}
</style>
</head>
<body>
<div class="cos-label">
    <div class="cos-header">
        <div class="cos-title">{_esc(name)}</div>
        {f'<div class="cos-brand">{_esc(brand)}</div>' if brand else ''}
    </div>

    <div class="cos-columns">
        <div class="cos-col-left">
            <div class="cos-field">
                <div class="cos-field-label">{_esc(t['function'])}</div>
                <div class="cos-field-value">{_esc(funcion)}</div>
            </div>
            <div class="cos-field">
                <div class="cos-field-label">{_esc(t['net_content'])}</div>
                <div class="cos-field-value">{_esc(contenido)}</div>
            </div>
            <div class="cos-field">
                <div class="cos-field-label">{_esc(t['batch'])}</div>
                <div class="cos-field-value">{_esc(lote)}</div>
            </div>
            <div class="cos-field">
                <div class="cos-field-label">{_esc(t['pao'])}</div>
                <div class="cos-pao">
                    <span class="cos-pao-icon">{_esc(pao_display)}</span>
                    {_esc(pao_display)} meses tras apertura
                </div>
            </div>
        </div>
        <div class="cos-col-right">
            <div class="cos-field">
                <div class="cos-field-label">{_esc(t['responsible'])}</div>
                <div class="cos-field-value">{_esc(responsable)}</div>
            </div>
            {origin_block}
            {barcode_block}
        </div>
    </div>

    <div class="cos-inci">
        <div class="cos-section-title">{_esc(t['ingredients_inci'])}</div>
        <p>{inci_html}</p>
    </div>

    {warnings_block}
    {usage_block}
    {storage_block}

    <div class="cos-footer">{_esc(t['regulation'])}</div>
</div>
</body>
</html>"""


def _esc(s: str) -> str:
    """Escape HTML special characters."""
    if not s:
        return ""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )
