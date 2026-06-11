# src/controversy.py
# Layer 4: Controversy Detector
#
# Logic: fetch multiple sources covering the same story,
# compare their sentiment. If they diverge → real debate exists.
# Divergence score multiplies the relevance score.
#
# Sentiment scoring is simple: count positive vs negative signal words.
# No ML needed at this stage.

import requests
import os
from collections import Counter

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")

# Signal word lists for basic sentiment
POSITIVE_SIGNALS = [
    "welcomed", "praised", "approved", "celebrated", "landmark",
    "historic", "positive", "benefit", "progress", "success",
    "growth", "reform", "milestone", "achievement", "strengthen"
]

NEGATIVE_SIGNALS = [
    "criticized", "condemned", "rejected", "protested", "slammed",
    "opposed", "backlash", "failure", "concern", "threat", "danger",
    "controversial", "disputed", "challenged", "unconstitutional", "flawed"
]


def get_sentiment_score(text: str) -> float:
    """
    Returns a sentiment score from -1 (very negative) to +1 (very positive).
    Simple signal-word count — no ML.
    """
    text_lower = text.lower()
    pos = sum(1 for w in POSITIVE_SIGNALS if w in text_lower)
    neg = sum(1 for w in NEGATIVE_SIGNALS if w in text_lower)
    total = pos + neg
    if total == 0:
        return 0.0
    return (pos - neg) / total


def fetch_related_articles(story: dict, max_articles: int = 5) -> list[dict]:
    """
    Fetch other articles covering the same story from NewsAPI.
    Uses the first 5 significant words of the title as the query.
    """
    if not NEWSAPI_KEY:
        return []

    # Build query from title keywords (skip common stop words)
    stop_words = {"the", "a", "an", "is", "are", "was", "were", "in", "of",
                  "to", "for", "and", "or", "but", "on", "at", "by", "with"}
    words = story.get("title", "").lower().split()
    keywords = [w for w in words if w not in stop_words and len(w) > 3]
    query = " ".join(keywords[:5])

    try:
        response = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": query,
                "language": "en",
                "sortBy": "relevancy",
                "pageSize": max_articles,
                "apiKey": NEWSAPI_KEY
            },
            timeout=10
        )
        data = response.json()
        return data.get("articles", [])

    except Exception as e:
        print(f"[controversy] NewsAPI error: {e}")
        return []


def detect_controversy(story: dict) -> float:
    """
    Returns a controversy multiplier (0.0 to 5.0).
    Higher = more divergent coverage = more debate potential.

    How it works:
    1. Fetch related articles from other sources
    2. Score each article's sentiment
    3. Calculate the variance of sentiment scores
    4. High variance = sources disagree = real controversy
    """
    articles = fetch_related_articles(story)

    if len(articles) < 2:
        # Not enough coverage to measure divergence
        # Return a neutral score
        return 1.0

    # Score sentiment of each article
    sentiments = []
    for article in articles:
        text = (article.get("title", "") + " " + (article.get("description") or ""))
        score = get_sentiment_score(text)
        sentiments.append(score)

    if not sentiments:
        return 1.0

    # Calculate standard deviation of sentiments
    # High std dev = sources disagree = controversy
    mean = sum(sentiments) / len(sentiments)
    variance = sum((s - mean) ** 2 for s in sentiments) / len(sentiments)
    std_dev = variance ** 0.5

    # Map std_dev (0–1) to multiplier (1.0–5.0)
    # std_dev of 0 = full consensus = multiplier 1.0
    # std_dev of 1 = maximum divergence = multiplier 5.0
    multiplier = 1.0 + (std_dev * 4.0)
    return round(min(multiplier, 5.0), 2)
