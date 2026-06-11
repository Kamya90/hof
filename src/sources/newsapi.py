# src/sources/newsapi.py
import os
import requests
from dotenv import load_dotenv

load_dotenv()

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")
BASE_URL    = "https://newsapi.org/v2/everything"

HOF_QUERIES = [
    "india policy youth employment",
    "india parliament bill law",
    "india supreme court verdict",
    "india startup economy gig workers",
    "india education NEP student",
    "india SEBI RBI regulation",
    "india climate environment policy"
]

def fetch_from_newsapi() -> list[dict]:
    if not NEWSAPI_KEY:
        print("[newsapi] No API key found — skipping")
        return []

    stories   = []
    seen_urls = set()

    for query in HOF_QUERIES:
        try:
            response = requests.get(
                BASE_URL,
                params={
                    "q":        query,
                    "language": "en",
                    "sortBy":   "relevancy",
                    "pageSize": 10,
                    "apiKey":   NEWSAPI_KEY
                },
                timeout=10
            )
            data = response.json()

            for article in data.get("articles", []):
                url = article.get("url", "")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                stories.append({
                    "title":        article.get("title", ""),
                    "content":      article.get("content", "") or article.get("description", ""),
                    "url":          url,
                    "source":       article.get("source", {}).get("name", "NewsAPI"),
                    "published_at": article.get("publishedAt", ""),
                    "source_type":  "newsapi"
                })

        except Exception as e:
            print(f"[newsapi] Error fetching '{query}': {e}")
            continue

    print(f"[newsapi] Fetched {len(stories)} stories")
    return stories