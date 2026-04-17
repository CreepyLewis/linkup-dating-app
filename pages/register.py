"""
pages/register.py
Registration - uses service role to skip email confirmation rate limits.
"""

import streamlit as st
from utils.auth import register_user, login_user, set_session, is_authenticated


def render():
    if is_authenticated():
        st.query_params["page"] = "home"
        st.rerun()

    st.markdown("""
    <style>
    .auth-logo {
        text-align: center; font-size: 2.5rem; font-weight: 900;
        background: linear-gradient(135deg, #FF6B6B, #FF8E53);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 0.25rem;
    }
    .auth-tagline { text-align: center; color: #888; font-size: .95rem; margin-bottom: 2rem; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="auth-logo">💘 LinkUp</div>', unsafe_allow_html=True)
    st.markdown('<div class="auth-tagline">Start your journey. It\'s free.</div>', unsafe_allow_html=True)

    with st.form("register_form", clear_on_submit=False):
        st.subheader("Create your account")

        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Full Name *", placeholder="e.g. Jane Mwangi")
        with col2:
            age = st.number_input("Age *", min_value=18, max_value=99, value=25)

        email    = st.text_input("Email *", placeholder="you@gmail.com")
        password = st.text_input("Password *", type="password", placeholder="At least 6 characters")
        confirm  = st.text_input("Confirm Password *", type="password")

        gender_options = ["Select...", "male", "female", "non-binary", "other"]
        gender = st.selectbox("I am *", gender_options)

        terms = st.checkbox("I agree to the Terms of Service")
        submitted = st.form_submit_button("Create Account", use_container_width=True, type="primary")

        if submitted:
            errors = []
            if not name.strip():             errors.append("Name is required.")
            if not email or "@" not in email: errors.append("Valid email required.")
            if len(password) < 6:            errors.append("Password must be 6+ characters.")
            if password != confirm:          errors.append("Passwords do not match.")
            if gender == "Select...":        errors.append("Please select your gender.")
            if not terms:                    errors.append("Accept the Terms of Service.")

            if errors:
                for e in errors:
                    st.error(e)
            else:
                with st.spinner("Creating your account..."):
                    result = register_user(email.strip().lower(), password, name.strip(), int(age), gender)

                if result["success"]:
                    # Auto-login right after register (no email confirmation needed)
                    with st.spinner("Logging you in..."):
                        login_result = login_user(email.strip().lower(), password)
                    if login_result["success"]:
                        set_session(login_result["user"], login_result.get("session"))
                        st.success("Account created! Let's set up your profile.")
                        st.query_params["page"] = "profile"
                        st.rerun()
                    else:
                        st.success("Account created! Please log in.")
                        st.query_params["page"] = "login"
                        st.rerun()
                else:
                    st.error(result["error"])

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Already have an account?", use_container_width=True):
            st.query_params["page"] = "login"
            st.rerun()
