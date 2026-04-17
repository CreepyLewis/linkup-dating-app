"""
utils/auth.py
Authentication helpers — register, login, logout, session management

Uses ONLY Supabase Auth (no bcrypt).
All profile DB operations go through the service-role client (bypasses RLS).
"""

import streamlit as st
from typing import Optional, Dict
from utils.db import get_client, get_admin_client, get_user_by_id, create_user, update_last_seen


SESSION_KEY = "linkup_user"
SESSION_TOKEN_KEY = "linkup_token"


# ─── Registration ─────────────────────────────────────────────────────────────

def register_user(email: str, password: str, name: str, age: int, gender: str) -> Dict:
    """
    Create a Supabase Auth account + insert profile row via service-role client.
    Returns {"success": bool, "user": dict | None, "error": str | None}
    """
    # Client-side validation
    if not email or "@" not in email:
        return {"success": False, "error": "Invalid email address."}
    if len(password) < 6:
        return {"success": False, "error": "Password must be at least 6 characters."}
    if not name.strip():
        return {"success": False, "error": "Name is required."}
    if not (18 <= age <= 100):
        return {"success": False, "error": "You must be at least 18 years old."}

    anon = get_client()

    try:
        auth_res = anon.auth.sign_up({"email": email, "password": password})
    except Exception as e:
        msg = str(e)
        if "already registered" in msg.lower() or "already been registered" in msg.lower():
            return {"success": False, "error": "Email already registered. Please log in."}
        return {"success": False, "error": f"Registration failed: {msg}"}

    auth_user = auth_res.user
    if not auth_user:
        return {"success": False, "error": "Registration failed — no user returned. Try again."}

    # Insert profile using service-role client (bypasses RLS)
    try:
        profile = create_user({
            "id": auth_user.id,
            "email": email,
            "name": name.strip(),
            "age": int(age),
            "gender": gender,
        })
    except Exception as e:
        return {"success": False, "error": f"Auth account created but profile failed: {e}"}

    if not profile:
        # create_user returned None — try fetching in case it already exists
        profile = get_user_by_id(auth_user.id)

    if not profile:
        return {
            "success": False,
            "error": (
                "Auth account created but profile could not be saved. "
                "Check that SUPABASE_SERVICE_ROLE_KEY is set in your .env file."
            ),
        }

    return {"success": True, "user": profile}


# ─── Login ────────────────────────────────────────────────────────────────────

def login_user(email: str, password: str) -> Dict:
    """
    Sign in with Supabase Auth, then fetch profile via service-role client.
    Returns {"success": bool, "user": dict | None, "session": obj, "error": str | None}
    """
    if not email or not password:
        return {"success": False, "error": "Email and password are required."}

    anon = get_client()

    try:
        auth_res = anon.auth.sign_in_with_password({"email": email, "password": password})
    except Exception as e:
        msg = str(e).lower()
        if "invalid" in msg or "credentials" in msg or "wrong" in msg:
            return {"success": False, "error": "Wrong email or password."}
        if "email not confirmed" in msg:
            return {"success": False, "error": "Please confirm your email before logging in."}
        return {"success": False, "error": f"Login error: {e}"}

    auth_user = auth_res.user
    session = auth_res.session

    if not auth_user:
        return {"success": False, "error": "Invalid credentials."}

    # Fetch profile via service-role client — never blocked by RLS
    profile = get_user_by_id(auth_user.id)

    if not profile:
        # Profile row is missing — create it automatically (handles users who registered
        # before profile creation was fixed, or if email confirmation delayed creation)
        try:
            profile = create_user({
                "id": auth_user.id,
                "email": auth_user.email,
                "name": auth_user.email.split("@")[0],  # temp name from email
                "age": 18,
                "gender": "other",
            })
        except Exception:
            profile = None

    if not profile:
        return {
            "success": False,
            "error": (
                "Profile not found. This usually means SUPABASE_SERVICE_ROLE_KEY "
                "is missing from your .env file — the backend cannot read the database."
            ),
        }

    if not profile.get("is_active", True):
        return {"success": False, "error": "Your account has been suspended."}

    update_last_seen(auth_user.id)
    return {"success": True, "user": profile, "session": session}


# ─── Logout ──────────────────────────────────────────────────────────────────

def logout_user():
    """Sign out from Supabase Auth and wipe local session."""
    try:
        get_client().auth.sign_out()
    except Exception:
        pass
    _clear_session()


# ─── Password reset ──────────────────────────────────────────────────────────

def request_password_reset(email: str) -> Dict:
    try:
        get_client().auth.reset_password_email(email)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── Session helpers ─────────────────────────────────────────────────────────

def set_session(user: Dict, session=None):
    st.session_state[SESSION_KEY] = user
    if session:
        st.session_state[SESSION_TOKEN_KEY] = session.access_token


def get_session_user() -> Optional[Dict]:
    return st.session_state.get(SESSION_KEY)


def is_authenticated() -> bool:
    return SESSION_KEY in st.session_state and st.session_state[SESSION_KEY] is not None


def refresh_session_user():
    """Re-fetch current user from DB (service-role) and update session state."""
    user = get_session_user()
    if user:
        updated = get_user_by_id(user["id"])
        if updated:
            st.session_state[SESSION_KEY] = updated  # update in-place, no token change


def _clear_session():
    keys = [
        SESSION_KEY, SESSION_TOKEN_KEY,
        "discover_index", "current_profiles",
        "discover_profiles", "current_page",
        "dark_mode",
    ]
    for key in keys:
        st.session_state.pop(key, None)


def require_auth():
    """Redirect to login if not authenticated."""
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
