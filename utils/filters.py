"""
utils/filters.py
Filter helpers for the Discover page
"""

from typing import Dict, List


INTERESTS_LIST = [
    "Music 🎵", "Travel ✈️", "Fitness 💪", "Cooking 🍳", "Art 🎨",
    "Movies 🎬", "Books 📚", "Gaming 🎮", "Photography 📸", "Dancing 💃",
    "Hiking 🥾", "Tech 💻", "Fashion 👗", "Sports ⚽", "Coffee ☕",
    "Yoga 🧘", "Animals 🐾", "Entrepreneurship 💼", "Comedy 😂", "Nature 🌿",
    "Foodie 🍜", "Nightlife 🎉", "Volunteering 🤝", "Languages 🌍",
    "Cars 🚗", "Crypto 💰", "Design 🖌️", "Health & Wellness 🧠",
]

GENDER_OPTIONS = ["any", "male", "female", "non-binary", "other"]
INTENT_OPTIONS = {
    "dating": "❤️ Dating",
    "friendship": "🤝 Friendship",
    "networking": "💼 Networking",
}


def apply_filters(profiles: List[Dict], filters: Dict) -> List[Dict]:
    """Client-side filter pass after DB query."""
    result = profiles

    # Keyword search on name / bio
    keyword = filters.get("keyword", "").strip().lower()
    if keyword:
        result = [
            p for p in result
            if keyword in (p.get("name") or "").lower()
            or keyword in (p.get("bio") or "").lower()
        ]

    # Has photo
    if filters.get("has_photo"):
        result = [p for p in result if p.get("photo_url")]

    # Verified (future feature placeholder)
    if filters.get("verified_only"):
        result = [p for p in result if p.get("is_verified")]

    return result


def format_distance(km: float) -> str:
    if km is None:
        return "Unknown distance"
    if km < 1:
        return "< 1 km away"
    return f"{int(km)} km away"


def format_age(age) -> str:
    return f"{age} years old" if age else "Age unknown"
