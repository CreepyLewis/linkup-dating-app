"""
pages/login.py
Login page for LinkUp
"""

import streamlit as st
from utils.auth import login_user, set_session, is_authenticated


def render():
    if is_authenticated():
        st.session_state["current_page"] = "home"
        st.query_params["page"] = "home"
        st.rerun()

    st.markdown("""
    <style>
    .auth-logo {
        text-align: center;
        font-size: 2.8rem;
        font-weight: 900;
        background: linear-gradient(135deg, #FF6B6B, #FF8E53);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.25rem;
    }
    .auth-tagline {
        text-align: center;
        color: #888;
        font-size: 0.95rem;
        margin-bottom: 2rem;
    }
    .auth-divider {
        text-align: center;
        color: #CCC;
        margin: 1rem 0;
        font-size: 0.85rem;
    }
    </style>
    """, unsafe_allow_html=True)

    # Center content
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown('<div class="auth-logo">💘 LinkUp</div>', unsafe_allow_html=True)
        st.markdown('<div class="auth-tagline">Find your person. For real.</div>', unsafe_allow_html=True)

        with st.form("login_form", clear_on_submit=False):
            st.subheader("Welcome back 👋")
            email = st.text_input("Email", placeholder="you@example.com")
            password = st.text_input("Password", type="password", placeholder="Your password")
            submitted = st.form_submit_button("Login →", use_container_width=True, type="primary")

            if submitted:
                if not email or not password:
                    st.error("Please fill in all fields.")
                else:
                    with st.spinner("Logging in..."):
                        result = login_user(email.strip().lower(), password)
                    if result["success"]:
                        set_session(result["user"], result.get("session"))
                        redirect = st.session_state.pop("redirect_after_login", "home")
                        st.session_state["current_page"] = redirect
                        st.query_params["page"] = redirect
                        st.success(f"Welcome back, {result['user'].get('name', '')}! 🎉")
                        st.rerun()
                    else:
                        st.error(result["error"])

        st.markdown('<div class="auth-divider">── OR ──</div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("📝 Create Account", use_container_width=True):
                st.session_state["current_page"] = "register"
                st.query_params["page"] = "register"
                st.rerun()
        with col2:
            if st.button("🔑 Forgot Password?", use_container_width=True):
                st.session_state["current_page"] = "reset_password"
                st.query_params["page"] = "reset_password"
                st.rerun()

        # Help text for common issue
        st.markdown("""
        <div style="text-align:center; margin-top:1.5rem; padding:1rem;
                    background:#FFF8F8; border-radius:12px; border:1px solid #FFE0E0;">
            <small style="color:#888;">
                <strong>Can't log in?</strong> Make sure <code>SUPABASE_SERVICE_ROLE_KEY</code>
                is set in your <code>.env</code> file — this is required for the app to read your profile.
            </small>
        </div>
        """, unsafe_allow_html=True)
