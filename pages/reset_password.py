"""
pages/reset_password.py
Password reset flow
"""

import streamlit as st
from utils.auth import request_password_reset


def render():
    st.markdown("""
    <style>
    .auth-logo {
        text-align: center;
        font-size: 2.5rem;
        font-weight: 900;
        background: linear-gradient(135deg, #FF6B6B, #FF8E53);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.25rem;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="auth-logo">💘 LinkUp</div>', unsafe_allow_html=True)
    st.markdown("<div style='text-align:center; color:#888; margin-bottom:2rem;'>Reset your password</div>", unsafe_allow_html=True)

    with st.form("reset_form"):
        st.subheader("🔑 Forgot Password?")
        st.caption("Enter your email and we'll send you a reset link.")
        email = st.text_input("Email", placeholder="you@example.com")
        submitted = st.form_submit_button("Send Reset Link →", use_container_width=True, type="primary")

        if submitted:
            if not email or "@" not in email:
                st.error("Enter a valid email address.")
            else:
                with st.spinner("Sending..."):
                    result = request_password_reset(email)
                if result["success"]:
                    st.success("📧 Check your email for a reset link!")
                else:
                    st.error(result.get("error", "Something went wrong."))

    st.markdown("---")
    if st.button("← Back to Login"):
        st.query_params["page"] = "login"
        st.rerun()
