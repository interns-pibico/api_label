"""Async HTTP client for api.pibico.es/barcode integration."""

import httpx

from src.core.config import settings
from src.core.exceptions import BadRequestException, NotFoundException


_TIMEOUT = httpx.Timeout(10.0, connect=5.0)
_MAX_RETRIES = 2


async def lookup_barcode(code: str) -> dict:
    """
    Query api.pibico.es/barcode/{code} and return the product data.
    Raises NotFoundException if the barcode is not found.
    Raises BadRequestException on upstream errors.
    """
    url = f"{settings.BARCODE_API_URL}/{code}"
    headers = {"X-API-Key": settings.BARCODE_API_KEY}

    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 404:
                    raise NotFoundException(detail=f"Barcode '{code}' not found in external registry")
                if response.status_code == 200:
                    return response.json()
                raise BadRequestException(
                    detail=f"Barcode API returned status {response.status_code}"
                )
        except (NotFoundException, BadRequestException):
            raise
        except httpx.TimeoutException as exc:
            last_exc = exc
        except httpx.RequestError as exc:
            last_exc = exc

    raise BadRequestException(
        detail=f"Could not reach barcode API after {_MAX_RETRIES + 1} attempts: {last_exc}"
    )


def transform_barcode_response(raw: dict) -> dict:
    """
    Transform external barcode API response to internal product format.
    The external API may return different field names; normalize here.
    """
    return {
        "name": raw.get("name") or raw.get("product_name") or raw.get("title", ""),
        "brand": raw.get("brand") or raw.get("manufacturer", ""),
        "barcode": raw.get("barcode") or raw.get("ean") or raw.get("upc", ""),
        "description": raw.get("description") or raw.get("summary", ""),
        "image_url": raw.get("image_url") or raw.get("image", ""),
        "regulatory_data": raw.get("nutrition") or raw.get("regulatory_data") or {},
        "_raw": raw,
    }
