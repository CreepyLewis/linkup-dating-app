"""
pages/register.py
Registration with 5-question compatibility quiz.
"""

import streamlit as st
from utils.auth import register_user, login_user, set_session, is_authenticated
from utils.matching import QUIZ_QUESTIONS


def render():
    if is_authenticated():
        st.query_params["page"] = "home"
        st.rerun()

    st.markdown("""
    <style>
    .auth-logo{text-align:center;font-size:2.5rem;font-weight:900;
        background:linear-gradient(135deg,#FF6B6B,#FF8E53);
        -webkit-background-clip:text;-webkit-text-fill-color:transparent;
        margin-bottom:.25rem;}
    .auth-sub{text-align:center;color:#888;font-size:.95rem;margin-bottom:1.5rem;}
    </style>
    """, unsafe_allow_html=True)
    st.markdown('<div class="auth-logo">💘 LinkUp</div>', unsafe_allow_html=True)
    st.markdown('<div class="auth-sub">Find your person. It\'s free.</div>', unsafe_allow_html=True)

    step = st.session_state.get("reg_step", 1)

    # ── Step 1: Basic info ────────────────────────────────────────────────────
    if step == 1:
        with st.form("reg_basic"):
            st.subheader("Step 1 of 2 — Your details")
            c1, c2 = st.columns(2)
            with c1: name = st.text_input("Full Name *", placeholder="Jane Mwangi")
            with c2: age  = st.number_input("Age *", 18, 99, 25)
            email    = st.text_input("Email *", placeholder="you@gmail.com")
            password = st.text_input("Password *", type="password", placeholder="6+ characters")
            confirm  = st.text_input("Confirm Password *", type="password")
            gender   = st.selectbox("I am *", ["Select...", "male", "female", "non-binary", "other"])
            terms    = st.checkbox("I agree to the Terms of Service")

            if st.form_submit_button("Next →", use_container_width=True, type="primary"):
                errors = []
                if not name.strip():             errors.append("Name required.")
                if not email or "@" not in email: errors.append("Valid email required.")
                if len(password) < 6:            errors.append("Password must be 6+ chars.")
                if password != confirm:          errors.append("Passwords don't match.")
                if gender == "Select...":        errors.append("Select your gender.")
                if not terms:                    errors.append("Accept Terms of Service.")
                if errors:
                    for e in errors: st.error(e)
                else:
                    st.session_state["reg_data"] = {
                        "email": email.strip().lower(),
                        "password": password,
                        "name": name.strip(),
                        "age": int(age),
                        "gender": gender,
                    }
                    st.session_state["reg_step"] = 2
                    st.rerun()

    # ── Step 2: Compatibility quiz ────────────────────────────────────────────
    elif step == 2:
        st.subheader("Step 2 of 2 — Quick compatibility quiz")
        st.caption("Takes 30 seconds • Helps us find better matches for you")

        quiz_answers = {}
        all_answered = True

        for q in QUIZ_QUESTIONS:
            ans = st.radio(
                q["q"], q["options"],
                key=f"quiz_{q['id']}",
                index=None,
                horizontal=True,
            )
            if ans:
                quiz_answers[q["id"]] = ans
            else:
                all_answered = False

        st.markdown("")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("← Back", use_container_width=True):
                st.session_state["reg_step"] = 1
                st.rerun()
        with c2:
            skip = st.button("Skip quiz →", use_container_width=True)
            done = st.button("Create Account", use_container_width=True, type="primary",
                             disabled=not all_answered)

        if skip or done:
            reg = st.session_state.get("reg_data", {})
            with st.spinner("Creating your account..."):
                result = register_user(
                    reg["email"], reg["password"],
                    reg["name"], reg["age"], reg["gender"],
                )
            if result["success"]:
                # Save quiz answers
                if quiz_answers:
                    from utils.db import update_user
                    update_user(result["user"]["id"], {"quiz_answers": quiz_answers})
                # Auto-login
                login_res = login_user(reg["email"], reg["password"])
                if login_res["success"]:
                    set_session(login_res["user"], login_res.get("session"))
                st.success("Welcome to LinkUp! 🎉 Add a photo to start discovering.")
                # Clean up
                for k in ["reg_step", "reg_data"] + [f"quiz_{q['id']}" for q in QUIZ_QUESTIONS]:
                    st.session_state.pop(k, None)
                st.query_params["page"] = "profile"
                st.rerun()
            else:
                st.error(result["error"])
                st.session_state["reg_step"] = 1
                st.rerun()

    st.markdown("---")
    if st.button("Already have an account? Log in", use_container_width=True):
        st.query_params["page"] = "login"
        st.rerun()
