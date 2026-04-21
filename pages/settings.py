"""
pages/settings.py
Settings - account, preferences, premium, safety, notifications
"""

import streamlit as st
from utils.auth import get_session_user, require_auth, logout_user, refresh_session_user, is_premium
from utils.db import update_user, block_user, report_user
from utils.payments import initiate_stk_push, activate_premium, PLANS


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
    .settings-section h3 {
        color: #FF6B6B;
        margin-bottom: 1rem;
        font-size: 1.05rem;
    }
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
        cursor: pointer;
        transition: border-color 0.2s;
    }
    .plan-card:hover { border-color: #FF6B6B; }
    .plan-card.selected { border-color: #FF6B6B; background: #FFF8F8; }
    .danger-zone {
        background: #FFF5F5;
        border: 1px solid #FFD5D5;
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }
    .danger-zone h3 { color: #E53E3E; }
    </style>
    <div class="settings-header">
        <h2 style="margin:0;">⚙️ Settings</h2>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "💎 Premium", "🔔 Notifications", "🛡️ Safety", "⚙️ Account", "🎨 Appearance", "🚪 Logout"
    ])

    # ── PREMIUM TAB ─────────────────────────────────────────────────────────
    with tab1:
        if is_premium():
            st.markdown("""
            <div class="premium-card">
                <h3>💎 You're Premium!</h3>
                <p style="margin:0; opacity:0.9;">Enjoy all premium benefits.</p>
            </div>
            """, unsafe_allow_html=True)
            st.success("✅ All premium features are active.")
        else:
            st.markdown("""
            <div class="premium-card">
                <h3>💎 Upgrade to Premium</h3>
                <p style="margin:0;">Unlock the full LinkUp experience</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("### Plans")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("""
            <div class="plan-card">
                <h4>⚡ Boost</h4>
                <div style="font-size:1.5rem; font-weight:800; color:#FF6B6B;">KES 100</div>
                <div style="color:#888; font-size:0.85rem;">7 days</div>
                <ul style="color:#555; font-size:0.85rem; margin-top:0.5rem;">
                    <li>Profile shown first</li>
                    <li>3x more visibility</li>
                    <li>Boost badge</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown("""
            <div class="plan-card">
                <h4>💎 Premium</h4>
                <div style="font-size:1.5rem; font-weight:800; color:#FF6B6B;">KES 500</div>
                <div style="color:#888; font-size:0.85rem;">30 days</div>
                <ul style="color:#555; font-size:0.85rem; margin-top:0.5rem;">
                    <li>See who liked you</li>
                    <li>Unlimited likes</li>
                    <li>Undo swipe</li>
                    <li>Priority visibility</li>
                    <li>All Boost features</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("### 📱 Pay with M-Pesa")
        with st.form("mpesa_form"):
            plan_choice = st.radio(
                "Select Plan",
                ["boost", "premium"],
                format_func=lambda x: f"{'⚡ Boost - KES 100' if x == 'boost' else '💎 Premium - KES 500'}",
                horizontal=True,
            )
            phone = st.text_input(
                "M-Pesa Phone Number",
                placeholder="07XX XXX XXX or 2547XX XXX XXX",
                value="+254",
            )
            pay_btn = st.form_submit_button("💳 Pay Now with M-Pesa", use_container_width=True, type="primary")

            if pay_btn:
                if not phone or len(phone.replace("+", "").replace(" ", "")) < 10:
                    st.error("Enter a valid Safaricom number.")
                else:
                    with st.spinner("Sending STK Push to your phone..."):
                        result = initiate_stk_push(phone, plan_choice, uid)
                    if result["success"]:
                        st.success(
                            "📱 Check your phone! Enter M-Pesa PIN to complete payment. "
                            "Your account will be upgraded automatically."
                        )
                        # In production: poll callback. For demo, activate directly.
                        st.info("Demo mode: activating premium now...")
                        activate_premium(uid, plan_choice, receipt="DEMO123")
                        refresh_session_user()
                        st.rerun()
                    else:
                        st.error(f"Payment failed: {result['error']}")

    # ── NOTIFICATIONS TAB ───────────────────────────────────────────────────
    with tab2:
        st.markdown('<div class="settings-section"><h3>🔔 Notification Preferences</h3>', unsafe_allow_html=True)

        notif_matches = st.toggle("New match notifications", value=True)
        notif_messages = st.toggle("New message notifications", value=True)
        notif_likes = st.toggle("Someone liked you (Premium)", value=is_premium(), disabled=not is_premium())
        notif_events = st.toggle("Event reminders", value=True)

        if st.button("💾 Save Notification Settings", type="primary"):
            st.success("Notification settings saved!")
        st.markdown("</div>", unsafe_allow_html=True)

    # ── SAFETY TAB ──────────────────────────────────────────────────────────
    with tab3:
        st.markdown('<div class="settings-section"><h3>🛡️ Privacy</h3>', unsafe_allow_html=True)

        hide_profile = st.toggle(
            "Hide my profile (won't appear in discovery)",
            value=user.get("profile_hidden", False),
        )

        if st.button("💾 Save Privacy Settings", type="primary"):
            update_user(uid, {"profile_hidden": hide_profile})
            refresh_session_user()
            st.success("Privacy settings saved!")
        st.markdown("</div>", unsafe_allow_html=True)

        # Report / Block
        st.markdown('<div class="settings-section"><h3>🚫 Block or Report a User</h3>', unsafe_allow_html=True)

        with st.expander("Block a user"):
            block_email = st.text_input("Enter email of user to block", key="block_input")
            if st.button("🚫 Block User", key="do_block"):
                if block_email:
                    from utils.db import get_user_by_email
                    target = get_user_by_email(block_email)
                    if target:
                        block_user(uid, target["id"])
                        st.success(f"✅ {target['name']} has been blocked.")
                    else:
                        st.error("User not found.")
                else:
                    st.error("Enter an email address.")

        with st.expander("Report a user"):
            report_email = st.text_input("Enter email of user to report", key="report_input")
            report_reason = st.selectbox("Reason", [
                "Inappropriate content",
                "Harassment",
                "Fake profile",
                "Spam",
                "Underage",
                "Other",
            ])
            report_details = st.text_area("Additional details (optional)")
            if st.button("🚨 Submit Report", key="do_report", type="primary"):
                if report_email:
                    from utils.db import get_user_by_email
                    target = get_user_by_email(report_email)
                    if target:
                        report_user(uid, target["id"], report_reason, report_details)
                        st.success("✅ Report submitted. Our team will review it shortly.")
                    else:
                        st.error("User not found.")
                else:
                    st.error("Enter an email address.")
        st.markdown("</div>", unsafe_allow_html=True)

    # ── ACCOUNT TAB ─────────────────────────────────────────────────────────
    with tab4:
        st.markdown('<div class="settings-section"><h3>⚙️ Account Settings</h3>', unsafe_allow_html=True)

        # Change password
        st.markdown("**Change Password**")
        with st.form("change_password"):
            new_pw = st.text_input("New Password", type="password")
            confirm_pw = st.text_input("Confirm New Password", type="password")
            if st.form_submit_button("Update Password"):
                if not new_pw or len(new_pw) < 6:
                    st.error("Password must be at least 6 characters.")
                elif new_pw != confirm_pw:
                    st.error("Passwords do not match.")
                else:
                    from utils.auth import update_password
                    result = update_password(uid, new_pw)
                    if result["success"]:
                        st.success("Password updated!")
                    else:
                        st.error(result["error"])

        st.markdown("</div>", unsafe_allow_html=True)

        # Danger zone
        st.markdown('<div class="danger-zone"><h3>⚠️ Danger Zone</h3>', unsafe_allow_html=True)

        if st.button("🗑️ Delete My Account", type="secondary"):
            st.warning(
                "This will permanently delete your account and all data. "
                "Contact support@linkup.app to proceed."
            )
        st.markdown("</div>", unsafe_allow_html=True)

    # ── APPEARANCE TAB ──────────────────────────────────────────────────────
    with tab5:
        st.markdown('<div class="settings-section"><h3>🎨 Appearance</h3>', unsafe_allow_html=True)
        st.markdown("**Theme**")

        import os
        config_path = os.path.join(os.path.dirname(__file__), "..", ".streamlit", "config.toml")
        config_path = os.path.normpath(config_path)

        # Read current theme
        current_bg = "#F8F9FA"
        try:
            content = open(config_path).read()
            if "#1A1A2E" in content:
                current_idx = 1
            else:
                current_idx = 0
        except Exception:
            current_idx = 0

        theme = st.radio(
            "Choose theme",
            ["☀️ Light", "🌙 Dark"],
            index=current_idx,
            horizontal=True,
        )

        if st.button("Apply Theme", type="primary", key="apply_theme"):
            if theme == "🌙 Dark":
                new_config = """[theme]
primaryColor = "#FF6B6B"
backgroundColor = "#1A1A2E"
secondaryBackgroundColor = "#16213E"
textColor = "#E8E8E8"
font = "sans serif"

[server]
headless = true
port = 8501

[browser]
gatherUsageStats = false

[client]
toolbarMode = "minimal"
"""
            else:
                new_config = """[theme]
primaryColor = "#FF6B6B"
backgroundColor = "#F8F9FA"
secondaryBackgroundColor = "#FFFFFF"
textColor = "#222222"
font = "sans serif"

[server]
headless = true
port = 8501

[browser]
gatherUsageStats = false

[client]
toolbarMode = "minimal"
"""
            try:
                with open(config_path, "w") as f:
                    f.write(new_config)
                st.success("Theme saved! The app will reload automatically.")
                import time; time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Could not save theme: {e}")
                st.info("On Streamlit Cloud, themes can't be changed at runtime. Change it in the Streamlit Cloud dashboard → Settings → Theme instead.")

        st.markdown("**Language**")
        st.selectbox("App language", ["English 🇬🇧", "Swahili 🇰🇪"], key="app_language")
        st.caption("Swahili translation coming soon.")
        st.markdown("</div>", unsafe_allow_html=True)

    # ── LOGOUT TAB ──────────────────────────────────────────────────────────
    with tab6:
        st.markdown("""
        <div style="text-align:center; padding:2rem;">
            <div style="font-size:4rem;">👋</div>
            <h3>See you soon!</h3>
            <p style="color:#888;">You can log back in anytime.</p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🚪 Log Out", use_container_width=True, type="primary"):
                logout_user()
                st.success("Logged out. Goodbye! 👋")
                st.query_params.clear()
                st.rerun()
