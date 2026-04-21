"""
components/navbar.py
Mobile-first navbar:
- Desktop: logo bar + horizontal nav buttons
- Mobile: logo bar + icon-only bottom bar (fixed)
Hides ALL Streamlit chrome.
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
    page         = st.query_params.get("page", "home")
    first_name   = (user.get("name") or "there").split()[0]

    # ── Hide every piece of Streamlit chrome ──────────────────────────────────
    st.markdown("""
    <style>
    #MainMenu,
    header[data-testid="stHeader"],
    footer,
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    .stDeployButton,
    [class*="viewerBadge"],
    [data-testid="manage-app-button"],
    iframe[title="streamlit_analytics"] { display: none !important; }

    /* Remove top gap Streamlit normally reserves for header */
    .block-container { padding-top: 0 !important; margin-top: 0 !important; }
    .main > div:first-child { padding-top: 0 !important; }

    /* ── Top brand bar ─────────────────────────────────── */
    .lu-topbar {
        display: flex; align-items: center;
        justify-content: space-between;
        padding: 0.7rem 1.25rem;
        background: linear-gradient(135deg,#FF6B6B,#FF8E53);
        box-shadow: 0 3px 16px rgba(255,107,107,.28);
        margin-bottom: 0.5rem;
    }
    .lu-logo {
        font-size: 1.35rem; font-weight: 900;
        color: white; letter-spacing: -0.5px;
        white-space: nowrap;
    }
    .lu-hi {
        color: white; font-size: 0.82rem; opacity:.92;
        white-space: nowrap; font-weight: 500;
    }

    /* ── Desktop nav (≥ 641px): tab row ───────────────── */
    .lu-desknav {
        display: flex; gap: 6px;
        padding: 0 0.5rem 0.75rem;
        overflow-x: auto; scrollbar-width: none;
    }
    .lu-desknav::-webkit-scrollbar { display: none; }
    .lu-navbtn {
        flex: 1; min-width: 80px;
        padding: 0.45rem 0.5rem;
        border-radius: 10px; border: 1.5px solid #EEE;
        background: white; cursor: pointer;
        font-size: 0.8rem; font-weight: 600; color: #555;
        text-align: center; white-space: nowrap;
        transition: all .15s ease;
    }
    .lu-navbtn.active {
        background: #FF6B6B; color: white; border-color: #FF6B6B;
    }
    .lu-navbtn:hover:not(.active) { border-color: #FF6B6B; color: #FF6B6B; }

    /* ── Mobile nav (≤ 640px): fixed bottom bar ────────── */
    @media (max-width: 640px) {
        .lu-desknav { display: none !important; }

        /* Give page content breathing room above the bottom bar */
        .block-container { padding-bottom: 80px !important; }

        .lu-bottomnav {
            position: fixed; bottom: 0; left: 0; right: 0;
            background: white;
            border-top: 1px solid #EEE;
            display: flex; justify-content: space-around;
            align-items: center;
            padding: 6px 4px 10px;
            z-index: 9999;
            box-shadow: 0 -4px 20px rgba(0,0,0,.08);
        }
        .lu-bnbtn {
            display: flex; flex-direction: column; align-items: center;
            flex: 1; padding: 4px 2px; cursor: pointer;
            border: none; background: transparent;
            font-size: 1.35rem; line-height: 1;
            color: #AAA; transition: color .15s ease;
        }
        .lu-bnbtn span {
            font-size: 0.58rem; font-weight: 600; margin-top: 2px;
            text-transform: uppercase; letter-spacing: 0.3px;
        }
        .lu-bnbtn.active { color: #FF6B6B; }
        .lu-badge {
            position: relative; display: inline-block;
        }
        .lu-badge::after {
            content: attr(data-count);
            position: absolute; top: -4px; right: -6px;
            background: #FF6B6B; color: white;
            font-size: 0.55rem; font-weight: 700;
            border-radius: 20px; padding: 1px 4px;
            min-width: 14px; text-align: center;
            display: var(--badge-display, none);
        }
    }
    @media (min-width: 641px) {
        .lu-bottomnav { display: none !important; }
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Top brand bar ──────────────────────────────────────────────────────────
    unread_dot = f'<span style="width:8px;height:8px;border-radius:50%;background:white;display:inline-block;margin-left:5px;opacity:.9;vertical-align:middle;"></span>' if unread_msgs > 0 else ""
    st.markdown(f"""
    <div class="lu-topbar">
        <div class="lu-logo">💘 LinkUp</div>
        <div class="lu-hi">Hi, {first_name} {unread_dot}</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Desktop nav row ────────────────────────────────────────────────────────
    pages = [
        ("home",     "🏠 Home"),
        ("discover", "🔥 Discover"),
        ("matches",  "💞 Matches"),
        ("chat",     f"💬 Chat {f'({unread_msgs})' if unread_msgs > 0 else ''}"),
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

    # ── Mobile bottom nav (HTML — buttons use JS to navigate) ─────────────────
    badge_style = "--badge-display: flex;" if unread_msgs > 0 else "--badge-display: none;"
    mobile_nav_items = [
        ("home",     "🏠", "Home"),
        ("discover", "🔥", "Discover"),
        ("matches",  "💞", "Matches"),
        ("chat",     "💬", f"Chat" if unread_msgs == 0 else f"Chat"),
        ("profile",  "👤", "Profile"),
        ("settings", "⚙️", "More"),
    ]

    btns_html = ""
    for key, icon, lbl in mobile_nav_items:
        active_cls = "active" if page == key else ""
        badge_html = f'<span class="lu-badge" data-count="{unread_msgs}" style="{badge_style if key=="chat" else ""}">{icon}</span>' if key == "chat" else icon
        btns_html += f"""
        <button class="lu-bnbtn {active_cls}"
                onclick="window.parent.postMessage({{type:'streamlit:setComponentValue',key:'{key}'}}, '*');
                         window.location.href=window.location.pathname+'?page={key}'">
            {badge_html}
            <span>{lbl}</span>
        </button>"""

    st.markdown(f'<div class="lu-bottomnav">{btns_html}</div>', unsafe_allow_html=True)
    st.markdown("<hr style='margin:0.3rem 0 0.7rem;opacity:0.1;'>", unsafe_allow_html=True)


def _go(page: str):
    st.query_params["page"] = page
