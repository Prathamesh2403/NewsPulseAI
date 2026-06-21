"""
Topic classification module.

Assigns one category from a fixed taxonomy to each article using
keyword-based matching. This approach is fast, free, and requires
no external API calls.
"""

import logging

logger = logging.getLogger(__name__)

# Fixed taxonomy of article categories
CATEGORIES: list[str] = [
    "LLMs",
    "Hardware/Chips",
    "Robotics",
    "Startups/Funding",
    "Policy/Regulation",
    "Research",
    "Industry News",
    "Other",
]

# Keyword map: each category maps to a list of lowercase keywords/phrases
KEYWORD_MAP: dict[str, list[str]] = {
    "LLMs": [
        "llm",
        "large language model",
        "gpt",
        "chatgpt",
        "claude",
        "gemini",
        "transformer",
        "chatbot",
        "generative ai",
        "gen ai",
        "foundation model",
        "fine-tuning",
        "prompt",
        "rag",
        "retrieval augmented",
    ],
    "Hardware/Chips": [
        "gpu",
        "tpu",
        "chip",
        "nvidia",
        "amd",
        "intel",
        "semiconductor",
        "processor",
        "computing power",
        "data center",
        "quantum",
    ],
    "Robotics": [
        "robot",
        "robotics",
        "autonomous",
        "drone",
        "self-driving",
        "humanoid",
        "manipulation",
        "boston dynamics",
    ],
    "Startups/Funding": [
        "startup",
        "funding",
        "venture",
        "valuation",
        "acquisition",
        "ipo",
        "series a",
        "series b",
        "investment",
        "unicorn",
        "raised",
    ],
    "Policy/Regulation": [
        "regulation",
        "policy",
        "legislation",
        "ban",
        "govern",
        "eu ai act",
        "safety",
        "ethics",
        "bias",
        "deepfake",
        "copyright",
        "congress",
        "senate",
    ],
    "Research": [
        "research",
        "paper",
        "arxiv",
        "benchmark",
        "dataset",
        "algorithm",
        "neural network",
        "deep learning",
        "reinforcement learning",
        "computer vision",
        "nlp",
    ],
    "Industry News": [
        "google",
        "microsoft",
        "apple",
        "meta",
        "amazon",
        "openai",
        "anthropic",
        "partnership",
        "launch",
        "release",
        "update",
        "product",
    ],
}


def classify_article(title: str, content: str) -> str:
    """Classify an article into one of the predefined categories.

    Combines the title and content, lowercases them, and counts keyword
    matches for each category. The category with the highest match count
    wins. Defaults to 'Other' if no keywords match.

    Args:
        title: The article title.
        content: The article body text.

    Returns:
        A category string from the CATEGORIES list.
    """
    combined_text: str = f"{title} {content}".lower()

    category_scores: dict[str, int] = {}

    for category, keywords in KEYWORD_MAP.items():
        score: int = 0
        for keyword in keywords:
            score += combined_text.count(keyword)
        category_scores[category] = score

    # Find the category with the highest score
    best_category: str = "Other"
    best_score: int = 0

    for category, score in category_scores.items():
        if score > best_score:
            best_score = score
            best_category = category

    logger.debug(
        "Classified article '%s' as '%s' (score=%d)",
        title[:60],
        best_category,
        best_score,
    )

    return best_category
