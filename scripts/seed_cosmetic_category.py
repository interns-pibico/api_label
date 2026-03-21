"""Seed script: insert/update the 'cosmetica_eu' regulatory category.

Run from the project root with the venv active:
    cd /home/erpnext/.services/api_label
    python scripts/seed_cosmetic_category.py

Uses asyncpg directly (no SQLAlchemy) for simplicity.
Is fully idempotent via INSERT ... ON CONFLICT DO UPDATE.
"""

import asyncio
import json
import os
import re
import sys
import uuid


def _load_env(env_path: str) -> dict:
    env: dict = {}
    if not os.path.exists(env_path):
        return env
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, raw_val = line.partition("=")
            key = key.strip()
            raw_val = raw_val.strip()
            if (raw_val.startswith('"') and raw_val.endswith('"')) or (
                raw_val.startswith("'") and raw_val.endswith("'")
            ):
                raw_val = raw_val[1:-1]
            env[key] = raw_val
    return env


def _asyncpg_url(database_url: str) -> str:
    return re.sub(r"^postgresql\+asyncpg://", "postgresql://", database_url)


SCHEMA_DEFINITION = {
    "required": [
        {
            "field": "nombre",
            "type": "string",
            "description": "Nombre del producto cosmético",
        },
        {
            "field": "responsable_ue",
            "type": "string",
            "description": "Nombre y dirección del responsable UE (fabricante o importador)",
        },
        {
            "field": "contenido_neto",
            "type": "string",
            "description": "Peso o volumen neto del producto (ej: '200 ml', '50 g')",
        },
        {
            "field": "ingredientes_inci",
            "type": "string",
            "description": (
                "Lista completa de ingredientes en nomenclatura INCI, "
                "separados por comas, en orden decreciente de concentración"
            ),
        },
        {
            "field": "numero_lote",
            "type": "string",
            "description": "Número de lote de fabricación",
        },
        {
            "field": "funcion_producto",
            "type": "string",
            "description": "Función del cosmético (ej: 'Crema hidratante', 'Gel de ducha')",
        },
        {
            "field": "pao_meses",
            "type": "number",
            "description": "Periodo después de apertura en meses (PAO). Ej: 12, 6, 24",
        },
    ],
    "optional": [
        {
            "field": "pais_fabricacion",
            "type": "string",
            "description": "País de fabricación del producto",
        },
        {
            "field": "condiciones_conservacion",
            "type": "string",
            "description": "Condiciones especiales de conservación",
        },
        {
            "field": "advertencias",
            "type": "string",
            "description": "Precauciones y advertencias de uso",
        },
        {
            "field": "modo_empleo",
            "type": "string",
            "description": "Instrucciones de uso del producto",
        },
    ],
    "notes": (
        "Conforme al Reglamento (CE) nº 1223/2009 del Parlamento Europeo y del Consejo "
        "sobre los productos cosméticos. Artículo 19: Etiquetado. "
        "La lista de ingredientes debe indicarse con la nomenclatura INCI "
        "(International Nomenclature of Cosmetic Ingredients). "
        "El símbolo PAO (tarro abierto) indica el periodo de uso seguro tras la apertura."
    ),
}


async def seed(database_url: str) -> None:
    try:
        import asyncpg
    except ImportError:
        print("ERROR: asyncpg is not installed. Run: pip install asyncpg")
        sys.exit(1)

    conn = await asyncpg.connect(database_url)
    try:
        category_id = str(uuid.uuid4())
        schema_json = json.dumps(SCHEMA_DEFINITION, ensure_ascii=False)

        existing = await conn.fetchrow(
            "SELECT id, code FROM regulatory_categories WHERE code = $1",
            "cosmetica_eu",
        )
        if existing:
            print(f"Category 'cosmetica_eu' already exists (id={existing['id']}). Updating schema_definition...")

        sql = """
            INSERT INTO regulatory_categories
                (id, code, name, description, schema_definition, regulations_reference,
                 sector, is_active, created_at, updated_at)
            VALUES
                ($1::uuid, $2, $3, $4, $5::jsonb, $6, $7, TRUE, NOW(), NOW())
            ON CONFLICT (code) DO UPDATE SET
                name                 = EXCLUDED.name,
                description          = EXCLUDED.description,
                schema_definition    = EXCLUDED.schema_definition,
                regulations_reference = EXCLUDED.regulations_reference,
                sector               = EXCLUDED.sector,
                is_active            = EXCLUDED.is_active,
                updated_at           = NOW()
            RETURNING id, code, name
        """

        row = await conn.fetchrow(
            sql,
            category_id,
            "cosmetica_eu",
            "Etiquetado Cosmético (UE)",
            (
                "Etiquetado obligatorio de productos cosméticos conforme al "
                "Reglamento (CE) nº 1223/2009 del Parlamento Europeo y del Consejo. "
                "Aplicable a todos los productos cosméticos comercializados en la Unión Europea."
            ),
            schema_json,
            "Reglamento (CE) nº 1223/2009 — Artículo 19 (Etiquetado)",
            "cosmetica",
        )

        print(f"OK: category upserted successfully.")
        print(f"    id   = {row['id']}")
        print(f"    code = {row['code']}")
        print(f"    name = {row['name']}")
    finally:
        await conn.close()


def main() -> None:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    env_path = os.path.join(project_root, ".env")

    env = _load_env(env_path)
    raw_url = env.get("DATABASE_URL") or os.environ.get("DATABASE_URL")

    if not raw_url:
        print(f"ERROR: DATABASE_URL not found in {env_path} or environment.")
        sys.exit(1)

    database_url = _asyncpg_url(raw_url)
    print(f"Connecting to: {database_url.split('@')[-1]}")

    asyncio.run(seed(database_url))


if __name__ == "__main__":
    main()
