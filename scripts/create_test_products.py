"""Create 3 test products for the admin user via the HTTP API.

Run from the project root with the venv active:
    cd /home/erpnext/.services/api_label
    python scripts/create_test_products.py

Requires: requests (pip install requests)
The api_label service must be running on port 6956.
"""

import json
import sys

BASE_URL = "http://localhost:6956/label"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "AdminLabel26"

# ---------------------------------------------------------------------------
# Test product definitions
# ---------------------------------------------------------------------------
TEST_PRODUCTS = [
    {
        "name": "Yogur Natural",
        "brand": "Danone",
        "description": "Yogur natural entero sin aditivos",
        "regulatory_data": {
            # Mandatory EU 1169/2011 fields (values per 100 g)
            "energy_kj": 265,
            "energy_kcal": 63,
            "fat_g": 3.5,
            "saturated_fat_g": 2.4,
            "carbohydrates_g": 4.7,
            "sugars_g": 4.7,
            "protein_g": 4.0,
            "salt_g": 0.1,
            # Optional fields
            "ingredients": (
                "Leche entera pasteurizada, fermentos lácteos "
                "(Streptococcus thermophilus, Lactobacillus bulgaricus)"
            ),
            "allergens": "leche",
            "net_weight": "125 g",
            "manufacturer": "Danone S.A., Barcelona, España",
            "best_before": "Ver base del envase",
            "storage_conditions": "Conservar entre 2 °C y 8 °C",
            "country_of_origin": "España",
        },
    },
    {
        "name": "Galletas María",
        "brand": "Artiach",
        "description": "Galletas María clásicas, porción de 30 g",
        "regulatory_data": {
            # Mandatory EU 1169/2011 fields (values per 100 g)
            "energy_kj": 1768,
            "energy_kcal": 422,
            "fat_g": 9.8,
            "saturated_fat_g": 2.3,
            "carbohydrates_g": 68.5,
            "sugars_g": 16.7,
            "fiber_g": 1.9,
            "protein_g": 7.5,
            "salt_g": 0.6,
            # Optional — includes serving size for per-portion column
            "serving_size_g": 30,
            "allergens": "Gluten (trigo), huevo, leche, soja",
            "ingredients": (
                "Harina de trigo, azúcar, aceite de girasol, "
                "suero de leche en polvo, huevo entero, "
                "sal, aroma de vainilla"
            ),
            "net_weight": "200 g",
            "manufacturer": "Artiach S.L., Madrid, España",
            "best_before": "Ver parte inferior del envase",
            "storage_conditions": "Conservar en lugar fresco y seco",
            "country_of_origin": "España",
        },
    },
    {
        "name": "Leche Entera",
        "brand": "Industrias Lácteas Asturianas",
        "description": "Leche entera pasteurizada UHT",
        "regulatory_data": {
            # Mandatory EU 1169/2011 fields (values per 100 ml)
            "energy_kj": 276,
            "energy_kcal": 66,
            "fat_g": 3.6,
            "saturated_fat_g": 2.2,
            "carbohydrates_g": 4.7,
            "sugars_g": 4.7,
            "protein_g": 3.3,
            # Provides sodium_mg instead of salt_g — salt auto-calculated
            "sodium_mg": 40,
            # Optional fields
            "ingredients": "Leche entera pasteurizada",
            "allergens": "leche",
            "net_weight": "1 L",
            "manufacturer": "Industrias Lácteas Asturianas S.A., Asturias, España",
            "best_before": "Ver impresión en el envase",
            "storage_conditions": "Conservar a temperatura ambiente. Una vez abierto, conservar en nevera entre 2 °C y 8 °C y consumir en 3 días.",
            "country_of_origin": "España",
        },
    },
]


def login(session, base_url: str, username: str, password: str) -> str:
    """Login and return the JWT access token."""
    resp = session.post(
        f"{base_url}/api/v1/auth/login",
        data={"username": username, "password": password},
        timeout=15,
    )
    if resp.status_code != 200:
        print(f"ERROR: Login failed ({resp.status_code}): {resp.text}")
        sys.exit(1)
    token = resp.json().get("access_token")
    if not token:
        print(f"ERROR: No access_token in login response: {resp.text}")
        sys.exit(1)
    print(f"OK: Logged in as '{username}'")
    return token


def get_category_id(session, base_url: str, code: str = "nutrition_eu") -> str:
    """Fetch the ID of the category with the given code."""
    resp = session.get(f"{base_url}/api/v1/categories", timeout=15)
    if resp.status_code != 200:
        print(f"ERROR: GET /categories failed ({resp.status_code}): {resp.text}")
        sys.exit(1)

    data = resp.json()
    # Support both paginated {items:[...]} and plain list responses
    items = data.get("items") if isinstance(data, dict) else data
    if items is None:
        items = data if isinstance(data, list) else []

    for cat in items:
        if cat.get("code") == code:
            cat_id = cat["id"]
            print(f"OK: Found category '{code}' (id={cat_id})")
            return cat_id

    print(f"ERROR: Category '{code}' not found. Run seed_categories.py first.")
    sys.exit(1)


def create_product(session, base_url: str, category_id: str, product_def: dict) -> dict:
    """POST a product and return the created product dict."""
    payload = {
        "category_id": category_id,
        "name": product_def["name"],
        "brand": product_def.get("brand"),
        "description": product_def.get("description"),
        "regulatory_data": product_def["regulatory_data"],
    }

    resp = session.post(
        f"{base_url}/api/v1/products",
        json=payload,
        timeout=15,
    )

    if resp.status_code in (200, 201):
        created = resp.json()
        print(f"OK: Created product '{created['name']}' (id={created['id']})")
        return created
    elif resp.status_code == 409:
        # Already exists — not an error for idempotency
        print(f"INFO: Product '{product_def['name']}' already exists (409 Conflict). Skipping.")
        return {}
    else:
        print(f"WARN: Failed to create '{product_def['name']}' ({resp.status_code}): {resp.text}")
        return {}


def main() -> None:
    try:
        import requests
    except ImportError:
        print("ERROR: 'requests' is not installed. Run: pip install requests")
        sys.exit(1)

    session = requests.Session()

    print(f"Connecting to: {BASE_URL}")

    # 1. Login
    token = login(session, BASE_URL, ADMIN_USERNAME, ADMIN_PASSWORD)
    session.headers.update({"Authorization": f"Bearer {token}"})

    # 2. Get category ID
    category_id = get_category_id(session, BASE_URL, "nutrition_eu")

    # 3. Create products
    created_count = 0
    for product_def in TEST_PRODUCTS:
        result = create_product(session, BASE_URL, category_id, product_def)
        if result:
            created_count = created_count + 1

    print(f"\nDone. {created_count}/{len(TEST_PRODUCTS)} products created.")
    print(f"Login to the web UI at {BASE_URL}/ to view and manage them.")


if __name__ == "__main__":
    main()
