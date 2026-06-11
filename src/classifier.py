import os
import json
from dotenv import load_dotenv
#from groq import Groq

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

CLASSIFIER_PROMPT = """
You are a news classifier for HOF, a debate platform for Indians aged 16-25.
Decide if a story is worth debating publicly.

SYSTEMIC: affects many people, reveals a flaw in Indian society/economy/law/politics, could spark genuine two-sided debate.
PERSONAL: one person's situation, asking for advice, rant, meme, or joke.

Reply with exactly one word: SYSTEMIC or PERSONAL
"""

def is_systemic(story: dict) -> bool:
    title = story.get("title", "")
    content = story.get("content", "")[:300]
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": CLASSIFIER_PROMPT},
                {"role": "user", "content": f"TITLE: {title}\nCONTENT: {content}"}
            ],
            temperature=0.0,
            max_tokens=5,
        )
        return response.choices[0].message.content.strip().upper() == "SYSTEMIC"
    except Exception as e:
        print(f"[classifier] Error: {e}")
        return True

def classify_batch(stories: list[dict]) -> list[dict]:
    systemic = []
    for story in stories:
        if is_systemic(story):
            systemic.append(story)
        else:
            print(f"[classifier] DROPPED: {story.get('title', '')[:60]}")
    print(f"[classifier] {len(systemic)} systemic of {len(stories)} total")
    return systemic
