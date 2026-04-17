"""
pages/chat.py
Chat page - select a match conversation and chat
"""

import streamlit as st
from utils.auth import get_session_user, require_auth
from utils.db import get_user_matches, get_unread_count
from components.chat_box import render_chat_box
from components.profile_card import get_avatar_url


def render():
    require_auth()
    user = get_session_user()

    st.markdown("""
    <style>
    .chat-page-header {
        background: linear-gradient(135deg, #FF6B6B, #FF8E53);
        border-radius: 20px;
        padding: 1.25rem 1.5rem;
        color: white;
        margin-bottom: 1rem;
    }
    .match-list-item {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.75rem;
        border-radius: 12px;
        background: white;
        margin-bottom: 0.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        cursor: pointer;
        transition: background 0.15s;
    }
    .match-list-item:hover { background: #FFF8F8; }
    .match-list-item.active { border-left: 3px solid #FF6B6B; background: #FFF0F0; }
    .match-list-avatar {
        width: 48px; height: 48px;
        border-radius: 50%; object-fit: cover;
        border: 2px solid #FF6B6B;
    }
    .match-list-name { font-weight: 600; font-size: 0.95rem; color: #222; }
    .match-list-preview { font-size: 0.8rem; color: #888; }
    </style>
    <div class="chat-page-header">
        <h2 style="margin:0;">💬 Messages</h2>
    </div>
    """, unsafe_allow_html=True)

    matches = get_user_matches(user["id"])

    if not matches:
        st.markdown("""
        <div style="text-align:center; padding:3rem; color:#888;">
            <div style="font-size:3rem;">💬</div>
            <h3>No conversations yet</h3>
            <p>Match with someone to start chatting!</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🔥 Go Discover", type="primary", use_container_width=True):
            st.query_params["page"] = "discover"
            st.rerun()
        return

    # Get active match from session
    active_match_id = st.session_state.get("active_match_id")
    active_match_user = st.session_state.get("active_match_user")

    # If no active match, default to first
    if not active_match_id and matches:
        active_match_id = matches[0]["match_id"]
        active_match_user = matches[0]["other_user"]

    # Two-column layout: sidebar list + chat area
    col_list, col_chat = st.columns([1, 3])

    with col_list:
        st.markdown("**Conversations**")
        for match in matches:
            other = match["other_user"]
            img = get_avatar_url(other)
            is_active = match["match_id"] == active_match_id
            active_class = "active" if is_active else ""

            st.markdown(f"""
            <div class="match-list-item {active_class}">
                <img class="match-list-avatar" src="{img}" alt="{other.get('name','?')}">
                <div>
                    <div class="match-list-name">{other.get('name','?')}</div>
                    <div class="match-list-preview">{other.get('age','?')} • {other.get('location','') or '📍 Unknown'}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button(
                f"Open",
                key=f"open_chat_{match['match_id']}",
                use_container_width=True,
            ):
                st.session_state["active_match_id"] = match["match_id"]
                st.session_state["active_match_user"] = match["other_user"]
                st.rerun()

    with col_chat:
        if active_match_id and active_match_user:
            render_chat_box(active_match_id, user, active_match_user)
        else:
            st.markdown("""
            <div style="text-align:center; padding:3rem; color:#888;">
                <div style="font-size:3rem;">👈</div>
                <p>Select a conversation</p>
            </div>
            """, unsafe_allow_html=True)
