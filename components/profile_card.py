"""
components/profile_card.py
Reusable profile card for Discover, Matches, etc.
"""

import streamlit as st
from typing import Dict, Optional
from utils.db import get_distance_km
from utils.filters import format_distance
from utils.matching import get_compatibility_badge, get_common_interests, calculate_match_score


PLACEHOLDER_IMG = "https://ui-avatars.com/api/?background=FF6B6B&color=fff&size=300&bold=true&name="


def get_avatar_url(user: Dict) -> str:
    if user.get("photo_url"):
        return user["photo_url"]
    name = (user.get("name") or "U").replace(" ", "+")
    return PLACEHOLDER_IMG + name


def render_profile_card(
    profile: Dict,
    current_user: Optional[Dict] = None,
    show_actions: bool = False,
    compact: bool = False,
    show_match_score: bool = True,
) -> Optional[str]:
    """
    Render a profile card.
    Returns "like", "pass", or None based on button click.
    """
    img_url = get_avatar_url(profile)
    name = profile.get("name", "Unknown")
    age = profile.get("age", "?")
    bio = profile.get("bio", "")
    location = profile.get("location", "")
    interests = profile.get("interests") or []
    intent = profile.get("intent", "dating")
    gender = profile.get("gender", "")

    intent_icons = {"dating": "❤️", "friendship": "🤝", "networking": "💼"}
    intent_label = intent_icons.get(intent, "❤️")

    distance_str = ""
    score_badge = ""
    common = []

    if current_user:
        dist = get_distance_km(
            current_user.get("latitude"), current_user.get("longitude"),
            profile.get("latitude"), profile.get("longitude")
        )
        if dist is not None:
            distance_str = format_distance(dist)

        if show_match_score:
            score = calculate_match_score(current_user, profile)
            score_badge = get_compatibility_badge(score)
            common = get_common_interests(current_user, profile)

    # Card HTML
    interests_html = "".join(
        f'<span class="interest-tag">{i}</span>' for i in interests[:6]
    )
    common_html = "".join(
        f'<span class="common-tag">✓ {i}</span>' for i in common[:3]
    )

    padding = "1rem" if compact else "1.5rem"
    img_height = "200px" if compact else "280px"

    st.markdown(f"""
    <style>
    .profile-card {{
        background: #fff;
        border-radius: 20px;
        overflow: hidden;
        box-shadow: 0 8px 32px rgba(0,0,0,0.12);
        transition: transform 0.2s ease;
        margin-bottom: 1rem;
    }}
    .profile-card:hover {{ transform: translateY(-4px); }}
    .profile-img {{
        width: 100%;
        height: {img_height};
        object-fit: cover;
    }}
    .profile-body {{ padding: {padding}; }}
    .profile-name {{
        font-size: 1.4rem;
        font-weight: 700;
        color: #222;
        margin: 0;
    }}
    .profile-meta {{ color: #888; font-size: 0.9rem; margin: 0.3rem 0; }}
    .profile-bio {{ color: #555; font-size: 0.95rem; margin: 0.6rem 0; line-height: 1.5; }}
    .interest-tag {{
        display: inline-block;
        background: #FFF0F0;
        color: #FF6B6B;
        border: 1px solid #FFCCCC;
        border-radius: 20px;
        padding: 3px 10px;
        font-size: 0.78rem;
        margin: 2px;
    }}
    .common-tag {{
        display: inline-block;
        background: #F0FFF4;
        color: #22C55E;
        border: 1px solid #BBF7D0;
        border-radius: 20px;
        padding: 3px 10px;
        font-size: 0.78rem;
        margin: 2px;
    }}
    .score-badge {{
        display: inline-block;
        background: linear-gradient(135deg, #FF6B6B, #FF8E53);
        color: white;
        border-radius: 20px;
        padding: 3px 12px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }}
    </style>
    <div class="profile-card">
        <img class="profile-img" src="{img_url}" alt="{name}" onerror="this.src='{PLACEHOLDER_IMG}{name}'">
        <div class="profile-body">
            {"<div class='score-badge'>" + score_badge + "</div>" if score_badge else ""}
            <p class="profile-name">{name}, {age} {intent_label}</p>
            <p class="profile-meta">
                {f"📍 {location}" if location else ""}
                {f" · {distance_str}" if distance_str else ""}
                {f" · {gender.capitalize()}" if gender else ""}
            </p>
            {"<p class='profile-bio'>" + bio[:150] + ("..." if len(bio) > 150 else "") + "</p>" if bio else ""}
            <div style="margin: 0.5rem 0;">{interests_html}</div>
            {f"<div style='margin-top:0.3rem;'>{common_html}</div>" if common_html else ""}
        </div>
    </div>
    """, unsafe_allow_html=True)

    if show_actions:
        action = None
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button("❌ Pass", key=f"pass_{profile['id']}", use_container_width=True):
                action = "pass"
        with col2:
            if st.button("💖 Like", key=f"like_{profile['id']}", use_container_width=True, type="primary"):
                action = "like"
        with col3:
            if st.button("⚡ Super", key=f"super_{profile['id']}", use_container_width=True):
                action = "super"
        return action

    return None


def render_mini_card(profile: Dict, key_suffix: str = "") -> bool:
    """Tiny card for matches list. Returns True if clicked."""
    img_url = get_avatar_url(profile)
    name = profile.get("name", "?")
    age = profile.get("age", "")

    clicked = False
    col1, col2 = st.columns([1, 4])
    with col1:
        st.image(img_url, width=60)
    with col2:
        st.markdown(f"**{name}**, {age}")
        if st.button("Open Chat →", key=f"mini_{profile['id']}_{key_suffix}", use_container_width=True):
            clicked = True
    return clicked
