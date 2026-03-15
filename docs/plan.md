# api_label -- Master Implementation Plan

**Date**: 2026-03-02
**Author**: DIRECTOR
**Status**: Pending Approval

---

## 1. Context

`api_label` is a product label generation system that produces legally compliant labels based on regulatory requirements. The initial focus is **EU nutritional labeling** (Reglamento UE 1169/2011), but the architecture is designed to be extensible to any product category (cosmetics, electronics, hardware, etc.), each with its own set of mandatory fields defined by the applicable regulation.

The system serves two audiences:
- **External API consumers** (via X-API-Key tokens): integrate label generation into their own workflows
- **Web UI users** (via JWT): manage products, generate labels, scan barcodes, and compare label compliance through a mobile-first dashboard

---

## 2. Architecture

### 2.1 App Type
- Full stack `api_*` application following the `api_cyber` reference pattern
- Port: **6956**
- Nginx path: **/label/**
- Database: `api_label_psql` (PostgreSQL)
- Redis DB: **3** (rate limiting, JWT blacklist, Celery broker/backend, cache)

### 2.2 Components
```
api_label/
├── src/
│   ├── main.py
│   ├── core/           # config, security, dependencies, exceptions, limiter
│   ├── db/
│   │   ├── session.py
│   │   └── repositories/   # user, api_token, product, category, label, comparison, usage_log
│   ├── models/          # user, api_token, regulatory_category, product, label, label_comparison, usage_log
│   ├── schemas/         # auth, user, token, category, product, label, comparison, usage, pagination
│   ├── services/        # auth, user, token, product, label_generator, comparison, barcode, usage
│   ├── api/v1/          # health, auth, users, tokens, categories, products, labels, comparisons, integrations, usage
│   └── workers/
│       ├── celery_app.py
│       └── tasks/       # label_tasks (PDF generation, batch processing)
├── frontend/
│   ├── templates/       # base, login, register, dashboard, products, product_detail, product_form,
│   │                    #   label_viewer, scanner, tokens, users, usage, profile
│   └── static/          # css/, js/, vendor/, fonts/, img/
├── alembic/
├── nginx/
├── supervisor/
├── scripts/             # init_db.py, create_admin.py, seed_categories.py
├── tests/
├── .env / .env.example
├── pyproject.toml
├── gunicorn.conf.py
└── alembic.ini
```

### 2.3 Layered Architecture
```
HTTP Request
  --> Routes (api/v1/*.py)         # Input validation, auth, response formatting
    --> Services (services/*.py)   # Business logic, orchestration
      --> Repositories (db/repositories/*.py)  # Data access, queries
        --> Models (models/*.py)   # SQLAlchemy ORM
```

### 2.4 Key Architectural Decisions

**Extensible Regulatory System**: Each `RegulatoryCategory` stores a JSON `schema_definition` that describes which fields are mandatory, their types, units, and validation rules. When a product is created under a category, its `regulatory_data` JSON must conform to that schema. This means adding a new regulation (e.g., cosmetics) only requires inserting a new row in `regulatory_categories` -- no migrations needed.

**Dual Auth**: JWT Bearer for human users (web UI + API), X-API-Key for external API consumers (ApiToken entity). Both can access product/label endpoints. The ApiToken system has its own rate limits and usage tracking.

**Label Generation Pipeline**: Product data + category schema --> validation --> template rendering (HTML) --> optional PDF export. HTML rendering uses Jinja2 templates per category. PDF uses WeasyPrint.

---

## 3. Data Models

### 3.1 users
| Column | Type | Constraints |
|--------|------|------------|
| id | SERIAL | PK |
| email | VARCHAR(255) | UNIQUE, NOT NULL |
| username | VARCHAR(100) | UNIQUE, NOT NULL |
| hashed_password | VARCHAR(255) | NOT NULL |
| full_name | VARCHAR(255) | nullable |
| is_active | BOOLEAN | DEFAULT true |
| is_admin | BOOLEAN | DEFAULT false |
| created_at | TIMESTAMPTZ | server_default now() |
| updated_at | TIMESTAMPTZ | server_default now(), onupdate |

### 3.2 api_tokens
| Column | Type | Constraints |
|--------|------|------------|
| id | SERIAL | PK |
| user_id | INTEGER | FK users.id, NOT NULL |
| name | VARCHAR(100) | NOT NULL |
| token_hash | VARCHAR(64) | UNIQUE, NOT NULL |
| prefix | VARCHAR(8) | NOT NULL (first 8 chars for identification) |
| is_active | BOOLEAN | DEFAULT true |
| rate_limit_daily | INTEGER | DEFAULT 100 |
| last_used_at | TIMESTAMPTZ | nullable |
| expires_at | TIMESTAMPTZ | nullable |
| created_at | TIMESTAMPTZ | server_default now() |

### 3.3 regulatory_categories
| Column | Type | Constraints |
|--------|------|------------|
| id | SERIAL | PK |
| code | VARCHAR(50) | UNIQUE, NOT NULL (e.g., "nutrition_eu", "cosmetics_eu") |
| name | VARCHAR(200) | NOT NULL |
| description | TEXT | nullable |
| schema_definition | JSONB | NOT NULL (defines required_fields, types, units) |
| regulation_reference | VARCHAR(500) | nullable (e.g., "Reglamento UE 1169/2011") |
| label_template | VARCHAR(100) | DEFAULT "default" (Jinja2 template name for label rendering) |
| is_active | BOOLEAN | DEFAULT true |
| created_at | TIMESTAMPTZ | server_default now() |
| updated_at | TIMESTAMPTZ | server_default now(), onupdate |

### 3.4 products
| Column | Type | Constraints |
|--------|------|------------|
| id | SERIAL | PK |
| user_id | INTEGER | FK users.id, NOT NULL |
| category_id | INTEGER | FK regulatory_categories.id, NOT NULL |
| name | VARCHAR(300) | NOT NULL |
| brand | VARCHAR(200) | nullable |
| barcode | VARCHAR(50) | nullable, INDEX |
| description | TEXT | nullable |
| regulatory_data | JSONB | NOT NULL (conforms to category schema) |
| image_url | VARCHAR(500) | nullable |
| is_active | BOOLEAN | DEFAULT true |
| created_at | TIMESTAMPTZ | server_default now() |
| updated_at | TIMESTAMPTZ | server_default now(), onupdate |

### 3.5 labels
| Column | Type | Constraints |
|--------|------|------------|
| id | SERIAL | PK |
| product_id | INTEGER | FK products.id, NOT NULL |
| format | VARCHAR(20) | NOT NULL (e.g., "html", "pdf") |
| label_data | JSONB | NOT NULL (processed data used to render the label) |
| rendered_html | TEXT | nullable (cached HTML output) |
| regulation_version | VARCHAR(100) | nullable |
| generated_at | TIMESTAMPTZ | server_default now() |

### 3.6 label_comparisons
| Column | Type | Constraints |
|--------|------|------------|
| id | SERIAL | PK |
| product_id | INTEGER | FK products.id, NOT NULL |
| label_id | INTEGER | FK labels.id, nullable |
| scanned_data | JSONB | NOT NULL (data from the real/scanned label) |
| discrepancies | JSONB | nullable (list of field-level differences) |
| compliance_score | FLOAT | nullable (0.0 to 100.0) |
| compared_at | TIMESTAMPTZ | server_default now() |

### 3.7 usage_logs
| Column | Type | Constraints |
|--------|------|------------|
| id | SERIAL | PK |
| user_id | INTEGER | FK users.id, nullable |
| token_id | INTEGER | FK api_tokens.id, nullable |
| endpoint | VARCHAR(200) | NOT NULL |
| method | VARCHAR(10) | NOT NULL |
| status_code | INTEGER | NOT NULL |
| response_time_ms | INTEGER | nullable |
| ip_address | VARCHAR(45) | nullable |
| created_at | TIMESTAMPTZ | server_default now() |

**Indexes**: barcode on products, user_id on products/api_tokens/usage_logs, token_id on usage_logs, created_at on usage_logs (for analytics queries).

---

## 4. API Endpoints

### 4.1 Health (no auth)
- `GET /api/v1/health` -- basic health
- `GET /api/v1/health/ready` -- readiness (DB + Redis connectivity)

### 4.2 Auth (no auth / JWT)
- `POST /api/v1/auth/login` -- returns JWT access token
- `POST /api/v1/auth/register` -- create account
- `POST /api/v1/auth/logout` -- blacklist JWT in Redis
- `GET /api/v1/auth/me` -- current user profile (JWT required)

### 4.3 Users (Admin JWT)
- `GET /api/v1/users` -- paginated list
- `GET /api/v1/users/{id}` -- detail
- `PUT /api/v1/users/{id}` -- update
- `DELETE /api/v1/users/{id}` -- soft deactivate

### 4.4 API Tokens (JWT)
- `GET /api/v1/tokens` -- list my tokens
- `POST /api/v1/tokens` -- create (returns raw token ONCE)
- `GET /api/v1/tokens/{id}` -- detail (shows prefix, not full token)
- `DELETE /api/v1/tokens/{id}` -- revoke
- `GET /api/v1/tokens/{id}/usage` -- usage stats for this token

### 4.5 Regulatory Categories (JWT or ApiKey; write=Admin)
- `GET /api/v1/categories` -- list all active categories
- `GET /api/v1/categories/{id}` -- detail including JSON schema
- `POST /api/v1/categories` -- create (Admin)
- `PUT /api/v1/categories/{id}` -- update (Admin)
- `DELETE /api/v1/categories/{id}` -- deactivate (Admin)

### 4.6 Products (JWT or ApiKey)
- `GET /api/v1/products` -- paginated, filterable by category/brand/barcode
- `GET /api/v1/products/{id}` -- detail
- `POST /api/v1/products` -- create (validates regulatory_data against category schema)
- `PUT /api/v1/products/{id}` -- update
- `DELETE /api/v1/products/{id}` -- soft delete
- `GET /api/v1/products/barcode/{code}` -- lookup by barcode

### 4.7 Labels (JWT or ApiKey)
- `POST /api/v1/labels/generate` -- generate label for product_id + format
- `GET /api/v1/labels/{id}` -- label metadata
- `GET /api/v1/labels/{id}/html` -- rendered HTML
- `GET /api/v1/labels/{id}/pdf` -- downloadable PDF
- `GET /api/v1/products/{id}/labels` -- all labels for a product

### 4.8 Label Comparisons (JWT or ApiKey)
- `POST /api/v1/comparisons` -- submit scanned_data + product_id, get compliance result
- `GET /api/v1/comparisons/{id}` -- comparison detail
- `GET /api/v1/products/{id}/comparisons` -- all comparisons for a product

### 4.9 External Integrations (JWT or ApiKey)
- `GET /api/v1/integrations/barcode/{code}` -- lookup via api.pibico.es/barcode
- `POST /api/v1/integrations/scan` -- submit barcode/QR image or text for processing

### 4.10 Usage & Stats (Admin JWT)
- `GET /api/v1/usage` -- global usage stats (requests/day, top endpoints, etc.)
- `GET /api/v1/usage/users/{id}` -- per-user breakdown
- `GET /api/v1/usage/tokens/{id}` -- per-token breakdown

---

## 5. Frontend Pages (Mobile-First)

All pages use `{{ root_path }}` for URLs. Brand guidelines: Steel Blue `#4682B4`, Red Brick `#CB4154`, Figtree/Poppins fonts, 12px card radius, box-shadow.

| Route | Template | Description |
|-------|----------|-------------|
| GET / | login.html | Login form |
| GET /register | register.html | Registration form |
| GET /dashboard | dashboard.html | Stats overview: total products, labels generated, API calls, recent activity |
| GET /products | products.html | Product list with search, filter by category, pagination |
| GET /products/new | product_form.html | Create product -- dynamic form fields based on selected category |
| GET /products/{id} | product_detail.html | Product view, regulatory data display, generate label button, label history |
| GET /products/{id}/edit | product_form.html | Edit product (same template as create) |
| GET /labels/{id} | label_viewer.html | View rendered label, download PDF, print button |
| GET /scanner | scanner.html | Input barcode/QR or upload image, view comparison results |
| GET /tokens | tokens.html | API token list, create new, revoke, copy token |
| GET /admin/users | users.html | User management table (admin only) |
| GET /admin/usage | usage.html | Usage analytics with charts (admin only) |
| GET /profile | profile.html | User profile edit, password change |

---

## 6. Label Generation Engine

### 6.1 Pipeline
1. **Validate**: Check product.regulatory_data against category.schema_definition
2. **Enrich**: Add calculated fields (e.g., reference intakes %, daily values)
3. **Render HTML**: Use category-specific Jinja2 template (e.g., `labels/nutrition_eu.html`)
4. **Store**: Save label_data + rendered_html to labels table
5. **PDF (optional)**: Convert HTML to PDF via WeasyPrint (Celery task for heavy loads)

### 6.2 Comparison Engine
1. **Input**: scanned_data JSON (same structure as regulatory_data)
2. **Generate reference**: Generate the legal label for the same product
3. **Diff**: Field-by-field comparison with tolerance thresholds (e.g., +/- 5% for nutritional values per EU regulation)
4. **Score**: Calculate compliance_score (0-100) based on number and severity of discrepancies
5. **Output**: List of discrepancies with field name, expected value, actual value, severity

---

## 7. Celery Workers

- **Broker**: Redis DB 3
- **Tasks**:
  - `generate_label_pdf`: Convert HTML label to PDF via WeasyPrint
  - `batch_generate_labels`: Generate labels for multiple products
  - `cleanup_expired_tokens`: Daily cleanup of expired API tokens
  - `aggregate_usage_stats`: Hourly aggregation of usage_logs for dashboard

---

## 8. Deployment

### 8.1 Infrastructure
- Gunicorn + UvicornWorker on port 6956
- Supervisor programs: `api_label` (gunicorn), `api_label_celery_worker`, `api_label_celery_beat`
- Nginx: upstream `api_label_server` + location `/label/`
- Logs: `/var/log/api_label/`

### 8.2 Nginx Config
```nginx
upstream api_label_server {
    server 127.0.0.1:6956;
}

location /label/ {
    proxy_pass http://api_label_server/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

### 8.3 Supervisor Config
```ini
[program:api_label]
command=/home/erpnext/api_label_env/bin/gunicorn -c gunicorn.conf.py src.main:app
directory=/home/erpnext/.services/api_label
user=erpnext
autostart=true
autorestart=true
stdout_logfile=/var/log/api_label/supervisor.log
stderr_logfile=/var/log/api_label/supervisor_error.log

[program:api_label_celery_worker]
command=/home/erpnext/api_label_env/bin/celery -A src.workers.celery_app worker --loglevel=info
directory=/home/erpnext/.services/api_label
user=erpnext
autostart=true
autorestart=true
stdout_logfile=/var/log/api_label/celery_worker.log
stderr_logfile=/var/log/api_label/celery_worker_error.log

[program:api_label_celery_beat]
command=/home/erpnext/api_label_env/bin/celery -A src.workers.celery_app beat --loglevel=info
directory=/home/erpnext/.services/api_label
user=erpnext
autostart=true
autorestart=true
stdout_logfile=/var/log/api_label/celery_beat.log
stderr_logfile=/var/log/api_label/celery_beat_error.log
```

---

## 9. Implementation Phases

### Phase 1: Scaffold (CREATOR)
- Directory structure per convention
- Venv at `/home/erpnext/api_label_env/`
- `pyproject.toml` with dependencies (fastapi, uvicorn, gunicorn, sqlalchemy[asyncio], asyncpg, alembic, pydantic-settings, python-jose, passlib, redis, celery, weasyprint, slowapi, httpx)
- Config files: `.env.example`, `gunicorn.conf.py`, `alembic.ini`
- Boilerplate: `main.py`, `config.py`, `health.py`, `router.py`
- Nginx/Supervisor config files
- App-specific `CLAUDE.md`

### Phase 2: Backend Core (BACKEND)
- Copy reusable files from api_cyber (security, exceptions, session, pagination)
- Models: User, ApiToken, RegulatoryCategory, Product, Label, LabelComparison, UsageLog
- Schemas: all request/response per model
- Repositories: all CRUD + domain queries
- Services: AuthService, UserService, TokenService
- Endpoints: health, auth, users, tokens
- Middleware: CORS, rate limiting, usage logging
- Alembic initial migration

### Phase 3: Backend Labels (BACKEND)
- Services: ProductService, LabelGeneratorService, ComparisonService, CategoryService
- Label generation pipeline (validate, enrich, render HTML)
- Comparison engine (diff, score, discrepancies)
- Category JSON schema validation
- Endpoints: categories, products, labels, comparisons
- Label HTML templates (nutrition_eu as first)

### Phase 4: Backend Integrations (BACKEND)
- Services: BarcodeService (httpx client to api.pibico.es/barcode), UsageService
- Endpoints: integrations, usage
- Usage logging middleware (intercept all API calls)

### Phase 5: Database (POSTGRE)
- Create database `api_label_psql`
- Install extensions (uuid-ossp, pgcrypto, pg_trgm for text search)
- Run `alembic upgrade head`
- Verify connectivity

### Phase 6: Frontend (BUILDER)
- base.html with responsive sidebar/topbar nav
- Login + Register pages
- Dashboard with stat cards and recent activity
- Products list with search/filter
- Product form with dynamic fields (fetches category schema via API)
- Product detail with label generation trigger
- Label viewer with print/download
- Scanner page (barcode input + comparison results)
- Token management page
- Admin: Users + Usage analytics
- Profile page
- All mobile-first, brand-compliant

### Phase 7: Celery Workers (BACKEND)
- celery_app.py configuration
- Task: generate_label_pdf
- Task: batch_generate_labels
- Task: cleanup_expired_tokens
- Task: aggregate_usage_stats
- Celery Beat schedule

### Phase 8: Deployment (DIRECTOR)
- Install venv + dependencies
- Deploy Supervisor config
- Deploy Nginx config
- Create log directories
- Verify health endpoints
- Run init_db + create_admin scripts

### Phase 9: Seed Data & Testing (DIRECTOR)
- Seed: EU Nutrition category (Reglamento UE 1169/2011) with full schema
- Seed: Sample products (3-5) with nutritional data
- Generate sample labels
- End-to-end API test
- Frontend walkthrough verification

---

## 10. Verification Checklist

- [ ] `GET /label/api/v1/health` returns `{"status": "healthy"}`
- [ ] `GET /label/api/v1/health/ready` returns `{"status": "ready"}`
- [ ] User registration + login + JWT works
- [ ] Admin can manage users
- [ ] API token creation returns raw token, subsequent calls show only prefix
- [ ] Categories CRUD works, schema_definition is valid JSON
- [ ] Product CRUD validates regulatory_data against category schema
- [ ] Label generation returns HTML for a product
- [ ] Label PDF download works
- [ ] Comparison endpoint returns discrepancies and compliance score
- [ ] Barcode integration endpoint calls api.pibico.es/barcode
- [ ] Usage logs are recorded for every API call
- [ ] Rate limiting works (Redis-backed)
- [ ] All frontend pages load correctly on mobile viewport
- [ ] Supervisor processes are running and auto-restart on failure
- [ ] Nginx proxying works with SSL on raquel.pibico.es/label/
- [ ] Celery worker and beat are operational
