"""
pages/profile.py
User profile - view & edit your own profile
"""

import streamlit as st
from utils.auth import get_session_user, require_auth, refresh_session_user
from utils.db import update_user, get_profile_completion
from utils.media import upload_image
from utils.filters import INTERESTS_LIST, INTENT_OPTIONS
from components.profile_card import get_avatar_url, render_profile_card


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
    .completion-bar { margin-top: 1rem; }
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
    .photo-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 0.75rem;
        margin-top: 1rem;
    }
    .photo-thumb {
        width: 100%;
        aspect-ratio: 1;
        object-fit: cover;
        border-radius: 12px;
        border: 2px solid #FFE4E4;
    }
    </style>
    """, unsafe_allow_html=True)

    # Hero header
    img_url = get_avatar_url(user)
    completion = get_profile_completion(user)
    intent_icons = {"dating": "❤️", "friendship": "🤝", "networking": "💼"}
    intent_label = intent_icons.get(user.get("intent", "dating"), "❤️")

    st.markdown(f"""
    <div class="profile-page-hero">
        <img class="profile-hero-avatar" src="{img_url}" alt="{user.get('name','?')}">
        <div>
            <p class="profile-hero-name">{user.get('name','Your Name')} {intent_label}</p>
            <p class="profile-hero-meta">
                {user.get('age','?')} years &nbsp;·&nbsp;
                {user.get('gender','').capitalize()} &nbsp;·&nbsp;
                📍 {user.get('location','Location not set')}
            </p>
            <div style="margin-top:0.5rem;">
                <small>Profile {completion}% complete</small>
                <div style="background:rgba(255,255,255,0.3); border-radius:10px; height:6px; margin-top:4px;">
                    <div style="background:white; border-radius:10px; height:6px; width:{completion}%;"></div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Tabs: Edit vs Preview
    tab_edit, tab_preview, tab_photos = st.tabs(["✏️ Edit Profile", "👁️ Preview", "📸 Photos"])

    # ── EDIT TAB ────────────────────────────────────────────────────────────
    with tab_edit:

        # Basic info
        st.markdown('<div class="section-card"><div class="section-title">👤 Basic Information</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Full Name", value=user.get("name") or "")
            age = st.number_input("Age", 18, 99, value=int(user.get("age") or 25))
        with col2:
            gender_opts = ["male", "female", "non-binary", "other"]
            gender_idx = gender_opts.index(user.get("gender", "male")) if user.get("gender") in gender_opts else 0
            gender = st.selectbox("Gender", gender_opts, index=gender_idx)
            location = st.text_input("City / Location", value=user.get("location") or "")
        st.markdown("</div>", unsafe_allow_html=True)

        # About
        st.markdown('<div class="section-card"><div class="section-title">💬 About Me</div>', unsafe_allow_html=True)
        bio = st.text_area(
            "Bio",
            value=user.get("bio") or "",
            max_chars=300,
            placeholder="Tell people something interesting about yourself...",
            height=120,
        )
        bio = bio or ""
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
        st.markdown("</div>", unsafe_allow_html=True)

        # Location coordinates (optional)
        st.markdown('<div class="section-card"><div class="section-title">📍 Location Coordinates (optional)</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            lat = st.number_input("Latitude", value=float(user.get("latitude") or -1.2921), format="%.6f")
        with col2:
            lon = st.number_input("Longitude", value=float(user.get("longitude") or 36.8219), format="%.6f")
        st.caption("Used to show distance to other users. Nairobi default shown.")
        st.markdown("</div>", unsafe_allow_html=True)

        # Save button
        if st.button("💾 Save Profile", use_container_width=True, type="primary"):
            if not name.strip():
                st.error("Name is required.")
            else:
                updates = {
                    "name": name.strip(),
                    "age": int(age),
                    "gender": gender,
                    "bio": bio.strip(),
                    "location": location.strip(),
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

    # -- PHOTOS TAB --
    with tab_photos:
        st.markdown('<div class="section-card"><div class="section-title">📸 Profile Photos</div>', unsafe_allow_html=True)

        # Storage setup reminder
        from utils.media import test_storage_connection
        storage_ok = test_storage_connection()
        if not storage_ok:
            st.warning(
                "⚠️ **Storage not set up yet.** Before uploading photos:\n\n"
                "1. Go to [Supabase Storage](https://supabase.com/dashboard/project/knhkbjyorbsjhwxnchlh/storage/buckets)\n"
                "2. Click **New bucket**\n"
                "3. Name it **`avatars`** ← exactly this\n"
                "4. Tick **Public bucket** ← important\n"
                "5. Click Save\n\n"
                "Then come back here and upload your photo."
            )

        # Current photos
        photos = user.get("photos") or []
        if user.get("photo_url") and user["photo_url"] not in photos:
            photos = [user["photo_url"]] + photos

        if photos:
            st.markdown("**Current Photos:**")
            cols = st.columns(3)
            for i, photo in enumerate(photos[:6]):
                with cols[i % 3]:
                    st.image(photo, use_container_width=True)
                    if i == 0:
                        st.caption("Main photo")
        else:
            st.info("No photos yet. Upload your first photo below!")

        # Upload new photo
        st.markdown("**Upload New Photo:**")
        uploaded = st.file_uploader(
            "Choose a photo (JPG, PNG, WEBP)",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=False,
            key="photo_upload",
        )

        if uploaded:
            # Resize image before upload to save storage
            try:
                from PIL import Image
                import io
                img = Image.open(uploaded)
                img = img.convert("RGB")
                img.thumbnail((800, 800))
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=85)
                img_bytes = buf.getvalue()
            except Exception:
                img_bytes = uploaded.getvalue()

            col1, col2 = st.columns(2)
            with col1:
                st.image(img_bytes, caption="Preview", use_container_width=True)
            with col2:
                set_as_main = st.checkbox("Set as main profile photo", value=len(photos) == 0)
                if st.button("Upload Photo", type="primary", use_container_width=True):
                    if not storage_ok:
                        st.error("Set up Supabase Storage bucket first (see instructions above).")
                    else:
                        with st.spinner("Uploading..."):
                            url = upload_image(img_bytes, uid)
                        if url:
                            new_photos = list(photos) + [url]
                            updates = {"photos": new_photos}
                            if set_as_main or not user.get("photo_url"):
                                updates["photo_url"] = url
                            update_user(uid, updates)
                            refresh_session_user()
                            st.success("Photo uploaded!")
                            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)
