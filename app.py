"""
app.py - LinkUp Dating App entry point
"""

import streamlit as st
from pathlib import Path
from dotenv import load_dotenv

# Load .env BEFORE any other import
load_dotenv()

# Also pull from Streamlit Cloud secrets if available
try:
    import os
    for k, v in st.secrets.items():
        if isinstance(v, str):
            os.environ.setdefault(k, v)
except Exception:
    pass

st.set_page_config(
    page_title="LinkUp - Find Your Person",
    page_icon="💘",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        "Get Help": "mailto:support@linkup.app",
        "About": "💘 LinkUp - Find your person. Built in Nairobi.",
    },
)

# Load global CSS
css_path = Path(__file__).parent / "assets" / "styles.css"
if css_path.exists():
    st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)

# PWA meta tags + hide Streamlit chrome
st.markdown("""
<link rel="manifest" href="/app/static/manifest.json">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="LinkUp">
<meta name="theme-color" content="#FF6B6B">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<style>
#MainMenu{visibility:hidden}
header[data-testid="stHeader"]{display:none!important}
footer{display:none!important}
[data-testid="stToolbar"]{display:none!important}
[data-testid="stDecoration"]{display:none!important}
.stDeployButton{display:none!important}
</style>
""", unsafe_allow_html=True)

# Startup config check
from utils.startup_check import show_setup_wizard
if not show_setup_wizard():
    st.stop()


def route():
    page = st.query_params.get("page", "login")

    if page == "login":
        from pages.login import render
        render()
    elif page == "register":
        from pages.register import render
        render()
    elif page == "reset_password":
        from pages.reset_password import render
        render()
    else:
        # All protected pages get navbar
        from components.navbar import render_navbar
        render_navbar()

        if page == "home":
            from pages.home import render
            render()
        elif page == "discover":
            from pages.discover import render
            render()
        elif page == "matches":
            from pages.matches import render
            render()
        elif page == "chat":
            from pages.chat import render
            render()
        elif page == "profile":
            from pages.profile import render
            render()
        elif page == "settings":
            from pages.settings import render
            render()
        elif page == "events":
            from pages.events import render
            render()
        elif page == "admin":
            from pages.admin import render
            render()
        else:
            st.error("Page not found.")
            if st.button("Go Home"):
                st.query_params["page"] = "home"
                st.rerun()


if "discover_index" not in st.session_state:
    st.session_state["discover_index"] = 0

try:
    route()
except Exception as e:
    err = str(e)
    if "SUPABASE" in err.upper() or "supabase" in err.lower():
        st.error(f"Database error: {err}")
        st.info("Check your .env file has the correct SUPABASE_URL and SUPABASE_ANON_KEY.")
    elif "not found" in err.lower() and "table" in err.lower():
        st.error("Database tables missing. Run `database/schema.sql` in Supabase SQL Editor.")
    else:
        st.exception(e)
