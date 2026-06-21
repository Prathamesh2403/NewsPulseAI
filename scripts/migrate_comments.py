import asyncio
from sqlalchemy import text
from app.db.session import async_session_factory

async def migrate():
    async with async_session_factory() as session:
        # Rename table
        await session.execute(text("ALTER TABLE IF EXISTS reddit_comments RENAME TO community_comments"))
        # Rename column reddit_post_id -> source_post_id
        await session.execute(text("ALTER TABLE community_comments RENAME COLUMN reddit_post_id TO source_post_id"))
        # Add source column
        await session.execute(text("ALTER TABLE community_comments ADD COLUMN IF NOT EXISTS source VARCHAR(50) NOT NULL DEFAULT 'reddit'"))
        # Add hn_story_id to articles
        await session.execute(text("ALTER TABLE articles ADD COLUMN IF NOT EXISTS hn_story_id VARCHAR(128)"))
        await session.commit()
        print("Migration complete!")

asyncio.run(migrate())
