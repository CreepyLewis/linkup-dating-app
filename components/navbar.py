"""
components/navbar.py
Navbar with unread message badge, notification dot, active page highlight.
"""

import streamlit as st
from utils.auth import get_session_user, is_authenticated
from utils.db import get_unread_count, get_unread_notification_count


def render_navbar():
    user = get_session_user()
    if not user or not is_authenticated():
        return

    uid          = user["id"]
    unread_msgs  = get_unread_count(uid)
    unread_notif = get_unread_notification_count(uid)
    page         = st.query_params.get("page", "home")

    # Brand bar
    notif_dot = (
        f'<span style="display:inline-block;width:8px;height:8px;'
        f'border-radius:50%;background:#FF6B6B;margin-left:4px;vertical-align:middle;"></span>'
        if unread_notif > 0 else ""
    )
    st.markdown(f"""
    <div style="display:flex;align-items:center;justify-content:space-between;
         padding:0.75rem 1.5rem;
         background:linear-gradient(135deg,#FF6B6B,#FF8E53);
         border-radius:0 0 16px 16px;margin-bottom:1rem;
         box-shadow:0 4px 20px rgba(255,107,107,0.3);">
        <div style="font-size:1.5rem;font-weight:900;color:white;letter-spacing:-0.5px;">
            💘 LinkUp
        </div>
        <div style="color:white;font-size:0.85rem;opacity:0.9;">
            Hi, {user.get('name','').split()[0] or 'there'} {notif_dot}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Nav buttons
    pages = [
        ("home",     "🏠",  "Home"),
        ("discover", "🔥",  "Discover"),
        ("matches",  "💞",  "Matches"),
        ("chat",     "💬",  f"Chat {'🔴' if unread_msgs > 0 else ''}"),
        ("profile",  "👤",  "Profile"),
        ("settings", "⚙️", "Settings"),
    ]

    cols = st.columns(len(pages))
    for col, (key, icon, label) in zip(cols, pages):
        with col:
            is_active = page == key
            # Show unread count on chat
            display = label
            if key == "chat" and unread_msgs > 0:
                display = f"💬 {unread_msgs}"
            st.button(
                display,
                key=f"nav_{key}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
                on_click=_go, args=(key,),
            )

    st.markdown("<hr style='margin:0.4rem 0;opacity:0.15;'>", unsafe_allow_html=True)


def _go(page: str):
    st.query_params["page"] = page
