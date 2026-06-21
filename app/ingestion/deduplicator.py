"""
Article deduplication using exact URL match and fuzzy title matching.

Two-phase approach:
1. Exact URL deduplication within the batch
2. Fuzzy title matching using rapidfuzz to catch near-duplicate stories
   covered by multiple sources
"""

import logging

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Article
from app.schemas.article import RawArticle

logger = logging.getLogger(__name__)

# Fuzzy matching threshold (0-100). 85 catches near-duplicates
# across sources while avoiding false positives.
FUZZY_THRESHOLD = 85


def deduplicate_batch(articles: list[RawArticle]) -> list[RawArticle]:
    """Remove duplicates within a single ingestion batch.

    Phase 1: Exact URL deduplication.
    Phase 2: Fuzzy title matching (token_sort_ratio >= threshold).

    Args:
        articles: List of normalized articles from all ingesters.

    Returns:
        Deduplicated list of articles.
    """
    if not articles:
        return []

    # Phase 1: exact URL dedup
    seen_urls: set[str] = set()
    url_deduped: list[RawArticle] = []
    for article in articles:
        normalized_url = article.url.strip().rstrip("/")
        if normalized_url not in seen_urls:
            seen_urls.add(normalized_url)
            url_deduped.append(article)

    removed_url = len(articles) - len(url_deduped)
    if removed_url:
        logger.info("URL dedup removed %d duplicates", removed_url)

    # Phase 2: fuzzy title dedup
    final: list[RawArticle] = []
    for article in url_deduped:
        is_duplicate = False
        for kept in final:
            ratio = fuzz.token_sort_ratio(article.title, kept.title)
            if ratio >= FUZZY_THRESHOLD:
                is_duplicate = True
                logger.debug(
                    "Fuzzy duplicate (%.0f%%): '%s' ≈ '%s'",
                    ratio,
                    article.title[:60],
                    kept.title[:60],
                )
                break
        if not is_duplicate:
            final.append(article)

    removed_fuzzy = len(url_deduped) - len(final)
    if removed_fuzzy:
        logger.info("Fuzzy title dedup removed %d duplicates", removed_fuzzy)

    logger.info(
        "Deduplication: %d → %d articles (removed %d)",
        len(articles),
        len(final),
        len(articles) - len(final),
    )
    return final


async def filter_existing_urls(
    articles: list[RawArticle], session: AsyncSession
) -> list[RawArticle]:
    """Filter out articles whose URLs already exist in the database.

    Args:
        articles: List of candidate articles.
        session: Active async database session.

    Returns:
        Only articles with URLs not already in the database.
    """
    if not articles:
        return []

    urls = [a.url.strip().rstrip("/") for a in articles]

    result = await session.execute(
        select(Article.url).where(Article.url.in_(urls))
    )
    existing_urls = {row[0].strip().rstrip("/") for row in result.fetchall()}

    new_articles = [
        a for a in articles if a.url.strip().rstrip("/") not in existing_urls
    ]

    filtered_count = len(articles) - len(new_articles)
    if filtered_count:
        logger.info(
            "Filtered %d articles already in database", filtered_count
        )

    return new_articles
