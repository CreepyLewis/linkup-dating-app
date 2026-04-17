"""
utils/startup_check.py
Config validator. Reads from Streamlit secrets (cloud) OR .env (local).
"""

import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()


def _get(key: str) -> str:
    """Get a config value - checks Streamlit secrets first, then os.environ."""
    # Streamlit Cloud: secrets stored in st.secrets
    try:
        val = st.secrets.get(key, "")
        if val:
            os.environ[key] = str(val)
            return str(val)
    except Exception:
        pass
    return os.getenv(key, "")


def load_all_secrets():
    """Load all secrets into os.environ so the whole app can use os.getenv()."""
    keys = [
        "SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY",
        "CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET",
        "MPESA_CONSUMER_KEY", "MPESA_CONSUMER_SECRET", "MPESA_SHORTCODE",
        "MPESA_PASSKEY", "MPESA_CALLBACK_URL",
    ]
    for k in keys:
        _get(k)  # This loads each value into os.environ if found in st.secrets


def check_env() -> dict:
    load_all_secrets()

    def _ok(v):
        return bool(v) and "PASTE_YOUR" not in v and "your-" not in v and len(v) > 5

    def _preview(v):
        if not v or not _ok(v): return "(not set)"
        return v[:25] + "..." if len(v) > 25 else v

    supabase_url = _get("SUPABASE_URL")
    supabase_key = _get("SUPABASE_ANON_KEY")

    return {
        "SUPABASE_URL": (_ok(supabase_url), _preview(supabase_url)),
        "SUPABASE_ANON_KEY": (_ok(supabase_key), _preview(supabase_key)),
    }


def show_setup_wizard() -> bool:
    """Returns True if all required config is set. Shows wizard if not."""
    checks = check_env()
    all_ok = all(ok for ok, _ in checks.values())
    if all_ok:
        return True

    st.markdown("""
    <style>
    .setup-hero {
        background: linear-gradient(135deg, #FF6B6B, #FF8E53);
        border-radius: 16px; padding: 1.5rem 2rem; color: white;
        text-align: center; margin-bottom: 1.5rem;
    }
    .cfg-row {
        display:flex; justify-content:space-between; align-items:center;
        padding:.65rem 1rem; border-radius:8px; margin-bottom:.4rem; font-size:.9rem;
    }
    .cfg-ok  { background: var(--color-background-success); }
    .cfg-err { background: var(--color-background-danger); }
    </style>
    <div class="setup-hero">
        <h2 style="margin:0;">💘 LinkUp - Setup Required</h2>
        <p style="margin:.3rem 0 0; opacity:.9;">Paste your Supabase key below to get started</p>
    </div>
    """, unsafe_allow_html=True)

    for key, (ok, preview) in checks.items():
        cls = "cfg-ok" if ok else "cfg-err"
        color = "var(--color-text-success)" if ok else "var(--color-text-danger)"
        st.markdown(
            f'<div class="cfg-row {cls}"><strong>{key}</strong>'
            f'<span style="color:{color}">{"✅" if ok else "❌"} {preview}</span></div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    if not checks["SUPABASE_ANON_KEY"][0]:
        st.markdown("### Step 1: Get your Supabase Anon Key")
        st.markdown(
            "Go to → "
            "[Supabase API Settings](https://supabase.com/dashboard/project/knhkbjyorbsjhwxnchlh/settings/api)"
            " → **Project API Keys** → copy the **`anon public`** key"
        )
        key_input = st.text_input(
            "Paste key here:",
            type="password",
            placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        )
        if key_input and len(key_input) > 30:
            if st.button("Save & Continue", type="primary"):
                _save_env_key("SUPABASE_ANON_KEY", key_input.strip())
                st.success("Saved! Restarting...")
                import time; time.sleep(1)
                st.rerun()

    with st.expander("Deploying on Streamlit Cloud?"):
        st.markdown("""
Add these in **Streamlit Cloud → App Settings → Secrets**:
```toml
SUPABASE_URL = "https://knhkbjyorbsjhwxnchlh.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
SUPABASE_SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
CLOUDINARY_CLOUD_NAME = "linkup"
CLOUDINARY_API_KEY = "358977134356166"
CLOUDINARY_API_SECRET = "ZD2g4KkmTwJbQ2H798LBhO-LCek"
MPESA_CONSUMER_KEY = "VgLDRD1fG01kxurBCtHGmwkHfx9oRlwqr9cyB70UtEIHXMX2"
MPESA_CONSUMER_SECRET = "3Oo1HalvCGWhAya0gQTdLefMAeEL5eBRjabmGv5HllpfKRkjcn4d3U3Ndf7foEe7"
MPESA_SHORTCODE = "174379"
MPESA_PASSKEY = "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919"
```
        """)

    return False


def _save_env_key(key: str, value: str):
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
            new_lines.append(f"{key}={value}\n")
        open(env_path, "w").writelines(new_lines)
        os.environ[key] = value
        import utils.db as _db
        _db._supabase_client = None
    except Exception as e:
        st.error(f"Could not save to .env: {e}")
