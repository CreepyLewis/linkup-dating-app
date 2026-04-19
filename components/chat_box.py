"""
components/chat_box.py
Sent messages on the RIGHT. Received on the LEFT.
"""

import streamlit as st
from typing import List, Dict
from datetime import datetime
from utils.db import get_messages, send_message, mark_messages_read
from components.profile_card import get_avatar_url


def render_chat_box(match_id: str, current_user: Dict, other_user: Dict):
    uid        = current_user["id"]
    other_id   = other_user["id"]
    other_name = other_user.get("name") or "?"
    other_img  = get_avatar_url(other_user)

    mark_messages_read(match_id, uid)

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:12px;padding:12px 16px;
         background:linear-gradient(135deg,#FF6B6B,#FF8E53);border-radius:12px;
         margin-bottom:1rem;color:white;">
        <img src="{other_img}" style="width:44px;height:44px;border-radius:50%;
             object-fit:cover;border:2px solid white;flex-shrink:0;">
        <div>
            <div style="font-weight:700;font-size:1rem;">{other_name}</div>
            <div style="font-size:0.78rem;opacity:0.85;">💞 You matched</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Messages ──────────────────────────────────────────────────────────────
    messages: List[Dict] = get_messages(match_id, limit=50)

    if not messages:
        st.markdown(
            f"<div style='text-align:center;color:#AAA;padding:2rem;'>"
            f"Start the conversation with {other_name} 👋</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown("""
        <style>
        .chat-wrap { display:flex; flex-direction:column; gap:6px; margin-bottom:1rem; }

        /* Received — LEFT */
        .msg-received {
            display:flex; align-items:flex-end; gap:8px;
            justify-content:flex-start;
        }
        .bubble-received {
            background:#F1F1F1; color:#222;
            border-radius:18px 18px 18px 4px;
            padding:8px 14px; max-width:70%;
            font-size:0.93rem; line-height:1.4;
        }

        /* Sent — RIGHT */
        .msg-sent {
            display:flex; align-items:flex-end; gap:8px;
            justify-content:flex-end;
        }
        .bubble-sent {
            background:linear-gradient(135deg,#FF6B6B,#FF8E53);
            color:white;
            border-radius:18px 18px 4px 18px;
            padding:8px 14px; max-width:70%;
            font-size:0.93rem; line-height:1.4;
        }

        .msg-avatar {
            width:28px;height:28px;border-radius:50%;
            object-fit:cover;flex-shrink:0;
        }
        .msg-time {
            font-size:0.68rem; color:#BBB;
            text-align:center; margin:2px 0 4px;
        }
        </style>
        <div class="chat-wrap">
        """, unsafe_allow_html=True)

        my_img = get_avatar_url(current_user)

        for msg in messages:
            is_mine = msg["sender_id"] == uid
            text    = (msg.get("message") or "").strip()
            media   = msg.get("media_url") or ""
            ts      = _fmt_time(msg.get("created_at", ""))
            tick    = " ✓✓" if (is_mine and msg.get("is_read")) else ""

            content = ""
            if media:
                content += f'<img src="{media}" style="max-width:180px;border-radius:10px;display:block;">'
            if text:
                content += f"<span>{text}</span>"

            if is_mine:
                st.markdown(f"""
                <div class="msg-sent">
                    <div class="bubble-sent">{content}</div>
                    <img class="msg-avatar" src="{my_img}">
                </div>
                <div class="msg-time" style="text-align:right;padding-right:36px;">{ts}{tick}</div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="msg-received">
                    <img class="msg-avatar" src="{other_img}">
                    <div class="bubble-received">{content}</div>
                </div>
                <div class="msg-time" style="text-align:left;padding-left:36px;">{ts}</div>
                """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    # ── Input ─────────────────────────────────────────────────────────────────
    msg_text = st.chat_input(f"Message {other_name}...")
    if msg_text:
        send_message(match_id, uid, other_id, msg_text.strip())
        st.rerun()

    # ── Image ─────────────────────────────────────────────────────────────────
    with st.expander("📎 Send image"):
        img_file = st.file_uploader(
            "Choose image", type=["jpg","jpeg","png"],
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
        if delta.days == 0:   return dt.strftime("%H:%M")
        if delta.days == 1:   return "Yesterday"
        return dt.strftime("%b %d")
    except Exception:
        return ""

# Backwards compatibility alias
_format_time = _fmt_time
