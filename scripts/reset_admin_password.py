"""
Reset password for an existing admin user.

Usage (from project root with venv active):
    python scripts/reset_admin_password.py --username admin --password NewSecret123
"""

import argparse
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def reset_password(username: str, password: str) -> None:
    if len(password) < 8:
        print("ERROR: Password must be at least 8 characters.")
        sys.exit(1)

    from sqlalchemy import select
    from src.db.session import AsyncSessionLocal
    from src.models.users import User
    from src.core.security import get_password_hash

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()

        if not user:
            print(f"ERROR: User '{username}' not found.")
            sys.exit(1)

        user.hashed_password = get_password_hash(password)
        await db.commit()
        print(f"Password updated for user '{username}' <{user.email}>")


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset admin password for api_label")
    parser.add_argument("--username", required=True, help="Username to reset")
    parser.add_argument("--password", required=True, help="New password (min 8 chars)")
    args = parser.parse_args()

    asyncio.run(reset_password(args.username, args.password))


if __name__ == "__main__":
    main()
