import os
import json
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

DEBATE_SCORE_PROMPT = """
Rate how genuinely controversial this story is for Indians aged 16-25 on a scale of 1-10.
1-3: Clear consensus. 4-6: Some disagreement. 7-9: Genuine controversy. 10: Deep fault line.

Return ONLY valid JSON:
{"debate_score": 8, "reason": "One sentence explaining the score"}
"""

def score_debate(story: dict, frame: dict) -> dict:
    user_message = f"TITLE: {story.get('title','')}\nCORE TENSION: {frame.get('core_tension','')}\nSIDE A: {frame.get('side_a','')[:200]}\nSIDE B: {frame.get('side_b','')[:200]}"
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": DEBATE_SCORE_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.0,
            max_tokens=100,
        )
        raw = response.choices[0].message.content.strip().replace("```json","").replace("```","").strip()
        result = json.loads(raw)
        return {"debate_score": int(result.get("debate_score", 5)), "debate_reason": result.get("reason","")}
    except Exception as e:
        print(f"[debate_scorer] Error: {e}")
        return {"debate_score": 5, "debate_reason": ""}
