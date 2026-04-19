"""
pages/discover.py
Discover page - swipe through opposite gender profiles.
- Shows all profiles, no permanent exclusions
- Like/pass moves to next in current session
- Coming back resets and shows everyone again fresh
- Can re-like someone you passed or re-pass someone you liked
"""

import streamlit as st
from utils.auth import get_session_user, require_auth, is_premium
from utils.db import get_discover_profiles, like_user, pass_user
from utils.filters import INTERESTS_LIST, GENDER_OPTIONS, INTENT_OPTIONS


def render():
    require_auth()
    user = get_session_user()
    uid  = user["id"]

    st.markdown("""
    <style>
    h1.discover-title {
        background: linear-gradient(135deg,#FF6B6B,#FF8E53);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center; font-size: 2rem; font-weight: 900; margin-bottom: 0;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<h1 class="discover-title">🔥 Discover</h1>', unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:#888;margin-bottom:1.5rem;'>Find people near you</p>",
                unsafe_allow_html=True)

    # ── Filters ───────────────────────────────────────────────────────────────
    with st.expander("🔧 Filters", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            age_range   = st.slider("Age range", 18, 80,
                                    (user.get("age_min") or 18, user.get("age_max") or 60))
            gender_pref = st.selectbox("Show me", GENDER_OPTIONS,
                                       index=GENDER_OPTIONS.index(user.get("gender_preference") or "any"))
        with c2:
            max_dist    = st.slider("Max distance (km)", 1, 200, user.get("max_distance") or 100)

        if st.button("Apply filters", type="primary"):
            from utils.db import update_user
            update_user(uid, {
                "age_min": age_range[0], "age_max": age_range[1],
                "gender_preference": gender_pref, "max_distance": max_dist,
            })
            from utils.auth import refresh_session_user
            refresh_session_user()
            # Clear session so profiles reload with new filters
            st.session_state.pop("disc_profiles", None)
            st.session_state.pop("disc_idx", None)
            st.rerun()

    # ── Load profiles (fresh every time page loads unless already in session) ──
    if "disc_profiles" not in st.session_state:
        with st.spinner("Loading profiles..."):
            profiles = get_discover_profiles(user, limit=100)
        if not profiles:
            st.info("No profiles found. Try widening your filters.")
            return
        st.session_state["disc_profiles"] = profiles
        st.session_state["disc_idx"]      = 0

    profiles = st.session_state["disc_profiles"]
    idx      = st.session_state.get("disc_idx", 0)

    # Wrap around — when you reach the end, start again from the beginning
    if idx >= len(profiles):
        st.session_state["disc_idx"] = 0
        idx = 0

    profile = profiles[idx]

    # Counter
    st.markdown(
        f"<p style='text-align:center;color:#AAA;font-size:0.85rem;'>"
        f"{idx + 1} / {len(profiles)}</p>",
        unsafe_allow_html=True,
    )

    # ── Profile card ─────────────────────────────────────────────────────────
    from components.profile_card import get_avatar_url
    from utils.db import get_distance_km
    from utils.filters import format_distance

    _, col, _ = st.columns([1, 3, 1])
    with col:
        with st.container(border=True):
            # Photo
            st.markdown(
                f'<img src="{get_avatar_url(profile)}" '
                f'style="width:100%;height:320px;object-fit:cover;border-radius:10px;">',
                unsafe_allow_html=True,
            )
            st.markdown("")

            # Name & age
            name   = profile.get("name") or "?"
            age    = profile.get("age")  or "?"
            gender = (profile.get("gender") or "").capitalize()
            intent = profile.get("intent") or "dating"
            icons  = {"dating": "❤️", "friendship": "🤝", "networking": "💼"}

            st.markdown(f"### {name}, {age}  {icons.get(intent,'')}")

            # Location / distance
            meta = []
            if profile.get("location"):
                meta.append(f"📍 {profile['location']}")
            dist = get_distance_km(
                user.get("latitude"), user.get("longitude"),
                profile.get("latitude"), profile.get("longitude"),
            )
            if dist is not None:
                meta.append(format_distance(dist))
            if gender:
                meta.append(gender)
            if meta:
                st.caption("  ·  ".join(meta))

            # Bio
            bio = (profile.get("bio") or "").strip()
            if bio:
                st.write(bio[:200] + ("..." if len(bio) > 200 else ""))

            # Interests
            interests = profile.get("interests") or []
            if interests:
                tags = " ".join(
                    f'<span style="background:#FFF0F0;color:#FF6B6B;border:1px solid #FFCCCC;'
                    f'border-radius:20px;padding:2px 10px;font-size:0.8rem;margin:2px 0;">'
                    f'{i}</span>'
                    for i in interests[:8]
                )
                st.markdown(tags, unsafe_allow_html=True)
                st.markdown("")

            # Action buttons
            b1, b2 = st.columns(2)
            with b1:
                if st.button("❌  Pass", key=f"pass_{idx}", use_container_width=True):
                    pass_user(uid, profile["id"])
                    st.session_state["disc_idx"] = idx + 1
                    st.rerun()
            with b2:
                if st.button("💖  Like", key=f"like_{idx}",
                             use_container_width=True, type="primary"):
                    matched = like_user(uid, profile["id"])
                    st.session_state["disc_idx"] = idx + 1
                    if matched:
                        st.balloons()
                        st.success(f"🎉 You matched with {name}!")
                        import time; time.sleep(1.5)
                    st.rerun()

    # ── Premium: see who liked you ────────────────────────────────────────────
    st.markdown("---")
    if is_premium():
        st.subheader("❤️ People who liked you")
        from utils.db import get_who_liked_me
        likers = get_who_liked_me(uid)
        if likers:
            cols = st.columns(min(4, len(likers)))
            for i, liker in enumerate(likers[:4]):
                with cols[i]:
                    st.image(get_avatar_url(liker), width=80)
                    st.caption(f"**{liker.get('name','?')}**, {liker.get('age','?')}")
        else:
            st.info("No likes yet — keep swiping!")
    else:
        st.info("💎 Upgrade to Premium to see who liked you!")
        if st.button("Upgrade to Premium", key="upgrade_btn", type="primary"):
            st.query_params["page"] = "settings"
            st.rerun()
