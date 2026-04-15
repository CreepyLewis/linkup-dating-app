"""
app.py
LinkUp Dating App — Main Streamlit Entry Point
"""

import streamlit as st
from pathlib import Path

# ── Page config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="LinkUp — Find Your Person",
    page_icon="💘",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        "Get Help": "mailto:support@linkup.app",
        "Report a bug": "mailto:bugs@linkup.app",
        "About": "💘 **LinkUp** — Find your person. Built with ❤️ in Nairobi.",
    },
)

# ── Load global CSS ──────────────────────────────────────────────────────────
css_path = Path(__file__).parent / "assets" / "styles.css"
if css_path.exists():
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ── Router ───────────────────────────────────────────────────────────────────
def route():
    page = st.query_params.get("page", "login")

    # Public pages (no auth required)
    if page == "login":
        from pages.login import render
        render()

    elif page == "register":
        from pages.register import render
        render()

    elif page == "reset_password":
        from pages.reset_password import render
        render()

    # Protected pages (auth required — handled inside each page)
    elif page == "home":
        from components.navbar import render_navbar
        render_navbar()
        from pages.home import render
        render()

    elif page == "discover":
        from components.navbar import render_navbar
        render_navbar()
        from pages.discover import render
        render()

    elif page == "matches":
        from components.navbar import render_navbar
        render_navbar()
        from pages.matches import render
        render()

    elif page == "chat":
        from components.navbar import render_navbar
        render_navbar()
        from pages.chat import render
        render()

    elif page == "profile":
        from components.navbar import render_navbar
        render_navbar()
        from pages.profile import render
        render()

    elif page == "settings":
        from components.navbar import render_navbar
        render_navbar()
        from pages.settings import render
        render()

    elif page == "events":
        from components.navbar import render_navbar
        render_navbar()
        from pages.events import render
        render()

    elif page == "admin":
        from components.navbar import render_navbar
        render_navbar()
        from pages.admin import render
        render()

    else:
        # 404 fallback
        st.markdown("""
        <div style="text-align:center; padding:4rem; color:#888;">
            <div style="font-size:4rem;">😕</div>
            <h2>Page not found</h2>
            <p>The page you're looking for doesn't exist.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("← Go Home"):
            st.query_params["page"] = "home"
            st.rerun()


# ── Initialise session defaults ───────────────────────────────────────────────
if "discover_index" not in st.session_state:
    st.session_state["discover_index"] = 0


# ── Run ───────────────────────────────────────────────────────────────────────
route()
