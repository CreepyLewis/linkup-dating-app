"""
utils/db.py
Supabase database connection + all query helpers for LinkUp

TWO CLIENTS:
  - get_client()         → anon key  (used ONLY for auth.sign_up / sign_in)
  - get_admin_client()   → service role key (bypasses RLS for all DB reads/writes)

This is the correct architecture for a Streamlit backend:
  - Auth calls use anon client (Supabase Auth API)
  - ALL table reads/writes use the service-role client so RLS never blocks server ops
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv
from typing import Optional, List, Dict, Any
import math

load_dotenv()

# ─── Singleton clients ────────────────────────────────────────────────────────

_anon_client: Optional[Client] = None
_admin_client: Optional[Client] = None


def get_client() -> Client:
    """Anon-key client — use ONLY for Supabase Auth calls (sign_up, sign_in, sign_out)."""
    global _anon_client
    if _anon_client is None:
        url = os.getenv("SUPABASE_URL", "").strip()
        key = os.getenv("SUPABASE_ANON_KEY", "").strip()
        if not url or "your-project-id" in url:
            raise ValueError(
                "❌ SUPABASE_URL not set.\n"
                "Open your .env file and set SUPABASE_URL=https://<project>.supabase.co"
            )
        if not key or "PASTE" in key:
            raise ValueError(
                "❌ SUPABASE_ANON_KEY not set.\n"
                "Get it from Supabase → Settings → API → anon public key."
            )
        _anon_client = create_client(url, key)
    return _anon_client


def get_admin_client() -> Client:
    """
    Service-role client — bypasses RLS for all table operations.
    Use for every table read/write in this backend (never expose to browser).
    """
    global _admin_client
    if _admin_client is None:
        url = os.getenv("SUPABASE_URL", "").strip()
        service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

        # Fall back to anon key with a warning if service role key isn't set yet
        if not service_key or "PASTE" in service_key:
            # Warn once
            import streamlit as st
            st.warning(
                "⚠️ **SUPABASE_SERVICE_ROLE_KEY** is not set in your `.env` file.\n\n"
                "Without it, profile reads/writes will fail due to RLS.\n\n"
                "Get it from: Supabase Dashboard → Settings → API → **service_role** key.",
                icon="🔑",
            )
            # Use anon key as fallback (will fail for RLS-protected ops but at least won't crash)
            return get_client()

        if not url or "your-project-id" in url:
            raise ValueError("❌ SUPABASE_URL not set.")

        _admin_client = create_client(url, service_key)
    return _admin_client


# ─── USER QUERIES ─────────────────────────────────────────────────────────────

def get_user_by_id(user_id: str) -> Optional[Dict]:
    """Fetch a user profile by UUID. Uses service role to bypass RLS."""
    db = get_admin_client()
    try:
        res = db.table("users").select("*").eq("id", user_id).single().execute()
        return res.data
    except Exception:
        return None


def get_user_by_email(email: str) -> Optional[Dict]:
    """Fetch a user profile by email. Uses service role to bypass RLS."""
    db = get_admin_client()
    try:
        res = db.table("users").select("*").eq("email", email).single().execute()
        return res.data
    except Exception:
        return None


def create_user(data: Dict) -> Optional[Dict]:
    """Insert a new user profile row. Uses service role to bypass RLS."""
    db = get_admin_client()
    try:
        res = db.table("users").insert(data).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        raise RuntimeError(f"Failed to create user profile: {e}")


def update_user(user_id: str, data: Dict) -> Optional[Dict]:
    """Update a user profile. Uses service role to bypass RLS."""
    db = get_admin_client()
    try:
        res = db.table("users").update(data).eq("id", user_id).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        return None


def update_last_seen(user_id: str):
    from datetime import datetime, timezone
    update_user(user_id, {"last_seen": datetime.now(timezone.utc).isoformat()})


def get_profile_completion(user: Dict) -> int:
    """Return profile completion percentage (0-100)."""
    fields = {
        "name": 15,
        "age": 10,
        "gender": 10,
        "bio": 15,
        "location": 10,
        "interests": 10,
        "photo_url": 20,
        "intent": 10,
    }
    score = 0
    for field, weight in fields.items():
        val = user.get(field)
        if val:
            if isinstance(val, list) and len(val) > 0:
                score += weight
            elif isinstance(val, str) and val.strip():
                score += weight
            elif isinstance(val, (int, float)) and val > 0:
                score += weight
    return score


# ─── DISCOVERY QUERIES ───────────────────────────────────────────────────────

def get_discover_profiles(current_user: Dict, limit: int = 20) -> List[Dict]:
    """
    Return candidate profiles for the discovery page.
    Excludes: self, already liked/passed, blocked users.
    """
    db = get_admin_client()
    uid = current_user["id"]

    liked_ids = get_liked_user_ids(uid)
    passed_ids = get_passed_user_ids(uid)
    blocked_ids = get_blocked_user_ids(uid)
    exclude_ids = {uid} | set(liked_ids) | set(passed_ids) | set(blocked_ids)

    try:
        query = (
            db.table("users")
            .select("*")
            .eq("profile_hidden", False)
            .eq("is_active", True)
            .neq("id", uid)
        )

        pref = current_user.get("gender_preference", "any")
        if pref and pref != "any":
            query = query.eq("gender", pref)

        age_min = current_user.get("age_min", 18)
        age_max = current_user.get("age_max", 60)
        query = query.gte("age", age_min).lte("age", age_max)

        intent = current_user.get("intent", "dating")
        if intent:
            query = query.eq("intent", intent)

        res = query.limit(limit + len(exclude_ids)).execute()
        candidates = res.data or []
    except Exception:
        return []

    candidates = [u for u in candidates if u["id"] not in exclude_ids]

    max_dist = current_user.get("max_distance", 50)
    lat1 = current_user.get("latitude")
    lon1 = current_user.get("longitude")
    if lat1 and lon1:
        candidates = [
            u for u in candidates
            if _within_distance(lat1, lon1, u.get("latitude"), u.get("longitude"), max_dist)
        ]

    return candidates[:limit]


def _within_distance(lat1, lon1, lat2, lon2, max_km: float) -> bool:
    if not lat2 or not lon2:
        return True
    R = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)) <= max_km


def get_distance_km(lat1, lon1, lat2, lon2) -> Optional[float]:
    if not all([lat1, lon1, lat2, lon2]):
        return None
    R = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ─── LIKES / PASSES ───────────────────────────────────────────────────────────

def like_user(user_id: str, liked_user_id: str) -> bool:
    """Record a like. Returns True if it created a mutual match."""
    db = get_admin_client()
    try:
        db.table("likes").insert({
            "user_id": user_id,
            "liked_user_id": liked_user_id,
        }).execute()
    except Exception:
        pass  # Duplicate like — already recorded

    try:
        res = db.table("likes").select("id").eq("user_id", liked_user_id).eq("liked_user_id", user_id).execute()
        return bool(res.data)
    except Exception:
        return False


def pass_user(user_id: str, passed_user_id: str):
    db = get_admin_client()
    try:
        db.table("passes").insert({
            "user_id": user_id,
            "passed_user_id": passed_user_id,
        }).execute()
    except Exception:
        pass


def undo_last_action(user_id: str):
    db = get_admin_client()
    try:
        db.table("likes").delete().eq("user_id", user_id).order("created_at", desc=True).limit(1).execute()
    except Exception:
        pass


def get_liked_user_ids(user_id: str) -> List[str]:
    db = get_admin_client()
    try:
        res = db.table("likes").select("liked_user_id").eq("user_id", user_id).execute()
        return [r["liked_user_id"] for r in (res.data or [])]
    except Exception:
        return []


def get_passed_user_ids(user_id: str) -> List[str]:
    db = get_admin_client()
    try:
        res = db.table("passes").select("passed_user_id").eq("user_id", user_id).execute()
        return [r["passed_user_id"] for r in (res.data or [])]
    except Exception:
        return []


def get_who_liked_me(user_id: str) -> List[Dict]:
    db = get_admin_client()
    try:
        res = (
            db.table("likes")
            .select("user_id, users(*)")
            .eq("liked_user_id", user_id)
            .execute()
        )
        return [r.get("users") for r in (res.data or []) if r.get("users")]
    except Exception:
        return []


# ─── MATCHES ─────────────────────────────────────────────────────────────────

def get_user_matches(user_id: str) -> List[Dict]:
    """Return all active matches with the other user's profile."""
    db = get_admin_client()
    try:
        res = (
            db.table("matches")
            .select("*, user1:user1_id(*), user2:user2_id(*)")
            .or_(f"user1_id.eq.{user_id},user2_id.eq.{user_id}")
            .eq("is_active", True)
            .order("matched_at", desc=True)
            .execute()
        )
        matches = []
        for m in (res.data or []):
            other = m.get("user2") if m["user1_id"] == user_id else m.get("user1")
            if other:
                matches.append({
                    "match_id": m["id"],
                    "matched_at": m["matched_at"],
                    "other_user": other,
                })
        return matches
    except Exception:
        return []


def create_match(user1_id: str, user2_id: str) -> Optional[Dict]:
    db = get_admin_client()
    uid1 = min(user1_id, user2_id)
    uid2 = max(user1_id, user2_id)
    try:
        res = db.table("matches").insert({"user1_id": uid1, "user2_id": uid2}).execute()
        return res.data[0] if res.data else None
    except Exception:
        return None


def unmatch(match_id: str):
    db = get_admin_client()
    try:
        db.table("matches").update({"is_active": False}).eq("id", match_id).execute()
    except Exception:
        pass


# ─── MESSAGES ────────────────────────────────────────────────────────────────

def get_messages(match_id: str, limit: int = 50) -> List[Dict]:
    db = get_admin_client()
    try:
        res = (
            db.table("messages")
            .select("*")
            .eq("match_id", match_id)
            .order("created_at", desc=False)
            .limit(limit)
            .execute()
        )
        return res.data or []
    except Exception:
        return []


def send_message(match_id: str, sender_id: str, receiver_id: str, message: str, media_url: str = None) -> Optional[Dict]:
    db = get_admin_client()
    payload = {
        "match_id": match_id,
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "message": message,
    }
    if media_url:
        payload["media_url"] = media_url
    try:
        res = db.table("messages").insert(payload).execute()
        return res.data[0] if res.data else None
    except Exception:
        return None


def mark_messages_read(match_id: str, user_id: str):
    db = get_admin_client()
    try:
        db.table("messages").update({"is_read": True}).eq("match_id", match_id).eq("receiver_id", user_id).execute()
    except Exception:
        pass


def get_unread_count(user_id: str) -> int:
    db = get_admin_client()
    try:
        res = db.table("messages").select("id", count="exact").eq("receiver_id", user_id).eq("is_read", False).execute()
        return res.count or 0
    except Exception:
        return 0


# ─── BLOCKS & REPORTS ────────────────────────────────────────────────────────

def block_user(blocker_id: str, blocked_user_id: str):
    db = get_admin_client()
    try:
        db.table("blocks").insert({"blocker_id": blocker_id, "blocked_user_id": blocked_user_id}).execute()
    except Exception:
        pass


def unblock_user(blocker_id: str, blocked_user_id: str):
    db = get_admin_client()
    try:
        db.table("blocks").delete().eq("blocker_id", blocker_id).eq("blocked_user_id", blocked_user_id).execute()
    except Exception:
        pass


def get_blocked_user_ids(user_id: str) -> List[str]:
    db = get_admin_client()
    try:
        res = db.table("blocks").select("blocked_user_id").eq("blocker_id", user_id).execute()
        return [r["blocked_user_id"] for r in (res.data or [])]
    except Exception:
        return []


def report_user(reporter_id: str, reported_user_id: str, reason: str, details: str = ""):
    db = get_admin_client()
    try:
        db.table("reports").insert({
            "reporter_id": reporter_id,
            "reported_user_id": reported_user_id,
            "reason": reason,
            "details": details,
        }).execute()
    except Exception:
        pass


# ─── NOTIFICATIONS ───────────────────────────────────────────────────────────

def get_notifications(user_id: str, limit: int = 20) -> List[Dict]:
    db = get_admin_client()
    try:
        res = (
            db.table("notifications")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []
    except Exception:
        return []


def mark_notifications_read(user_id: str):
    db = get_admin_client()
    try:
        db.table("notifications").update({"is_read": True}).eq("user_id", user_id).execute()
    except Exception:
        pass


def get_unread_notification_count(user_id: str) -> int:
    db = get_admin_client()
    try:
        res = db.table("notifications").select("id", count="exact").eq("user_id", user_id).eq("is_read", False).execute()
        return res.count or 0
    except Exception:
        return 0


# ─── EVENTS ──────────────────────────────────────────────────────────────────

def get_events(limit: int = 20) -> List[Dict]:
    db = get_admin_client()
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    try:
        res = (
            db.table("events")
            .select("*, creator:creator_id(*)")
            .eq("is_active", True)
            .gte("event_date", now)
            .order("event_date")
            .limit(limit)
            .execute()
        )
        return res.data or []
    except Exception:
        return []


def create_event(data: Dict) -> Optional[Dict]:
    db = get_admin_client()
    try:
        res = db.table("events").insert(data).execute()
        return res.data[0] if res.data else None
    except Exception:
        return None


def join_event(event_id: str, user_id: str):
    db = get_admin_client()
    try:
        db.table("event_attendees").insert({"event_id": event_id, "user_id": user_id}).execute()
    except Exception:
        pass


def leave_event(event_id: str, user_id: str):
    db = get_admin_client()
    try:
        db.table("event_attendees").delete().eq("event_id", event_id).eq("user_id", user_id).execute()
    except Exception:
        pass


def get_event_attendees(event_id: str) -> List[Dict]:
    db = get_admin_client()
    try:
        res = (
            db.table("event_attendees")
            .select("*, user:user_id(*)")
            .eq("event_id", event_id)
            .execute()
        )
        return [r["user"] for r in (res.data or []) if r.get("user")]
    except Exception:
        return []



def delete_user_account(user_id: str):
    """
    Hard-delete a user profile row.
    Auth user deletion is done in settings.py via admin.auth.admin.delete_user().
    """
    db = get_admin_client()
    # Clean up related rows first to avoid FK constraint errors
    for table, col in [
        ("messages", "sender_id"), ("messages", "receiver_id"),
        ("likes", "user_id"), ("likes", "liked_user_id"),
        ("passes", "user_id"), ("passes", "passed_user_id"),
        ("blocks", "blocker_id"), ("blocks", "blocked_user_id"),
        ("reports", "reporter_id"), ("reports", "reported_user_id"),
    ]:
        try:
            db.table(table).delete().eq(col, user_id).execute()
        except Exception:
            pass
    # Delete profile row
    try:
        db.table("users").delete().eq("id", user_id).execute()
    except Exception as e:
        raise RuntimeError(f"Could not delete user profile: {e}")

# ─── ADMIN ───────────────────────────────────────────────────────────────────

def get_all_reports() -> List[Dict]:
    db = get_admin_client()
    try:
        res = (
            db.table("reports")
            .select("*, reporter:reporter_id(name,email), reported:reported_user_id(name,email)")
            .order("created_at", desc=True)
            .execute()
        )
        return res.data or []
    except Exception:
        return []


def ban_user(user_id: str):
    update_user(user_id, {"is_active": False})


def get_stats() -> Dict:
    db = get_admin_client()
    results = {}
    for table, key in [("users", "total_users"), ("matches", "total_matches"),
                        ("messages", "total_messages")]:
        try:
            results[key] = db.table(table).select("id", count="exact").execute().count or 0
        except Exception:
            results[key] = 0
    try:
        results["pending_reports"] = db.table("reports").select("id", count="exact").eq("status", "pending").execute().count or 0
    except Exception:
        results["pending_reports"] = 0
    return results
