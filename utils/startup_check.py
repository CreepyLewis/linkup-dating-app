"""
utils/startup_check.py
Validates environment variables and connections at app startup.
Works with both .env (local) and Streamlit Cloud secrets.
Shows a friendly setup wizard if configuration is missing.
"""

import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()


def _get(key: str) -> str:
    """Get config value from Streamlit secrets (cloud) or .env (local)."""
    # Try Streamlit secrets first (Streamlit Cloud deployment)
    try:
        val = st.secrets.get(key, "")
        if val:
            os.environ[key] = val  # make available via os.getenv too
            return str(val)
    except Exception:
        pass
    return os.getenv(key, "")


def check_env() -> dict:
    """Return {key: (is_ok: bool, display: str)} for required config."""
    supabase_url  = _get("SUPABASE_URL")
    supabase_key  = _get("SUPABASE_ANON_KEY")
    cld_name      = _get("CLOUDINARY_CLOUD_NAME")
    cld_key       = _get("CLOUDINARY_API_KEY")

    def _ok(v, bad_substrings=("your-", "PASTE_")):
        return bool(v) and not any(s in v for s in bad_substrings) and len(v) > 5

    def _preview(v, max_len=30):
        if not v: return "(not set)"
        return v[:max_len] + "..." if len(v) > max_len else v

    return {
        "SUPABASE_URL":         (_ok(supabase_url),  _preview(supabase_url)),
        "SUPABASE_ANON_KEY":    (_ok(supabase_key),  _preview(supabase_key)),
        "CLOUDINARY_CLOUD_NAME":(_ok(cld_name, ("your-cloud",)), _preview(cld_name)),
        "CLOUDINARY_API_KEY":   (_ok(cld_key,  ("your-api",)),   _preview(cld_key)),
    }


def show_setup_wizard() -> bool:
    """
    Returns True (proceed) if all required config is set.
    Returns False and shows wizard if anything is missing.
    """
    checks = check_env()
    all_ok = all(ok for ok, _ in checks.values())
    if all_ok:
        return True

    # ── Wizard UI ────────────────────────────────────────────────────────────
    st.markdown("""
    <style>
    .setup-hero {
        background: linear-gradient(135deg, #FF6B6B, #FF8E53);
        border-radius: 20px;
        padding: 2rem;
        color: white;
        text-align: center;
        margin-bottom: 1.5rem;
        box-shadow: 0 8px 32px rgba(255,107,107,.25);
    }
    .setup-hero h1 { margin:0; font-size:2rem; }
    .setup-hero p  { margin:.4rem 0 0; opacity:.88; }
    .cfg-row {
        display:flex; align-items:center; justify-content:space-between;
        padding:.7rem 1rem; border-radius:10px; margin-bottom:.45rem; font-size:.9rem;
    }
    .cfg-ok  { background:#F0FFF4; border-left:4px solid #22C55E; }
    .cfg-err { background:#FFF5F5; border-left:4px solid #EF4444; }
    </style>
    <div class="setup-hero">
        <h1>💘 LinkUp Setup</h1>
        <p>One-time configuration - takes about 2 minutes.</p>
    </div>
    """, unsafe_allow_html=True)

    # Status rows
    st.subheader("🔧 Configuration Status")
    for key, (ok, preview) in checks.items():
        cls = "cfg-ok" if ok else "cfg-err"
        icon = "✅" if ok else "❌"
        st.markdown(
            f'<div class="cfg-row {cls}"><strong>{key}</strong>'
            f'<span>{icon} {preview}</span></div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ── Fix: Missing Supabase Anon Key ───────────────────────────────────────
    if not checks["SUPABASE_ANON_KEY"][0]:
        with st.expander("📋 Step 1 - Get your Supabase Anon Key", expanded=True):
            st.markdown("""
**How to find it:**
1. Open → [Supabase API Settings](https://supabase.com/dashboard/project/knhkbjyorbsjhwxnchlh/settings/api)
2. Scroll to **"Project API Keys"**
3. Click the 👁️ eye icon next to **`anon` `public`**
4. Copy the long key starting with `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
5. Paste it below:
            """)

            anon_key_input = st.text_input(
                "Supabase Anon Key:",
                type="password",
                placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                key="wizard_anon_key",
            )
            if anon_key_input and len(anon_key_input) > 30:
                if st.button("💾 Save Key & Continue", type="primary", use_container_width=True):
                    _save_env_key("SUPABASE_ANON_KEY", anon_key_input.strip())
                    st.success("✅ Key saved! Restarting in 2 seconds...")
                    import time; time.sleep(2)
                    st.rerun()

    # ── Database schema reminder ─────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🗄️ Step 2 - Run Database Schema")
    st.info(
        "If you haven't already, run `database/schema.sql` in your Supabase SQL Editor:\n"
        "→ https://supabase.com/dashboard/project/knhkbjyorbsjhwxnchlh/sql/new"
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📋 Copy Schema SQL", use_container_width=True):
            try:
                import pathlib
                sql = pathlib.Path("database/schema.sql").read_text()
                st.code(sql[:3000] + ("\n... (truncated)" if len(sql) > 3000 else ""), language="sql")
            except FileNotFoundError:
                st.error("schema.sql not found. Make sure you're running from the project root.")
    with col2:
        st.link_button(
            "🔗 Open SQL Editor",
            "https://supabase.com/dashboard/project/knhkbjyorbsjhwxnchlh/sql/new",
            use_container_width=True,
        )

    # ── Streamlit Cloud instructions ─────────────────────────────────────────
    with st.expander("☁️ Deploying to Streamlit Cloud?"):
        st.markdown("""
In Streamlit Cloud, go to **App settings → Secrets** and add:
```toml
SUPABASE_URL = "https://knhkbjyorbsjhwxnchlh.supabase.co"
SUPABASE_ANON_KEY = "eyJ..."
CLOUDINARY_CLOUD_NAME = "linkup"
CLOUDINARY_API_KEY = "358977134356166"
CLOUDINARY_API_SECRET = "ZD2g4KkmTwJbQ2H798LBhO-LCek"
```
        """)

    return False  # Not ready yet - stop the app


def _save_env_key(key: str, value: str):
    """Write/update a single key in .env and reload."""
    env_path = ".env"
    try:
        try:
            lines = open(env_path).readlines()
        except FileNotFoundError:
            lines = []

        new_lines, found = [], False
        for line in lines:
            if line.startswith(f"{key}="):
                new_lines.append(f"{key}={value}\n")
                found = True
            else:
                new_lines.append(line)
        if not found:
            new_lines.append(f"\n{key}={value}\n")

        with open(env_path, "w") as f:
            f.writelines(new_lines)

        # Reload into os.environ immediately
        os.environ[key] = value

        # Reset Supabase client singleton
        import utils.db as _db
        _db._supabase_client = None

    except Exception as e:
        st.error(f"Could not save to .env: {e}")
        st.info(f"Add this line to your .env manually:\n`{key}={value}`")
