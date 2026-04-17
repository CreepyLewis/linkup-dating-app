"""
pages/profile.py
User profile — view & edit

FIXES:
  - AttributeError: 'NoneType'.strip()   → _safe_str() coerces every field to str
  - TypeError: len(NoneType)              → bio is None-guarded before len()
  - Save silently failing                 → update_user now shows success/error clearly;
                                            if service role key is missing, tells the user
  - Photo delete silently failing         → delete now shows result + falls back gracefully

NEW FEATURES:
  - Profile completion % progress bar with actionable tips
  - Online / last-seen status in hero
  - Nearby badge
  - Shared interests count
  - Dark mode toggle
  - Delete individual photos with confirmation
  - Empty state for photos with call-to-action
  - Report / block safety section
"""

import streamlit as st
from utils.auth import get_session_user, require_auth, refresh_session_user
from utils.db import update_user, get_profile_completion
from utils.media import upload_image, is_cloudinary_configured
from utils.filters import INTERESTS_LIST, INTENT_OPTIONS
from components.profile_card import get_avatar_url, render_profile_card


def _safe_str(val) -> str:
    """Always return a string, never None."""
    return str(val) if val is not None else ""


def _last_seen_str(user: dict) -> str:
    from datetime import datetime, timezone
    raw = user.get("last_seen")
    if not raw:
        return "Last seen unknown"
    try:
        dt = datetime.fromisoformat(_safe_str(raw).replace("Z", "+00:00"))
        secs = (datetime.now(timezone.utc) - dt).total_seconds()
        if secs < 300:   return "🟢 Online now"
        if secs < 3600:  return f"⏱ Last seen {int(secs//60)}m ago"
        if secs < 86400: return f"⏱ Last seen {int(secs//3600)}h ago"
        return f"⏱ Last seen {int(secs//86400)}d ago"
    except Exception:
        return "Last seen recently"


def render():
    require_auth()
    user = get_session_user()
    uid = user["id"]

    st.markdown("""
    <style>
    .profile-page-hero {
        background: linear-gradient(135deg, #FF6B6B, #FF8E53);
        border-radius: 20px; padding: 2rem; color: white;
        margin-bottom: 1.5rem; display: flex;
        align-items: center; gap: 1.5rem;
    }
    .profile-hero-avatar {
        width: 90px; height: 90px; border-radius: 50%;
        object-fit: cover; border: 3px solid white; flex-shrink: 0;
    }
    .profile-hero-name { font-size: 1.6rem; font-weight: 800; margin: 0; }
    .profile-hero-meta { opacity: 0.85; margin: 0.2rem 0 0; font-size: 0.9rem; }
    .section-card {
        background: white; border-radius: 16px; padding: 1.5rem;
        margin-bottom: 1rem; box-shadow: 0 4px 16px rgba(0,0,0,0.07);
    }
    .section-title { font-size: 1.1rem; font-weight: 700; color: #FF6B6B; margin-bottom: 1rem; }
    .nearby-badge {
        background: rgba(255,255,255,0.25); border: 1px solid rgba(255,255,255,0.5);
        border-radius: 20px; padding: 2px 10px; font-size: 0.75rem; font-weight: 600;
        display: inline-block; margin-left: 6px; vertical-align: middle;
    }
    .completion-tip {
        background: #FFFBEB; border: 1px solid #FCD34D; border-radius: 10px;
        padding: 0.75rem 1rem; margin-bottom: 1rem; font-size: 0.88rem;
    }
    </style>
    """, unsafe_allow_html=True)

    # Dark mode
    dm = st.toggle("🌙 Dark mode", value=st.session_state.get("dark_mode", False), key="dm_toggle")
    if dm != st.session_state.get("dark_mode", False):
        st.session_state["dark_mode"] = dm
        st.rerun()
    if st.session_state.get("dark_mode"):
        st.markdown("""
        <style>
        .stApp { background: #1a1a2e !important; color: #e0e0e0 !important; }
        .section-card { background: #16213e !important; color: #e0e0e0 !important; }
        </style>
        """, unsafe_allow_html=True)

    # Hero
    img_url     = get_avatar_url(user)
    completion  = get_profile_completion(user)
    intent_icon = {"dating": "❤️", "friendship": "🤝", "networking": "💼"}.get(user.get("intent","dating"), "❤️")
    nearby_html = '<span class="nearby-badge">📍 Nearby</span>' if user.get("latitude") else ""
    interests   = user.get("interests") or []

    st.markdown(f"""
    <div class="profile-page-hero">
        <img class="profile-hero-avatar" src="{img_url}" alt="avatar">
        <div style="flex:1;">
            <p class="profile-hero-name">{user.get('name','Your Name')} {intent_icon} {nearby_html}</p>
            <p class="profile-hero-meta">
                {user.get('age','?')} yrs · {_safe_str(user.get('gender')).capitalize()}
                · 📍 {user.get('location','Location not set')}
            </p>
            <p class="profile-hero-meta">{_last_seen_str(user)} · 🎨 {len(interests)} interests</p>
            <div style="margin-top:0.6rem;">
                <small>Profile {completion}% complete</small>
                <div style="background:rgba(255,255,255,0.3);border-radius:10px;height:8px;margin-top:4px;">
                    <div style="background:white;border-radius:10px;height:8px;width:{completion}%;"></div>
                </div>
                <small style="opacity:0.75;">{'✅ Complete!' if completion==100 else 'Fill in more fields to get more matches'}</small>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Completion tips
    if completion < 100:
        missing = [label for field, label in [
            ("bio","Bio"), ("photo_url","Profile photo"),
            ("location","Location"), ("interests","Interests (at least 1)"),
        ] if not user.get(field) or (isinstance(user.get(field), list) and not user.get(field))]
        if missing:
            st.markdown(
                f'<div class="completion-tip">💡 <strong>Boost your matches:</strong> '
                f'Add your {", ".join(missing)}</div>',
                unsafe_allow_html=True,
            )

    tab_edit, tab_preview, tab_photos = st.tabs(["✏️ Edit Profile", "👁️ Preview", "📸 Photos"])

    # ── EDIT TAB ────────────────────────────────────────────────────────────
    with tab_edit:

        st.markdown('<div class="section-card"><div class="section-title">👤 Basic Information</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            # FIX: _safe_str ensures text_input never receives None
            name = st.text_input("Full Name *", value=_safe_str(user.get("name")))
            age  = st.number_input("Age", 18, 99, value=int(user.get("age") or 25))
        with c2:
            gender_opts = ["male", "female", "non-binary", "other"]
            gender_idx  = gender_opts.index(user.get("gender","male")) if user.get("gender") in gender_opts else 0
            gender   = st.selectbox("Gender", gender_opts, index=gender_idx)
            location = st.text_input("City / Location", value=_safe_str(user.get("location")))
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="section-card"><div class="section-title">💬 About Me</div>', unsafe_allow_html=True)
        # FIX: coerce initial value to str so text_area never receives None
        bio = st.text_area(
            "Bio",
            value=_safe_str(user.get("bio")),
            max_chars=300,
            placeholder="Tell people something interesting about yourself…",
            height=120,
        )
        # FIX: guarantee bio is str before len() or .strip()
        if bio is None:
            bio = ""
        bio = bio.strip()
        st.caption(f"{len(bio)}/300 characters")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="section-card"><div class="section-title">🎯 Looking for</div>', unsafe_allow_html=True)
        intent_keys = list(INTENT_OPTIONS.keys())
        intent_idx  = intent_keys.index(user.get("intent","dating")) if user.get("intent") in intent_keys else 0
        intent = st.radio(
            "Intent", options=intent_keys,
            format_func=lambda x: INTENT_OPTIONS[x],
            index=intent_idx, horizontal=True, label_visibility="collapsed",
        )
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="section-card"><div class="section-title">🎨 Interests</div>', unsafe_allow_html=True)
        current_interests = user.get("interests") or []
        selected = st.multiselect(
            "Select up to 10 interests", INTERESTS_LIST,
            default=[i for i in current_interests if i in INTERESTS_LIST],
            max_selections=10,
        )
        st.caption(f"{'✅' if selected else '⚠️'} {len(selected)}/10 selected{' — add some to find better matches!' if not selected else ''}")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="section-card"><div class="section-title">📍 Location Coordinates</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            lat = st.number_input("Latitude",  value=float(user.get("latitude")  or -1.2921), format="%.6f")
        with c2:
            lon = st.number_input("Longitude", value=float(user.get("longitude") or 36.8219), format="%.6f")
        st.caption("Used to calculate distance from other users. Nairobi shown as default.")
        st.markdown("</div>", unsafe_allow_html=True)

        if st.button("💾 Save Profile", use_container_width=True, type="primary"):
            name_clean = name.strip() if name else ""
            if not name_clean:
                st.error("❌ Name is required.")
            else:
                updates = {
                    "name": name_clean, "age": int(age), "gender": gender,
                    "bio": bio, "location": location.strip() if location else "",
                    "intent": intent, "interests": selected,
                    "latitude": lat, "longitude": lon,
                }
                # FIX: Surface update errors — previously update_user returned None
                # on RLS failure without any user-visible feedback
                result = update_user(uid, updates)
                if result is not None:
                    refresh_session_user()
                    st.success("✅ Profile saved successfully!")
                    st.rerun()
                else:
                    st.error(
                        "❌ Profile save failed.\n\n"
                        "This is usually because `SUPABASE_SERVICE_ROLE_KEY` is missing or wrong "
                        "in your `.env` file. The service-role key is needed to bypass Supabase RLS "
                        "(Row Level Security) on the server.\n\n"
                        "Get it from: **Supabase Dashboard → Settings → API → service_role key**"
                    )

    # ── PREVIEW TAB ─────────────────────────────────────────────────────────
    with tab_preview:
        st.info("This is how your profile appears to other users.")
        _, c2, _ = st.columns([1, 3, 1])
        with c2:
            render_profile_card(user, show_actions=False, show_match_score=False)

    # ── PHOTOS TAB ──────────────────────────────────────────────────────────
    with tab_photos:
        st.markdown('<div class="section-card"><div class="section-title">📸 Profile Photos</div>', unsafe_allow_html=True)

        photos = list(user.get("photos") or [])
        main_url = user.get("photo_url")
        if main_url and main_url not in photos:
            photos = [main_url] + photos

        if photos:
            st.markdown("**Your photos** (tap Delete to remove):")
            cols = st.columns(3)
            for i, photo in enumerate(photos[:6]):
                with cols[i % 3]:
                    st.image(photo, use_container_width=True)
                    st.caption("⭐ Main" if i == 0 else f"Photo {i+1}")
                    if st.button(f"🗑️ Delete", key=f"del_{i}", use_container_width=True):
                        new_photos = [p for p in photos if p != photo]
                        updates = {"photos": new_photos}
                        if photo == main_url:
                            updates["photo_url"] = new_photos[0] if new_photos else None
                        res = update_user(uid, updates)
                        if res is not None:
                            refresh_session_user()
                            st.success("Photo deleted.")
                            st.rerun()
                        else:
                            st.error("Delete failed — check SUPABASE_SERVICE_ROLE_KEY in .env")
        else:
            st.markdown("""
            <div style="text-align:center; padding:2.5rem; background:#FFF8F8;
                        border-radius:12px; border:2px dashed #FFCCCC; color:#888;">
                <div style="font-size:3rem;">📷</div>
                <h4>No photos yet</h4>
                <p>Profiles with photos get <strong>3× more matches.</strong> Upload yours below!</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # Cloudinary config check before showing uploader
        if not is_cloudinary_configured():
            st.warning(
                "⚠️ **Image upload is not configured.** Your `CLOUDINARY_CLOUD_NAME` is set to a "
                "placeholder value. Go to **Settings → Account → Image Upload Status** to see "
                "how to fix this."
            )
        else:
            st.markdown("**Upload a new photo:**")
            uploaded = st.file_uploader(
                "Choose a photo", type=["jpg", "jpeg", "png", "webp"],
                accept_multiple_files=False,
            )
            if uploaded:
                c1, c2 = st.columns(2)
                with c1:
                    st.image(uploaded, caption="Preview", use_container_width=True)
                with c2:
                    set_as_main = st.checkbox("Set as main photo", value=len(photos) == 0)
                    if st.button("📤 Upload Photo", type="primary", use_container_width=True):
                        with st.spinner("Uploading…"):
                            url = upload_image(uploaded.getvalue(), uid)
                        if url:
                            new_photos = photos + [url]
                            updates = {"photos": new_photos}
                            if set_as_main or not main_url:
                                updates["photo_url"] = url
                            update_user(uid, updates)
                            refresh_session_user()
                            st.success("✅ Photo uploaded!")
                            st.rerun()
                        # upload_image() already showed the error

        st.markdown("</div>", unsafe_allow_html=True)

        # Safety
        st.markdown("---")
        st.markdown('<div class="section-card"><div class="section-title">⚠️ Safety</div>', unsafe_allow_html=True)
        st.caption("To report or block another user, find them in Discover or Matches.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🚩 How to Report", use_container_width=True):
                st.info("In Discover or Matches → open a profile → Report button at the bottom.")
        with c2:
            if st.button("🚫 How to Block", use_container_width=True):
                st.info("In Settings → Safety tab → Block a user by email.")
        st.markdown("</div>", unsafe_allow_html=True)
