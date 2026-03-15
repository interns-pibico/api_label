"""Motor de generación de etiquetas

Este módulo contiene la lógica principal para:
- Validación de esquemas JSON de productos
- Generación de etiquetas conforme a normativa legal
- Exportación a PDF con ReportLab
"""

from src.services.label_engine.base import BaseLabelGenerator
from src.services.label_engine.registry import get_generator, CATEGORY_GENERATORS

__all__ = ["BaseLabelGenerator", "get_generator", "CATEGORY_GENERATORS"]
