"""
utils/auth.py
Authentication - register, login, logout, session management.
Uses service role key for DB writes to bypass RLS.
"""

import os
import streamlit as st
from typing import Optional, Dict
from dotenv import load_dotenv

load_dotenv()


# ── Password hashing ──────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    import bcrypt
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


# ── Supabase clients ──────────────────────────────────────────────────────────

def _anon_client():
    from utils.db import get_client
    return get_client()


def _service_client():
    """Service role client - bypasses RLS for all DB writes."""
    from utils.db import get_service_client
    return get_service_client()


# ── Registration ──────────────────────────────────────────────────────────────

def register_user(email: str, password: str, name: str, age: int, gender: str) -> Dict:
    """
    Create Supabase Auth user + profile row.
    Uses service role to bypass RLS on INSERT.
    """
    if not email or "@" not in email:
        return {"success": False, "error": "Invalid email address."}
    if len(password) < 6:
        return {"success": False, "error": "Password must be at least 6 characters."}
    if not name.strip():
        return {"success": False, "error": "Name is required."}
    if not (18 <= int(age) <= 100):
        return {"success": False, "error": "You must be at least 18 years old."}

    try:
        # Use service role to create auth user - skips email confirmation entirely
        svc = _service_client()
        auth_res = svc.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,   # auto-confirm - no email needed
            "user_metadata": {"name": name, "age": age, "gender": gender},
        })
        auth_user = auth_res.user
        if not auth_user:
            return {"success": False, "error": "Registration failed. Try again."}

        # Insert profile using service role (bypasses RLS)
        profile_data = {
            "id": auth_user.id,
            "email": email,
            "name": name.strip(),
            "age": int(age),
            "gender": gender,
            "intent": "dating",
            "is_active": True,
            "is_premium": False,
        }
        res = svc.table("users").insert(profile_data).execute()
        profile = res.data[0] if res.data else profile_data

        return {"success": True, "user": profile}

    except Exception as e:
        err = str(e)
        if "already registered" in err.lower() or "already been registered" in err.lower() or "duplicate" in err.lower():
            return {"success": False, "error": "This email is already registered. Try logging in instead."}
        if "rate" in err.lower() and "limit" in err.lower():
            return {"success": False, "error": "Too many attempts. Wait a few minutes and try again."}
        return {"success": False, "error": err}


# ── Login ──────────────────────────────────────────────────────────────────────

def login_user(email: str, password: str) -> Dict:
    """
    Sign in. If profile row is missing (can happen), auto-creates it.
    """
    if not email or not password:
        return {"success": False, "error": "Email and password are required."}

    try:
        # Sign in with anon client
        auth_res = _anon_client().auth.sign_in_with_password({
            "email": email, "password": password
        })
        auth_user = auth_res.user
        session   = auth_res.session

        if not auth_user:
            return {"success": False, "error": "Invalid credentials."}

        # Fetch profile using service client (bypasses RLS read restrictions)
        svc = _service_client()
        res = svc.table("users").select("*").eq("id", auth_user.id).execute()
        profile = res.data[0] if res.data else None

        # Auto-heal: profile row missing (common after RLS blocks registration)
        if not profile:
            profile = _auto_create_profile(svc, auth_user)

        if not profile:
            return {"success": False, "error": "Could not load profile. Try registering again."}

        if not profile.get("is_active", True):
            return {"success": False, "error": "Your account has been suspended."}

        # Update last seen
        try:
            from datetime import datetime, timezone
            svc.table("users").update({"last_seen": datetime.now(timezone.utc).isoformat()}).eq("id", auth_user.id).execute()
        except Exception:
            pass

        return {"success": True, "user": profile, "session": session}

    except Exception as e:
        err = str(e).lower()
        if "invalid" in err or "credentials" in err or "wrong" in err:
            return {"success": False, "error": "Wrong email or password."}
        if "email not confirmed" in err:
            return {"success": False, "error": "Email not confirmed. Check your inbox or contact support."}
        return {"success": False, "error": str(e)}


def _auto_create_profile(svc, auth_user) -> Optional[Dict]:
    """Create a profile row from auth user metadata when it's missing."""
    try:
        meta = auth_user.user_metadata or {}
        profile_data = {
            "id": auth_user.id,
            "email": auth_user.email,
            "name": meta.get("name") or auth_user.email.split("@")[0],
            "age": int(meta.get("age") or 25),
            "gender": meta.get("gender") or "other",
            "intent": "dating",
            "is_active": True,
            "is_premium": False,
        }
        res = svc.table("users").insert(profile_data).execute()
        return res.data[0] if res.data else profile_data
    except Exception:
        return None


# ── Logout ────────────────────────────────────────────────────────────────────

def logout_user():
    try:
        _anon_client().auth.sign_out()
    except Exception:
        pass
    _clear_session()


# ── Password reset ────────────────────────────────────────────────────────────

def request_password_reset(email: str) -> Dict:
    try:
        _anon_client().auth.reset_password_email(email)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── Session helpers ───────────────────────────────────────────────────────────

SESSION_KEY       = "linkup_user"
SESSION_TOKEN_KEY = "linkup_token"


def set_session(user: Dict, session=None):
    st.session_state[SESSION_KEY] = user
    if session:
        try:
            st.session_state[SESSION_TOKEN_KEY] = session.access_token
        except Exception:
            pass


def get_session_user() -> Optional[Dict]:
    return st.session_state.get(SESSION_KEY)


def is_authenticated() -> bool:
    return get_session_user() is not None


def refresh_session_user():
    """Re-fetch user from DB and update session state."""
    user = get_session_user()
    if not user:
        return
    try:
        svc = _service_client()
        res = svc.table("users").select("*").eq("id", user["id"]).execute()
        if res.data:
            set_session(res.data[0])
    except Exception:
        pass


def _clear_session():
    for key in [SESSION_KEY, SESSION_TOKEN_KEY, "discover_index",
                "current_profiles", "active_match_id", "active_match_user",
                "discover_profiles"]:
        st.session_state.pop(key, None)


def require_auth():
    if not is_authenticated():
        st.session_state["redirect_after_login"] = st.query_params.get("page", "home")
        st.query_params["page"] = "login"
        st.rerun()


def is_premium() -> bool:
    user = get_session_user()
    return bool(user and user.get("is_premium"))


def is_admin() -> bool:
    user = get_session_user()
    return bool(user and user.get("is_admin"))
