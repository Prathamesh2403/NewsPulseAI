import asyncio
from sqlalchemy import text
from app.db.session import async_session_factory

async def check():
    async with async_session_factory() as session:
        result = await session.execute(text("SELECT source, COUNT(id) FROM articles GROUP BY source"))
        for row in result:
            print(f"{row[0]}: {row[1]}")

asyncio.run(check())
