"""
pages/admin.py
Admin panel with charts, heatmap, bulk actions, reports, user management.
"""

import streamlit as st
from utils.auth import get_session_user, require_auth, is_admin
from utils.db import get_all_reports, ban_user, get_stats, update_user, get_client, get_service_client


def render():
    require_auth()
    if not is_admin():
        st.error("🚫 Admin only.")
        if st.button("← Home"): st.query_params["page"] = "home"; st.rerun()
        return

    st.markdown("""
    <div style="background:linear-gradient(135deg,#1A1A2E,#16213E);
         border-radius:20px;padding:1.5rem 2rem;color:white;margin-bottom:1.5rem;">
        <h2 style="margin:0;">🛡️ Admin Panel</h2>
        <p style="margin:.25rem 0 0;opacity:.7;">Moderation · Analytics · Platform settings</p>
    </div>
    """, unsafe_allow_html=True)

    tab_dash, tab_reports, tab_users, tab_email = st.tabs([
        "📊 Dashboard", "🚨 Reports", "👥 Users", "📧 Bulk Email"
    ])

    # ── DASHBOARD ─────────────────────────────────────────────────────────────
    with tab_dash:
        stats = get_stats()
        c1, c2, c3, c4 = st.columns(4)
        for col, (label, val) in zip(
            [c1, c2, c3, c4],
            [("👥 Users", stats["total_users"]),
             ("💞 Matches", stats["total_matches"]),
             ("💬 Messages", stats["total_messages"]),
             ("🚨 Pending Reports", stats["pending_reports"])],
        ):
            with col:
                st.metric(label, val)

        st.markdown("---")

        # Signups chart
        st.subheader("📈 Signups over time")
        try:
            res = get_client().table("users").select("created_at").order("created_at").execute()
            if res.data:
                import pandas as pd
                df = pd.DataFrame(res.data)
                df["created_at"] = pd.to_datetime(df["created_at"])
                df["date"] = df["created_at"].dt.date
                daily = df.groupby("date").size().reset_index(name="signups")
                st.line_chart(daily.set_index("date")["signups"])
            else:
                st.info("No signup data yet.")
        except Exception as e:
            st.error(f"Chart error: {e}")

        # Matches chart
        st.subheader("💞 Matches over time")
        try:
            res = get_client().table("matches").select("matched_at").order("matched_at").execute()
            if res.data:
                import pandas as pd
                df = pd.DataFrame(res.data)
                df["matched_at"] = pd.to_datetime(df["matched_at"])
                df["date"] = df["matched_at"].dt.date
                daily = df.groupby("date").size().reset_index(name="matches")
                st.bar_chart(daily.set_index("date")["matches"])
            else:
                st.info("No match data yet.")
        except Exception as e:
            st.error(f"Chart error: {e}")

        # User heatmap
        st.subheader("🗺️ User locations")
        try:
            res = get_client().table("users").select("name,latitude,longitude,location")\
                .not_.is_("latitude", "null").execute()
            if res.data:
                import pandas as pd
                df = pd.DataFrame(res.data).dropna(subset=["latitude","longitude"])
                df = df.rename(columns={"latitude":"lat","longitude":"lon"})
                if not df.empty:
                    st.map(df[["lat","lon"]], zoom=5, use_container_width=True)
                    st.caption(f"{len(df)} users with location data")
            else:
                st.info("No users have set their location yet.")
        except Exception as e:
            st.error(f"Map error: {e}")

        # Gender breakdown
        st.subheader("👥 Gender breakdown")
        try:
            res = get_client().table("users").select("gender").execute()
            if res.data:
                import pandas as pd
                df  = pd.DataFrame(res.data)
                cnt = df["gender"].value_counts()
                st.bar_chart(cnt)
        except Exception as e:
            st.warning(f"Could not load gender data: {e}")

    # ── REPORTS ───────────────────────────────────────────────────────────────
    with tab_reports:
        st.subheader("🚨 User Reports")
        reports = get_all_reports()
        if not reports:
            st.success("No reports. ✅")
        else:
            status_filter = st.selectbox("Filter", ["all","pending","reviewed","resolved"])
            filtered = reports if status_filter == "all" else [r for r in reports if r.get("status") == status_filter]
            st.write(f"**{len(filtered)} report(s)**")

            for r in filtered:
                reporter = r.get("reporter") or {}
                reported = r.get("reported") or {}
                status   = r.get("status","pending")
                color    = {"pending":"#FF6B6B","reviewed":"#F59E0B","resolved":"#22C55E"}.get(status,"#AAA")
                with st.container(border=True):
                    st.markdown(
                        f"**{r.get('reason','?')}** "
                        f'<span style="color:{color};font-weight:600;">[{status.upper()}]</span>',
                        unsafe_allow_html=True,
                    )
                    st.caption(
                        f"From: {reporter.get('name','?')} ({reporter.get('email','?')})  →  "
                        f"Against: {reported.get('name','?')} ({reported.get('email','?')})"
                    )
                    if r.get("details"):
                        st.write(r["details"])
                    if status == "pending":
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button("✅ Resolve", key=f"res_{r['id']}"):
                                _set_report_status(r["id"], "resolved"); st.rerun()
                        with c2:
                            rep_id = reported.get("id")
                            if rep_id and st.button("🚫 Ban user", key=f"ban_{r['id']}"):
                                ban_user(rep_id); _set_report_status(r["id"],"resolved"); st.rerun()

    # ── USERS ─────────────────────────────────────────────────────────────────
    with tab_users:
        st.subheader("👥 User Management")
        search = st.text_input("Search by name or email", placeholder="Type to search...")
        if search:
            try:
                res = get_service_client().table("users")\
                    .select("id,name,email,age,gender,is_active,is_premium,is_admin,is_verified,created_at")\
                    .ilike("name", f"%{search}%").limit(20).execute()
                if not res.data:
                    st.info("No users found.")
                else:
                    for u in res.data:
                        badges = []
                        if u.get("is_premium"):  badges.append("💎 Premium")
                        if u.get("is_admin"):    badges.append("🛡️ Admin")
                        if u.get("is_verified"): badges.append("✓ Verified")
                        if not u.get("is_active"): badges.append("🚫 Banned")
                        with st.container(border=True):
                            c1, c2, c3 = st.columns([4, 1, 1])
                            with c1:
                                st.write(f"**{u.get('name','?')}** ({u.get('email','?')})  {' '.join(badges)}")
                                st.caption(f"Age {u.get('age','?')} · {u.get('gender','?')}")
                            with c2:
                                if u.get("is_active"):
                                    if st.button("🚫 Ban", key=f"ban_u_{u['id']}"):
                                        ban_user(u["id"]); st.rerun()
                                else:
                                    if st.button("✅ Unban", key=f"unban_{u['id']}"):
                                        update_user(u["id"], {"is_active": True}); st.rerun()
                            with c3:
                                if not u.get("is_verified"):
                                    if st.button("✓ Verify", key=f"verify_{u['id']}"):
                                        update_user(u["id"], {"is_verified": True}); st.rerun()
                                else:
                                    if st.button("✗ Unverify", key=f"unverify_{u['id']}"):
                                        update_user(u["id"], {"is_verified": False}); st.rerun()
            except Exception as e:
                st.error(f"Search error: {e}")
        else:
            st.info("Type a name to search.")

    # ── BULK EMAIL ────────────────────────────────────────────────────────────
    with tab_email:
        st.subheader("📧 Send Announcement")
        st.info(
            "To send emails you need an email API key. "
            "Recommended: **Resend** (resend.com) — free tier has 3,000 emails/month."
        )

        resend_key = st.text_input("Resend API Key", type="password",
                                    placeholder="re_xxxxxxxxxxxx")
        subject    = st.text_input("Subject", placeholder="New feature on LinkUp!")
        body       = st.text_area("Message (plain text)", height=150,
                                   placeholder="Hey! We've added some cool new features...")
        audience   = st.radio("Send to", ["All users", "Premium users only", "Free users only"])

        if st.button("📤 Send to all", type="primary", disabled=not (resend_key and subject and body)):
            _send_bulk_email(resend_key, subject, body, audience)


def _set_report_status(report_id: str, status: str):
    get_service_client().table("reports").update({"status": status}).eq("id", report_id).execute()


def _send_bulk_email(api_key: str, subject: str, body: str, audience: str):
    import requests
    try:
        if audience == "Premium users only":
            res = get_client().table("users").select("email").eq("is_premium", True).eq("is_active", True).execute()
        elif audience == "Free users only":
            res = get_client().table("users").select("email").eq("is_premium", False).eq("is_active", True).execute()
        else:
            res = get_client().table("users").select("email").eq("is_active", True).execute()

        emails = [r["email"] for r in (res.data or []) if r.get("email")]
        st.write(f"Sending to {len(emails)} users...")

        progress = st.progress(0)
        sent = 0
        failed = 0
        for i, email in enumerate(emails):
            r = requests.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"from": "LinkUp <hello@linkup.app>", "to": [email],
                      "subject": subject, "text": body},
                timeout=10,
            )
            if r.status_code in (200, 201):
                sent += 1
            else:
                failed += 1
            progress.progress((i + 1) / len(emails))

        st.success(f"✅ Sent: {sent}  |  ❌ Failed: {failed}")
    except Exception as e:
        st.error(f"Email error: {e}")
