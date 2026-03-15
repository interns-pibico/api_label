from src.services.label_engine.base import BaseLabelGenerator
from src.services.label_engine.nutrition import NutritionLabelGenerator

CATEGORY_GENERATORS: dict[str, type[BaseLabelGenerator]] = {
    "nutrition_eu": NutritionLabelGenerator,
}


def get_generator(category_code: str) -> BaseLabelGenerator | None:
    """Return an instantiated generator for the given category code, or None if unsupported."""
    cls = CATEGORY_GENERATORS.get(category_code)
    if cls is None:
        return None
    return cls()
