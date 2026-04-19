"""
components/profile_card.py
Profile card using native Streamlit widgets - no HTML rendering issues.
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
    Render a profile card using native Streamlit.
    Returns 'like', 'pass', 'super', or None.
    """
    img_url   = get_avatar_url(profile)
    name      = profile.get("name") or "Unknown"
    age       = profile.get("age") or "?"
    bio       = (profile.get("bio") or "").strip()
    location  = (profile.get("location") or "").strip()
    interests = profile.get("interests") or []
    gender    = (profile.get("gender") or "").capitalize()
    intent    = profile.get("intent") or "dating"

    intent_icons = {"dating": "❤️", "friendship": "🤝", "networking": "💼"}
    intent_icon  = intent_icons.get(intent, "❤️")

    # Distance & match score
    distance_str = ""
    score_badge  = ""
    common       = []
    if current_user:
        dist = get_distance_km(
            current_user.get("latitude"), current_user.get("longitude"),
            profile.get("latitude"),      profile.get("longitude"),
        )
        if dist is not None:
            distance_str = format_distance(dist)
        if show_match_score:
            score       = calculate_match_score(current_user, profile)
            score_badge = get_compatibility_badge(score)
            common      = get_common_interests(current_user, profile)

    # ── Card container ────────────────────────────────────────────────────
    with st.container(border=True):
        # Photo
        img_height = 200 if compact else 320
        st.markdown(
            f'<img src="{img_url}" style="width:100%;height:{img_height}px;'
            f'object-fit:cover;border-radius:12px;" '
            f'onerror="this.style.display=\'none\'">',
            unsafe_allow_html=True,
        )

        # Name + age + intent
        st.markdown(
            f"### {name}, {age} {intent_icon}"
        )

        # Meta line
        meta_parts = []
        if location:      meta_parts.append(f"📍 {location}")
        if distance_str:  meta_parts.append(distance_str)
        if gender:        meta_parts.append(gender)
        if meta_parts:
            st.caption("  ·  ".join(meta_parts))

        # Match score badge
        if score_badge:
            st.markdown(
                f'<span style="background:linear-gradient(135deg,#FF6B6B,#FF8E53);'
                f'color:white;border-radius:20px;padding:3px 12px;font-size:0.8rem;">'
                f'{score_badge}</span>',
                unsafe_allow_html=True,
            )

        # Bio
        if bio:
            st.write(bio[:200] + ("..." if len(bio) > 200 else ""))

        # Interests
        if interests:
            tags = "  ".join(
                f'<span style="background:#FFF0F0;color:#FF6B6B;border:1px solid #FFCCCC;'
                f'border-radius:20px;padding:2px 10px;font-size:0.78rem;margin:2px;">'
                f'{i}</span>'
                for i in interests[:8]
            )
            st.markdown(tags, unsafe_allow_html=True)

        # Common interests
        if common:
            c_tags = "  ".join(
                f'<span style="background:#F0FFF4;color:#22C55E;border:1px solid #BBF7D0;'
                f'border-radius:20px;padding:2px 10px;font-size:0.78rem;margin:2px;">'
                f'✓ {i}</span>'
                for i in common[:3]
            )
            st.markdown(c_tags, unsafe_allow_html=True)

        # Action buttons
        if show_actions:
            st.markdown("")
            c1, c2, c3 = st.columns(3)
            action = None
            pid = profile["id"]
            with c1:
                if st.button("❌  Pass",  key=f"pass_{pid}",  use_container_width=True):
                    action = "pass"
            with c2:
                if st.button("💖  Like",  key=f"like_{pid}",  use_container_width=True, type="primary"):
                    action = "like"
            with c3:
                if st.button("⚡  Super", key=f"super_{pid}", use_container_width=True):
                    action = "super"
            return action

    return None


def render_mini_card(profile: Dict, key_suffix: str = "") -> bool:
    """Small card for matches list."""
    c1, c2 = st.columns([1, 4])
    with c1:
        st.image(get_avatar_url(profile), width=60)
    with c2:
        name = profile.get("name") or "?"
        age  = profile.get("age") or ""
        st.markdown(f"**{name}**, {age}")
        if st.button("Open Chat →", key=f"mini_{profile['id']}_{key_suffix}", use_container_width=True):
            return True
    return False
