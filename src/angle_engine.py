import os
import json
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

ANGLE_PROMPT = """
Write three angle statements for a HOF story — one per youth segment.
Each must be one sentence max 15 words starting with "For you:".

Return ONLY valid JSON:
{"student": "For you: ...", "working": "For you: ...", "builder": "For you: ..."}
"""

def generate_angles(story: dict, frame: dict) -> dict:
    user_message = f"TITLE: {story.get('title','')}\nWHAT HAPPENED: {frame.get('what_happened','')[:300]}\nWHY IT MATTERS: {frame.get('why_it_matters','')[:200]}"
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": ANGLE_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.3,
            max_tokens=200,
        )
        raw = response.choices[0].message.content.strip().replace("```json","").replace("```","").strip()
        result = json.loads(raw)
        return {"angle_student": result.get("student",""), "angle_working": result.get("working",""), "angle_builder": result.get("builder","")}
    except Exception as e:
        print(f"[angle_engine] Error: {e}")
        return {"angle_student": "", "angle_working": "", "angle_builder": ""}
