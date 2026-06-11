# src/scorer.py
from dataclasses import dataclass

KEYWORDS = {
    "youth_economic": [
        "jobs", "employment", "salary", "fees", "loan", "inflation", "gig",
        "startup", "internship", "wage", "cost of living", "student",
        "debt", "neet", "jee", "college", "placement", "fresher", "layoff",
        "hiring", "income", "emi", "rent", "unemployed", "unemployment",
        "graduate", "graduates", "youth", "young", "overestimated", "gdp",
        "economy", "economic", "economists", "report", "shoppers", "fake",
        "knockoff", "power", "electricity", "flyers", "flights", "seats",
        "adani", "government", "mandates", "pay", "excessive", "demographic",
        "dividend", "skills", "gap", "onsite", "opportunities", "wages",
        "minimum wage", "cost", "prices", "inflation", "recession"
    ],
    "power_shift": [
        "parliament", "supreme court", "policy", "regulation", "bill", "act",
        "government", "minister", "sebi", "rbi", "election", "amendment",
        "law", "constitution", "verdict", "arrested", "arrest",
        "police", "court", "judge", "order", "ban", "agrees", "mandates",
        "gov", "govt", "authority", "official", "agency", "probe", "cbi",
        "ed", "action", "scheme", "allocated", "fund", "budget", "relief",
        "modi", "congress", "bjp", "quota", "semiconductor", "policy",
        "dtaa", "tax", "conversion", "religious", "ministry", "commissioner",
        "high court", "tribunal", "ordinance", "notification", "circular"
    ],
    "opportunity": [
        "scholarship", "fellowship", "skilling", "training", "startup",
        "access", "nep", "free", "subsidy", "reservation", "admission",
        "seats", "relief", "mandate", "report", "reveals", "semiconductor",
        "investment", "delhi", "policy", "university", "campus", "course",
        "apprenticeship", "internship", "programme", "scheme", "portal"
    ],
    "long_term": [
        "decade", "future", "generation", "structural", "systemic", "reform",
        "2030", "2035", "climate", "demographic", "infrastructure", "landmark",
        "historic", "permanent", "overestimated", "annual", "boom", "trend",
        "pattern", "rise", "surge", "crisis", "collapse", "report", "reveals",
        "study", "survey", "data", "statistics", "percent", "%", "dividend",
        "skills gap", "jobs gap", "long term", "years", "decade", "century"
    ],
    "debate_tension": [
        "controversy", "debate", "divided", "protest", "backlash", "criticism",
        "opposition", "argue", "dispute", "conflict", "vs", "versus",
        "disagree", "challenge", "reject", "oppose", "slams", "tension",
        "religious", "conversion", "quota", "rights", "violated", "accused",
        "defended", "condemned", "welcomed", "rejected", "demanded",
        "warned", "alleged", "claimed", "denied", "questioned", "exposed"
    ],
    "youth_specific": [
        "youth", "student", "young", "teen", "gen z", "millennial", "campus",
        "graduate", "graduates", "fresher", "college", "university", "school",
        "unemployed", "india", "indian", "delhi", "mumbai", "bangalore",
        "hyderabad", "chennai", "pune", "first job", "entry level",
        "new graduate", "class of", "batch of"
    ]
}

WEIGHTS = {
    "youth_economic": 1.5,
    "power_shift":    1.2,
    "opportunity":    1.0,
    "long_term":      1.8,
    "debate_tension": 2.0,
    "youth_specific": 1.6
}

MAX_POSSIBLE = 10 * sum(WEIGHTS.values())

# Personal posts that have zero systemic angle — drop immediately
# Keep this list tight — only add things you are 100% sure are never
# going to appear in a legitimate systemic story
PERSONAL_SIGNALS = [
    "advise on my", "advice on my", "i need advice on my",
    "please help me with my", "what should i do about my",
    "am i wrong to", "aita", "feeling lost about",
    "my boyfriend left", "my girlfriend left",
    "marriage scam", "failed marriage advice",
    "pro bono legal help", "pro bono lawyer",
    "destroy your career", "not the place to be",
    "moved to singapore as", "honest assessment af",
    "my manager switched", "my world has turned",
    "is jtp worth", "they are offering", "year bond",
    "3 year bond", "yen salary", "worth joining"
]

# Systemic signals — personal cases that reveal broken systems score higher
SYSTEMIC_SIGNALS = [
    "policy", "law", "court", "government", "system", "rule",
    "regulation", "rights", "constitutional", "amendment", "bill",
    "scheme", "ministry", "authority", "institution", "structural",
    "nationwide", "crore", "lakh people", "millions", "majority",
    "pattern", "data shows", "report", "study", "survey",
    "across india", "every year", "annually", "consistently",
    "labour law", "labour code", "workers", "employees", "employers",
    "precedent", "policy change", "systemic", "widespread", "endemic"
]


@dataclass
class ScoreResult:
    total:          float
    breakdown:      dict
    verdict:        str
    weighted_total: float


def score_story(story: dict) -> ScoreResult:
    text = (story.get("title", "") + " " + story.get("content", "")).lower()

    # Drop purely personal posts with no systemic angle
    if any(signal in text for signal in PERSONAL_SIGNALS):
        return ScoreResult(
            total=0.0,
            breakdown={},
            verdict="DROP",
            weighted_total=0.0
        )

    # Score across all dimensions
    breakdown      = {}
    weighted_total = 0.0

    for dimension, keywords in KEYWORDS.items():
        hits      = sum(1 for kw in keywords if kw in text)
        raw_score = min(hits * 2, 10)
        weighted  = raw_score * WEIGHTS[dimension]
        breakdown[dimension] = raw_score
        weighted_total += weighted

    # Apply systemic boost
    # Personal cases that reveal broken systems score higher
    # Pure policy stories score highest because they hit both
    systemic_hits  = sum(1 for s in SYSTEMIC_SIGNALS if s in text)
    if systemic_hits >= 3:
        systemic_boost = 1.4
    elif systemic_hits >= 1:
        systemic_boost = 1.15
    else:
        systemic_boost = 1.0

    normalized = (weighted_total / MAX_POSSIBLE) * 50 * systemic_boost

    if normalized >= 8:
        verdict = "PASS"
    elif normalized >= 5:
        verdict = "REVIEW"
    else:
        verdict = "DROP"

    return ScoreResult(
        total=round(normalized, 1),
        breakdown=breakdown,
        verdict=verdict,
        weighted_total=round(weighted_total, 2)
    )


def score_batch(stories: list[dict]) -> list[dict]:
    results = []
    for story in stories:
        score = score_story(story)
        if score.verdict != "DROP":
            results.append({
                **story,
                "score":           score.total,
                "score_breakdown": score.breakdown,
                "verdict":         score.verdict
            })
    results.sort(key=lambda x: x["score"], reverse=True)
    return results