"""
app.py
LinkUp Dating App - Main Streamlit Entry Point
"""

import streamlit as st
from pathlib import Path
from dotenv import load_dotenv

# ── Load .env FIRST - before ANY other import ────────────────────────────────
load_dotenv()

# ── Page config (must be FIRST Streamlit call) ───────────────────────────────
st.set_page_config(
    page_title="LinkUp - Find Your Person",
    page_icon="💘",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        "Get Help": "mailto:support@linkup.app",
        "Report a bug": "mailto:bugs@linkup.app",
        "About": "💘 **LinkUp** - Find your person. Built with ❤️ in Nairobi.",
    },
)

# ── Load global CSS ──────────────────────────────────────────────────────────
css_path = Path(__file__).parent / "assets" / "styles.css"
if css_path.exists():
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ── Startup config check ─────────────────────────────────────────────────────
from utils.startup_check import show_setup_wizard
if not show_setup_wizard():
    st.stop()  # Don't proceed until config is complete


# ── Page routing ─────────────────────────────────────────────────────────────
# Uses st.session_state["current_page"] as the source of truth.
# st.query_params["page"] is synced on load and after navigation for bookmarkability.

VALID_PAGES = {
    "login", "register", "reset_password",
    "home", "discover", "matches", "chat",
    "profile", "settings", "events", "admin",
}

def get_current_page() -> str:
    """
    Determine the current page.
    Priority: session_state > query_params > default("login")
    """
    # If session_state already has a page, use it
    if "current_page" in st.session_state:
        return st.session_state["current_page"]

    # Otherwise bootstrap from query_params (e.g. direct URL visit / page refresh)
    qp = st.query_params.get("page", "login")
    page = qp if qp in VALID_PAGES else "login"
    st.session_state["current_page"] = page
    return page


def navigate(page: str):
    """Navigate to a page — update both session_state and query_params."""
    if page not in VALID_PAGES:
        page = "login"
    st.session_state["current_page"] = page
    st.query_params["page"] = page


def route():
    page = get_current_page()

    # Keep query_params in sync (handles browser back/forward edge cases)
    st.query_params["page"] = page

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

    # Protected pages (auth guard handled inside each page via require_auth)
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
        st.markdown("""
        <div style="text-align:center; padding:4rem; color:#888;">
            <div style="font-size:4rem;">😕</div>
            <h2>Page not found</h2>
            <p>The page you're looking for doesn't exist.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("← Go Home"):
            navigate("home")
            st.rerun()


# ── Initialise session defaults ───────────────────────────────────────────────
if "discover_index" not in st.session_state:
    st.session_state["discover_index"] = 0

# ── Run ───────────────────────────────────────────────────────────────────────
try:
    route()
except Exception as e:
    err = str(e)
    if "SUPABASE" in err or "supabase" in err.lower():
        st.error(f"⚠️ Database connection error: {err}")
        st.info("👆 Fix your `.env` file and restart the app.")
    elif "Cloudinary" in err or "cloudinary" in err.lower():
        st.error(f"⚠️ Image service error: {err}")
    elif "Name or service not known" in err:
        st.error(
            "⚠️ **Network Error:** Could not connect to the database.\n\n"
            "This usually means `SUPABASE_URL` in your `.env` file is wrong or missing.\n\n"
            f"Details: `{err}`"
        )
    else:
        st.exception(e)
