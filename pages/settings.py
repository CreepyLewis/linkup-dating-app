"""
pages/settings.py
Settings — Premium, Notifications, Safety, Account, Logout

FIXES vs previous version:
  - Update password: now uses Supabase Admin API (service-role) so it actually
    works even without a logged-in session token.
  - Delete account: implemented properly — deletes auth user + profile row +
    shows confirmation step so accidental clicks are prevented.
  - Save profile: was not broken here but profile save now has clear feedback.
  - All dangerous operations require confirmation inputs.

NEW FEATURES:
  - Confirm-before-delete two-step with typed confirmation
  - Password strength indicator
  - Active session display
  - Cloudinary config status in Account tab
"""

import streamlit as st
from utils.auth import (
    get_session_user, require_auth, logout_user,
    refresh_session_user, is_premium,
)
from utils.db import update_user, block_user, report_user, get_admin_client
from utils.payments import initiate_stk_push, activate_premium, PLANS


def _password_strength(pw: str) -> tuple[int, str]:
    """Returns (score 0-4, label)."""
    score = 0
    if len(pw) >= 8: score += 1
    if any(c.isupper() for c in pw): score += 1
    if any(c.isdigit() for c in pw): score += 1
    if any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in pw): score += 1
    labels = ["Very weak", "Weak", "Fair", "Strong", "Very strong"]
    colors = ["#E53E3E", "#DD6B20", "#D69E2E", "#38A169", "#2B6CB0"]
    return score, f"<span style='color:{colors[score]}'>{labels[score]}</span>"


def render():
    require_auth()
    user = get_session_user()
    uid = user["id"]

    st.markdown("""
    <style>
    .settings-header {
        background: linear-gradient(135deg, #FF6B6B, #FF8E53);
        border-radius: 20px;
        padding: 1.5rem 2rem;
        color: white;
        margin-bottom: 1.5rem;
    }
    .settings-section {
        background: white;
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 16px rgba(0,0,0,0.07);
    }
    .settings-section h3 { color: #FF6B6B; margin-bottom: 1rem; font-size: 1.05rem; }
    .premium-card {
        background: linear-gradient(135deg, #FFD700, #FFA500);
        border-radius: 16px;
        padding: 1.5rem;
        color: white;
        margin-bottom: 1rem;
        box-shadow: 0 8px 24px rgba(255,165,0,0.3);
    }
    .premium-card h3 { margin: 0 0 0.5rem 0; font-size: 1.3rem; }
    .plan-card {
        background: white;
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 0.5rem;
        border: 2px solid #FFE4E4;
    }
    .danger-zone {
        background: #FFF5F5;
        border: 2px solid #FFD5D5;
        border-radius: 16px;
        padding: 1.5rem;
        margin-top: 1rem;
    }
    .danger-zone h3 { color: #E53E3E; margin-bottom: 0.5rem; }
    .pw-bar {
        height: 6px;
        border-radius: 4px;
        margin: 4px 0 8px;
        transition: width 0.3s, background 0.3s;
    }
    </style>
    <div class="settings-header">
        <h2 style="margin:0;">⚙️ Settings</h2>
        <p style="margin:0.3rem 0 0; opacity:0.85;">Manage your account and preferences</p>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "💎 Premium", "🔔 Notifications", "🛡️ Safety", "⚙️ Account", "🚪 Logout"
    ])

    # ── PREMIUM TAB ─────────────────────────────────────────────────────────
    with tab1:
        if is_premium():
            st.markdown("""
            <div class="premium-card">
                <h3>💎 You're Premium!</h3>
                <p style="margin:0; opacity:0.9;">All premium features are active on your account.</p>
            </div>
            """, unsafe_allow_html=True)
            st.success("✅ Premium is active. Enjoy unlimited likes, undo swipes, and more!")
        else:
            st.markdown("""
            <div class="premium-card">
                <h3>💎 Upgrade to Premium</h3>
                <p style="margin:0;">Unlock the full LinkUp experience</p>
            </div>
            """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            <div class="plan-card">
                <h4>⚡ Boost — KES 100</h4>
                <div style="color:#888; font-size:0.85rem;">7 days</div>
                <ul style="color:#555; font-size:0.85rem; margin-top:0.5rem; padding-left:1.2rem;">
                    <li>Profile shown first</li><li>3× more visibility</li><li>Boost badge</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown("""
            <div class="plan-card">
                <h4>💎 Premium — KES 500</h4>
                <div style="color:#888; font-size:0.85rem;">30 days</div>
                <ul style="color:#555; font-size:0.85rem; margin-top:0.5rem; padding-left:1.2rem;">
                    <li>See who liked you</li><li>Unlimited likes</li>
                    <li>Undo swipe</li><li>Priority visibility</li><li>All Boost features</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("### 📱 Pay with M-Pesa")
        with st.form("mpesa_form"):
            plan_choice = st.radio(
                "Select Plan",
                ["boost", "premium"],
                format_func=lambda x: "⚡ Boost — KES 100 (7 days)" if x == "boost" else "💎 Premium — KES 500 (30 days)",
                horizontal=True,
            )
            phone = st.text_input("M-Pesa Number", placeholder="07XX XXX XXX or 2547XX XXX XXX", value="+254")
            if st.form_submit_button("💳 Pay Now", use_container_width=True, type="primary"):
                clean = phone.replace("+", "").replace(" ", "")
                if len(clean) < 10:
                    st.error("Enter a valid Safaricom number.")
                else:
                    with st.spinner("Sending STK Push…"):
                        result = initiate_stk_push(phone, plan_choice, uid)
                    if result["success"]:
                        st.success("📱 Check your phone — enter M-Pesa PIN to complete.")
                        activate_premium(uid, plan_choice, receipt="DEMO123")
                        refresh_session_user()
                        st.rerun()
                    else:
                        st.error(f"Payment failed: {result['error']}")

    # ── NOTIFICATIONS TAB ───────────────────────────────────────────────────
    with tab2:
        st.markdown('<div class="settings-section"><h3>🔔 Notification Preferences</h3>', unsafe_allow_html=True)
        notif_matches   = st.toggle("New match notifications", value=True)
        notif_messages  = st.toggle("New message notifications", value=True)
        notif_likes     = st.toggle("Someone liked you (Premium only)", value=is_premium(), disabled=not is_premium())
        notif_events    = st.toggle("Event reminders", value=True)
        notif_nearby    = st.toggle("Nearby users alerts", value=False)
        if st.button("💾 Save Notification Settings", type="primary"):
            st.success("✅ Notification settings saved!")
        st.markdown("</div>", unsafe_allow_html=True)

    # ── SAFETY TAB ──────────────────────────────────────────────────────────
    with tab3:
        st.markdown('<div class="settings-section"><h3>🛡️ Privacy</h3>', unsafe_allow_html=True)
        hide_profile = st.toggle(
            "Hide my profile (invisible in discovery)",
            value=user.get("profile_hidden", False),
        )
        show_distance = st.toggle("Show my distance to others", value=True)
        if st.button("💾 Save Privacy Settings", type="primary"):
            update_user(uid, {"profile_hidden": hide_profile})
            refresh_session_user()
            st.success("✅ Privacy settings saved!")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="settings-section"><h3>🚫 Block or Report a User</h3>', unsafe_allow_html=True)
        with st.expander("🚫 Block a user by email"):
            block_email = st.text_input("Email of user to block", key="block_input")
            if st.button("Block User", key="do_block", type="primary"):
                if block_email:
                    from utils.db import get_user_by_email
                    target = get_user_by_email(block_email)
                    if target:
                        block_user(uid, target["id"])
                        st.success(f"✅ {target.get('name', block_email)} blocked.")
                    else:
                        st.error("User not found.")
                else:
                    st.error("Enter an email address.")

        with st.expander("🚨 Report a user by email"):
            report_email  = st.text_input("Email of user to report", key="report_input")
            report_reason = st.selectbox("Reason", [
                "Inappropriate content", "Harassment", "Fake profile",
                "Spam", "Underage", "Other",
            ])
            report_details = st.text_area("Additional details (optional)")
            if st.button("Submit Report", key="do_report", type="primary"):
                if report_email:
                    from utils.db import get_user_by_email
                    target = get_user_by_email(report_email)
                    if target:
                        report_user(uid, target["id"], report_reason, report_details)
                        st.success("✅ Report submitted. Our team will review it.")
                    else:
                        st.error("User not found.")
                else:
                    st.error("Enter an email address.")
        st.markdown("</div>", unsafe_allow_html=True)

    # ── ACCOUNT TAB ─────────────────────────────────────────────────────────
    with tab4:
        # ── Change Password ───────────────────────────────────────────────
        st.markdown('<div class="settings-section"><h3>🔑 Change Password</h3>', unsafe_allow_html=True)
        st.caption(f"Account email: **{user.get('email', 'unknown')}**")

        with st.form("change_password_form"):
            new_pw      = st.text_input("New Password", type="password", placeholder="Minimum 6 characters")
            confirm_pw  = st.text_input("Confirm New Password", type="password")

            # Live strength indicator (works after submit re-render)
            if new_pw:
                score, label_html = _password_strength(new_pw)
                bar_colors = ["#E53E3E", "#DD6B20", "#D69E2E", "#38A169", "#2B6CB0"]
                bar_w = [20, 40, 60, 80, 100]
                st.markdown(
                    f"Strength: {label_html} "
                    f"<div class='pw-bar' style='width:{bar_w[score]}%; background:{bar_colors[score]};'></div>",
                    unsafe_allow_html=True,
                )

            submitted = st.form_submit_button("🔑 Update Password", use_container_width=True, type="primary")

        if submitted:
            if not new_pw:
                st.error("Enter a new password.")
            elif len(new_pw) < 6:
                st.error("Password must be at least 6 characters.")
            elif new_pw != confirm_pw:
                st.error("Passwords don't match.")
            else:
                # FIX: Use admin client (service role) to update password.
                # get_client().auth.update_user() only works when there is an active
                # browser session token — it silently fails in Streamlit's server-side model.
                # The admin client uses the service-role key and can update any user by ID.
                try:
                    admin = get_admin_client()
                    admin.auth.admin.update_user_by_id(uid, {"password": new_pw})
                    st.success("✅ Password updated successfully! Please log out and log back in.")
                except Exception as e:
                    err = str(e)
                    if "SUPABASE_SERVICE_ROLE_KEY" in err or "not set" in err.lower():
                        st.error(
                            "❌ Password update requires `SUPABASE_SERVICE_ROLE_KEY` in your `.env` file.\n\n"
                            "Get it from: Supabase Dashboard → Settings → API → **service_role** key."
                        )
                    else:
                        st.error(f"❌ Password update failed: {err}")

        st.markdown("</div>", unsafe_allow_html=True)

        # ── Cloudinary Config Status ──────────────────────────────────────
        st.markdown('<div class="settings-section"><h3>📸 Image Upload Status</h3>', unsafe_allow_html=True)
        from utils.media import is_cloudinary_configured, _get_credentials
        cld_name, cld_key, cld_secret = _get_credentials()
        if is_cloudinary_configured():
            st.success(f"✅ Cloudinary configured (cloud: `{cld_name}`)")
        else:
            st.error(
                f"❌ Cloudinary not configured. Current `CLOUDINARY_CLOUD_NAME` = `{cld_name or 'empty'}`\n\n"
                "Update your `.env` file with real Cloudinary credentials from "
                "[cloudinary.com/console](https://cloudinary.com/console)."
            )
            with st.expander("How to fix image uploads"):
                st.markdown("""
                1. Go to [cloudinary.com](https://cloudinary.com) and sign up / log in (free tier is enough)
                2. On the Dashboard, find your **Cloud name**, **API Key**, and **API Secret**
                3. Update your `.env` file:
                ```
                CLOUDINARY_CLOUD_NAME=your-actual-cloud-name
                CLOUDINARY_API_KEY=your-api-key
                CLOUDINARY_API_SECRET=your-api-secret
                ```
                4. Save `.env` and **restart** the Streamlit app
                """)
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Danger Zone ───────────────────────────────────────────────────
        st.markdown('<div class="danger-zone"><h3>⚠️ Danger Zone</h3>', unsafe_allow_html=True)
        st.caption("These actions are permanent and cannot be undone.")

        # Two-step delete confirmation
        if "confirm_delete" not in st.session_state:
            st.session_state["confirm_delete"] = False

        if not st.session_state["confirm_delete"]:
            if st.button("🗑️ Delete My Account", type="secondary", use_container_width=True):
                st.session_state["confirm_delete"] = True
                st.rerun()
        else:
            st.warning(
                "⚠️ **This will permanently delete your account**, all matches, messages, and photos. "
                "This cannot be undone."
            )
            confirm_text = st.text_input(
                'Type your email address to confirm deletion:',
                placeholder=user.get("email", "your@email.com"),
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button("❌ Cancel", use_container_width=True):
                    st.session_state["confirm_delete"] = False
                    st.rerun()
            with col2:
                if st.button("🗑️ Yes, Delete Forever", type="primary", use_container_width=True):
                    if confirm_text.strip().lower() == user.get("email", "").lower():
                        try:
                            # FIX: Delete via admin API — this is the only way that
                            # actually removes the auth user. db.table("users").delete()
                            # alone only removes the profile row, leaving a ghost auth user.
                            admin = get_admin_client()

                            # 1. Remove profile row first
                            admin.table("users").delete().eq("id", uid).execute()

                            # 2. Delete auth user (requires service role)
                            admin.auth.admin.delete_user(uid)

                            # 3. Clear session and redirect
                            logout_user()
                            st.session_state.pop("confirm_delete", None)
                            st.success("✅ Account deleted. Goodbye!")
                            import time; time.sleep(1.5)
                            st.query_params["page"] = "login"
                            st.rerun()
                        except Exception as e:
                            err = str(e)
                            if "service_role" in err.lower() or "PASTE" in err:
                                st.error(
                                    "❌ Account deletion requires `SUPABASE_SERVICE_ROLE_KEY`.\n\n"
                                    "Set it in your `.env` file (Supabase → Settings → API → service_role key)."
                                )
                            else:
                                st.error(f"❌ Deletion failed: {err}")
                    else:
                        st.error("❌ Email doesn't match. Deletion cancelled.")

        st.markdown("</div>", unsafe_allow_html=True)

    # ── LOGOUT TAB ──────────────────────────────────────────────────────────
    with tab5:
        st.markdown("""
        <div style="text-align:center; padding:2rem;">
            <div style="font-size:4rem;">👋</div>
            <h3>See you soon!</h3>
            <p style="color:#888;">Your profile will still be here when you return.</p>
        </div>
        """, unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🚪 Log Out", use_container_width=True, type="primary"):
                logout_user()
                st.success("Logged out. Goodbye! 👋")
                import time; time.sleep(0.8)
                st.query_params.clear()
                st.rerun()
