"""
pages/chat.py
One conversation at a time. Left = received, Right = sent.
"""

import streamlit as st
from utils.auth import get_session_user, require_auth
from utils.db import get_user_matches
from components.chat_box import render_chat_box
from components.profile_card import get_avatar_url


def render():
    require_auth()
    user = get_session_user()

    st.markdown("""
    <style>
    .chat-header {
        background: linear-gradient(135deg,#FF6B6B,#FF8E53);
        border-radius:16px; padding:1rem 1.5rem;
        color:white; margin-bottom:1rem;
    }
    .conv-item {
        display:flex; align-items:center; gap:10px;
        padding:10px 12px; border-radius:10px;
        background:white; margin-bottom:6px;
        border:1px solid #EEE; cursor:pointer;
    }
    .conv-item.active { border-left:4px solid #FF6B6B; background:#FFF5F5; }
    .conv-avatar { width:44px;height:44px;border-radius:50%;object-fit:cover;border:2px solid #FF6B6B;flex-shrink:0; }
    .conv-name { font-weight:600;font-size:0.9rem;color:#222; }
    .conv-sub  { font-size:0.75rem;color:#999; }
    </style>
    <div class="chat-header"><h3 style="margin:0">💬 Messages</h3></div>
    """, unsafe_allow_html=True)

    matches = get_user_matches(user["id"])

    if not matches:
        st.info("No matches yet. Go discover someone! 🔥")
        if st.button("Go Discover", type="primary"):
            st.query_params["page"] = "discover"
            st.rerun()
        return

    # Default to first match if nothing selected
    if "active_match_id" not in st.session_state:
        st.session_state["active_match_id"]   = matches[0]["match_id"]
        st.session_state["active_match_user"] = matches[0]["other_user"]

    active_id = st.session_state["active_match_id"]

    # ── Layout: contact list left | chat right ────────────────────────────────
    col_list, col_chat = st.columns([1, 3])

    with col_list:
        st.markdown("**Chats**")
        for m in matches:
            other     = m["other_user"]
            mid       = m["match_id"]
            is_active = mid == active_id
            img       = get_avatar_url(other)
            name      = other.get("name") or "?"
            age       = other.get("age") or ""
            loc       = other.get("location") or ""

            # Highlight active conversation
            active_cls = "active" if is_active else ""
            st.markdown(f"""
            <div class="conv-item {active_cls}">
                <img class="conv-avatar" src="{img}">
                <div>
                    <div class="conv-name">{name}{f', {age}' if age else ''}</div>
                    <div class="conv-sub">{loc or 'Tap to chat'}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # One button per match — clicking switches conversation
            btn_label = "▶ Open" if not is_active else "✓ Open"
            if st.button(btn_label, key=f"sel_{mid}", use_container_width=True,
                         type="primary" if is_active else "secondary"):
                # Only switch if it's a different match
                if mid != active_id:
                    st.session_state["active_match_id"]   = mid
                    st.session_state["active_match_user"] = other
                    st.rerun()

    with col_chat:
        active_user = st.session_state.get("active_match_user")
        if active_id and active_user:
            render_chat_box(active_id, user, active_user)
        else:
            st.markdown("<div style='text-align:center;padding:3rem;color:#AAA;'>Select a chat</div>",
                        unsafe_allow_html=True)
