import asyncio
from sqlalchemy import select, delete, text
from app.db.session import async_session_factory
from app.db.models import Article

async def main():
    async with async_session_factory() as session:
        # PostgreSQL specific regex to count words
        # Count how many we are going to delete
        count_stmt = select(Article.id).where(text("array_length(regexp_split_to_array(trim(content), '\\s+'), 1) < 180"))
        result = await session.execute(count_stmt)
        ids_to_delete = result.scalars().all()
        
        print(f"Found {len(ids_to_delete)} articles with less than 180 words.")
        
        if ids_to_delete:
            delete_stmt = delete(Article).where(Article.id.in_(ids_to_delete))
            await session.execute(delete_stmt)
            await session.commit()
            print("Successfully deleted the articles.")

if __name__ == "__main__":
    asyncio.run(main())
