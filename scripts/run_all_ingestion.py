import asyncio
import os
import sys

# Add the project root to sys.path so we can import from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ingestion.pipeline import run_pipeline
from app.processing.indexer import index_articles
from app.ingestion.community_pipeline import run_community_pipeline
from app.core.logging import setup_logging

async def main():
    setup_logging()
    
    print("=========================================")
    print("1. RUNNING COMMUNITY PIPELINE")
    print("=========================================")
    try:
        new_comments_count = await run_community_pipeline()
        print(f"Finished community pipeline. Fetched {new_comments_count} new comments.")
    except Exception as e:
        print(f"Community pipeline failed: {e}")
        
    print("\n=========================================")
    print("2. RUNNING NEWS PIPELINE")
    print("=========================================")
    try:
        new_articles = await run_pipeline()
        print(f"Fetched {len(new_articles)} new articles")
        
        if new_articles:
            print("Indexing news articles (this takes a while due to AI processing)...")
            indexed_count = await index_articles(new_articles)
            print(f"Finished indexing {indexed_count} news articles")
    except Exception as e:
        print(f"News pipeline failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
