"""
pages/admin.py
Admin moderation panel - only accessible to admin users
"""

import streamlit as st
from utils.auth import get_session_user, require_auth, is_admin
from utils.db import (
    get_all_reports, ban_user, get_stats, update_user,
    get_client
)


def render():
    require_auth()
    if not is_admin():
        st.error("🚫 Access denied. Admin only.")
        if st.button("← Back to Home"):
            st.query_params["page"] = "home"
            st.rerun()
        return

    st.markdown("""
    <style>
    .admin-header {
        background: linear-gradient(135deg, #1A1A2E, #16213E);
        border-radius: 20px;
        padding: 1.5rem 2rem;
        color: white;
        margin-bottom: 1.5rem;
    }
    .admin-stat {
        background: white;
        border-radius: 12px;
        padding: 1.25rem;
        text-align: center;
        box-shadow: 0 4px 16px rgba(0,0,0,0.08);
        border-top: 4px solid #FF6B6B;
    }
    .admin-stat-num { font-size: 2rem; font-weight: 800; color: #FF6B6B; }
    .admin-stat-label { color: #888; font-size: 0.8rem; }
    .report-card {
        background: white;
        border-radius: 12px;
        padding: 1rem 1.25rem;
        margin-bottom: 0.75rem;
        border-left: 4px solid #FF6B6B;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
    .report-pending { border-left-color: #FF6B6B; }
    .report-reviewed { border-left-color: #F59E0B; }
    .report-resolved { border-left-color: #22C55E; }
    </style>
    <div class="admin-header">
        <h2 style="margin:0;">🛡️ Admin Panel</h2>
        <p style="margin:0.25rem 0 0; opacity:0.7;">Moderation & platform management</p>
    </div>
    """, unsafe_allow_html=True)

    # Stats row
    stats = get_stats()
    col1, col2, col3, col4 = st.columns(4)
    for col, (label, val) in zip(
        [col1, col2, col3, col4],
        [
            ("👥 Total Users", stats["total_users"]),
            ("💞 Matches", stats["total_matches"]),
            ("💬 Messages", stats["total_messages"]),
            ("🚨 Pending Reports", stats["pending_reports"]),
        ],
    ):
        with col:
            st.markdown(f"""
            <div class="admin-stat">
                <div class="admin-stat-num">{val}</div>
                <div class="admin-stat-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    tab_reports, tab_users, tab_settings = st.tabs(["🚨 Reports", "👥 Users", "⚙️ Platform Settings"])

    # ── REPORTS ─────────────────────────────────────────────────────────────
    with tab_reports:
        st.subheader("🚨 User Reports")
        reports = get_all_reports()

        if not reports:
            st.info("No reports yet. ✅")
        else:
            # Filter
            status_filter = st.selectbox("Filter by status", ["all", "pending", "reviewed", "resolved"])
            filtered = reports if status_filter == "all" else [r for r in reports if r.get("status") == status_filter]

            st.markdown(f"**{len(filtered)} report(s)**")

            for report in filtered:
                reporter = report.get("reporter") or {}
                reported = report.get("reported") or {}
                status = report.get("status", "pending")
                color_class = f"report-{status}"

                col_info, col_actions = st.columns([4, 1])

                with col_info:
                    st.markdown(f"""
                    <div class="report-card {color_class}">
                        <strong>🚨 {report.get('reason','?')}</strong>
                        &nbsp; <span style="background:#FFE4E4; color:#FF6B6B; border-radius:10px; padding:2px 8px; font-size:0.75rem;">{status.upper()}</span>
                        <br>
                        <small style="color:#888;">
                            Reporter: <b>{reporter.get('name','?')}</b> ({reporter.get('email','?')}) &nbsp;→&nbsp;
                            Reported: <b>{reported.get('name','?')}</b> ({reported.get('email','?')})
                        </small>
                        {f"<br><small style='color:#666;'>Note: {report.get('details','')}</small>" if report.get('details') else ""}
                    </div>
                    """, unsafe_allow_html=True)

                with col_actions:
                    if status == "pending":
                        if st.button("✅ Resolve", key=f"resolve_{report['id']}", use_container_width=True):
                            _update_report_status(report["id"], "resolved")
                            st.rerun()
                        if reported.get("id") and st.button("🚫 Ban User", key=f"ban_{report['id']}", use_container_width=True):
                            ban_user(reported["id"])
                            _update_report_status(report["id"], "resolved")
                            st.warning(f"User {reported.get('name','?')} has been banned.")
                            st.rerun()

    # ── USERS ───────────────────────────────────────────────────────────────
    with tab_users:
        st.subheader("👥 User Management")

        # Search users
        search = st.text_input("🔍 Search by name or email", placeholder="Type to search...")
        if search:
            db = get_client()
            res = (
                db.table("users")
                .select("id, name, email, age, gender, is_active, is_premium, is_admin, created_at")
                .ilike("name", f"%{search}%")
                .limit(20)
                .execute()
            )
            users_found = res.data or []

            if not users_found:
                st.info("No users found.")
            else:
                for u in users_found:
                    col_info, col_actions = st.columns([4, 1])
                    with col_info:
                        badges = []
                        if u.get("is_premium"): badges.append("💎 Premium")
                        if u.get("is_admin"): badges.append("🛡️ Admin")
                        if not u.get("is_active"): badges.append("🚫 Banned")
                        badge_str = " ".join(badges)

                        st.markdown(f"""
                        **{u.get('name','?')}** ({u.get('email','?')}) {badge_str}
                        - Age {u.get('age','?')}, {u.get('gender','?')}
                        """)
                    with col_actions:
                        if u.get("is_active"):
                            if st.button("🚫 Ban", key=f"ban_user_{u['id']}", use_container_width=True):
                                ban_user(u["id"])
                                st.success(f"Banned {u['name']}")
                                st.rerun()
                        else:
                            if st.button("✅ Unban", key=f"unban_{u['id']}", use_container_width=True):
                                update_user(u["id"], {"is_active": True})
                                st.success(f"Unbanned {u['name']}")
                                st.rerun()
        else:
            st.info("Type a name or email to search for users.")

    # ── PLATFORM SETTINGS ───────────────────────────────────────────────────
    with tab_settings:
        st.subheader("⚙️ Platform Settings")
        st.info("Platform-wide settings coming soon.")

        st.markdown("**Quick Actions:**")
        if st.button("📧 Send Announcement to All Users"):
            st.info("Email broadcast feature coming soon.")
        if st.button("🗑️ Clear Expired Boosts"):
            _clear_expired_boosts()
            st.success("Expired boosts cleared!")


def _update_report_status(report_id: str, status: str):
    db = get_client()
    db.table("reports").update({"status": status}).eq("id", report_id).execute()


def _clear_expired_boosts():
    from datetime import datetime, timezone
    db = get_client()
    now = datetime.now(timezone.utc).isoformat()
    db.table("users").update({
        "is_boosted": False,
        "boost_expires_at": None,
    }).lte("boost_expires_at", now).eq("is_boosted", True).execute()
