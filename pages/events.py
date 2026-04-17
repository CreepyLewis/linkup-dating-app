"""
pages/events.py
Events - create and join meetups
"""

import streamlit as st
from datetime import datetime, timezone, timedelta
from utils.auth import get_session_user, require_auth
from utils.db import (
    get_events, create_event, join_event, leave_event, get_event_attendees
)
from components.profile_card import get_avatar_url


def render():
    require_auth()
    user = get_session_user()
    uid = user["id"]

    st.markdown("""
    <style>
    .events-header {
        background: linear-gradient(135deg, #7C3AED, #A78BFA);
        border-radius: 20px;
        padding: 1.5rem 2rem;
        color: white;
        margin-bottom: 1.5rem;
    }
    .event-card {
        background: white;
        border-radius: 16px;
        overflow: hidden;
        margin-bottom: 1rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        transition: transform 0.2s;
    }
    .event-card:hover { transform: translateY(-3px); }
    .event-cover {
        height: 160px;
        background: linear-gradient(135deg, #FF6B6B, #FF8E53);
        display: flex; align-items: center; justify-content: center;
        font-size: 3rem;
    }
    .event-body { padding: 1.25rem; }
    .event-title { font-size: 1.15rem; font-weight: 700; color: #222; margin-bottom: 0.5rem; }
    .event-meta { color: #888; font-size: 0.85rem; margin-bottom: 0.75rem; }
    .attendee-avatar {
        width: 32px; height: 32px;
        border-radius: 50%; object-fit: cover;
        border: 2px solid white;
        display: inline-block;
        margin-left: -8px;
    }
    </style>
    <div class="events-header">
        <h2 style="margin:0;">🎉 Events</h2>
        <p style="margin:0.25rem 0 0; opacity:0.85;">Join local meetups and social events</p>
    </div>
    """, unsafe_allow_html=True)

    tab_browse, tab_create = st.tabs(["🔍 Browse Events", "➕ Create Event"])

    # ── BROWSE ──────────────────────────────────────────────────────────────
    with tab_browse:
        events = get_events(limit=20)

        if not events:
            st.info("No upcoming events. Be the first to create one! 🎉")
        else:
            st.subheader(f"🗓️ {len(events)} Upcoming Event{'s' if len(events) != 1 else ''}")

            for event in events:
                attendees = get_event_attendees(event["id"]) or []
                attendee_ids = [a["id"] for a in attendees]
                is_joined = uid in attendee_ids
                creator = event.get("creator") or {}

                # Format date
                event_dt_str = event.get("event_date", "")
                try:
                    event_dt = datetime.fromisoformat(event_dt_str.replace("Z", "+00:00"))
                    formatted_date = event_dt.strftime("%A, %B %d · %I:%M %p")
                    days_away = (event_dt - datetime.now(event_dt.tzinfo)).days
                    time_label = (
                        "Today!" if days_away == 0
                        else f"In {days_away} day{'s' if days_away != 1 else ''}"
                    )
                except Exception:
                    formatted_date = event_dt_str
                    time_label = ""

                cover_img = event.get("cover_image_url", "")
                cover_style = f'background-image: url({cover_img}); background-size: cover;' if cover_img else ""

                # Attendee avatars HTML
                avatars_html = ""
                for attendee in attendees[:5]:
                    img = get_avatar_url(attendee)
                    avatars_html += f'<img class="attendee-avatar" src="{img}" title="{attendee.get("name","?")}">'

                col_main, col_btn = st.columns([4, 1])
                with col_main:
                    st.markdown(f"""
                    <div class="event-card">
                        <div class="event-cover" style="{cover_style}">
                            {"" if cover_img else "🎉"}
                        </div>
                        <div class="event-body">
                            <div class="event-title">{event.get('title','Event')}</div>
                            <div class="event-meta">
                                📅 {formatted_date} &nbsp;·&nbsp;
                                ⚡ {time_label} &nbsp;·&nbsp;
                                📍 {event.get('location','TBD')} &nbsp;·&nbsp;
                                👥 {len(attendees)}/{event.get('max_attendees', 50)} attending
                            </div>
                            <p style="color:#555; font-size:0.9rem; margin-bottom:0.75rem;">
                                {(event.get('description') or '')[:120]}{'...' if len(event.get('description') or '') > 120 else ''}
                            </p>
                            <div style="display:flex; align-items:center; gap:0.5rem;">
                                <div style="margin-left:8px;">{avatars_html}</div>
                                <span style="color:#888; font-size:0.8rem; margin-left:4px;">
                                    {f"+ {len(attendees)-5} more" if len(attendees) > 5 else ""}
                                </span>
                            </div>
                            <div style="margin-top:0.5rem; color:#AAA; font-size:0.78rem;">
                                Hosted by {creator.get('name','?')}
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                with col_btn:
                    st.markdown("<br><br><br><br><br>", unsafe_allow_html=True)
                    if is_joined:
                        if st.button("✅ Joined", key=f"leave_{event['id']}", use_container_width=True):
                            leave_event(event["id"], uid)
                            st.rerun()
                    else:
                        if len(attendees) >= event.get("max_attendees", 50):
                            st.button("🔒 Full", disabled=True, key=f"full_{event['id']}", use_container_width=True)
                        else:
                            if st.button("Join 🎟️", key=f"join_{event['id']}", use_container_width=True, type="primary"):
                                join_event(event["id"], uid)
                                st.success(f"You're in! See you at '{event.get('title','the event')}' 🎉")
                                st.rerun()

    # ── CREATE ──────────────────────────────────────────────────────────────
    with tab_create:
        st.subheader("🗓️ Create a New Event")

        with st.form("create_event_form"):
            title = st.text_input("Event Title *", placeholder="e.g. Coffee Meetup in Westlands")
            description = st.text_area("Description", placeholder="What's this event about?", height=100)

            col1, col2 = st.columns(2)
            with col1:
                location = st.text_input("Location / Venue", placeholder="e.g. Java House, Westlands")
            with col2:
                max_att = st.number_input("Max Attendees", min_value=2, max_value=500, value=20)

            col3, col4 = st.columns(2)
            with col3:
                event_date = st.date_input("Date", value=(datetime.now() + timedelta(days=7)).date())
            with col4:
                event_time = st.time_input("Time", value=datetime.now().replace(hour=18, minute=0).time())

            submitted = st.form_submit_button("🎉 Create Event", use_container_width=True, type="primary")

            if submitted:
                if not title.strip():
                    st.error("Event title is required.")
                else:
                    event_dt = datetime.combine(event_date, event_time).replace(tzinfo=timezone.utc)
                    if event_dt < datetime.now(timezone.utc):
                        st.error("Event date must be in the future.")
                    else:
                        new_event = create_event({
                            "creator_id": uid,
                            "title": title.strip(),
                            "description": description.strip(),
                            "location": location.strip(),
                            "event_date": event_dt.isoformat(),
                            "max_attendees": int(max_att),
                        })
                        if new_event:
                            join_event(new_event["id"], uid)
                            st.success(f"✅ Event '{title}' created! You've been added as the first attendee.")
                            st.rerun()
                        else:
                            st.error("Failed to create event. Please try again.")
