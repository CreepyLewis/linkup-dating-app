"""
pages/profile.py
User profile — view & edit your own profile

Fixes in this version:
  - Profile completion updates immediately after Save (session refreshed before rerun)
  - Dark mode toggle is persistent and doesn't loop
  - update_user now uses service-role client so saves actually land in the DB
  - completion bar recalculates from the FRESHLY FETCHED user after save
"""

import streamlit as st
from utils.auth import get_session_user, require_auth, refresh_session_user
from utils.db import update_user, get_profile_completion, get_user_by_id
from utils.media import upload_image, is_cloudinary_configured
from utils.filters import INTERESTS_LIST, INTENT_OPTIONS
from components.profile_card import get_avatar_url, render_profile_card


def _safe_str(val) -> str:
    return str(val) if val is not None else ""


def render():
    require_auth()
    user = get_session_user()
    uid = user["id"]

    # ── Dark mode (persistent, no-loop) ──────────────────────────────────────
    # Initialise once from session_state — never from widget value directly
    if "dark_mode" not in st.session_state:
        st.session_state["dark_mode"] = False

    # Render toggle bound to session_state key directly
    st.toggle("🌙 Dark mode", key="dark_mode")

    if st.session_state["dark_mode"]:
        st.markdown("""
        <style>
        .stApp { background-color: #1a1a2e !important; color: #e0e0e0 !important; }
        .section-card { background: #16213e !important; color: #e0e0e0 !important; }
        .stTextInput input, .stTextArea textarea, .stSelectbox select {
            background-color: #2a2a4a !important; color: #e0e0e0 !important;
        }
        </style>
        """, unsafe_allow_html=True)

    st.markdown("""
    <style>
    .profile-page-hero {
        background: linear-gradient(135deg, #FF6B6B, #FF8E53);
        border-radius: 20px;
        padding: 2rem;
        color: white;
        margin-bottom: 1.5rem;
    }
    .profile-hero-avatar {
        width: 90px; height: 90px;
        border-radius: 50%;
        object-fit: cover;
        border: 3px solid white;
        float: left;
        margin-right: 1.5rem;
    }
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
    </style>
    """, unsafe_allow_html=True)

    # ── Hero ─────────────────────────────────────────────────────────────────
    img_url = get_avatar_url(user)
    completion = get_profile_completion(user)

    from datetime import datetime, timezone
    last_seen_raw = user.get("last_seen")
    last_seen_str = "🟢 Online now"
    if last_seen_raw:
        try:
            last_seen_dt = datetime.fromisoformat(_safe_str(last_seen_raw).replace("Z", "+00:00"))
            delta = datetime.now(timezone.utc) - last_seen_dt
            secs = delta.total_seconds()
            if secs >= 300:
                if secs < 3600:
                    last_seen_str = f"Last seen {int(secs // 60)}m ago"
                elif delta.days == 0:
                    last_seen_str = f"Last seen {int(secs // 3600)}h ago"
                else:
                    last_seen_str = f"Last seen {delta.days}d ago"
        except Exception:
            last_seen_str = "Last seen recently"

    interests = user.get("interests") or []
    intent_icons = {"dating": "❤️", "friendship": "🤝", "networking": "💼"}
    intent_label = intent_icons.get(user.get("intent", "dating"), "❤️")

    st.markdown(f"""
    <div class="profile-page-hero" style="overflow:hidden;">
        <img class="profile-hero-avatar" src="{img_url}" alt="{user.get('name','?')}">
        <div>
            <p style="font-size:1.6rem; font-weight:800; margin:0;">{user.get('name','Your Name')} {intent_label}</p>
            <p style="opacity:0.85; margin:0.25rem 0 0 0;">
                {user.get('age','?')} yrs &nbsp;·&nbsp;
                {_safe_str(user.get('gender','')).capitalize()} &nbsp;·&nbsp;
                📍 {user.get('location','Location not set')}
            </p>
            <p style="opacity:0.8; font-size:0.85rem; margin-top:3px;">
                {last_seen_str} &nbsp;·&nbsp; 🎨 {len(interests)} interests
            </p>
            <div style="margin-top:0.8rem;">
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
        for field, label in [("bio", "Bio"), ("photo_url", "Profile photo"),
                              ("location", "Location"), ("interests", "Interests")]:
            val = user.get(field)
            if not val or (isinstance(val, list) and len(val) == 0):
                missing.append(label)
        if missing:
            st.info(f"💡 **Boost your profile:** Add your {', '.join(missing)} to attract more matches!")

    # ── Tabs ─────────────────────────────────────────────────────────────────
    tab_edit, tab_preview, tab_photos = st.tabs(["✏️ Edit Profile", "👁️ Preview", "📸 Photos"])

    # ── EDIT TAB ─────────────────────────────────────────────────────────────
    with tab_edit:
        st.markdown('<div class="section-card"><div class="section-title">👤 Basic Information</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Full Name", value=_safe_str(user.get("name")))
            age = st.number_input("Age", 18, 99, value=int(user.get("age") or 25))
        with col2:
            gender_opts = ["male", "female", "non-binary", "other"]
            gender_idx = gender_opts.index(user.get("gender", "male")) if user.get("gender") in gender_opts else 0
            gender = st.selectbox("Gender", gender_opts, index=gender_idx)
            location = st.text_input("City / Location", value=_safe_str(user.get("location")))
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="section-card"><div class="section-title">💬 About Me</div>', unsafe_allow_html=True)
        bio = st.text_area(
            "Bio",
            value=_safe_str(user.get("bio")),
            max_chars=300,
            placeholder="Tell people something interesting about yourself...",
            height=120,
        )
        bio = (bio or "").strip()
        st.caption(f"{len(bio)}/300 characters")
        st.markdown("</div>", unsafe_allow_html=True)

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

        st.markdown('<div class="section-card"><div class="section-title">🎨 Interests</div>', unsafe_allow_html=True)
        current_interests = user.get("interests") or []
        selected = st.multiselect(
            "Select up to 10 interests",
            INTERESTS_LIST,
            default=[i for i in current_interests if i in INTERESTS_LIST],
            max_selections=10,
        )
        st.caption(f"{'✅' if selected else '⚠️'} {len(selected)}/10 selected")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="section-card"><div class="section-title">📍 Location Coordinates (optional)</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            lat = st.number_input("Latitude", value=float(user.get("latitude") or -1.2921), format="%.6f")
        with col2:
            lon = st.number_input("Longitude", value=float(user.get("longitude") or 36.8219), format="%.6f")
        st.caption("Used to show distance to others. Nairobi coordinates shown as default.")
        st.markdown("</div>", unsafe_allow_html=True)

        # ── SAVE ─────────────────────────────────────────────────────────────
        col_save, col_status = st.columns([1, 2])
        with col_save:
            save_clicked = st.button("💾 Save Profile", use_container_width=True, type="primary")

        if save_clicked:
            name_clean = (name or "").strip()
            if not name_clean:
                st.error("Name is required.")
            else:
                updates = {
                    "name": name_clean,
                    "age": int(age),
                    "gender": gender,
                    "bio": bio,
                    "location": (location or "").strip(),
                    "intent": intent,
                    "interests": selected,
                    "latitude": lat,
                    "longitude": lon,
                }
                result = update_user(uid, updates)

                if result is not None:
                    # Re-fetch fresh data from DB so completion bar recalculates correctly
                    fresh = get_user_by_id(uid)
                    if fresh:
                        st.session_state["linkup_user"] = fresh
                    new_pct = get_profile_completion(fresh or {**user, **updates})
                    st.success(f"✅ Profile saved! Completion: {new_pct}%")
                    st.rerun()
                else:
                    st.error(
                        "❌ Save failed. Check that **SUPABASE_SERVICE_ROLE_KEY** is set "
                        "correctly in your `.env` file."
                    )

    # ── PREVIEW TAB ──────────────────────────────────────────────────────────
    with tab_preview:
        st.info("This is how your profile looks to others.")
        col1, col2, col3 = st.columns([1, 3, 1])
        with col2:
            render_profile_card(user, show_actions=False, show_match_score=False)

    # ── PHOTOS TAB ───────────────────────────────────────────────────────────
    with tab_photos:
        st.markdown('<div class="section-card"><div class="section-title">📸 Profile Photos</div>', unsafe_allow_html=True)

        photos = list(user.get("photos") or [])
        if user.get("photo_url") and user["photo_url"] not in photos:
            photos = [user["photo_url"]] + photos

        if photos:
            st.markdown("**Current Photos:**")
            cols = st.columns(min(3, len(photos)))
            for i, photo in enumerate(photos[:6]):
                with cols[i % 3]:
                    st.image(photo, use_container_width=True)
                    st.caption("⭐ Main photo" if i == 0 else f"Photo {i + 1}")
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

        if not is_cloudinary_configured():
            st.warning(
                "⚠️ Photo upload is disabled — Cloudinary is not configured.\n\n"
                "Add `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, and `CLOUDINARY_API_SECRET` "
                "to your `.env` file to enable photo uploads."
            )
        else:
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
                            upd = {"photos": new_photos}
                            if set_as_main or not user.get("photo_url"):
                                upd["photo_url"] = url
                            update_user(uid, upd)
                            refresh_session_user()
                            st.success("✅ Photo uploaded!")
                            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

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
