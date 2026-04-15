"""
utils/matching.py
Smart matching score + compatibility helpers
"""

from typing import Dict, List
from utils.db import get_distance_km


# ─── Core Match Score ─────────────────────────────────────────────────────────

def calculate_match_score(user_a: Dict, user_b: Dict) -> float:
    """
    Score = weighted sum of:
      - Shared interests     (40%)
      - Proximity            (30%)
      - Activity recency     (20%)
      - Completeness         (10%)
    Returns float 0.0 – 100.0
    """
    score = 0.0

    # 1. Shared interests (0–40)
    interests_a = set(user_a.get("interests") or [])
    interests_b = set(user_b.get("interests") or [])
    if interests_a or interests_b:
        shared = len(interests_a & interests_b)
        total = len(interests_a | interests_b)
        interest_score = (shared / total) * 40 if total > 0 else 0
    else:
        interest_score = 0
    score += interest_score

    # 2. Proximity (0–30)
    lat_a = user_a.get("latitude")
    lon_a = user_a.get("longitude")
    lat_b = user_b.get("latitude")
    lon_b = user_b.get("longitude")
    dist = get_distance_km(lat_a, lon_a, lat_b, lon_b)
    if dist is not None:
        if dist <= 5:
            prox_score = 30
        elif dist <= 20:
            prox_score = 20
        elif dist <= 50:
            prox_score = 10
        else:
            prox_score = max(0, 10 - (dist - 50) / 10)
    else:
        prox_score = 15  # unknown = neutral
    score += prox_score

    # 3. Activity recency (0–20)
    from datetime import datetime, timezone, timedelta
    last_seen_str = user_b.get("last_seen")
    if last_seen_str:
        try:
            last_seen = datetime.fromisoformat(last_seen_str.replace("Z", "+00:00"))
            delta = datetime.now(timezone.utc) - last_seen
            if delta <= timedelta(hours=1):
                score += 20
            elif delta <= timedelta(days=1):
                score += 15
            elif delta <= timedelta(days=7):
                score += 10
            elif delta <= timedelta(days=30):
                score += 5
        except Exception:
            score += 10

    # 4. Profile completeness (0–10)
    from utils.db import get_profile_completion
    completeness = get_profile_completion(user_b)
    score += (completeness / 100) * 10

    return round(min(score, 100), 1)


def rank_profiles(current_user: Dict, profiles: List[Dict]) -> List[Dict]:
    """Sort profiles by match score (descending). Boosted users come first."""
    for p in profiles:
        p["_match_score"] = calculate_match_score(current_user, p)

    # Boosted profiles go to top
    boosted = [p for p in profiles if p.get("is_boosted")]
    normal = [p for p in profiles if not p.get("is_boosted")]

    boosted.sort(key=lambda x: x["_match_score"], reverse=True)
    normal.sort(key=lambda x: x["_match_score"], reverse=True)

    return boosted + normal


def get_compatibility_badge(score: float) -> str:
    if score >= 80:
        return "🔥 Great Match"
    elif score >= 60:
        return "✨ Good Match"
    elif score >= 40:
        return "👍 Decent Match"
    else:
        return "🤷 Low Match"


def get_common_interests(user_a: Dict, user_b: Dict) -> List[str]:
    a = set(user_a.get("interests") or [])
    b = set(user_b.get("interests") or [])
    return sorted(a & b)
