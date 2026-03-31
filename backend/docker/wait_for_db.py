import asyncio
import os

import asyncpg


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://roadcheck:roadcheck@db:5432/roadcheck",
)


async def wait_for_db() -> None:
    attempts = 60

    for attempt in range(1, attempts + 1):
        try:
            connection = await asyncpg.connect(DATABASE_URL)
            await connection.execute("SELECT 1")
            await connection.close()
            print("Database is ready.")
            return
        except Exception as error:  # pragma: no cover - used only in container startup
            print(f"Waiting for database ({attempt}/{attempts}): {error}")
            await asyncio.sleep(2)

    raise SystemExit("Database is not available after waiting.")


if __name__ == "__main__":
    asyncio.run(wait_for_db())
