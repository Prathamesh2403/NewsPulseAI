import asyncio
import os
import sys

# Add the project root to sys.path so we can import from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import engine, Base
from app.db.models import Article, CommunityComment, IngestionRun

async def async_recreate():
    print("Dropping all tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    print("Creating all tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    print("Done!")

if __name__ == "__main__":
    asyncio.run(async_recreate())
