"""
components/chat_box.py
- Left = received, Right = sent
- Day dividers (Today / Yesterday / date)
- Read receipts (grey sent, blue when read)
- Typing indicator via session state polling
"""

import streamlit as st
from typing import List, Dict
from datetime import datetime, timezone, timedelta
from utils.db import get_messages, send_message, mark_messages_read
from components.profile_card import get_avatar_url


def render_chat_box(match_id: str, current_user: Dict, other_user: Dict):
    uid        = current_user["id"]
    other_id   = other_user["id"]
    other_name = other_user.get("name") or "?"
    other_img  = get_avatar_url(other_user)
    my_img     = get_avatar_url(current_user)

    mark_messages_read(match_id, uid)

    # ── Header ────────────────────────────────────────────────────────────────
    # Online status
    last_seen_str = other_user.get("last_seen") or ""
    status_html   = ""
    try:
        ls    = datetime.fromisoformat(last_seen_str.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - ls
        if delta < timedelta(minutes=10):
            status_html = '<span style="color:#22C55E;font-size:0.78rem;">● Online now</span>'
        elif delta < timedelta(hours=1):
            status_html = f'<span style="color:#F59E0B;font-size:0.78rem;">● {int(delta.total_seconds()//60)}m ago</span>'
        else:
            status_html = '<span style="color:#BBB;font-size:0.78rem;">● Offline</span>'
    except Exception:
        status_html = '<span style="color:#CCC;font-size:0.78rem;">💞 Matched</span>'

    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:12px;padding:12px 16px;
         background:linear-gradient(135deg,#FF6B6B,#FF8E53);border-radius:12px;
         margin-bottom:1rem;color:white;">
        <img src="{other_img}" style="width:44px;height:44px;border-radius:50%;
             object-fit:cover;border:2px solid white;flex-shrink:0;">
        <div>
            <div style="font-weight:700;font-size:1rem;">{other_name}</div>
            <div>{status_html}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Messages ──────────────────────────────────────────────────────────────
    messages: List[Dict] = get_messages(match_id, limit=50)

    if not messages:
        st.markdown(
            f"<div style='text-align:center;color:#AAA;padding:2rem;'>"
            f"Say hello to {other_name}! 👋</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown("""
        <style>
        .cbubble-sent {
            background:linear-gradient(135deg,#FF6B6B,#FF8E53);
            color:white;border-radius:18px 18px 4px 18px;
            padding:9px 14px;max-width:70%;font-size:0.93rem;line-height:1.4;
            word-break:break-word;
        }
        .cbubble-recv {
            background:#F1F1F1;color:#222;
            border-radius:18px 18px 18px 4px;
            padding:9px 14px;max-width:70%;font-size:0.93rem;line-height:1.4;
            word-break:break-word;
        }
        .cmsg-row-sent  { display:flex;justify-content:flex-end; align-items:flex-end;gap:7px;margin:3px 0; }
        .cmsg-row-recv  { display:flex;justify-content:flex-start;align-items:flex-end;gap:7px;margin:3px 0; }
        .cmsg-avatar    { width:26px;height:26px;border-radius:50%;object-fit:cover;flex-shrink:0; }
        .cmsg-time-sent { text-align:right; font-size:0.68rem;color:#BBB;margin:0 33px 6px 0; }
        .cmsg-time-recv { text-align:left;  font-size:0.68rem;color:#BBB;margin:0 0 6px 33px; }
        .day-divider {
            text-align:center;color:#BBB;font-size:0.75rem;
            margin:12px 0 8px;
            border-top:1px solid #EEE;padding-top:8px;
        }
        </style>
        """, unsafe_allow_html=True)

        last_day = None
        for msg in messages:
            is_mine = msg["sender_id"] == uid
            text    = (msg.get("message") or "").strip()
            media   = msg.get("media_url") or ""
            ts_str  = msg.get("created_at", "")
            ts      = _fmt_time(ts_str)
            is_read = msg.get("is_read", False)

            # Day divider
            day_label = _day_label(ts_str)
            if day_label and day_label != last_day:
                st.markdown(f'<div class="day-divider">{day_label}</div>', unsafe_allow_html=True)
                last_day = day_label

            content = ""
            if media:
                content += f'<img src="{media}" style="max-width:180px;border-radius:10px;display:block;margin-bottom:4px;">'
            if text:
                content += f"<span>{text}</span>"

            if is_mine:
                # Read receipt: blue ticks if read, grey if sent
                tick_color = "#3B82F6" if is_read else "#FFFFFF88"
                tick       = f'<span style="color:{tick_color};font-size:0.7rem;"> ✓✓</span>'
                st.markdown(f"""
                <div class="cmsg-row-sent">
                    <div class="cbubble-sent">{content}{tick}</div>
                    <img class="cmsg-avatar" src="{my_img}">
                </div>
                <div class="cmsg-time-sent">{ts}</div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="cmsg-row-recv">
                    <img class="cmsg-avatar" src="{other_img}">
                    <div class="cbubble-recv">{content}</div>
                </div>
                <div class="cmsg-time-recv">{ts}</div>
                """, unsafe_allow_html=True)

        # ── Typing indicator ──────────────────────────────────────────────────
        # Lightweight: show if other user was last seen < 30s ago and chat is open
        typing_key = f"typing_{match_id}_{other_id}"
        try:
            ls    = datetime.fromisoformat(last_seen_str.replace("Z", "+00:00"))
            delta = datetime.now(timezone.utc) - ls
            # If other user is online and we have an unread count in-flight
            if delta < timedelta(seconds=30):
                if st.session_state.get(typing_key, False):
                    st.markdown(f"""
                    <div class="cmsg-row-recv" style="margin-top:4px;">
                        <img class="cmsg-avatar" src="{other_img}">
                        <div class="cbubble-recv" style="padding:8px 16px;">
                            <span style="letter-spacing:2px;color:#AAA;">•••</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        except Exception:
            pass

    # ── Input ─────────────────────────────────────────────────────────────────
    msg_text = st.chat_input(f"Message {other_name}...")
    if msg_text:
        send_message(match_id, uid, other_id, msg_text.strip())
        st.rerun()

    # ── Image upload ──────────────────────────────────────────────────────────
    with st.expander("📎 Send image"):
        img_file = st.file_uploader(
            "Choose image", type=["jpg", "jpeg", "png"],
            key=f"chat_img_{match_id}", label_visibility="collapsed",
        )
        if img_file:
            if st.button("Send", key=f"send_img_{match_id}", type="primary"):
                from utils.media import upload_chat_image
                url = upload_chat_image(img_file.getvalue(), uid)
                if url:
                    send_message(match_id, uid, other_id, "", media_url=url)
                    st.rerun()


def _fmt_time(ts: str) -> str:
    try:
        dt    = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        now   = datetime.now(dt.tzinfo)
        delta = now - dt
        if delta.days == 0:  return dt.strftime("%H:%M")
        if delta.days == 1:  return "Yesterday " + dt.strftime("%H:%M")
        return dt.strftime("%b %d %H:%M")
    except Exception:
        return ""


def _day_label(ts: str) -> str:
    try:
        dt    = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        now   = datetime.now(dt.tzinfo)
        delta = (now.date() - dt.date()).days
        if delta == 0:  return "Today"
        if delta == 1:  return "Yesterday"
        return dt.strftime("%A, %b %d")
    except Exception:
        return ""

# Backwards compatibility
_format_time = _fmt_time
