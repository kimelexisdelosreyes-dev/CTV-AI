import asyncio
import getpass

from sqlalchemy import select

from app.core.security import hash_password
from app.db.models.user import User, UserRole
from app.db.session import AsyncSessionLocal


async def main() -> None:
    email = input("Administrator email: ").strip().lower()
    full_name = input("Administrator full name: ").strip()
    password = getpass.getpass("Administrator password: ")
    confirm = getpass.getpass("Confirm password: ")

    if not email or not full_name or not password:
        raise SystemExit("All fields are required.")

    if password != confirm:
        raise SystemExit("Passwords do not match.")

    if len(password) < 12:
        raise SystemExit("Use a password with at least 12 characters.")

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            raise SystemExit("A user with that email already exists.")

        session.add(
            User(
                email=email,
                full_name=full_name,
                password_hash=hash_password(password),
                role=UserRole.admin,
                is_active=True,
            )
        )
        await session.commit()

    print("Administrator created successfully.")


if __name__ == "__main__":
    asyncio.run(main())
