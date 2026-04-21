"""
pages/home.py
Mobile-first home dashboard.
"""

import streamlit as st
from utils.auth import get_session_user, require_auth
from utils.db import (
    get_user_matches, get_unread_count, get_notifications,
    mark_notifications_read, get_unread_notification_count,
    get_profile_completion, update_last_seen,
)


def render():
    require_auth()
    user = get_session_user()
    update_last_seen(user["id"])

    completion  = get_profile_completion(user)
    matches     = get_user_matches(user["id"]) or []
    unread_msgs = get_unread_count(user["id"])
    first_name  = (user.get("name") or "there").split()[0]

    # Profile nudge
    if completion < 60:
        st.warning(f"⚠️ Profile {completion}% complete — add more info to get matches!")
        if st.button("Complete Profile →", key="nudge_btn"):
            st.query_params["page"] = "profile"
            st.rerun()

    st.markdown(f"""
    <style>
    .hero {{
        background: linear-gradient(135deg,#FF6B6B,#FF8E53);
        border-radius: 20px; padding: 1.75rem 1.5rem;
        color: white; margin-bottom: 1.25rem;
        box-shadow: 0 8px 32px rgba(255,107,107,.25);
    }}
    .hero h2 {{ margin:0; font-size:1.6rem; font-weight:800; }}
    .hero p  {{ margin:.4rem 0 0; opacity:.9; font-size:.95rem; }}

    /* Stats grid — 4 cols desktop, 2x2 mobile */
    .stats-grid {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 12px;
        margin-bottom: 1.25rem;
    }}
    .stat-card {{
        background: white; border-radius: 14px;
        padding: 1rem 0.75rem; text-align: center;
        box-shadow: 0 3px 12px rgba(0,0,0,.07);
        border-top: 4px solid #FF6B6B;
    }}
    .stat-num  {{ font-size: 1.7rem; font-weight: 800; color: #FF6B6B; line-height:1.1; }}
    .stat-lbl  {{ color: #999; font-size: 0.76rem; margin-top: 4px; }}

    /* Action grid — 2x2 */
    .action-grid {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
        margin-bottom: 1.25rem;
    }}
    .action-card {{
        background: white; border-radius: 14px;
        padding: 1.1rem 0.75rem; text-align: center;
        box-shadow: 0 3px 12px rgba(0,0,0,.07);
        cursor: pointer; border: 1.5px solid #FFE4E4;
        transition: transform .15s ease;
        text-decoration: none;
    }}
    .action-card:hover {{ transform: translateY(-3px); border-color: #FF6B6B; }}
    .action-icon {{ font-size: 1.5rem; }}
    .action-lbl  {{ font-size: .82rem; font-weight: 600; color: #444; margin-top: 4px; }}

    /* Notification item */
    .notif {{
        padding: .65rem 1rem; border-radius: 10px;
        background: white; margin-bottom: .4rem;
        border-left: 3px solid #FF6B6B;
        box-shadow: 0 2px 8px rgba(0,0,0,.05);
        font-size: .88rem;
    }}
    .notif-new {{ background: #FFF8F8; }}

    /* Match row */
    .match-row {{
        display: flex; gap: 10px; overflow-x: auto;
        padding-bottom: 4px; scrollbar-width: none;
    }}
    .match-chip {{
        flex-shrink: 0; text-align: center;
        cursor: pointer; width: 72px;
    }}
    .match-chip img {{
        width: 60px; height: 60px; border-radius: 50%;
        object-fit: cover; border: 2.5px solid #FF6B6B;
        display: block; margin: 0 auto 4px;
    }}
    .match-chip span {{ font-size: .72rem; color: #555; font-weight: 600; }}

    /* Mobile overrides */
    @media (max-width: 640px) {{
        .stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
        .hero h2   {{ font-size: 1.35rem; }}
        .stat-num  {{ font-size: 1.4rem; }}
    }}
    </style>

    <div class="hero">
        <h2>Hey {first_name} 👋</h2>
        <p>Ready to find your person today?</p>
    </div>

    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-num">{len(matches)}</div>
            <div class="stat-lbl">💞 Matches</div>
        </div>
        <div class="stat-card">
            <div class="stat-num">{unread_msgs if unread_msgs > 0 else "—"}</div>
            <div class="stat-lbl">💬 Messages</div>
        </div>
        <div class="stat-card">
            <div class="stat-num">{completion}%</div>
            <div class="stat-lbl">📊 Profile</div>
        </div>
        <div class="stat-card">
            <div class="stat-num">🔥</div>
            <div class="stat-lbl">Active Now</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Profile completion bar
    if completion < 100:
        st.progress(completion / 100, text=f"Profile {completion}% complete")

    # ── Quick actions ──────────────────────────────────────────────────────────
    st.markdown("**Quick Actions**")
    a1, a2, a3, a4 = st.columns(4)
    for col, (icon, label, page, style) in zip(
        [a1, a2, a3, a4],
        [
            ("🔥", "Discover", "discover", "primary"),
            ("💞", "Matches",  "matches",  "secondary"),
            ("💬", "Chat",     "chat",     "secondary"),
            ("👤", "Profile",  "profile",  "secondary"),
        ],
    ):
        with col:
            if st.button(f"{icon}\n{label}", key=f"qa_{page}",
                         use_container_width=True, type=style):
                st.query_params["page"] = page
                st.rerun()

    # ── Recent matches ─────────────────────────────────────────────────────────
    if matches:
        st.markdown("---")
        st.markdown("**💞 Recent Matches**")
        from components.profile_card import get_avatar_url

        # Build horizontal scroll row in HTML
        chips = ""
        for m in matches[:8]:
            other = m["other_user"]
            img   = get_avatar_url(other)
            name  = (other.get("name") or "?").split()[0]
            chips += f"""
            <div class="match-chip">
                <img src="{img}" alt="{name}">
                <span>{name}</span>
            </div>"""

        st.markdown(f'<div class="match-row">{chips}</div>', unsafe_allow_html=True)

        # Chat buttons below
        for i, m in enumerate(matches[:4]):
            other = m["other_user"]
            name  = other.get("name") or "?"
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"**{name}**, {other.get('age','?')}")
            with c2:
                if st.button("Chat", key=f"hchat_{m['match_id']}", use_container_width=True):
                    st.session_state["active_match_id"]   = m["match_id"]
                    st.session_state["active_match_user"] = other
                    st.query_params["page"] = "chat"
                    st.rerun()

    # ── Notifications ──────────────────────────────────────────────────────────
    st.markdown("---")
    notifs      = get_notifications(user["id"], limit=6)
    notif_count = get_unread_notification_count(user["id"])

    hdr_c1, hdr_c2 = st.columns([3, 1])
    with hdr_c1:
        st.markdown("**🔔 Notifications**")
    with hdr_c2:
        if notif_count > 0:
            if st.button(f"Read all ({notif_count})", key="mark_all_read"):
                mark_notifications_read(user["id"])
                st.rerun()

    if not notifs:
        st.info("No notifications yet. Start swiping! 🔥")
    else:
        for n in notifs:
            cls = "notif notif-new" if not n.get("is_read") else "notif"
            st.markdown(f"""
            <div class="{cls}">
                {n.get('title','')}
                <br><small style="color:#AAA">{n.get('body','')}</small>
            </div>
            """, unsafe_allow_html=True)
