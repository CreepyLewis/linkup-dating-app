"""
utils/matching.py
Match score as a real percentage + compatibility quiz helpers.
"""

from typing import Dict, List
from utils.db import get_distance_km
from datetime import datetime, timezone, timedelta


QUIZ_QUESTIONS = [
    {
        "id": "schedule",
        "q":  "Are you a morning or night person?",
        "options": ["Morning bird 🌅", "Night owl 🦉", "Depends on the day"],
    },
    {
        "id": "social",
        "q":  "Your ideal weekend is...",
        "options": ["Out exploring 🌍", "Home relaxing 🏠", "Mix of both"],
    },
    {
        "id": "ambition",
        "q":  "Career vs personal life?",
        "options": ["Career first 💼", "Life first 🌸", "Balance both ⚖️"],
    },
    {
        "id": "kids",
        "q":  "Do you want kids someday?",
        "options": ["Yes 👶", "No", "Maybe / not sure"],
    },
    {
        "id": "exercise",
        "q":  "How active are you?",
        "options": ["Very active 🏃", "Somewhat active 🚶", "Not really 🛋️"],
    },
]


def calculate_match_score(user_a: Dict, user_b: Dict) -> float:
    """
    Returns match percentage 0–100.
    Weights: interests 35%, proximity 25%, activity 20%, quiz 15%, completeness 5%
    """
    score = 0.0

    # 1. Shared interests (0–35)
    ia = set(user_a.get("interests") or [])
    ib = set(user_b.get("interests") or [])
    if ia or ib:
        shared = len(ia & ib)
        total  = len(ia | ib)
        score += (shared / total) * 35 if total else 0
    else:
        score += 10  # neutral

    # 2. Proximity (0–25)
    dist = get_distance_km(
        user_a.get("latitude"), user_a.get("longitude"),
        user_b.get("latitude"), user_b.get("longitude"),
    )
    if dist is None:
        score += 12
    elif dist <= 5:   score += 25
    elif dist <= 20:  score += 20
    elif dist <= 50:  score += 14
    elif dist <= 100: score += 8
    else:             score += 3

    # 3. Activity recency (0–20)
    ls = user_b.get("last_seen") or ""
    try:
        dt    = datetime.fromisoformat(ls.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - dt
        if   delta < timedelta(hours=1):   score += 20
        elif delta < timedelta(days=1):    score += 15
        elif delta < timedelta(days=7):    score += 8
        elif delta < timedelta(days=30):   score += 3
    except Exception:
        score += 10

    # 4. Compatibility quiz (0–15)
    qa = user_a.get("quiz_answers") or {}
    qb = user_b.get("quiz_answers") or {}
    if qa and qb:
        common_qs = set(qa.keys()) & set(qb.keys())
        if common_qs:
            matches = sum(1 for k in common_qs if qa[k] == qb[k])
            score  += (matches / len(common_qs)) * 15

    # 5. Profile completeness (0–5)
    fields = ["name","age","bio","photo_url","interests","location"]
    filled = sum(1 for f in fields if user_b.get(f))
    score += (filled / len(fields)) * 5

    return round(min(score, 100), 1)


def get_match_label(pct: float) -> tuple:
    """Returns (emoji_label, colour) for a given percentage."""
    if pct >= 85: return ("🔥 Hot match",   "#FF6B6B")
    if pct >= 70: return ("✨ Great match",  "#FF8E53")
    if pct >= 55: return ("👍 Good match",   "#F59E0B")
    if pct >= 40: return ("🙂 Decent match", "#6B7280")
    return           ("🤷 Low match",        "#9CA3AF")


def get_compatibility_badge(score: float) -> str:
    label, _ = get_match_label(score)
    return label


def get_common_interests(user_a: Dict, user_b: Dict) -> List[str]:
    a = set(user_a.get("interests") or [])
    b = set(user_b.get("interests") or [])
    return sorted(a & b)


def rank_profiles(current_user: Dict, profiles: List[Dict]) -> List[Dict]:
    """Sort by score descending; boosted users float to top."""
    for p in profiles:
        p["_score"] = calculate_match_score(current_user, p)
    boosted = sorted([p for p in profiles if p.get("is_boosted")],  key=lambda x: x["_score"], reverse=True)
    normal  = sorted([p for p in profiles if not p.get("is_boosted")], key=lambda x: x["_score"], reverse=True)
    return boosted + normal
