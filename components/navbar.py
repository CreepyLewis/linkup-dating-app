"""
components/navbar.py
Clean navbar - no Streamlit toolbar, full-width logo, mobile responsive.
"""

import streamlit as st
from utils.auth import get_session_user, is_authenticated
from utils.db import get_unread_count, get_unread_notification_count


def render_navbar():
    user = get_session_user()
    if not user or not is_authenticated():
        return

    uid           = user["id"]
    unread_msgs   = get_unread_count(uid)
    unread_notif  = get_unread_notification_count(uid)
    page          = st.query_params.get("page", "home")
    first_name    = (user.get("name") or "there").split()[0]
    notif_dot     = '<span style="width:8px;height:8px;border-radius:50%;background:#fff;display:inline-block;margin-left:4px;vertical-align:middle;opacity:0.9;"></span>' if unread_notif > 0 else ""

    st.markdown("""
    <style>
    /* ── Hide ALL Streamlit chrome ───────────────────────── */
    #MainMenu { visibility: hidden; }
    header[data-testid="stHeader"] { display: none !important; }
    footer { display: none !important; }
    [data-testid="stToolbar"] { display: none !important; }
    [data-testid="stDecoration"] { display: none !important; }
    [data-testid="stStatusWidget"] { display: none !important; }
    .viewerBadge_container__1QSob { display: none !important; }
    .stDeployButton { display: none !important; }

    /* ── Remove top padding Streamlit adds ───────────────── */
    .block-container {
        padding-top: 0.5rem !important;
    }

    /* ── Navbar ──────────────────────────────────────────── */
    .lu-nav {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.8rem 1.5rem;
        background: linear-gradient(135deg, #FF6B6B, #FF8E53);
        border-radius: 0 0 20px 20px;
        margin-bottom: 0.75rem;
        box-shadow: 0 4px 24px rgba(255,107,107,0.3);
        width: 100%;
    }
    .lu-logo {
        font-size: 1.5rem;
        font-weight: 900;
        color: white;
        letter-spacing: -0.5px;
        white-space: nowrap;
    }
    .lu-greeting {
        color: white;
        font-size: 0.85rem;
        opacity: 0.92;
        white-space: nowrap;
    }

    /* ── Nav buttons ──────────────────────────────────────── */
    div[data-testid="stHorizontalBlock"] button {
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 0.82rem !important;
    }

    /* ── Mobile: stack nav 2 rows ─────────────────────────── */
    @media (max-width: 640px) {
        .lu-logo { font-size: 1.2rem; }
        .lu-greeting { font-size: 0.75rem; }
        div[data-testid="stHorizontalBlock"] button {
            font-size: 0.7rem !important;
            padding: 0.3rem 0.2rem !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

    # Brand bar — full width, no gap
    st.markdown(f"""
    <div class="lu-nav">
        <div class="lu-logo">💘 LinkUp</div>
        <div class="lu-greeting">Hi, {first_name} {notif_dot}</div>
    </div>
    """, unsafe_allow_html=True)

    # Nav tabs
    pages = [
        ("home",     "🏠 Home"),
        ("discover", "🔥 Discover"),
        ("matches",  "💞 Matches"),
        ("chat",     f"💬 {unread_msgs}" if unread_msgs > 0 else "💬 Chat"),
        ("profile",  "👤 Profile"),
        ("settings", "⚙️ Settings"),
    ]

    cols = st.columns(len(pages))
    for col, (key, label) in zip(cols, pages):
        with col:
            st.button(
                label,
                key=f"nav_{key}",
                use_container_width=True,
                type="primary" if page == key else "secondary",
                on_click=_go, args=(key,),
            )

    st.markdown("<hr style='margin:0.4rem 0 0.8rem;opacity:0.12;border-color:#FF6B6B;'>",
                unsafe_allow_html=True)


def _go(page: str):
    st.query_params["page"] = page
