import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.security import hash_password
from app.db.database import AsyncSessionLocal
from app.db.models import Role, User


SEED_USERS = [
    {"email": "user@roadcheck.ru",  "password": "user1234",  "role": Role.user},
    {"email": "pro@roadcheck.ru",   "password": "pro1234",   "role": Role.pro},
    {"email": "admin@roadcheck.ru", "password": "admin1234", "role": Role.admin},
]


async def seed():
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select

        for data in SEED_USERS:
            existing = await db.execute(select(User).where(User.email == data["email"]))
            if existing.scalar_one_or_none():
                print(f"[skip]  {data['email']} уже существует")
                continue

            user = User(
                email=data["email"],
                hashed_password=hash_password(data["password"]),
                role=data["role"],
            )
            db.add(user)
            print(f"[create] {data['role'].value:5s}  {data['email']}  /  {data['password']}")

        await db.commit()
    print("done")


if __name__ == "__main__":
    asyncio.run(seed())
