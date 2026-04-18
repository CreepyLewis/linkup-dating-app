"""
utils/auth.py
Authentication - register, login, logout, session management.
Uses regular sign_up (works on all Supabase plans).
Email confirmation is disabled via Supabase dashboard.
"""

import os
import streamlit as st
from typing import Optional, Dict
from dotenv import load_dotenv

load_dotenv()


def _anon():
    from utils.db import get_client
    return get_client()


def _svc():
    from utils.db import get_service_client
    return get_service_client()


# ── Register ───────────────────────────────────────────────────────────────────

def register_user(email: str, password: str, name: str, age: int, gender: str) -> Dict:
    email = email.strip().lower()

    if not email or "@" not in email:
        return {"success": False, "error": "Invalid email address."}
    if len(password) < 6:
        return {"success": False, "error": "Password must be at least 6 characters."}
    if not name.strip():
        return {"success": False, "error": "Name is required."}
    if not (18 <= int(age) <= 100):
        return {"success": False, "error": "You must be at least 18 years old."}

    auth_user = None

    # Try admin API first (auto-confirms, no rate limit)
    try:
        res = _svc().auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {"name": name, "age": int(age), "gender": gender},
        })
        auth_user = res.user
    except Exception as admin_err:
        admin_msg = str(admin_err).lower()
        if "already" in admin_msg or "duplicate" in admin_msg or "registered" in admin_msg:
            return {"success": False, "error": "Email already registered. Try logging in."}
        # Admin API not available - fall through to regular sign_up
        auth_user = None

    # Fallback: regular sign_up
    if not auth_user:
        try:
            res = _anon().auth.sign_up({
                "email": email,
                "password": password,
                "options": {"data": {"name": name, "age": int(age), "gender": gender}},
            })
            auth_user = res.user
        except Exception as e:
            msg = str(e).lower()
            if "already" in msg or "registered" in msg:
                return {"success": False, "error": "Email already registered. Try logging in."}
            if "rate" in msg and "limit" in msg:
                return {
                    "success": False,
                    "error": (
                        "Too many signups from this network.\n\n"
                        "Fix: Go to Supabase Dashboard → Authentication → Providers → Email → "
                        "turn OFF 'Confirm email' → Save. Then try again."
                    ),
                }
            return {"success": False, "error": f"Signup failed: {e}"}

    if not auth_user:
        return {"success": False, "error": "Could not create account. Please try again."}

    # Insert profile row using service role (bypasses RLS)
    profile_data = {
        "id":         auth_user.id,
        "email":      email,
        "name":       name.strip(),
        "age":        int(age),
        "gender":     gender,
        "intent":     "dating",
        "is_active":  True,
        "is_premium": False,
    }
    try:
        res = _svc().table("users").insert(profile_data).execute()
        profile = res.data[0] if res.data else profile_data
    except Exception as e:
        msg = str(e).lower()
        # Profile row already exists (trigger may have created it) - just fetch it
        if "duplicate" in msg or "unique" in msg or "already exists" in msg:
            try:
                r2 = _svc().table("users").select("*").eq("id", auth_user.id).execute()
                profile = r2.data[0] if r2.data else profile_data
            except Exception:
                profile = profile_data
        else:
            profile = profile_data  # Auth succeeded; profile insert failed silently

    return {"success": True, "user": profile}


# ── Login ──────────────────────────────────────────────────────────────────────

def login_user(email: str, password: str) -> Dict:
    email = email.strip().lower()
    if not email or not password:
        return {"success": False, "error": "Email and password are required."}

    try:
        res     = _anon().auth.sign_in_with_password({"email": email, "password": password})
        session = res.session
        user    = res.user
        if not user:
            return {"success": False, "error": "Invalid credentials."}
    except Exception as e:
        msg = str(e).lower()
        if "invalid" in msg or "credentials" in msg or "wrong" in msg:
            return {"success": False, "error": "Wrong email or password."}
        if "not confirmed" in msg or "confirm" in msg:
            return {
                "success": False,
                "error": (
                    "Email not confirmed.\n"
                    "Fix: Supabase Dashboard → Authentication → Providers → Email → "
                    "turn OFF 'Confirm email' → Save. Then try again."
                ),
            }
        return {"success": False, "error": str(e)}

    # Fetch profile via service role (bypasses RLS)
    profile = None
    try:
        r = _svc().table("users").select("*").eq("id", user.id).execute()
        profile = r.data[0] if r.data else None
    except Exception:
        pass

    # Auto-heal missing profile
    if not profile:
        profile = _rebuild_profile(user)

    if not profile:
        return {"success": False, "error": "Profile missing. Please register again."}

    if not profile.get("is_active", True):
        return {"success": False, "error": "Your account has been suspended."}

    # Bump last_seen
    try:
        from datetime import datetime, timezone
        _svc().table("users").update(
            {"last_seen": datetime.now(timezone.utc).isoformat()}
        ).eq("id", user.id).execute()
    except Exception:
        pass

    return {"success": True, "user": profile, "session": session}


def _rebuild_profile(auth_user) -> Optional[Dict]:
    """Recreate a missing profile row from auth metadata."""
    try:
        meta = auth_user.user_metadata or {}
        data = {
            "id":         auth_user.id,
            "email":      auth_user.email,
            "name":       meta.get("name") or auth_user.email.split("@")[0].title(),
            "age":        int(meta.get("age") or 25),
            "gender":     meta.get("gender") or "other",
            "intent":     "dating",
            "is_active":  True,
            "is_premium": False,
        }
        r = _svc().table("users").insert(data).execute()
        return r.data[0] if r.data else data
    except Exception:
        return None


# ── Logout ─────────────────────────────────────────────────────────────────────

def logout_user():
    try:
        _anon().auth.sign_out()
    except Exception:
        pass
    _clear_session()


# ── Password reset ─────────────────────────────────────────────────────────────

def request_password_reset(email: str) -> Dict:
    try:
        _anon().auth.reset_password_email(email.strip())
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── Session ────────────────────────────────────────────────────────────────────

SESSION_KEY = "linkup_user"
TOKEN_KEY   = "linkup_token"


def set_session(user: Dict, session=None):
    st.session_state[SESSION_KEY] = user
    if session:
        try:
            st.session_state[TOKEN_KEY] = session.access_token
        except Exception:
            pass


def get_session_user() -> Optional[Dict]:
    return st.session_state.get(SESSION_KEY)


def is_authenticated() -> bool:
    return get_session_user() is not None


def refresh_session_user():
    user = get_session_user()
    if not user:
        return
    try:
        r = _svc().table("users").select("*").eq("id", user["id"]).execute()
        if r.data:
            set_session(r.data[0])
    except Exception:
        pass


def _clear_session():
    for k in [SESSION_KEY, TOKEN_KEY, "discover_index",
              "discover_profiles", "active_match_id", "active_match_user"]:
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
