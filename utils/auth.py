"""
components/navbar.py
Top navigation bar for LinkUp
"""

import streamlit as st
from utils.auth import get_session_user, is_authenticated
from utils.db import get_unread_count, get_unread_notification_count


def render_navbar():
    """Render the top navigation bar."""
    user = get_session_user()
    if not user or not is_authenticated():
        return

    unread_msgs = get_unread_count(user["id"])
    unread_notifs = get_unread_notification_count(user["id"])
    msg_badge = f" ({unread_msgs})" if unread_msgs > 0 else ""
    notif_badge = f" ({unread_notifs})" if unread_notifs > 0 else ""

    current_page = st.query_params.get("page", "home")

    st.markdown("""
    <style>
    .navbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.75rem 1.5rem;
        background: linear-gradient(135deg, #FF6B6B, #FF8E53);
        border-radius: 0 0 16px 16px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 20px rgba(255,107,107,0.35);
    }
    .navbar-logo {
        font-size: 1.6rem;
        font-weight: 800;
        color: white;
        letter-spacing: -0.5px;
    }
    .navbar-logo span { color: #FFE4E4; }
    </style>
    <div class="navbar">
        <div class="navbar-logo">💘 Link<span>Up</span></div>
    </div>
    """, unsafe_allow_html=True)

    # Navigation tabs
    cols = st.columns(6)
    pages = [
        ("home", "🏠 Home"),
        ("discover", "🔥 Discover"),
        ("matches", "💞 Matches"),
        ("chat", f"💬 Chat{msg_badge}"),
        ("profile", "👤 Profile"),
        ("settings", "⚙️ Settings"),
    ]

    for col, (page_key, label) in zip(cols, pages):
        with col:
            is_active = current_page == page_key
            btn_style = "primary" if is_active else "secondary"
            if st.button(label, key=f"nav_{page_key}", use_container_width=True, type=btn_style):
                st.query_params["page"] = page_key
                st.rerun()

    st.markdown("<hr style='margin: 0.5rem 0; border-color: #FF6B6B33;'>", unsafe_allow_html=True)
