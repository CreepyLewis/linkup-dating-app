"""
pages/matches.py
View all matches
"""

import streamlit as st
from utils.auth import get_session_user, require_auth
from utils.db import get_user_matches
from components.profile_card import get_avatar_url, render_mini_card


def render():
    require_auth()
    user = get_session_user()

    st.markdown("""
    <style>
    .matches-header {
        background: linear-gradient(135deg, #FF6B6B, #FF8E53);
        border-radius: 20px;
        padding: 1.5rem 2rem;
        color: white;
        margin-bottom: 1.5rem;
    }
    .matches-header h1 { margin: 0; }
    .match-card {
        background: white;
        border-radius: 16px;
        padding: 1rem;
        display: flex;
        align-items: center;
        gap: 1rem;
        margin-bottom: 0.75rem;
        box-shadow: 0 4px 16px rgba(0,0,0,0.08);
        transition: transform 0.15s;
        cursor: pointer;
    }
    .match-card:hover { transform: translateX(4px); }
    .match-avatar {
        width: 64px; height: 64px;
        border-radius: 50%;
        object-fit: cover;
        border: 3px solid #FF6B6B;
        flex-shrink: 0;
    }
    .match-info { flex: 1; }
    .match-name { font-weight: 700; font-size: 1.05rem; color: #222; }
    .match-meta { color: #888; font-size: 0.85rem; }
    .match-date { color: #CCC; font-size: 0.8rem; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="matches-header">
        <h1>💞 Your Matches</h1>
        <p style="margin:0; opacity:0.85;">People you connected with</p>
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("Loading matches..."):
        matches = get_user_matches(user["id"])

    if not matches:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("""
            <div style="text-align:center; padding: 3rem 0; color: #888;">
                <div style="font-size:4rem;">💘</div>
                <h3>No matches yet</h3>
                <p>Start swiping to find your match!</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button("🔥 Go to Discover", use_container_width=True, type="primary"):
                st.query_params["page"] = "discover"
                st.rerun()
        return

    st.subheader(f"You have {len(matches)} match{'es' if len(matches) != 1 else ''}! 🎉")

    # Search filter
    search = st.text_input("🔍 Search matches...", placeholder="Type a name...", label_visibility="collapsed")

    filtered = matches
    if search:
        filtered = [
            m for m in matches
            if search.lower() in (m["other_user"].get("name") or "").lower()
        ]

    for match in filtered:
        other = match["other_user"]
        img = get_avatar_url(other)
        name = other.get("name", "?")
        age = other.get("age", "")
        location = other.get("location", "")
        matched_at = match.get("matched_at", "")

        # Format date
        from components.chat_box import _format_time
        date_str = _format_time(matched_at) if matched_at else ""

        col1, col2 = st.columns([5, 1])
        with col1:
            st.markdown(f"""
            <div class="match-card">
                <img class="match-avatar" src="{img}" alt="{name}">
                <div class="match-info">
                    <div class="match-name">{name}, {age}</div>
                    <div class="match-meta">📍 {location or 'Location unknown'} · 🎨 {len([i for i in (other.get('interests') or []) if i in (user.get('interests') or [])])} shared interests</div>
                </div>
                <div class="match-date">Matched {date_str}</div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            if st.button("💬 Chat", key=f"chat_{match['match_id']}", use_container_width=True, type="primary"):
                st.session_state["active_match_id"] = match["match_id"]
                st.session_state["active_match_user"] = other
                st.query_params["page"] = "chat"
                st.rerun()

    st.markdown("---")
    if st.button("🔥 Discover More People", use_container_width=True):
        st.query_params["page"] = "discover"
        st.rerun()
