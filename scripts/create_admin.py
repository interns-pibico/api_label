"""
Create an admin user.

Usage (from project root with venv active):
    python scripts/create_admin.py --email admin@example.com --username admin --password Secret123
"""

import argparse
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def create_admin(email: str, username: str, password: str, full_name: str) -> None:
    from sqlalchemy import select
    from src.db.session import AsyncSessionLocal
    from src.models.users import User
    from src.core.security import get_password_hash
    import uuid

    async with AsyncSessionLocal() as db:
        # Check existing
        existing_email = await db.execute(select(User).where(User.email == email))
        if existing_email.scalar_one_or_none():
            print(f"ERROR: User with email '{email}' already exists.")
            sys.exit(1)

        existing_username = await db.execute(select(User).where(User.username == username))
        if existing_username.scalar_one_or_none():
            print(f"ERROR: User with username '{username}' already exists.")
            sys.exit(1)

        user = User(
            id=uuid.uuid4(),
            email=email,
            username=username,
            hashed_password=get_password_hash(password),
            full_name=full_name,
            is_active=True,
            is_admin=True,
        )
        db.add(user)
        await db.commit()
        print(f"Admin user created: {username} <{email}> (id={user.id})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an admin user for api_label")
    parser.add_argument("--email", required=True, help="Admin email")
    parser.add_argument("--username", required=True, help="Admin username")
    parser.add_argument("--password", required=True, help="Admin password (min 8 chars)")
    parser.add_argument("--full-name", default="Admin", dest="full_name", help="Full name")
    args = parser.parse_args()

    asyncio.run(create_admin(args.email, args.username, args.password, args.full_name))


if __name__ == "__main__":
    main()
