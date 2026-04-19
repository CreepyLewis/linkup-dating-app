"""
utils/db.py
Supabase database connection + all query helpers for LinkUp
"""

import os
import math
from supabase import create_client, Client
from dotenv import load_dotenv
from typing import Optional, List, Dict, Any

load_dotenv()

_supabase_client: Optional[Client] = None
_service_client: Optional[Client] = None


def get_client() -> Client:
    """Return the shared Supabase client (anon key)."""
    global _supabase_client
    if _supabase_client is None:
        url = os.getenv("SUPABASE_URL", "").strip()
        key = os.getenv("SUPABASE_ANON_KEY", "").strip()
        if not url or "your-project-id" in url:
            raise ValueError(
                "SUPABASE_URL is not set. Add it to your .env file."
            )
        if not key or "PASTE_YOUR" in key or len(key) < 30:
            raise ValueError(
                "SUPABASE_ANON_KEY is not set. Add it to your .env file.\n"
                "Get it from: https://supabase.com/dashboard/project/knhkbjyorbsjhwxnchlh/settings/api"
            )
        _supabase_client = create_client(url, key)
    return _supabase_client


def get_service_client() -> Client:
    """Return a service-role Supabase client (for storage uploads and admin ops)."""
    global _service_client
    if _service_client is None:
        url = os.getenv("SUPABASE_URL", "").strip()
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        if not key or len(key) < 30:
            # Fall back to anon client
            return get_client()
        _service_client = create_client(url, key)
    return _service_client


# USER QUERIES

def get_user_by_id(user_id: str) -> Optional[Dict]:
    try:
        res = get_client().table("users").select("*").eq("id", user_id).single().execute()
        return res.data
    except Exception:
        return None


def get_user_by_email(email: str) -> Optional[Dict]:
    try:
        res = get_client().table("users").select("*").eq("email", email).single().execute()
        return res.data
    except Exception:
        return None


def create_user(data: Dict) -> Optional[Dict]:
    """Use service role to bypass RLS on INSERT."""
    try:
        res = get_service_client().table("users").insert(data).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        raise e


def update_user(user_id: str, data: Dict) -> Optional[Dict]:
    """Use service role to bypass RLS on UPDATE."""
    try:
        res = get_service_client().table("users").update(data).eq("id", user_id).execute()
        return res.data[0] if res.data else None
    except Exception:
        return None


def update_last_seen(user_id: str):
    from datetime import datetime, timezone
    try:
        update_user(user_id, {"last_seen": datetime.now(timezone.utc).isoformat()})
    except Exception:
        pass


def get_profile_completion(user: Dict) -> int:
    """Return profile completion 0-100."""
    fields = {
        "name": 15, "age": 10, "gender": 10, "bio": 15,
        "location": 10, "interests": 10, "photo_url": 20, "intent": 10,
    }
    score = 0
    for field, weight in fields.items():
        val = user.get(field)
        if val:
            if isinstance(val, list) and len(val) > 0:
                score += weight
            elif isinstance(val, str) and val.strip():
                score += weight
    return score


# DISCOVERY

def get_discover_profiles(current_user: Dict, limit: int = 20) -> List[Dict]:
    """Return candidate profiles for discovery."""
    db = get_client()
    uid = current_user["id"]

    # Only exclude blocked users - NOT liked/passed, so profiles show again
    blocked_ids = set(get_blocked_user_ids(uid))
    exclude_ids = {uid} | blocked_ids

    query = (
        db.table("users")
        .select("*")
        .eq("profile_hidden", False)
        .eq("is_active", True)
        .neq("id", uid)
    )

    # Gender filter - default to opposite gender
    pref = current_user.get("gender_preference", "any")
    if not pref or pref == "any":
        my_gender = current_user.get("gender", "")
        if my_gender == "male":
            pref = "female"
        elif my_gender == "female":
            pref = "male"
    if pref and pref != "any":
        query = query.eq("gender", pref)

    age_min = current_user.get("age_min") or 18
    age_max = current_user.get("age_max") or 60
    query = query.gte("age", age_min).lte("age", age_max)

    # Remove intent filter - show all intents so more profiles appear
    # Users can still filter by intent in preferences

    res = query.limit(limit + len(exclude_ids) + 10).execute()
    candidates = [u for u in (res.data or []) if u["id"] not in exclude_ids]

    max_dist = current_user.get("max_distance") or 50
    lat1, lon1 = current_user.get("latitude"), current_user.get("longitude")
    if lat1 and lon1:
        candidates = [
            u for u in candidates
            if _within_distance(lat1, lon1, u.get("latitude"), u.get("longitude"), max_dist)
        ]

    return candidates[:limit]


def _within_distance(lat1, lon1, lat2, lon2, max_km: float) -> bool:
    if not lat2 or not lon2:
        return True
    d = get_distance_km(lat1, lon1, lat2, lon2)
    return d is None or d <= max_km


def get_distance_km(lat1, lon1, lat2, lon2) -> Optional[float]:
    if not all([lat1, lon1, lat2, lon2]):
        return None
    R = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# LIKES / PASSES

def like_user(user_id: str, liked_user_id: str) -> bool:
    """Like a user (upsert - safe to call multiple times). Returns True if mutual match."""
    try:
        # Remove any existing pass for this person first
        get_service_client().table("passes").delete()            .eq("user_id", user_id).eq("passed_user_id", liked_user_id).execute()
        # Upsert the like
        get_service_client().table("likes").upsert({
            "user_id": user_id, "liked_user_id": liked_user_id,
        }, on_conflict="user_id,liked_user_id").execute()
        # Check for mutual like
        res = get_client().table("likes").select("id")            .eq("user_id", liked_user_id).eq("liked_user_id", user_id).execute()
        return bool(res.data)
    except Exception:
        return False


def pass_user(user_id: str, passed_user_id: str):
    """Pass a user (upsert - safe to call multiple times)."""
    try:
        # Remove any existing like for this person first
        get_service_client().table("likes").delete()            .eq("user_id", user_id).eq("liked_user_id", passed_user_id).execute()
        # Upsert the pass
        get_service_client().table("passes").upsert({
            "user_id": user_id, "passed_user_id": passed_user_id,
        }, on_conflict="user_id,passed_user_id").execute()
    except Exception:
        pass


def super_like_user(user_id: str, liked_user_id: str) -> bool:
    """Super like - same as like but sends a special notification."""
    is_match = like_user(user_id, liked_user_id)
    try:
        # Notify the liked user that they got a super like
        get_service_client().table("notifications").upsert({
            "user_id": liked_user_id,
            "type": "like",
            "title": "⚡ Someone Super Liked you!",
            "body": "You got a Super Like! Check who it is.",
            "related_user_id": user_id,
            "is_read": False,
        }, on_conflict="user_id,type,related_user_id").execute()
    except Exception:
        pass
    return is_match


def undo_last_action(user_id: str):
    try:
        get_service_client().table("likes").delete().eq("user_id", user_id).order("created_at", desc=True).limit(1).execute()
    except Exception:
        pass


def get_liked_user_ids(user_id: str) -> List[str]:
    try:
        res = get_client().table("likes").select("liked_user_id").eq("user_id", user_id).execute()
        return [r["liked_user_id"] for r in (res.data or [])]
    except Exception:
        return []


def get_passed_user_ids(user_id: str) -> List[str]:
    try:
        res = get_client().table("passes").select("passed_user_id").eq("user_id", user_id).execute()
        return [r["passed_user_id"] for r in (res.data or [])]
    except Exception:
        return []


def get_who_liked_me(user_id: str) -> List[Dict]:
    """Premium: users who liked me."""
    try:
        res = (
            get_client().table("likes")
            .select("user_id, users!likes_user_id_fkey(*)")
            .eq("liked_user_id", user_id)
            .execute()
        )
        return [r.get("users") for r in (res.data or []) if r.get("users")]
    except Exception:
        return []


# MATCHES

def get_user_matches(user_id: str) -> List[Dict]:
    """All active matches with the other user's profile."""
    try:
        res = (
            get_client().table("matches")
            .select("id, matched_at, user1_id, user2_id")
            .or_(f"user1_id.eq.{user_id},user2_id.eq.{user_id}")
            .eq("is_active", True)
            .order("matched_at", desc=True)
            .execute()
        )
        matches = []
        for m in (res.data or []):
            other_id = m["user2_id"] if m["user1_id"] == user_id else m["user1_id"]
            other = get_user_by_id(other_id)
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
    try:
        uid1, uid2 = min(user1_id, user2_id), max(user1_id, user2_id)
        res = get_service_client().table("matches").insert({
            "user1_id": uid1, "user2_id": uid2,
        }).execute()
        return res.data[0] if res.data else None
    except Exception:
        return None


def unmatch(match_id: str):
    try:
        get_service_client().table("matches").update({"is_active": False}).eq("id", match_id).execute()
    except Exception:
        pass


# MESSAGES

def get_messages(match_id: str, limit: int = 50) -> List[Dict]:
    try:
        res = (
            get_client().table("messages")
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
    try:
        payload = {
            "match_id": match_id,
            "sender_id": sender_id,
            "receiver_id": receiver_id,
            "message": message or "",
        }
        if media_url:
            payload["media_url"] = media_url
        res = get_service_client().table("messages").insert(payload).execute()
        return res.data[0] if res.data else None
    except Exception:
        return None


def mark_messages_read(match_id: str, user_id: str):
    try:
        get_service_client().table("messages").update({"is_read": True}).eq("match_id", match_id).eq("receiver_id", user_id).execute()
    except Exception:
        pass


def get_unread_count(user_id: str) -> int:
    try:
        res = get_client().table("messages").select("id", count="exact").eq("receiver_id", user_id).eq("is_read", False).execute()
        return res.count or 0
    except Exception:
        return 0


# BLOCKS & REPORTS

def block_user(blocker_id: str, blocked_user_id: str):
    try:
        get_service_client().table("blocks").insert({
            "blocker_id": blocker_id, "blocked_user_id": blocked_user_id,
        }).execute()
    except Exception:
        pass


def unblock_user(blocker_id: str, blocked_user_id: str):
    try:
        get_service_client().table("blocks").delete().eq("blocker_id", blocker_id).eq("blocked_user_id", blocked_user_id).execute()
    except Exception:
        pass


def get_blocked_user_ids(user_id: str) -> List[str]:
    try:
        res = get_client().table("blocks").select("blocked_user_id").eq("blocker_id", user_id).execute()
        return [r["blocked_user_id"] for r in (res.data or [])]
    except Exception:
        return []


def report_user(reporter_id: str, reported_user_id: str, reason: str, details: str = ""):
    try:
        get_service_client().table("reports").insert({
            "reporter_id": reporter_id,
            "reported_user_id": reported_user_id,
            "reason": reason,
            "details": details,
        }).execute()
    except Exception:
        pass


# NOTIFICATIONS

def get_notifications(user_id: str, limit: int = 20) -> List[Dict]:
    try:
        res = (
            get_client().table("notifications")
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
    try:
        get_service_client().table("notifications").update({"is_read": True}).eq("user_id", user_id).execute()
    except Exception:
        pass


def get_unread_notification_count(user_id: str) -> int:
    try:
        res = get_client().table("notifications").select("id", count="exact").eq("user_id", user_id).eq("is_read", False).execute()
        return res.count or 0
    except Exception:
        return 0


# EVENTS

def get_events(limit: int = 20) -> List[Dict]:
    try:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        res = (
            get_client().table("events")
            .select("*")
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
    try:
        res = get_service_client().table("events").insert(data).execute()
        return res.data[0] if res.data else None
    except Exception:
        return None


def join_event(event_id: str, user_id: str):
    try:
        get_service_client().table("event_attendees").insert({
            "event_id": event_id, "user_id": user_id,
        }).execute()
    except Exception:
        pass


def leave_event(event_id: str, user_id: str):
    try:
        get_service_client().table("event_attendees").delete().eq("event_id", event_id).eq("user_id", user_id).execute()
    except Exception:
        pass


def get_event_attendees(event_id: str) -> List[Dict]:
    try:
        res = (
            get_client().table("event_attendees")
            .select("user_id")
            .eq("event_id", event_id)
            .execute()
        )
        attendees = []
        for r in (res.data or []):
            u = get_user_by_id(r["user_id"])
            if u:
                attendees.append(u)
        return attendees
    except Exception:
        return []


# ADMIN

def get_all_reports() -> List[Dict]:
    try:
        res = (
            get_client().table("reports")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        results = []
        for r in (res.data or []):
            reporter = get_user_by_id(r["reporter_id"]) or {}
            reported = get_user_by_id(r["reported_user_id"]) or {}
            r["reporter"] = {"name": reporter.get("name", "?"), "email": reporter.get("email", "?")}
            r["reported"] = {"name": reported.get("name", "?"), "email": reported.get("email", "?"), "id": reported.get("id")}
            results.append(r)
        return results
    except Exception:
        return []


def ban_user(user_id: str):
    update_user(user_id, {"is_active": False})


def get_stats() -> Dict:
    try:
        db = get_client()
        users    = db.table("users").select("id", count="exact").execute().count or 0
        matches  = db.table("matches").select("id", count="exact").execute().count or 0
        messages = db.table("messages").select("id", count="exact").execute().count or 0
        reports  = db.table("reports").select("id", count="exact").eq("status", "pending").execute().count or 0
        return {"total_users": users, "total_matches": matches, "total_messages": messages, "pending_reports": reports}
    except Exception:
        return {"total_users": 0, "total_matches": 0, "total_messages": 0, "pending_reports": 0}
