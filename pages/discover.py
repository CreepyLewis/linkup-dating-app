"""
pages/discover.py
Swipe / discover page - like or pass profiles
"""

import streamlit as st
from utils.auth import get_session_user, require_auth, is_premium
from utils.db import (
    get_discover_profiles, like_user, pass_user, undo_last_action
)
from utils.matching import rank_profiles
from utils.filters import (
    INTERESTS_LIST, GENDER_OPTIONS, INTENT_OPTIONS, apply_filters
)
from components.profile_card import render_profile_card, render_report_block_buttons


def render():
    require_auth()
    user = get_session_user()
    uid = user["id"]

    st.markdown("""
    <style>
    .discover-header {
        text-align: center;
        margin-bottom: 1.5rem;
    }
    .discover-header h1 {
        background: linear-gradient(135deg, #FF6B6B, #FF8E53);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2rem;
        font-weight: 900;
    }
    .filter-panel {
        background: white;
        border-radius: 16px;
        padding: 1.25rem;
        box-shadow: 0 4px 16px rgba(0,0,0,0.08);
        margin-bottom: 1rem;
    }
    .empty-state {
        text-align: center;
        padding: 3rem 1rem;
        color: #888;
    }
    .empty-state .emoji { font-size: 4rem; }
    </style>
    <div class="discover-header">
        <h1>🔥 Discover</h1>
        <p style="color:#888;">Find people near you</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Filter Sidebar ──────────────────────────────────────────────────────
    with st.expander("🔧 Filters & Preferences", expanded=False):
        st.markdown('<div class="filter-panel">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)

        with col1:
            age_range = st.slider(
                "Age Range",
                18, 80,
                (user.get("age_min", 18), user.get("age_max", 60)),
                key="filter_age"
            )
            gender_pref = st.selectbox(
                "Show me",
                GENDER_OPTIONS,
                index=GENDER_OPTIONS.index(user.get("gender_preference", "any")),
                key="filter_gender"
            )

        with col2:
            max_dist = st.slider(
                "Max Distance (km)", 1, 200, user.get("max_distance", 50), key="filter_dist"
            )
            intent_key = st.selectbox(
                "Intent",
                list(INTENT_OPTIONS.keys()),
                format_func=lambda x: INTENT_OPTIONS[x],
                index=list(INTENT_OPTIONS.keys()).index(user.get("intent", "dating")),
                key="filter_intent"
            )

        selected_interests = st.multiselect(
            "Interests (filter by shared interests)",
            INTERESTS_LIST,
            key="filter_interests"
        )

        has_photo = st.checkbox("Has profile photo only", value=True, key="filter_photo")

        if st.button("💾 Save Preferences", key="save_prefs"):
            from utils.db import update_user
            update_user(uid, {
                "age_min": age_range[0],
                "age_max": age_range[1],
                "gender_preference": gender_pref,
                "max_distance": max_dist,
                "intent": intent_key,
            })
            from utils.auth import refresh_session_user
            refresh_session_user()
            st.success("Preferences saved!")
            st.session_state.pop("discover_profiles", None)
            st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    # ── Load Profiles ────────────────────────────────────────────────────────
    if "discover_profiles" not in st.session_state or st.button("🔄 Refresh", key="refresh_discover"):
        with st.spinner("Finding people near you..."):
            raw = get_discover_profiles(user, limit=30)
            ranked = rank_profiles(user, raw)
            # Apply client-side filters
            ranked = apply_filters(ranked, {
                "has_photo": st.session_state.get("filter_photo", True),
            })
            st.session_state["discover_profiles"] = ranked
            st.session_state["discover_index"] = 0

    profiles = st.session_state.get("discover_profiles", [])
    idx = st.session_state.get("discover_index", 0)

    if not profiles:
        st.markdown("""
        <div class="empty-state">
            <div class="emoji">😮</div>
            <h3>No more profiles!</h3>
            <p>You've seen everyone nearby. Try adjusting your filters or check back later.</p>
        </div>
        """, unsafe_allow_html=True)
        return

    if idx >= len(profiles):
        st.markdown("""
        <div class="empty-state">
            <div class="emoji">🎉</div>
            <h3>You're all caught up!</h3>
            <p>Come back later or expand your filters to see more people.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🔄 Start Over", key="start_over"):
            st.session_state.pop("discover_profiles", None)
            st.session_state["discover_index"] = 0
            st.rerun()
        return

    profile = profiles[idx]
    remaining = len(profiles) - idx

    # Counter
    st.markdown(
        f"<div style='text-align:center; color:#AAA; font-size:0.85rem;'>"
        f"Profile {idx + 1} of {len(profiles)} &nbsp;|&nbsp; {remaining} remaining</div>",
        unsafe_allow_html=True
    )

    # Main profile card layout
    col_left, col_center, col_right = st.columns([1, 3, 1])

    with col_center:
        action = render_profile_card(
            profile,
            current_user=user,
            show_actions=True,
            show_match_score=True,
        )

        if action == "like" or action == "super":
            is_match = like_user(uid, profile["id"])
            st.session_state["discover_index"] = idx + 1
            if is_match:
                st.balloons()
                st.success(f"🎉 It's a match with {profile.get('name', 'them')}! Go say hello!")
                st.session_state["discover_index"] = idx + 1
                import time; time.sleep(2)
            st.rerun()

        elif action == "pass":
            pass_user(uid, profile["id"])
            st.session_state["discover_index"] = idx + 1
            st.rerun()

    # Undo button (premium)
    with col_right:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        if is_premium():
            if st.button("↩️ Undo", key="undo_swipe", help="Undo last swipe"):
                undo_last_action(uid)
                if idx > 0:
                    st.session_state["discover_index"] = idx - 1
                st.rerun()
        else:
            st.markdown(
                "<div style='text-align:center; color:#CCC; font-size:0.75rem;'>💎 Undo<br>Premium</div>",
                unsafe_allow_html=True
            )

    # Report / Block current profile
    with st.expander("⚠️ Report or Block this person", expanded=False):
        render_report_block_buttons(profile, user)

    # Who liked me (premium)
    st.markdown("---")
    if is_premium():
        st.subheader("❤️ People who liked you")
        from utils.db import get_who_liked_me
        likers = get_who_liked_me(uid)
        if likers:
            cols = st.columns(min(4, len(likers)))
            for i, liker in enumerate(likers[:4]):
                with cols[i]:
                    from components.profile_card import get_avatar_url
                    st.image(get_avatar_url(liker), width=80)
                    st.caption(f"**{liker.get('name','?')}**, {liker.get('age','?')}")
        else:
            st.info("No likes yet! Keep swiping to get more visibility.")
    else:
        st.info("💎 **Upgrade to Premium** to see who liked you and get unlimited likes!")
        if st.button("⚡ Upgrade to Premium", key="upgrade_btn", type="primary"):
            st.query_params["page"] = "settings"
            st.rerun()
