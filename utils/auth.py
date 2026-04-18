"""
utils/auth.py
Custom authentication - no Supabase Auth service.
Passwords stored as bcrypt hashes in public.users table.
No email confirmation, no rate limits, no admin API needed.
"""

import os
import uuid
import bcrypt
import streamlit as st
from typing import Optional, Dict
from dotenv import load_dotenv

load_dotenv()


def _db():
    from utils.db import get_service_client
    return get_service_client()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=10)).decode()

def _verify(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False


# ── Register ───────────────────────────────────────────────────────────────────

def register_user(email: str, password: str, name: str, age: int, gender: str) -> Dict:
    """
    Create a new user directly in public.users.
    No Supabase Auth service - no email confirmation, no rate limits.
    """
    email = email.strip().lower()

    if not email or "@" not in email:
        return {"success": False, "error": "Invalid email address."}
    if len(password) < 6:
        return {"success": False, "error": "Password must be at least 6 characters."}
    if not name.strip():
        return {"success": False, "error": "Name is required."}
    if not (18 <= int(age) <= 100):
        return {"success": False, "error": "You must be at least 18 years old."}

    db = _db()

    # Check if email already exists
    try:
        existing = db.table("users").select("id").eq("email", email).execute()
        if existing.data:
            return {"success": False, "error": "Email already registered. Try logging in."}
    except Exception as e:
        return {"success": False, "error": f"Database error: {e}"}

    # Create user row
    user_id = str(uuid.uuid4())
    profile = {
        "id":            user_id,
        "email":         email,
        "name":          name.strip(),
        "age":           int(age),
        "gender":        gender,
        "password_hash": _hash(password),
        "intent":        "dating",
        "is_active":     True,
        "is_premium":    False,
    }

    try:
        res = db.table("users").insert(profile).execute()
        created = res.data[0] if res.data else profile
        return {"success": True, "user": created}
    except Exception as e:
        msg = str(e).lower()
        if "duplicate" in msg or "unique" in msg or "already exists" in msg:
            return {"success": False, "error": "Email already registered. Try logging in."}
        return {"success": False, "error": f"Could not create account: {e}"}


# ── Login ──────────────────────────────────────────────────────────────────────

def login_user(email: str, password: str) -> Dict:
    """
    Sign in by checking bcrypt hash directly in public.users.
    No Supabase Auth service needed.
    """
    email = email.strip().lower()
    if not email or not password:
        return {"success": False, "error": "Email and password are required."}

    db = _db()

    try:
        res = db.table("users").select("*").eq("email", email).execute()
    except Exception as e:
        return {"success": False, "error": f"Database error: {e}"}

    if not res.data:
        return {"success": False, "error": "No account found with that email."}

    profile = res.data[0]

    # Check password
    stored_hash = profile.get("password_hash") or ""
    if not stored_hash:
        return {"success": False, "error": "Account has no password set. Use 'Forgot Password'."}

    if not _verify(password, stored_hash):
        return {"success": False, "error": "Wrong password."}

    if not profile.get("is_active", True):
        return {"success": False, "error": "Your account has been suspended."}

    # Update last seen
    try:
        from datetime import datetime, timezone
        db.table("users").update(
            {"last_seen": datetime.now(timezone.utc).isoformat()}
        ).eq("id", profile["id"]).execute()
    except Exception:
        pass

    return {"success": True, "user": profile, "session": None}


# ── Logout ─────────────────────────────────────────────────────────────────────

def logout_user():
    _clear_session()


# ── Password reset ─────────────────────────────────────────────────────────────

def request_password_reset(email: str) -> Dict:
    """
    For now: confirm the email exists. 
    Full reset requires email service (future feature).
    """
    email = email.strip().lower()
    try:
        res = _db().table("users").select("id").eq("email", email).execute()
        if res.data:
            return {"success": True}
        return {"success": False, "error": "No account with that email."}
    except Exception as e:
        return {"success": False, "error": str(e)}


def update_password(user_id: str, new_password: str) -> Dict:
    if len(new_password) < 6:
        return {"success": False, "error": "Password must be at least 6 characters."}
    try:
        _db().table("users").update(
            {"password_hash": _hash(new_password)}
        ).eq("id", user_id).execute()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── Session ────────────────────────────────────────────────────────────────────

SESSION_KEY = "linkup_user"


def set_session(user: Dict, session=None):
    # Never store password_hash in session
    safe = {k: v for k, v in user.items() if k != "password_hash"}
    st.session_state[SESSION_KEY] = safe


def get_session_user() -> Optional[Dict]:
    return st.session_state.get(SESSION_KEY)


def is_authenticated() -> bool:
    return get_session_user() is not None


def refresh_session_user():
    user = get_session_user()
    if not user:
        return
    try:
        r = _db().table("users").select("*").eq("id", user["id"]).execute()
        if r.data:
            set_session(r.data[0])
    except Exception:
        pass


def _clear_session():
    for k in [SESSION_KEY, "discover_index", "discover_profiles",
              "active_match_id", "active_match_user"]:
        st.session_state.pop(k, None)


def require_auth():
    if not is_authenticated():
        st.session_state["redirect_after_login"] = st.query_params.get("page", "home")
        st.query_params["page"] = "login"
        st.rerun()


def is_premium() -> bool:
    u = get_session_user()
    return bool(u and u.get("is_premium"))


def is_admin() -> bool:
    u = get_session_user()
    return bool(u and u.get("is_admin"))


# Keep these so settings.py password-change still works
def hash_password(p: str) -> str: return _hash(p)
def verify_password(p: str, h: str) -> bool: return _verify(p, h)
