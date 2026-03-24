"""Seed script: insert/update the 'nutrition_eu' regulatory category.

Run from the project root with the venv active:
    cd /home/erpnext/.services/api_label
    python scripts/seed_categories.py

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
    """Parse a .env file into a dict. Handles quoted values."""
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
            # Strip surrounding quotes
            if (raw_val.startswith('"') and raw_val.endswith('"')) or (
                raw_val.startswith("'") and raw_val.endswith("'")
            ):
                raw_val = raw_val[1:-1]
            env[key] = raw_val
    return env


def _asyncpg_url(database_url: str) -> str:
    """Convert SQLAlchemy asyncpg URL to plain asyncpg URL.

    postgresql+asyncpg://user:pass@host:port/db  ->  postgresql://user:pass@host:port/db
    """
    return re.sub(r"^postgresql\+asyncpg://", "postgresql://", database_url)


# ---------------------------------------------------------------------------
# Schema definition for nutrition_eu per EU Reg. 1169/2011
# ---------------------------------------------------------------------------
SCHEMA_DEFINITION = {
    "required": [
        {
            "field": "energy_kj",
            "type": "number",
            "unit": "kJ",
            "description": "Valor energético en kilojulios por 100 g o 100 ml",
        },
        {
            "field": "energy_kcal",
            "type": "number",
            "unit": "kcal",
            "description": "Valor energético en kilocalorías por 100 g o 100 ml",
        },
        {
            "field": "fat_g",
            "type": "number",
            "unit": "g",
            "description": "Grasas totales por 100 g o 100 ml",
        },
        {
            "field": "saturated_fat_g",
            "type": "number",
            "unit": "g",
            "description": "Ácidos grasos saturados por 100 g o 100 ml",
        },
        {
            "field": "carbohydrates_g",
            "type": "number",
            "unit": "g",
            "description": "Hidratos de carbono por 100 g o 100 ml",
        },
        {
            "field": "sugars_g",
            "type": "number",
            "unit": "g",
            "description": "Azúcares por 100 g o 100 ml",
        },
        {
            "field": "protein_g",
            "type": "number",
            "unit": "g",
            "description": "Proteínas por 100 g o 100 ml",
        },
        {
            "field": "salt_g",
            "type": "number",
            "unit": "g",
            "description": (
                "Sal por 100 g o 100 ml. "
                "Si no se proporciona, se calcula automáticamente desde 'sodium_mg' "
                "usando la fórmula: salt_g = sodium_mg * 2.5 / 1000. "
                "Al menos uno de 'salt_g' o 'sodium_mg' es obligatorio."
            ),
        },
    ],
    "optional": [
        {
            "field": "sodium_mg",
            "type": "number",
            "unit": "mg",
            "description": (
                "Sodio en mg por 100 g o 100 ml. "
                "Si 'salt_g' no se proporciona, se usa para calcular la sal automáticamente."
            ),
        },
        {
            "field": "fiber_g",
            "type": "number",
            "unit": "g",
            "description": (
                "Fibra alimentaria por 100 g o 100 ml. "
                "Si se declara, aparece en la tabla entre azúcares y proteínas "
                "(conforme al orden del Reglamento)."
            ),
        },
        {
            "field": "serving_size_g",
            "type": "number",
            "unit": "g",
            "description": (
                "Tamaño de porción en gramos. "
                "Si se proporciona, la etiqueta añade una columna adicional con "
                "los valores nutricionales por porción."
            ),
        },
        {
            "field": "ingredients",
            "type": "string",
            "description": (
                "Lista completa de ingredientes en orden decreciente de peso, "
                "tal como aparecen en el momento de su uso en la fabricación."
            ),
        },
        {
            "field": "allergens",
            "type": "string",
            "description": (
                "Alérgenos presentes. Deben destacarse en la lista de ingredientes "
                "(el motor los marca en negrita automáticamente). "
                "Ejemplo: 'Gluten (trigo), huevo, leche, soja'. "
                "Usar coma como separador para múltiples alérgenos."
            ),
        },
        {
            "field": "net_weight",
            "type": "string",
            "description": (
                "Cantidad neta del alimento (peso o volumen). "
                "Ejemplos: '500 g', '1 L', '330 ml'."
            ),
        },
        {
            "field": "manufacturer",
            "type": "string",
            "description": (
                "Nombre y dirección del operador de empresa alimentaria "
                "responsable de la información alimentaria."
            ),
        },
        {
            "field": "best_before",
            "type": "string",
            "description": (
                "Fecha de consumo preferente o fecha de caducidad. "
                "Ejemplos: 'Ver base del envase', '12/2026'."
            ),
        },
        {
            "field": "storage_conditions",
            "type": "string",
            "description": (
                "Condiciones de conservación del alimento. "
                "Ejemplo: 'Conservar en lugar fresco y seco. Una vez abierto, consumir en 3 días'."
            ),
        },
        {
            "field": "country_of_origin",
            "type": "string",
            "description": (
                "País de origen o lugar de procedencia. "
                "Obligatorio para determinadas categorías (carnes, frutas y hortalizas frescas, etc.). "
                "Ejemplo: 'España'."
            ),
        },
    ],
    "notes": (
        "Conforme al Reglamento (UE) nº 1169/2011 sobre la información alimentaria "
        "facilitada al consumidor. "
        "La declaración nutricional obligatoria debe expresarse por 100 g o 100 ml. "
        "Los valores por porción son opcionales pero recomendados; si se declaran, "
        "deben acompañar siempre a los valores por 100 g. "
        "El orden de presentación en la etiqueta sigue el Anexo XV del Reglamento: "
        "energía, grasas, saturadas, hidratos de carbono, azúcares, [fibra], proteínas, sal."
    ),
}


async def seed(database_url: str) -> None:
    """Connect to PostgreSQL and upsert the nutrition_eu category."""
    try:
        import asyncpg
    except ImportError:
        print("ERROR: asyncpg is not installed. Run: pip install asyncpg")
        sys.exit(1)

    conn = await asyncpg.connect(database_url)
    try:
        category_id = str(uuid.uuid4())
        schema_json = json.dumps(SCHEMA_DEFINITION, ensure_ascii=False)

        # Check if already exists
        existing = await conn.fetchrow(
            "SELECT id, code FROM regulatory_categories WHERE code = $1",
            "nutrition_eu",
        )
        if existing:
            print(f"Category 'nutrition_eu' already exists (id={existing['id']}). Updating schema_definition...")

        sql = """
            INSERT INTO regulatory_categories
                (id, code, name, description, schema_definition, regulations_reference, sector, is_active, created_at, updated_at)
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
            "nutrition_eu",
            "Etiquetado Nutricional (UE)",
            (
                "Declaración nutricional obligatoria conforme al "
                "Reglamento (UE) nº 1169/2011 del Parlamento Europeo y del Consejo. "
                "Aplicable a todos los alimentos envasados comercializados en la Unión Europea."
            ),
            schema_json,
            "Reglamento (UE) nº 1169/2011 — Anexo XV (Declaración nutricional)",
            "alimentacion",
        )

        print(f"OK: category upserted successfully.")
        print(f"    id   = {row['id']}")
        print(f"    code = {row['code']}")
        print(f"    name = {row['name']}")
    finally:
        await conn.close()


def main() -> None:
    # Resolve .env path relative to the script's parent directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    env_path = os.path.join(project_root, ".env")

    env = _load_env(env_path)
    raw_url = env.get("DATABASE_URL") or os.environ.get("DATABASE_URL")

    if not raw_url:
        print(f"ERROR: DATABASE_URL not found in {env_path} or environment.")
        sys.exit(1)

    database_url = _asyncpg_url(raw_url)
    print(f"Connecting to: {database_url.split('@')[-1]}")  # Hide credentials in output

    asyncio.run(seed(database_url))


if __name__ == "__main__":
    main()
