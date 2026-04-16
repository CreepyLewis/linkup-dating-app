"""
utils/auth.py
Authentication helpers - register, login, logout, session management

Uses ONLY Supabase Auth. No bcrypt or custom password hashing.
"""

import streamlit as st
from typing import Optional, Dict
from supabase import AuthApiError
from utils.db import get_client, get_user_by_id, create_user, update_last_seen


# ─── Supabase Auth ────────────────────────────────────────────────────────────

def register_user(email: str, password: str, name: str, age: int, gender: str) -> Dict:
    """
    Create a Supabase Auth user + insert profile row.
    Returns {"success": bool, "user": dict | None, "error": str | None}
    """
    db = get_client()

    # Validate inputs
    if not email or "@" not in email:
        return {"success": False, "error": "Invalid email address."}
    if len(password) < 6:
        return {"success": False, "error": "Password must be at least 6 characters."}
    if not name.strip():
        return {"success": False, "error": "Name is required."}
    if not (18 <= age <= 100):
        return {"success": False, "error": "You must be at least 18 years old."}

    try:
        # Create Supabase Auth account
        auth_res = db.auth.sign_up({"email": email, "password": password})
        auth_user = auth_res.user
        if not auth_user:
            return {"success": False, "error": "Registration failed. Try again."}

        # Insert profile — password managed entirely by Supabase Auth
        profile = create_user({
            "id": auth_user.id,
            "email": email,
            "name": name.strip(),
            "age": age,
            "gender": gender,
        })

        if not profile:
            return {"success": False, "error": "Account created but profile setup failed. Please contact support."}

        return {"success": True, "user": profile}

    except AuthApiError as e:
        msg = str(e)
        if "already registered" in msg.lower():
            return {"success": False, "error": "Email already registered."}
        return {"success": False, "error": msg}
    except Exception as e:
        return {"success": False, "error": str(e)}


def login_user(email: str, password: str) -> Dict:
    """
    Sign in with email + password.
    Returns {"success": bool, "user": dict | None, "session": obj, "error": str | None}
    """
    db = get_client()

    if not email or not password:
        return {"success": False, "error": "Email and password are required."}

    try:
        auth_res = db.auth.sign_in_with_password({"email": email, "password": password})
        auth_user = auth_res.user
        session = auth_res.session

        if not auth_user:
            return {"success": False, "error": "Invalid credentials."}

        # Fetch profile
        profile = get_user_by_id(auth_user.id)
        if not profile:
            return {"success": False, "error": "Profile not found. Please contact support."}

        if not profile.get("is_active", True):
            return {"success": False, "error": "Your account has been suspended."}

        update_last_seen(auth_user.id)
        return {"success": True, "user": profile, "session": session}

    except AuthApiError as e:
        msg = str(e).lower()
        if "invalid" in msg or "credentials" in msg:
            return {"success": False, "error": "Wrong email or password."}
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def logout_user():
    """Sign out and clear Streamlit session."""
    try:
        db = get_client()
        db.auth.sign_out()
    except Exception:
        pass
    _clear_session()


def request_password_reset(email: str) -> Dict:
    db = get_client()
    try:
        db.auth.reset_password_email(email)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── Session State Helpers ────────────────────────────────────────────────────

SESSION_KEY = "linkup_user"
SESSION_TOKEN_KEY = "linkup_token"


def set_session(user: Dict, session=None):
    st.session_state[SESSION_KEY] = user
    if session:
        st.session_state[SESSION_TOKEN_KEY] = session.access_token


def get_session_user() -> Optional[Dict]:
    return st.session_state.get(SESSION_KEY)


def is_authenticated() -> bool:
    return get_session_user() is not None


def refresh_session_user():
    """Re-fetch current user from DB and update session."""
    user = get_session_user()
    if user:
        updated = get_user_by_id(user["id"])
        if updated:
            set_session(updated)


def _clear_session():
    for key in [SESSION_KEY, SESSION_TOKEN_KEY, "discover_index", "current_profiles",
                "discover_profiles", "current_page"]:
        st.session_state.pop(key, None)


def require_auth():
    """Call at top of any protected page. Sets page to login if not authenticated."""
    if not is_authenticated():
        st.session_state["redirect_after_login"] = st.session_state.get("current_page", "home")
        st.session_state["current_page"] = "login"
        st.query_params["page"] = "login"
        st.rerun()


def is_premium() -> bool:
    user = get_session_user()
    return bool(user and user.get("is_premium"))


def is_admin() -> bool:
    user = get_session_user()
    return bool(user and user.get("is_admin"))
