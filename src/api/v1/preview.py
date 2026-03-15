"""Public label preview -- no authentication required.

Allows visitors to generate a nutritional label HTML preview without
registering, subject to:
  1. slowapi rate limit (10/hour per IP) -- first defence layer
  2. Redis trial counters (session cookie + IP hash) -- authoritative limit

No data is persisted to the database.
"""

import hashlib
import uuid

import redis.asyncio as aioredis
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.core.config import settings
from src.core.exceptions import BadRequestException
from src.core.limiter import limiter
from src.services.integrations.openfoodfacts import lookup_barcode as off_lookup_barcode
from src.services.label_engine.registry import get_generator

router = APIRouter(tags=["preview"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class PreviewRequest(BaseModel):
    product_name: str
    brand: str | None = None
    language: str = "es"
    regulatory_data: dict


class PreviewResponse(BaseModel):
    html: str
    regulation_version: str
    regulation: str
    tries_remaining: int


class PreviewByBarcodeRequest(BaseModel):
    barcode: str


class PreviewByBarcodeResponse(BaseModel):
    html: str
    nutriscore: str | None
    product_name: str
    brand: str | None = None
    image_url: str | None = None
    tries_remaining: int


# ---------------------------------------------------------------------------
# Redis helper (same pattern as auth_service._get_redis)
# ---------------------------------------------------------------------------

async def _get_redis() -> aioredis.Redis:
    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


def _hash_ip(ip: str) -> str:
    """SHA-256 hash of the IP so we never store raw IPs in Redis."""
    return hashlib.sha256(ip.encode()).hexdigest()


def _get_client_ip(request: Request) -> str:
    """Extract real client IP, preferring X-Forwarded-For behind nginx."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ---------------------------------------------------------------------------
# Trial counter logic
# ---------------------------------------------------------------------------

_TRIAL_BLOCKED = -1  # sentinel: limit already reached, no increment performed


async def _check_and_increment_trial(
    session_id: str, client_ip: str
) -> int:
    """Check trial limits and increment counters.

    Returns:
        >= 0 : tries remaining AFTER this successful attempt
        _TRIAL_BLOCKED (-1) : limit was already reached, no increment done
    """
    redis = await _get_redis()
    try:
        session_key = f"trial_session:{session_id}"
        ip_key = f"trial_ip:{_hash_ip(client_ip)}"

        # Read current counts BEFORE incrementing
        session_count = int(await redis.get(session_key) or 0)
        ip_count = int(await redis.get(ip_key) or 0)

        # If either limit is already reached, reject without incrementing
        if session_count >= settings.TRIAL_MAX_SESSION:
            return _TRIAL_BLOCKED
        if ip_count >= settings.TRIAL_MAX_IP:
            return _TRIAL_BLOCKED

        # Increment both counters atomically via pipeline
        pipe = redis.pipeline(transaction=True)
        pipe.incr(session_key)
        pipe.expire(session_key, settings.TRIAL_SESSION_TTL)
        pipe.incr(ip_key)
        pipe.expire(ip_key, settings.TRIAL_IP_TTL)
        results = await pipe.execute()

        new_session_count = results[0]  # INCR returns the new value
        return max(0, settings.TRIAL_MAX_SESSION - new_session_count)
    finally:
        await redis.aclose()


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("/labels/preview", response_model=PreviewResponse)
@limiter.limit("10/hour")
async def preview_label(request: Request, data: PreviewRequest, response: Response):
    """Generate a label HTML preview without authentication.

    - Only nutrition_eu category is supported.
    - No data is persisted to the database.
    - Rate limited: 10 requests/hour per IP (slowapi).
    - Trial limited: 3 per session cookie, 10 per IP (Redis).
    """
    # --- Resolve session ID from cookie or generate new one ---
    session_id = request.cookies.get("lbl_sid")
    is_new_session = False
    if not session_id:
        session_id = str(uuid.uuid4())
        is_new_session = True

    # --- Get client IP ---
    client_ip = _get_client_ip(request)

    # --- Check trial limits ---
    tries_remaining = await _check_and_increment_trial(session_id, client_ip)

    if tries_remaining == _TRIAL_BLOCKED:
        # Set the cookie even on rejection so the session persists
        resp = JSONResponse(
            status_code=429,
            content={"detail": "trial_limit_reached", "tries_remaining": 0},
        )
        resp.set_cookie(
            key="lbl_sid",
            value=session_id,
            max_age=settings.TRIAL_SESSION_TTL,
            httponly=True,
            secure=True,
            samesite="lax",
        )
        return resp

    # --- Generate label ---
    generator = get_generator("nutrition_eu")
    if generator is None:
        raise BadRequestException(detail="Generador de etiquetas no disponible")

    errors = generator.validate_data(data.regulatory_data)
    if errors:
        raise BadRequestException(detail=f"Datos invalidos: {'; '.join(errors)}")

    lang = data.language if data.language in ("es", "en") else "es"
    product_dict = {
        "name": data.product_name,
        "brand": data.brand,
        "barcode": None,
        "regulatory_data": data.regulatory_data,
    }

    html = generator.generate_html(product_dict, lang=lang)
    label_json = generator.generate_json(product_dict, lang=lang)

    # --- Set session cookie on the response ---
    response.set_cookie(
        key="lbl_sid",
        value=session_id,
        max_age=settings.TRIAL_SESSION_TTL,  # 30 days
        httponly=True,
        secure=True,
        samesite="lax",
    )

    return PreviewResponse(
        html=html,
        regulation_version=generator.REGULATION_VERSION,
        regulation=label_json.get("regulation", "Reglamento (UE) n 1169/2011"),
        tries_remaining=tries_remaining,
    )


# ---------------------------------------------------------------------------
# Preview by barcode (Open Food Facts) — consumes trial
# ---------------------------------------------------------------------------

def _set_session_cookie(response: Response, session_id: str) -> None:
    """Set the lbl_sid HttpOnly session cookie."""
    response.set_cookie(
        key="lbl_sid",
        value=session_id,
        max_age=settings.TRIAL_SESSION_TTL,
        httponly=True,
        secure=True,
        samesite="lax",
    )


@router.post("/labels/preview-by-barcode", response_model=PreviewByBarcodeResponse)
@limiter.limit("10/hour")
async def preview_label_by_barcode(
    request: Request,
    data: PreviewByBarcodeRequest,
    response: Response,
):
    """Generate a label HTML preview from an Open Food Facts barcode.

    Flow:
    1. Check trial limits (cookie + IP Redis) and increment counter.
    2. Fetch product data from Open Food Facts by barcode.
    3. Validate that required nutritional data is present.
    4. Generate EU 1169/2011 nutrition label HTML via label_engine.
    5. Return HTML + nutriscore + product_name + tries_remaining.

    Rate limited: 10 requests/hour per IP (slowapi).
    Trial limited: 3 per session cookie, 10 per IP (Redis).
    """
    # --- Resolve session ID from cookie or generate new one ---
    session_id = request.cookies.get("lbl_sid")
    if not session_id:
        session_id = str(uuid.uuid4())

    # --- Get client IP ---
    client_ip = _get_client_ip(request)

    # --- Check trial limits ---
    tries_remaining = await _check_and_increment_trial(session_id, client_ip)

    if tries_remaining == _TRIAL_BLOCKED:
        resp = JSONResponse(
            status_code=429,
            content={"detail": "trial_limit_reached", "tries_remaining": 0},
        )
        _set_session_cookie(resp, session_id)
        return resp

    # --- Fetch product from Open Food Facts ---
    product = await off_lookup_barcode(data.barcode)
    if product is None:
        # Trial was already incremented — that is intentional (prevents abuse)
        _set_session_cookie(response, session_id)
        return JSONResponse(
            status_code=404,
            content={
                "detail": "Producto no encontrado en Open Food Facts",
                "tries_remaining": tries_remaining,
            },
        )

    # --- Validate nutritional data ---
    if not product.has_required_nutrition():
        _set_session_cookie(response, session_id)
        return JSONResponse(
            status_code=422,
            content={
                "detail": (
                    "El producto no tiene datos nutricionales suficientes para "
                    "generar una etiqueta conforme al Reglamento (UE) 1169/2011. "
                    "Faltan campos obligatorios como energia, grasas, hidratos de "
                    "carbono, proteinas o sal."
                ),
                "tries_remaining": tries_remaining,
            },
        )

    # --- Generate label ---
    generator = get_generator("nutrition_eu")
    if generator is None:
        raise BadRequestException(detail="Generador de etiquetas no disponible")

    regulatory_data = product.to_regulatory_data()

    errors = generator.validate_data(regulatory_data)
    if errors:
        _set_session_cookie(response, session_id)
        return JSONResponse(
            status_code=422,
            content={
                "detail": f"Datos nutricionales incompletos: {'; '.join(errors)}",
                "tries_remaining": tries_remaining,
            },
        )

    product_dict = {
        "name": product.name,
        "brand": product.brand,
        "barcode": product.barcode,
        "regulatory_data": regulatory_data,
    }

    html = generator.generate_html(product_dict, lang="es")

    # --- Set session cookie ---
    _set_session_cookie(response, session_id)

    return PreviewByBarcodeResponse(
        html=html,
        nutriscore=product.nutriscore,
        product_name=product.name,
        brand=product.brand,
        image_url=product.image_url,
        tries_remaining=tries_remaining,
    )
