"""
pages/login.py
Login page for LinkUp
"""

import streamlit as st
from utils.auth import login_user, set_session, is_authenticated


def render():
    if is_authenticated():
        st.query_params["page"] = "home"
        st.rerun()

    st.markdown("""
    <style>
    .auth-card {
        max-width: 420px;
        margin: 2rem auto;
        background: white;
        border-radius: 24px;
        padding: 2.5rem;
        box-shadow: 0 20px 60px rgba(255,107,107,0.15);
    }
    .auth-logo {
        text-align: center;
        font-size: 2.5rem;
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

    st.markdown('<div class="auth-logo">💘 LinkUp</div>', unsafe_allow_html=True)
    st.markdown('<div class="auth-tagline">Find your person. For real.</div>', unsafe_allow_html=True)

    with st.form("login_form"):
        st.subheader("Welcome back 👋")
        email = st.text_input("Email", placeholder="you@example.com")
        password = st.text_input("Password", type="password", placeholder="Your password")
        remember = st.checkbox("Remember me", value=True)
        submitted = st.form_submit_button("Login →", use_container_width=True, type="primary")

        if submitted:
            if not email or not password:
                st.error("Please fill in all fields.")
            else:
                with st.spinner("Logging in..."):
                    result = login_user(email, password)
                if result["success"]:
                    set_session(result["user"], result.get("session"))
                    st.success("Welcome back!")
                    redirect = st.session_state.pop("redirect_after_login", "home")
                    st.query_params["page"] = redirect
                    st.rerun()
                else:
                    err = result["error"]
                    st.error(err)
                    if "profile not found" in err.lower() or "could not load" in err.lower():
                        st.info(
                            "Your account exists but your profile data is missing. "
                            "This can be fixed automatically - click Login again and it will rebuild your profile."
                        )

    st.markdown('<div class="auth-divider">── OR ──</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📝 Create Account", use_container_width=True):
            st.query_params["page"] = "register"
            st.rerun()
    with col2:
        if st.button("🔑 Forgot Password?", use_container_width=True):
            st.query_params["page"] = "reset_password"
            st.rerun()
