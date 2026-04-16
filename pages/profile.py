"""
pages/profile.py
User profile - view & edit your own profile
FIXES:
  - AttributeError: 'NoneType' object has no attribute 'strip'  → bio/name/location always coerced to str
  - TypeError: object of type 'NoneType' has no len()           → bio guaranteed non-None before len()
NEW FEATURES:
  - Profile completion % bar with tips
  - Shared interests count in hero
  - Last seen / online status
  - Nearby badge
  - Dark mode toggle
  - Delete photo button
  - Report/block user hint section
  - Empty state message for photos
"""

import streamlit as st
from utils.auth import get_session_user, require_auth, refresh_session_user
from utils.db import update_user, get_profile_completion
from utils.media import upload_image
from utils.filters import INTERESTS_LIST, INTENT_OPTIONS
from components.profile_card import get_avatar_url, render_profile_card


def _safe_str(val) -> str:
    """Return val as string; never None."""
    return str(val) if val is not None else ""


def render():
    require_auth()
    user = get_session_user()
    uid = user["id"]

    st.markdown("""
    <style>
    .profile-page-hero {
        background: linear-gradient(135deg, #FF6B6B, #FF8E53);
        border-radius: 20px;
        padding: 2rem;
        color: white;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        gap: 1.5rem;
    }
    .profile-hero-avatar {
        width: 90px; height: 90px;
        border-radius: 50%;
        object-fit: cover;
        border: 3px solid white;
    }
    .profile-hero-name { font-size: 1.6rem; font-weight: 800; margin: 0; }
    .profile-hero-meta { opacity: 0.85; margin: 0.25rem 0 0 0; }
    .section-card {
        background: white;
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 16px rgba(0,0,0,0.07);
    }
    .section-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #FF6B6B;
        margin-bottom: 1rem;
    }
    .nearby-badge {
        background: rgba(255,255,255,0.25);
        border: 1px solid rgba(255,255,255,0.5);
        border-radius: 20px;
        padding: 2px 10px;
        font-size: 0.78rem;
        font-weight: 600;
        display: inline-block;
        margin-left: 6px;
        vertical-align: middle;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Dark mode ────────────────────────────────────────────────────────────
    dark_mode = st.toggle("🌙 Dark mode", value=st.session_state.get("dark_mode", False), key="dm_toggle")
    if dark_mode != st.session_state.get("dark_mode", False):
        st.session_state["dark_mode"] = dark_mode
        st.rerun()
    if st.session_state.get("dark_mode"):
        st.markdown("""
        <style>
        .stApp { background-color: #1a1a2e !important; color: #e0e0e0 !important; }
        .section-card { background: #16213e !important; color: #e0e0e0 !important; }
        </style>
        """, unsafe_allow_html=True)

    # ── Hero ─────────────────────────────────────────────────────────────────
    img_url = get_avatar_url(user)
    completion = get_profile_completion(user)
    intent_icons = {"dating": "❤️", "friendship": "🤝", "networking": "💼"}
    intent_label = intent_icons.get(user.get("intent", "dating"), "❤️")

    # Last seen / online status
    from datetime import datetime, timezone
    last_seen_raw = user.get("last_seen")
    is_online = False
    last_seen_str = "Last seen unknown"
    if last_seen_raw:
        try:
            last_seen_dt = datetime.fromisoformat(_safe_str(last_seen_raw).replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            delta = now - last_seen_dt
            secs = delta.total_seconds()
            is_online = secs < 300
            if is_online:
                last_seen_str = "🟢 Online now"
            elif secs < 3600:
                last_seen_str = f"Last seen {int(secs // 60)}m ago"
            elif delta.days == 0:
                last_seen_str = f"Last seen {int(secs // 3600)}h ago"
            else:
                last_seen_str = f"Last seen {delta.days}d ago"
        except Exception:
            last_seen_str = "Last seen recently"

    interests = user.get("interests") or []
    interests_count = len(interests)
    nearby_html = '<span class="nearby-badge">📍 Nearby</span>' if user.get("latitude") else ""

    st.markdown(f"""
    <div class="profile-page-hero">
        <img class="profile-hero-avatar" src="{img_url}" alt="{user.get('name','?')}">
        <div style="flex:1;">
            <p class="profile-hero-name">{user.get('name','Your Name')} {intent_label} {nearby_html}</p>
            <p class="profile-hero-meta">
                {user.get('age','?')} years &nbsp;·&nbsp;
                {user.get('gender','').capitalize()} &nbsp;·&nbsp;
                📍 {user.get('location','Location not set')}
            </p>
            <p class="profile-hero-meta" style="margin-top:3px; font-size:0.85rem;">
                {last_seen_str} &nbsp;·&nbsp; 🎨 {interests_count} interests
            </p>
            <div style="margin-top:0.6rem;">
                <small>Profile {completion}% complete</small>
                <div style="background:rgba(255,255,255,0.3); border-radius:10px; height:8px; margin-top:4px;">
                    <div style="background:white; border-radius:10px; height:8px; width:{completion}%;"></div>
                </div>
                <small style="opacity:0.75;">{'✅ Profile complete!' if completion == 100 else 'Fill in more details to get more matches'}</small>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Completion tips
    if completion < 100:
        missing = []
        checks = [("bio", "Bio"), ("photo_url", "Profile photo"),
                  ("location", "Location"), ("interests", "Interests")]
        for field, label in checks:
            val = user.get(field)
            if not val or (isinstance(val, list) and len(val) == 0):
                missing.append(label)
        if missing:
            st.info(f"💡 **Boost your profile:** Add your {', '.join(missing)} to attract more matches!")

    # ── Tabs ─────────────────────────────────────────────────────────────────
    tab_edit, tab_preview, tab_photos = st.tabs(["✏️ Edit Profile", "👁️ Preview", "📸 Photos"])

    # ── EDIT TAB ────────────────────────────────────────────────────────────
    with tab_edit:

        # Basic info
        st.markdown('<div class="section-card"><div class="section-title">👤 Basic Information</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            # FIX: coerce to str so text_input never receives None
            name = st.text_input("Full Name", value=_safe_str(user.get("name")))
            age = st.number_input("Age", 18, 99, value=int(user.get("age") or 25))
        with col2:
            gender_opts = ["male", "female", "non-binary", "other"]
            gender_idx = gender_opts.index(user.get("gender", "male")) if user.get("gender") in gender_opts else 0
            gender = st.selectbox("Gender", gender_opts, index=gender_idx)
            # FIX: coerce to str
            location = st.text_input("City / Location", value=_safe_str(user.get("location")))
        st.markdown("</div>", unsafe_allow_html=True)

        # About
        st.markdown('<div class="section-card"><div class="section-title">💬 About Me</div>', unsafe_allow_html=True)
        # FIX 1: coerce bio initial value to str so text_area never receives None
        bio = st.text_area(
            "Bio",
            value=_safe_str(user.get("bio")),
            max_chars=300,
            placeholder="Tell people something interesting about yourself...",
            height=120,
        )
        # FIX 2: guarantee bio is a non-None string after widget returns
        # (handles the TypeError: object of type 'NoneType' has no len())
        if bio is None:
            bio = ""
        # FIX 3: safe .strip() — bio is now guaranteed str
        # (handles AttributeError: 'NoneType' object has no attribute 'strip')
        bio = bio.strip()
        st.caption(f"{len(bio)}/300 characters")
        st.markdown("</div>", unsafe_allow_html=True)

        # Intent
        st.markdown('<div class="section-card"><div class="section-title">🎯 What are you looking for?</div>', unsafe_allow_html=True)
        intent_keys = list(INTENT_OPTIONS.keys())
        intent_idx = intent_keys.index(user.get("intent", "dating")) if user.get("intent") in intent_keys else 0
        intent = st.radio(
            "Intent",
            options=intent_keys,
            format_func=lambda x: INTENT_OPTIONS[x],
            index=intent_idx,
            horizontal=True,
            label_visibility="collapsed",
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # Interests
        st.markdown('<div class="section-card"><div class="section-title">🎨 Interests</div>', unsafe_allow_html=True)
        current_interests = user.get("interests") or []
        selected = st.multiselect(
            "Select up to 10 interests",
            INTERESTS_LIST,
            default=[i for i in current_interests if i in INTERESTS_LIST],
            max_selections=10,
        )
        if selected:
            st.caption(f"✅ {len(selected)}/10 interests selected")
        else:
            st.caption("No interests selected yet — add some to find better matches!")
        st.markdown("</div>", unsafe_allow_html=True)

        # Location coordinates
        st.markdown('<div class="section-card"><div class="section-title">📍 Location Coordinates (optional)</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            lat = st.number_input("Latitude", value=float(user.get("latitude") or -1.2921), format="%.6f")
        with col2:
            lon = st.number_input("Longitude", value=float(user.get("longitude") or 36.8219), format="%.6f")
        st.caption("Used to show distance to other users. Nairobi default shown.")
        st.markdown("</div>", unsafe_allow_html=True)

        # Save
        if st.button("💾 Save Profile", use_container_width=True, type="primary"):
            name_clean = name.strip() if name else ""
            if not name_clean:
                st.error("Name is required.")
            else:
                updates = {
                    "name": name_clean,
                    "age": int(age),
                    "gender": gender,
                    "bio": bio,           # already stripped above
                    "location": location.strip() if location else "",
                    "intent": intent,
                    "interests": selected,
                    "latitude": lat,
                    "longitude": lon,
                }
                update_user(uid, updates)
                refresh_session_user()
                st.success("✅ Profile updated successfully!")
                st.rerun()

    # ── PREVIEW TAB ─────────────────────────────────────────────────────────
    with tab_preview:
        st.info("This is how your profile looks to others.")
        col1, col2, col3 = st.columns([1, 3, 1])
        with col2:
            render_profile_card(user, show_actions=False, show_match_score=False)

    # ── PHOTOS TAB ──────────────────────────────────────────────────────────
    with tab_photos:
        st.markdown('<div class="section-card"><div class="section-title">📸 Profile Photos</div>', unsafe_allow_html=True)

        photos = user.get("photos") or []
        if user.get("photo_url") and user["photo_url"] not in photos:
            photos = [user["photo_url"]] + photos

        if photos:
            st.markdown("**Current Photos:**")
            cols = st.columns(3)
            for i, photo in enumerate(photos[:6]):
                with cols[i % 3]:
                    st.image(photo, use_container_width=True)
                    label = "⭐ Main photo" if i == 0 else f"Photo {i+1}"
                    st.caption(label)
                    # Delete photo
                    if st.button("🗑️ Delete", key=f"del_photo_{i}", use_container_width=True):
                        new_photos = [p for p in photos if p != photo]
                        updates = {"photos": new_photos}
                        if photo == user.get("photo_url"):
                            updates["photo_url"] = new_photos[0] if new_photos else None
                        update_user(uid, updates)
                        refresh_session_user()
                        st.success("Photo deleted.")
                        st.rerun()
        else:
            # Empty state
            st.markdown("""
            <div style="text-align:center; padding:2.5rem; color:#888;
                        background:#FFF8F8; border-radius:12px; border:2px dashed #FFCCCC;">
                <div style="font-size:3rem;">📷</div>
                <h4 style="margin:0.5rem 0;">No photos yet</h4>
                <p style="margin:0;">Profiles with photos get <strong>3× more matches</strong>. Upload one below!</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("**Upload New Photo:**")
        uploaded = st.file_uploader(
            "Choose a photo",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=False,
        )

        if uploaded:
            col1, col2 = st.columns(2)
            with col1:
                st.image(uploaded, caption="Preview", use_container_width=True)
            with col2:
                set_as_main = st.checkbox("Set as main profile photo", value=len(photos) == 0)
                if st.button("📤 Upload Photo", type="primary", use_container_width=True):
                    with st.spinner("Uploading..."):
                        url = upload_image(uploaded.getvalue(), uid)
                    if url:
                        new_photos = list(photos) + [url]
                        updates = {"photos": new_photos}
                        if set_as_main or not user.get("photo_url"):
                            updates["photo_url"] = url
                        update_user(uid, updates)
                        refresh_session_user()
                        st.success("✅ Photo uploaded!")
                        st.rerun()
                    else:
                        st.error("Upload failed. Check your Cloudinary settings.")

        st.markdown("</div>", unsafe_allow_html=True)

        # Safety section
        st.markdown("---")
        st.markdown('<div class="section-card"><div class="section-title">⚠️ Safety & Privacy</div>', unsafe_allow_html=True)
        st.caption("Report or block users from their profile card in Discover or Matches.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🚩 How to Report a User", use_container_width=True):
                st.info("Open any profile card → tap the ⋮ menu → select **Report**.")
        with col2:
            if st.button("🚫 How to Block a User", use_container_width=True):
                st.info("Open any profile card → tap the ⋮ menu → select **Block**.")
        st.markdown("</div>", unsafe_allow_html=True)
