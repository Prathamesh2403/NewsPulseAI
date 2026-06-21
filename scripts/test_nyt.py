import asyncio, sys, logging
sys.path.insert(0, '.')
logging.basicConfig(level=logging.INFO)
from app.ingestion.nyt_ingester import NYTIngester

async def test():
    ing = NYTIngester(sections=['technology', 'science'])
    articles = await ing.fetch()
    print(f'\nFetched {len(articles)} articles')
    for a in articles[:5]:
        sec = a.raw_metadata.get('section', '')
        print(f'  [{sec}] {a.title[:70]}')

asyncio.run(test())
