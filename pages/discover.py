"""
pages/discover.py
Full discover page:
- Profile completion nudge (photo required)
- Location via browser geolocation
- Multiple photos gallery
- Block/Report from card
- Super like with notification
- Match celebration popup
- Online now / Last seen
"""

import streamlit as st
from utils.auth import get_session_user, require_auth, is_premium, refresh_session_user
from utils.db import (
    get_discover_profiles, like_user, pass_user,
    super_like_user, block_user, report_user, update_user,
)
from utils.filters import GENDER_OPTIONS, INTENT_OPTIONS


def render():
    require_auth()
    user = get_session_user()
    uid  = user["id"]

    # ── Profile completion nudge — photo required ─────────────────────────────
    if not user.get("photo_url"):
        st.markdown("""
        <div style="background:linear-gradient(135deg,#FF6B6B,#FF8E53);
             border-radius:16px;padding:1.5rem 2rem;color:white;margin-bottom:1rem;">
            <h3 style="margin:0 0 0.5rem;">📸 Add a photo first!</h3>
            <p style="margin:0;opacity:0.9;">You need at least one profile photo before you can discover others.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Upload my photo →", type="primary", use_container_width=True):
            st.query_params["page"] = "profile"
            st.rerun()
        return

    # ── Match celebration popup ───────────────────────────────────────────────
    if st.session_state.get("show_match_popup"):
        match_info = st.session_state.pop("show_match_popup")
        _show_match_popup(match_info, user)
        return

    st.markdown("""
    <style>
    h1.dtitle { background:linear-gradient(135deg,#FF6B6B,#FF8E53);
      -webkit-background-clip:text;-webkit-text-fill-color:transparent;
      text-align:center;font-size:2rem;font-weight:900;margin-bottom:0; }
    .online-dot { width:10px;height:10px;border-radius:50%;
      background:#22C55E;display:inline-block;margin-right:4px; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<h1 class="dtitle">🔥 Discover</h1>', unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:#888;margin-bottom:1rem;'>Find people near you</p>",
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
            max_dist = st.slider("Max distance (km)", 1, 500, user.get("max_distance") or 200)

        # Location button
        st.markdown("**📍 Your location**")
        if user.get("latitude") and user.get("longitude"):
            st.success(f"Location set ✓  ({user['latitude']:.3f}, {user['longitude']:.3f})")
        else:
            st.warning("Location not set — distance filter won't work without it.")

        # Streamlit can't directly call browser GPS, but we collect coords manually
        col_lat, col_lon = st.columns(2)
        with col_lat:
            lat_in = st.number_input("Latitude",  value=float(user.get("latitude")  or -1.2921), format="%.4f")
        with col_lon:
            lon_in = st.number_input("Longitude", value=float(user.get("longitude") or 36.8219), format="%.4f")
        st.caption("Default is Nairobi. Change to your actual coordinates.")

        if st.button("Apply & Save filters", type="primary"):
            update_user(uid, {
                "age_min": age_range[0], "age_max": age_range[1],
                "gender_preference": gender_pref, "max_distance": max_dist,
                "latitude": lat_in, "longitude": lon_in,
            })
            refresh_session_user()
            st.session_state.pop("disc_profiles", None)
            st.session_state.pop("disc_idx", None)
            st.rerun()

    # ── Load profiles ─────────────────────────────────────────────────────────
    if "disc_profiles" not in st.session_state:
        with st.spinner("Finding people near you..."):
            profiles = get_discover_profiles(user, limit=100)
        if not profiles:
            st.info("No profiles found. Try widening your filters or distance.")
            return
        st.session_state["disc_profiles"] = profiles
        st.session_state["disc_idx"]      = 0

    profiles = st.session_state["disc_profiles"]
    idx      = st.session_state.get("disc_idx", 0)
    if idx >= len(profiles):
        st.session_state["disc_idx"] = 0
        idx = 0

    profile = profiles[idx]

    # counter
    st.markdown(
        f"<p style='text-align:center;color:#AAA;font-size:0.85rem;'>"
        f"{idx+1} / {len(profiles)}</p>",
        unsafe_allow_html=True,
    )

    # ── Profile card ─────────────────────────────────────────────────────────
    _, col, _ = st.columns([1, 3, 1])
    with col:
        _render_card(profile, user, uid, idx, profiles)


# ── Profile card renderer ──────────────────────────────────────────────────────

def _render_card(profile, user, uid, idx, profiles):
    from components.profile_card import get_avatar_url
    from utils.db import get_distance_km
    from utils.filters import format_distance
    from datetime import datetime, timezone, timedelta

    name      = profile.get("name") or "?"
    age       = profile.get("age") or "?"
    gender    = (profile.get("gender") or "").capitalize()
    intent    = profile.get("intent") or "dating"
    bio       = (profile.get("bio") or "").strip()
    location  = (profile.get("location") or "").strip()
    photos    = profile.get("photos") or []
    main_photo = profile.get("photo_url")
    is_verified = profile.get("is_verified", False)
    icons = {"dating": "❤️", "friendship": "🤝", "networking": "💼"}

    # Build photo list
    all_photos = []
    if main_photo:
        all_photos.append(main_photo)
    for p in photos:
        if p not in all_photos:
            all_photos.append(p)
    if not all_photos:
        all_photos = [get_avatar_url(profile)]

    # Online / last seen
    last_seen_str = profile.get("last_seen") or ""
    online_badge  = ""
    try:
        ls = datetime.fromisoformat(last_seen_str.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - ls
        if delta < timedelta(minutes=10):
            online_badge = '<span style="color:#22C55E;font-size:0.8rem;">● Online now</span>'
        elif delta < timedelta(hours=1):
            mins = int(delta.total_seconds() // 60)
            online_badge = f'<span style="color:#F59E0B;font-size:0.8rem;">● {mins}m ago</span>'
        elif delta < timedelta(days=1):
            hrs = int(delta.total_seconds() // 3600)
            online_badge = f'<span style="color:#AAA;font-size:0.8rem;">● {hrs}h ago</span>'
        else:
            days = delta.days
            online_badge = f'<span style="color:#CCC;font-size:0.8rem;">● {days}d ago</span>'
    except Exception:
        pass

    # Distance
    dist = get_distance_km(
        user.get("latitude"), user.get("longitude"),
        profile.get("latitude"), profile.get("longitude"),
    )
    dist_str = format_distance(dist) if dist is not None else ""

    with st.container(border=True):
        # Photo gallery — use index in session
        photo_key = f"photo_idx_{profile['id']}"
        if photo_key not in st.session_state:
            st.session_state[photo_key] = 0

        pidx = st.session_state[photo_key]
        if pidx >= len(all_photos):
            pidx = 0

        # Show current photo
        st.markdown(
            f'<img src="{all_photos[pidx]}" style="width:100%;height:340px;'
            f'object-fit:cover;border-radius:10px;">',
            unsafe_allow_html=True,
        )

        # Photo navigation (only if multiple photos)
        if len(all_photos) > 1:
            dot_html = " ".join(
                f'<span style="font-size:0.5rem;color:{"#FF6B6B" if i==pidx else "#CCC"};">●</span>'
                for i in range(len(all_photos))
            )
            st.markdown(f"<div style='text-align:center;margin:4px 0;'>{dot_html}</div>",
                        unsafe_allow_html=True)
            pc1, pc2, pc3 = st.columns([1, 3, 1])
            with pc1:
                if st.button("‹", key=f"pprev_{profile['id']}_{idx}"):
                    st.session_state[photo_key] = (pidx - 1) % len(all_photos)
                    st.rerun()
            with pc3:
                if st.button("›", key=f"pnext_{profile['id']}_{idx}"):
                    st.session_state[photo_key] = (pidx + 1) % len(all_photos)
                    st.rerun()

        st.markdown("")

        # Name, age, verified, intent
        verified_html = ' <span style="color:#3B82F6;font-size:0.9rem;" title="Verified">✓</span>' if is_verified else ""
        st.markdown(
            f"<h3 style='margin-bottom:2px;'>{name}, {age}{verified_html}  {icons.get(intent,'')}</h3>",
            unsafe_allow_html=True,
        )

        # Meta
        meta = []
        if location:  meta.append(f"📍 {location}")
        if dist_str:  meta.append(dist_str)
        if gender:    meta.append(gender)
        meta_str = "  ·  ".join(meta)
        st.markdown(
            f"<div style='color:#888;font-size:0.85rem;margin-bottom:4px;'>"
            f"{meta_str}  {online_badge}</div>",
            unsafe_allow_html=True,
        )

        # Bio
        if bio:
            st.write(bio[:200] + ("..." if len(bio) > 200 else ""))

        # Interests
        interests = profile.get("interests") or []
        if interests:
            tags = " ".join(
                f'<span style="background:#FFF0F0;color:#FF6B6B;border:1px solid #FFCCCC;'
                f'border-radius:20px;padding:2px 10px;font-size:0.78rem;">{i}</span>'
                for i in interests[:8]
            )
            st.markdown(tags, unsafe_allow_html=True)

        st.markdown("")

        # ── Action buttons ────────────────────────────────────────────────────
        b1, b2, b3 = st.columns(3)
        with b1:
            if st.button("❌  Pass", key=f"pass_{idx}", use_container_width=True):
                pass_user(uid, profile["id"])
                _next(idx)
        with b2:
            if st.button("💖  Like", key=f"like_{idx}",
                         use_container_width=True, type="primary"):
                matched = like_user(uid, profile["id"])
                if matched:
                    st.session_state["show_match_popup"] = {
                        "name": name, "photo": all_photos[0]
                    }
                _next(idx)
        with b3:
            if st.button("⚡  Super", key=f"super_{idx}", use_container_width=True):
                matched = super_like_user(uid, profile["id"])
                if matched:
                    st.session_state["show_match_popup"] = {
                        "name": name, "photo": all_photos[0]
                    }
                _next(idx)

        # ── Block / Report inline ─────────────────────────────────────────────
        with st.expander("⋯  More options"):
            c1, c2 = st.columns(2)
            with c1:
                if st.button("🚫  Block", key=f"block_{idx}", use_container_width=True):
                    block_user(uid, profile["id"])
                    # Remove from current session list
                    profiles.pop(idx)
                    st.session_state["disc_profiles"] = profiles
                    st.success(f"Blocked {name}.")
                    st.rerun()
            with c2:
                report_reasons = ["Fake profile", "Inappropriate", "Harassment", "Spam", "Underage"]
                reason = st.selectbox("Reason", report_reasons, key=f"rr_{idx}", label_visibility="collapsed")
                if st.button("🚨  Report", key=f"report_{idx}", use_container_width=True):
                    report_user(uid, profile["id"], reason)
                    st.success("Report submitted.")

    # ── Premium: who liked me ────────────────────────────────────────────────
    st.markdown("---")
    if is_premium():
        st.subheader("❤️ People who liked you")
        from utils.db import get_who_liked_me
        likers = get_who_liked_me(uid)
        if likers:
            from components.profile_card import get_avatar_url as gav
            cols = st.columns(min(4, len(likers)))
            for i, liker in enumerate(likers[:4]):
                with cols[i]:
                    st.image(gav(liker), width=80)
                    st.caption(f"**{liker.get('name','?')}**")
        else:
            st.info("No likes yet — keep swiping!")
    else:
        st.info("💎 Upgrade to Premium to see who liked you!")
        if st.button("Upgrade", key="upg_btn", type="primary"):
            st.query_params["page"] = "settings"
            st.rerun()


def _next(idx):
    st.session_state["disc_idx"] = idx + 1
    st.rerun()


# ── Match celebration popup ───────────────────────────────────────────────────

def _show_match_popup(match_info, user):
    from components.profile_card import get_avatar_url
    my_photo    = get_avatar_url(user)
    their_photo = match_info.get("photo") or get_avatar_url({})
    their_name  = match_info.get("name", "them")

    st.markdown(f"""
    <style>
    .match-popup {{
        background: linear-gradient(135deg,#FF6B6B,#FF8E53);
        border-radius: 24px; padding: 2.5rem; text-align: center; color: white;
    }}
    .match-photos {{ display:flex; justify-content:center; gap:1rem; margin:1.5rem 0; }}
    .match-photos img {{
        width: 110px; height: 110px; border-radius: 50%;
        object-fit: cover; border: 4px solid white;
        box-shadow: 0 4px 20px rgba(0,0,0,0.2);
    }}
    .heart-icon {{ font-size: 2.5rem; position:absolute; }}
    </style>
    <div class="match-popup">
        <div style="font-size:1rem;opacity:0.9;letter-spacing:2px;">IT'S A MATCH!</div>
        <h1 style="margin:0.25rem 0;font-size:2.2rem;">🎉</h1>
        <p style="opacity:0.9;margin:0 0 0.5rem;">
            You and <strong>{their_name}</strong> liked each other
        </p>
        <div class="match-photos">
            <img src="{my_photo}">
            <img src="{their_photo}">
        </div>
        <p style="opacity:0.85;font-size:0.9rem;">Say something — don't be shy!</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("💬  Send a message", use_container_width=True, type="primary"):
            st.query_params["page"] = "chat"
            st.rerun()
    with c2:
        if st.button("🔥  Keep swiping", use_container_width=True):
            st.rerun()
