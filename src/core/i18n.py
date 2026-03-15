"""i18n helpers for label generation.

Uses a simple dict-based translation store so there are no compile-time
.mo file dependencies; Babel is available for more advanced usage if needed.
"""

from src.core.config import settings

_LABEL_TRANSLATIONS: dict[str, dict[str, str]] = {
    "es": {
        # Nutritional fields
        "energy": "Energía",
        "fat": "Grasas",
        "saturated_fat": "Ácidos grasos saturados",
        "carbohydrates": "Hidratos de carbono",
        "sugars": "Azúcares",
        "fiber": "Fibra alimentaria",
        "protein": "Proteínas",
        "salt": "Sal",
        # Label sections
        "nutrition_facts": "Información Nutricional",
        "ingredients": "Ingredientes",
        "allergens": "Alérgenos",
        "net_weight": "Peso neto",
        "manufacturer": "Fabricante",
        "best_before": "Consumir preferentemente antes de",
        "storage": "Condiciones de conservación",
        "per_100g": "Por 100 g",
        "per_serving": "Por porción",
        "regulation_eu_1169": "Reglamento (UE) nº 1169/2011",
        # Units
        "kj": "kJ",
        "kcal": "kcal",
        "grams": "g",
        "milligrams": "mg",
        # General
        "yes": "Sí",
        "no": "No",
        "unknown": "Desconocido",
    },
    "en": {
        "energy": "Energy",
        "fat": "Fat",
        "saturated_fat": "Saturated fat",
        "carbohydrates": "Carbohydrate",
        "sugars": "Sugars",
        "fiber": "Fibre",
        "protein": "Protein",
        "salt": "Salt",
        "nutrition_facts": "Nutrition Facts",
        "ingredients": "Ingredients",
        "allergens": "Allergens",
        "net_weight": "Net weight",
        "manufacturer": "Manufacturer",
        "best_before": "Best before",
        "storage": "Storage conditions",
        "per_100g": "Per 100 g",
        "per_serving": "Per serving",
        "regulation_eu_1169": "Regulation (EU) No 1169/2011",
        "kj": "kJ",
        "kcal": "kcal",
        "grams": "g",
        "milligrams": "mg",
        "yes": "Yes",
        "no": "No",
        "unknown": "Unknown",
    },
}


def get_label_translations(lang: str) -> dict[str, str]:
    """Return the translation dict for the given language code.

    Falls back to DEFAULT_LANGUAGE if the requested language is not supported.
    """
    if lang in _LABEL_TRANSLATIONS:
        return _LABEL_TRANSLATIONS[lang]
    fallback = settings.DEFAULT_LANGUAGE
    return _LABEL_TRANSLATIONS.get(fallback, _LABEL_TRANSLATIONS["es"])


def get_supported_languages() -> list[str]:
    return list(_LABEL_TRANSLATIONS.keys())
