import asyncio
import sys
sys.path.insert(0, '.')
from app.db.session import async_session_factory
from sqlalchemy import text

async def main():
    async with async_session_factory() as session:
        r = await session.execute(text("SELECT COUNT(*) FROM articles WHERE source = 'reddit' AND comments IS NOT NULL AND jsonb_array_length(comments::jsonb) > 0"))
        print(f"Reddit articles with comments: {r.scalar()}")
        
        r2 = await session.execute(text("SELECT COUNT(*) FROM articles WHERE source = 'reddit'"))
        print(f"Total Reddit articles: {r2.scalar()}")

asyncio.run(main())
