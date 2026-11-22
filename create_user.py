"""Create a local account: python create_user.py USERNAME (password is hidden)."""
import asyncio
import getpass
import sys

from sqlalchemy.exc import IntegrityError

from auth import hash_password
from db import Base, SessionLocal, engine
from models import User


async def main() -> None:
    """Create one user without exposing their password in command history."""
    if len(sys.argv) != 2 or not sys.argv[1].strip():
        raise SystemExit("Usage: python create_user.py USERNAME")
    password = getpass.getpass("Password (at least 12 characters): ")
    if len(password) < 12:
        raise SystemExit("Password must have at least 12 characters")
    if password != getpass.getpass("Confirm password: "):
        raise SystemExit("Passwords do not match")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with SessionLocal() as session:
        session.add(User(username=sys.argv[1].strip(), password_hash=hash_password(password)))
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            raise SystemExit("That username already exists")
    await engine.dispose()
    print("User created.")


if __name__ == "__main__":
    asyncio.run(main())
