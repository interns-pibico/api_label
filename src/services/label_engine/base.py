from abc import ABC, abstractmethod


class BaseLabelGenerator(ABC):
    """Abstract base class for all label generators."""

    REGULATION_VERSION: str = "unknown"

    @abstractmethod
    def validate_data(self, regulatory_data: dict) -> list[str]:
        """
        Validate regulatory_data against expected fields.
        Returns a list of validation error messages (empty = valid).
        """
        ...

    @abstractmethod
    def generate_html(self, product_data: dict, lang: str = "es") -> str:
        """
        Generate an HTML string representation of the label.
        product_data contains product fields + regulatory_data merged.
        """
        ...

    @abstractmethod
    def generate_json(self, product_data: dict, lang: str = "es") -> dict:
        """
        Generate a structured JSON representation of the label data.
        """
        ...
