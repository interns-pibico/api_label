# api_label

Product label generation system compliant with legal regulations (nutrition, cosmetics, electronics).

## Stack

- **Framework:** FastAPI
- **Database:** PostgreSQL (async via SQLAlchemy + asyncpg)
- **Task Queue:** Celery + Redis
- **Migrations:** Alembic
- **Auth:** JWT (python-jose)
- **i18n:** Babel + gettext
- **Server:** Gunicorn + Uvicorn workers

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

Copy `.env.example` to `.env` and fill in the required values.

```bash
alembic upgrade head
```

## Running

```bash
gunicorn app.main:app -c gunicorn.conf.py
```

## URL

Served at `https://raquel.pibico.es/label/`

## License

MIT - see [LICENSE](LICENSE)
