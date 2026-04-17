"""
pages/home.py
Home dashboard - stats, quick actions, notifications
"""

import streamlit as st
from utils.auth import get_session_user, require_auth, refresh_session_user
from utils.db import (
    get_user_matches, get_unread_count, get_notifications,
    mark_notifications_read, get_unread_notification_count,
    get_profile_completion, update_last_seen
)


def render():
    require_auth()
    user = get_session_user()
    update_last_seen(user["id"])

    # Profile completion warning
    completion = get_profile_completion(user)
    if completion < 60:
        st.warning(
            f"⚠️ Your profile is only **{completion}% complete**. "
            "Complete it to get more matches! "
        )
        if st.button("Complete Profile →"):
            st.query_params["page"] = "profile"
            st.rerun()

    # Welcome header
    st.markdown(f"""
    <style>
    .home-hero {{
        background: linear-gradient(135deg, #FF6B6B 0%, #FF8E53 100%);
        border-radius: 20px;
        padding: 2rem;
        color: white;
        margin-bottom: 1.5rem;
        box-shadow: 0 8px 32px rgba(255,107,107,0.3);
    }}
    .home-hero h1 {{ margin: 0; font-size: 1.8rem; }}
    .home-hero p {{ margin: 0.5rem 0 0 0; opacity: 0.9; }}
    .stat-card {{
        background: white;
        border-radius: 16px;
        padding: 1.25rem;
        text-align: center;
        box-shadow: 0 4px 16px rgba(0,0,0,0.08);
        border-left: 4px solid #FF6B6B;
    }}
    .stat-number {{ font-size: 2rem; font-weight: 800; color: #FF6B6B; }}
    .stat-label {{ color: #888; font-size: 0.85rem; margin-top: 0.25rem; }}
    .notif-item {{
        padding: 0.75rem 1rem;
        border-radius: 12px;
        background: white;
        margin-bottom: 0.5rem;
        border-left: 3px solid #FF6B6B;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        font-size: 0.9rem;
    }}
    .notif-unread {{ background: #FFF8F8; }}
    .quick-action {{
        background: white;
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        cursor: pointer;
        box-shadow: 0 4px 16px rgba(0,0,0,0.08);
        transition: transform 0.2s;
    }}
    .quick-action:hover {{ transform: translateY(-4px); }}
    </style>
    <div class="home-hero">
        <h1>Hey {user.get('name','').split()[0] or 'there'} 👋</h1>
        <p>Ready to find your person today?</p>
    </div>
    """, unsafe_allow_html=True)

    # Stats row
    matches = get_user_matches(user["id"]) or []
    unread_msgs = get_unread_count(user["id"])

    col1, col2, col3, col4 = st.columns(4)
    stats = [
        (col1, len(matches), "💞 Matches"),
        (col2, unread_msgs, "💬 New Messages"),
        (col3, f"{completion}%", "📊 Profile"),
        (col4, "🔥", "Active Now"),
    ]
    for col, val, label in stats:
        with col:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">{val}</div>
                <div class="stat-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # Quick actions + notifications
    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.subheader("🚀 Quick Actions")
        action_cols = st.columns(2)
        actions = [
            ("action_discover", "🔥 Discover People", "discover"),
            ("action_matches", "💞 My Matches", "matches"),
            ("action_chat", "💬 Open Chat", "chat"),
            ("action_profile", "✏️ Edit Profile", "profile"),
        ]
        for i, (key, label, page) in enumerate(actions):
            with action_cols[i % 2]:
                if st.button(label, key=key, use_container_width=True,
                             type="primary" if i == 0 else "secondary"):
                    st.query_params["page"] = page
                    st.rerun()

        # Profile completion bar
        st.markdown(f"**Profile Completion: {completion}%**")
        st.progress(completion / 100)

    with col_right:
        st.subheader("🔔 Notifications")
        notifications = get_notifications(user["id"], limit=8)
        unread_count = get_unread_notification_count(user["id"])

        if unread_count > 0:
            if st.button(f"Mark all read ({unread_count})", key="mark_read"):
                mark_notifications_read(user["id"])
                st.rerun()

        if not notifications:
            st.info("No notifications yet. Start swiping! 🔥")
        else:
            for notif in notifications:
                cls = "notif-item notif-unread" if not notif.get("is_read") else "notif-item"
                st.markdown(f"""
                <div class="{cls}">
                    {notif.get('title', '')} <br>
                    <small style="color:#AAA">{notif.get('body', '')}</small>
                </div>
                """, unsafe_allow_html=True)

    # Recent matches preview
    if matches:
        st.markdown("---")
        st.subheader("💞 Recent Matches")
        cols = st.columns(min(4, len(matches)))
        for i, match in enumerate(matches[:4]):
            other = match["other_user"]
            with cols[i]:
                from components.profile_card import get_avatar_url
                img = get_avatar_url(other)
                st.image(img, width=80)
                st.caption(f"**{other.get('name','?')}**, {other.get('age','?')}")
                if st.button("Chat →", key=f"home_chat_{match['match_id']}", use_container_width=True):
                    st.session_state["active_match_id"] = match["match_id"]
                    st.session_state["active_match_user"] = other
                    st.query_params["page"] = "chat"
                    st.rerun()
