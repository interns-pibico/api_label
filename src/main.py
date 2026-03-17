"""api_label — FastAPI application entry point."""

import time
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from src.api.v1.router import router as api_router
from src.core.config import settings
from src.core.limiter import limiter

# ---------------------------------------------------------------------------
# Jinja2 Templates
# ---------------------------------------------------------------------------

templates = Jinja2Templates(
    directory="/home/erpnext/.services/api_label/frontend/templates"
)

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="api_label",
    description="Sistema de generación de etiquetas de producto conforme a normativa legal",
    version="0.1.0",
    root_path=settings.ROOT_PATH,
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
)

# ---------------------------------------------------------------------------
# Rate limiter state (must be attached before SlowAPIMiddleware)
# ---------------------------------------------------------------------------

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ---------------------------------------------------------------------------
# 1. CORS Middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://raquel.pibico.es", "https://api.pibico.es"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-API-Key",
        "X-Request-ID",
        "Accept",
        "Origin",
    ],
)

# ---------------------------------------------------------------------------
# 2. Rate limiting middleware
# ---------------------------------------------------------------------------

app.add_middleware(SlowAPIMiddleware)

# ---------------------------------------------------------------------------
# 3. Security headers middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def security_headers_middleware(request: Request, call_next) -> Response:
    response: Response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# ---------------------------------------------------------------------------
# 4. Request logging middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def request_logging_middleware(request: Request, call_next) -> Response:
    request_id = str(uuid.uuid4())
    start_time = time.monotonic()

    response: Response = await call_next(request)

    duration_ms = int((time.monotonic() - start_time) * 1000)
    response.headers["X-Request-ID"] = request_id

    import logging
    logger = logging.getLogger("api_label.access")
    logger.info(
        "method=%s path=%s status=%d duration_ms=%d request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        request_id,
    )

    return response


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(api_router, prefix="/api/v1")

# ---------------------------------------------------------------------------
# Static files (optional — if frontend/static exists)
# ---------------------------------------------------------------------------

try:
    app.mount(
        "/static",
        StaticFiles(directory="/home/erpnext/.services/api_label/frontend/static"),
        name="static",
    )
except Exception:
    pass


# ---------------------------------------------------------------------------
# Frontend page routes (Jinja2)
# ---------------------------------------------------------------------------

def _ctx(request: Request, **kwargs):
    """Build a base template context with root_path."""
    return {"request": request, "root_path": settings.ROOT_PATH, **kwargs}


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def landing_page(request: Request):
    return templates.TemplateResponse("landing.html", _ctx(request))


@app.get("/try", response_class=HTMLResponse, include_in_schema=False)
async def try_page(request: Request):
    return templates.TemplateResponse("try.html", _ctx(request))


@app.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", _ctx(request, auth_page=True))


@app.get("/pricing", response_class=HTMLResponse, include_in_schema=False)
async def pricing_page(request: Request):
    return templates.TemplateResponse("pricing.html", _ctx(request))


@app.get("/register", response_class=HTMLResponse, include_in_schema=False)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", _ctx(request, auth_page=True))


@app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", _ctx(request))


@app.get("/scanner", response_class=HTMLResponse, include_in_schema=False)
async def scanner_page(request: Request):
    return templates.TemplateResponse("scanner.html", _ctx(request))


@app.get("/products", response_class=HTMLResponse, include_in_schema=False)
async def products_page(request: Request):
    return templates.TemplateResponse("products.html", _ctx(request))


@app.get("/products/new", response_class=HTMLResponse, include_in_schema=False)
async def product_new_page(request: Request):
    return templates.TemplateResponse("product_form.html", _ctx(request))


@app.get("/products/{product_id}", response_class=HTMLResponse, include_in_schema=False)
async def product_detail_page(request: Request, product_id: str):
    if product_id == "new":
        return templates.TemplateResponse("product_form.html", _ctx(request))
    return templates.TemplateResponse("product_detail.html", _ctx(request))


@app.get("/products/{product_id}/edit", response_class=HTMLResponse, include_in_schema=False)
async def product_edit_page(request: Request, product_id: str):
    return templates.TemplateResponse("product_form.html", _ctx(request))


@app.get("/labels/{label_id}", response_class=HTMLResponse, include_in_schema=False)
async def label_viewer_page(request: Request, label_id: str):
    return templates.TemplateResponse("label_viewer.html", _ctx(request))


@app.get("/labels", response_class=HTMLResponse, include_in_schema=False)
async def labels_page(request: Request):
    return templates.TemplateResponse("labels.html", _ctx(request))


@app.get("/baskets", response_class=HTMLResponse, include_in_schema=False)
async def baskets_page(request: Request):
    return templates.TemplateResponse("baskets.html", _ctx(request))


@app.get("/baskets/{basket_id}", response_class=HTMLResponse, include_in_schema=False)
async def basket_detail_page(request: Request, basket_id: str):
    return templates.TemplateResponse(
        "basket_detail.html", _ctx(request, basket_id=basket_id)
    )


@app.get("/tokens", response_class=HTMLResponse, include_in_schema=False)
async def tokens_page(request: Request):
    return templates.TemplateResponse("tokens.html", _ctx(request))


@app.get("/profile", response_class=HTMLResponse, include_in_schema=False)
async def profile_page(request: Request):
    return templates.TemplateResponse("profile.html", _ctx(request))


@app.get("/admin/users", response_class=HTMLResponse, include_in_schema=False)
async def admin_users_page(request: Request):
    return templates.TemplateResponse("admin_users.html", _ctx(request))


@app.get("/admin/usage", response_class=HTMLResponse, include_in_schema=False)
async def admin_usage_page(request: Request):
    return templates.TemplateResponse("admin_usage.html", _ctx(request))


@app.get("/legal", response_class=HTMLResponse, include_in_schema=False)
async def legal_page(request: Request):
    return templates.TemplateResponse("legal.html", _ctx(request))


# ---------------------------------------------------------------------------
# Startup / shutdown
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def on_startup() -> None:
    import logging
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("api_label").info("api_label started on root_path=%s", settings.ROOT_PATH)
