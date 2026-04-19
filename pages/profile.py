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


def _save_profile(uid, updates):
    """Try saving via update_user, fall back to service client."""
    result = update_user(uid, updates)
    if result is not None:
        return True, None
    try:
        from utils.db import get_service_client
        get_service_client().table("users").update(updates).eq("id", uid).execute()
        return True, None
    except Exception as e:
        return False, str(e)


def render():
    require_auth()
    user = get_session_user()
    uid = user["id"]

    # ── Session state for edit mode ─────────────────────────────────────────
    if "profile_edit_mode" not in st.session_state:
        st.session_state.profile_edit_mode = False

    # ── Styles ──────────────────────────────────────────────────────────────
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600;800&display=swap');

    .profile-page-hero {
        background: linear-gradient(135deg, #FF6B6B 0%, #FF8E53 100%);
        border-radius: 24px;
        padding: 2rem 2rem 1.5rem;
        color: white;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        gap: 1.5rem;
        box-shadow: 0 8px 32px rgba(255,107,107,0.25);
        font-family: 'Sora', sans-serif;
    }
    .profile-hero-avatar {
        width: 96px; height: 96px;
        border-radius: 50%;
        object-fit: cover;
        border: 3px solid white;
        box-shadow: 0 4px 16px rgba(0,0,0,0.2);
        flex-shrink: 0;
    }
    .profile-hero-name { font-size: 1.6rem; font-weight: 800; margin: 0; }
    .profile-hero-meta { opacity: 0.88; margin: 0.3rem 0 0 0; font-size: 0.95rem; }
    .profile-hero-intent {
        display: inline-block;
        background: rgba(255,255,255,0.2);
        border-radius: 20px;
        padding: 2px 12px;
        font-size: 0.85rem;
        margin-top: 0.5rem;
        backdrop-filter: blur(4px);
    }
    .completion-wrap { margin-top: 0.75rem; }
    .completion-track {
        background: rgba(255,255,255,0.25);
        border-radius: 10px;
        height: 6px;
        margin-top: 4px;
        overflow: hidden;
    }
    .completion-fill {
        background: white;
        border-radius: 10px;
        height: 6px;
        transition: width 0.4s ease;
    }

    /* Section cards */
    .section-card {
        background: white;
        border-radius: 18px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 16px rgba(0,0,0,0.06);
        border: 1px solid #FFF0F0;
    }
    .section-title {
        font-size: 1rem;
        font-weight: 700;
        color: #FF6B6B;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }

    /* Read-only view field */
    .field-row {
        display: flex;
        align-items: flex-start;
        padding: 0.55rem 0;
        border-bottom: 1px solid #FFF5F5;
        gap: 0.75rem;
    }
    .field-row:last-child { border-bottom: none; }
    .field-label {
        font-size: 0.8rem;
        font-weight: 600;
        color: #aaa;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        min-width: 110px;
        padding-top: 2px;
    }
    .field-value {
        font-size: 0.97rem;
        color: #333;
        flex: 1;
        word-break: break-word;
    }
    .tag-pill {
        display: inline-block;
        background: #FFF0F0;
        color: #FF6B6B;
        border-radius: 20px;
        padding: 3px 12px;
        font-size: 0.82rem;
        margin: 2px 3px 2px 0;
        font-weight: 600;
    }
    .edit-btn-row {
        display: flex;
        justify-content: flex-end;
        margin-bottom: 0.5rem;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Hero Header ─────────────────────────────────────────────────────────
    img_url = get_avatar_url(user)
    completion = get_profile_completion(user)
    intent_icons = {"dating": "❤️ Dating", "friendship": "🤝 Friendship", "networking": "💼 Networking"}
    intent_label = intent_icons.get(user.get("intent", "dating"), "❤️ Dating")

    st.markdown(f"""
    <div class="profile-page-hero">
        <img class="profile-hero-avatar" src="{img_url}" alt="{user.get('name','?')}">
        <div style="flex:1; min-width:0;">
            <p class="profile-hero-name">{user.get('name','Your Name')}</p>
            <p class="profile-hero-meta">
                {user.get('age','?')} yrs &nbsp;·&nbsp;
                {user.get('gender','').capitalize()} &nbsp;·&nbsp;
                📍 {user.get('location','Location not set')}
            </p>
            <span class="profile-hero-intent">{intent_label}</span>
            <div class="completion-wrap">
                <small>Profile {completion}% complete</small>
                <div class="completion-track">
                    <div class="completion-fill" style="width:{completion}%;"></div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Tabs ────────────────────────────────────────────────────────────────
    tab_info, tab_photos = st.tabs(["👤 Profile", "📸 Photos"])

    # ── PROFILE TAB ─────────────────────────────────────────────────────────
    with tab_info:

        if st.session_state.profile_edit_mode:
            # ── EDIT MODE ──────────────────────────────────────────────────
            st.markdown("#### ✏️ Editing your profile")

            with st.form("edit_profile_form", border=False):

                # Basic Info
                st.markdown('<div class="section-card"><div class="section-title">👤 Basic Information</div>', unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                with c1:
                    name = st.text_input("Full Name", value=user.get("name") or "")
                    age  = st.number_input("Age", 18, 99, value=int(user.get("age") or 25))
                with c2:
                    gender_opts = ["male", "female", "non-binary", "other"]
                    gender_idx  = gender_opts.index(user.get("gender", "male")) if user.get("gender") in gender_opts else 0
                    gender   = st.selectbox("Gender", gender_opts, index=gender_idx)
                    location = st.text_input("City / Location", value=user.get("location") or "")
                st.markdown("</div>", unsafe_allow_html=True)

                # About Me
                st.markdown('<div class="section-card"><div class="section-title">💬 About Me</div>', unsafe_allow_html=True)
                bio = st.text_area(
                    "Bio",
                    value=user.get("bio") or "",
                    max_chars=300,
                    placeholder="Tell people something interesting about yourself...",
                    height=110,
                )
                bio = bio or ""
                st.caption(f"{len(bio)}/300 characters")
                st.markdown("</div>", unsafe_allow_html=True)

                # Intent
                st.markdown('<div class="section-card"><div class="section-title">🎯 Looking For</div>', unsafe_allow_html=True)
                intent_keys = list(INTENT_OPTIONS.keys())
                intent_idx  = intent_keys.index(user.get("intent", "dating")) if user.get("intent") in intent_keys else 0
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

                # Coordinates
                st.markdown('<div class="section-card"><div class="section-title">📍 Location Coordinates</div>', unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                with c1:
                    lat = st.number_input("Latitude",  value=float(user.get("latitude")  or -1.2921), format="%.6f")
                with c2:
                    lon = st.number_input("Longitude", value=float(user.get("longitude") or 36.8219), format="%.6f")
                st.caption("Used to calculate distance to other users. Nairobi default shown.")
                st.markdown("</div>", unsafe_allow_html=True)

                # Form buttons
                col_save, col_cancel = st.columns([1, 1])
                with col_save:
                    submitted = st.form_submit_button("💾 Save Changes", use_container_width=True, type="primary")
                with col_cancel:
                    cancelled = st.form_submit_button("✕ Cancel", use_container_width=True)

            # Handle form submission OUTSIDE the form
            if submitted:
                if not name.strip():
                    st.error("Name is required.")
                else:
                    updates = {
                        "name":      name.strip(),
                        "age":       int(age),
                        "gender":    gender,
                        "bio":       bio.strip(),
                        "location":  (location or "").strip(),
                        "intent":    intent,
                        "interests": selected,
                        "latitude":  lat,
                        "longitude": lon,
                    }
                    with st.spinner("Saving…"):
                        ok, err = _save_profile(uid, updates)
                    if ok:
                        refresh_session_user()
                        st.session_state.profile_edit_mode = False
                        st.success("✅ Profile saved!")
                        st.rerun()
                    else:
                        st.error(f"Save failed: {err}")

            if cancelled:
                st.session_state.profile_edit_mode = False
                st.rerun()

        else:
            # ── VIEW MODE ──────────────────────────────────────────────────
            # Edit button top-right
            st.markdown('<div class="edit-btn-row">', unsafe_allow_html=True)
            if st.button("✏️ Edit Profile", key="enter_edit_mode"):
                st.session_state.profile_edit_mode = True
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

            # Basic info card
            interests_html = "".join(
                f'<span class="tag-pill">{i}</span>'
                for i in (user.get("interests") or [])
            ) or "<span style='color:#bbb;'>None added yet</span>"

            intent_display = INTENT_OPTIONS.get(user.get("intent", ""), user.get("intent", "—"))
            bio_display    = user.get("bio") or "<span style='color:#bbb;'>No bio yet</span>"

            st.markdown(f"""
            <div class="section-card">
                <div class="section-title">👤 Basic Information</div>
                <div class="field-row">
                    <span class="field-label">Name</span>
                    <span class="field-value">{user.get('name','—')}</span>
                </div>
                <div class="field-row">
                    <span class="field-label">Age</span>
                    <span class="field-value">{user.get('age','—')}</span>
                </div>
                <div class="field-row">
                    <span class="field-label">Gender</span>
                    <span class="field-value">{(user.get('gender') or '—').capitalize()}</span>
                </div>
                <div class="field-row">
                    <span class="field-label">Location</span>
                    <span class="field-value">📍 {user.get('location','Not set')}</span>
                </div>
            </div>

            <div class="section-card">
                <div class="section-title">💬 About Me</div>
                <div style="color:#333; font-size:0.97rem; line-height:1.6;">{bio_display}</div>
            </div>

            <div class="section-card">
                <div class="section-title">🎯 Looking For</div>
                <div class="field-value">{intent_display}</div>
            </div>

            <div class="section-card">
                <div class="section-title">🎨 Interests</div>
                <div style="margin-top:0.25rem;">{interests_html}</div>
            </div>
            """, unsafe_allow_html=True)

            # Completion nudge
            if completion < 80:
                missing = []
                if not user.get("bio"):        missing.append("bio")
                if not user.get("location"):   missing.append("location")
                if not user.get("interests"):  missing.append("interests")
                if not user.get("photo_url"):  missing.append("profile photo")
                if missing:
                    st.info(f"💡 Complete your profile by adding: **{', '.join(missing)}**")

    # ── PHOTOS TAB ──────────────────────────────────────────────────────────
    with tab_photos:
        from utils.media import test_storage_connection
        import io

        # Key counter lets us reset the file uploader after a successful upload
        if "uploader_key" not in st.session_state:
            st.session_state.uploader_key = 0

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

        # Build canonical photo list (deduplicated, main photo always first)
        photos = list(user.get("photos") or [])
        main   = user.get("photo_url")
        if main and main not in photos:
            photos.insert(0, main)

        # ── Current photos grid with remove buttons ──────────────────────
        st.markdown('<div class="section-card"><div class="section-title">📸 Your Photos</div>', unsafe_allow_html=True)

        if photos:
            cols = st.columns(3)
            for i, photo_url in enumerate(photos[:6]):
                with cols[i % 3]:
                    st.image(photo_url, use_container_width=True)
                    label = "⭐ Main" if i == 0 else f"Photo {i + 1}"
                    st.caption(label)
                    if st.button("🗑️ Remove", key=f"remove_photo_{i}", use_container_width=True):
                        new_photos = [p for p in photos if p != photo_url]
                        updates = {"photos": new_photos}
                        # If we removed the main photo, promote the next one (or clear it)
                        if photo_url == main:
                            updates["photo_url"] = new_photos[0] if new_photos else None
                        ok, err = _save_profile(uid, updates)
                        if ok:
                            refresh_session_user()
                            st.success("Photo removed.")
                            st.rerun()
                        else:
                            st.error(f"Could not remove photo: {err}")
        else:
            st.info("No photos yet. Upload your first photo below!")

        st.markdown("</div>", unsafe_allow_html=True)

        # ── Upload section ───────────────────────────────────────────────
        st.markdown('<div class="section-card"><div class="section-title">⬆️ Upload New Photo</div>', unsafe_allow_html=True)

        uploaded = st.file_uploader(
            "Choose a photo (JPG, PNG, WEBP) — max 5 MB",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=False,
            key=f"photo_upload_{st.session_state.uploader_key}",
        )

        if uploaded:
            # Resize / compress
            try:
                from PIL import Image
                img = Image.open(uploaded)
                img = img.convert("RGB")
                img.thumbnail((800, 800))
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=85)
                img_bytes = buf.getvalue()
            except Exception:
                img_bytes = uploaded.getvalue()

            c1, c2 = st.columns([1, 1])
            with c1:
                st.image(img_bytes, caption="Preview", use_container_width=True)
            with c2:
                set_as_main = st.checkbox(
                    "Set as main profile photo",
                    value=len(photos) == 0,
                    key="set_as_main_chk",
                )
                st.write("")  # spacer
                if st.button("⬆️ Upload Photo", type="primary", use_container_width=True):
                    if not storage_ok:
                        st.error("Set up Supabase Storage bucket first (see instructions above).")
                    else:
                        with st.spinner("Uploading…"):
                            url = upload_image(img_bytes, uid)
                        if url:
                            # Avoid duplicates
                            new_photos = photos + ([url] if url not in photos else [])
                            updates = {"photos": new_photos}
                            if set_as_main or not user.get("photo_url"):
                                updates["photo_url"] = url
                            ok, err = _save_profile(uid, updates)
                            if ok:
                                refresh_session_user()
                                # Rotate key → clears the file uploader widget
                                st.session_state.uploader_key += 1
                                st.success("✅ Photo uploaded!")
                                st.rerun()
                            else:
                                st.error(f"Save failed: {err}")
                        else:
                            st.error("Upload failed — check your storage bucket settings.")

        st.markdown("</div>", unsafe_allow_html=True)
