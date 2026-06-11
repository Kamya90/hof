import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SUMMARISER_PROMPT = """Write ONE sharp sentence max 20 words that makes a 19-year-old want to read this story. No preamble. No quotes. Just the sentence."""

IMPACT_PROMPT = """Write ONE concrete sentence max 25 words about how this story affects a young Indian personally in 1-3 years. Must use "you" or "your". Must be specific. No quotes."""

def generate_summary(story: dict, frame: dict) -> str:
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SUMMARISER_PROMPT},
                {"role": "user", "content": f"TITLE: {story.get('title','')}\nCORE TENSION: {frame.get('core_tension','')}\nWHY IT MATTERS: {frame.get('why_it_matters','')[:300]}"}
            ],
            temperature=0.4, max_tokens=60,
        )
        return response.choices[0].message.content.strip().strip('"')
    except Exception as e:
        print(f"[summariser] Error: {e}")
        return frame.get("what_happened","")[:120]

def generate_impact(story: dict, frame: dict) -> str:
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": IMPACT_PROMPT},
                {"role": "user", "content": f"TITLE: {story.get('title','')}\nWHY YOU: {frame.get('why_you','')[:300]}\nOPEN QUESTION: {frame.get('open_question','')}"}
            ],
            temperature=0.3, max_tokens=80,
        )
        return response.choices[0].message.content.strip().strip('"')
    except Exception as e:
        print(f"[impact] Error: {e}")
        return frame.get("open_question","")

def generate_summary_and_impact(story: dict, frame: dict) -> dict:
    return {"hook": generate_summary(story, frame), "impact": generate_impact(story, frame)}
