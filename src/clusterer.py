import os
import json
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

CLUSTER_PROMPT = """
You are an editor at HOF. Group news stories about the SAME underlying issue.
Only group if genuinely the same issue. Min 2 per cluster. Max 4 per cluster.

Return ONLY valid JSON:
{
  "clusters": [
    {"theme": "one sharp sentence describing the debate", "story_indices": [0, 2]}
  ],
  "standalone": [1, 3, 4]
}
"""

def cluster_stories(stories: list[dict]) -> list[dict]:
    if len(stories) <= 2:
        return stories
    story_list = [{"index": i, "title": s.get("title", "")} for i, s in enumerate(stories)]
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": CLUSTER_PROMPT},
                {"role": "user", "content": json.dumps(story_list, indent=2)}
            ],
            temperature=0.0,
            max_tokens=800,
        )
        raw = response.choices[0].message.content.strip().replace("```json","").replace("```","").strip()
        result = json.loads(raw)
        output = []
        for cluster in result.get("clusters", []):
            indices = cluster.get("story_indices", [])
            theme = cluster.get("theme", "")
            if not indices:
                continue
            cluster_list = [stories[i] for i in indices if i < len(stories)]
            base = max(cluster_list, key=lambda s: s.get("score", 0))
            output.append({
                **base,
                "title": theme,
                "content": " | ".join(s.get("title","") for s in cluster_list) + " | " + base.get("content",""),
                "source": "Multiple Sources",
                "is_cluster": True,
                "cluster_stories": [s.get("title","") for s in cluster_list],
                "score": max(s.get("score",0) for s in cluster_list)
            })
            print(f"[clusterer] Clustered {len(indices)} -> '{theme[:60]}'")
        for i in result.get("standalone", []):
            if i < len(stories):
                output.append(stories[i])
        output.sort(key=lambda s: s.get("score",0), reverse=True)
        print(f"[clusterer] {len(stories)} -> {len(output)} debates")
        return output
    except Exception as e:
        print(f"[clusterer] Error: {e} — passing through unchanged")
        return stories
