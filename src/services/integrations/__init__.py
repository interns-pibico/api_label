"""Integraciones externas

Este módulo contiene la lógica para integración con:
- api.pibico.es/barcode — generación de códigos de barras
- Open Food Facts — búsqueda de productos alimentarios
"""

from src.services.integrations.barcode_client import lookup_barcode, transform_barcode_response
from src.services.integrations import openfoodfacts as off_client

__all__ = ["lookup_barcode", "transform_barcode_response", "off_client"]
