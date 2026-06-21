"""
Trend analysis prompt template.

Instructs the LLM to interpret aggregate statistics about news
coverage and surface notable patterns.
"""

TREND_SYSTEM_PROMPT: str = (
    "You are an AI/tech news analyst. Based on the following statistics "
    "about recent news coverage, provide a brief analysis of trends and "
    "notable patterns."
)

TREND_USER_TEMPLATE: str = (
    "Statistics:\n{stats}\n\n"
    "Provide a 2-3 sentence interpretation of these trends:"
)
