"""
components/chat_box.py
Chat UI using st.chat_input — no session state conflicts.
"""

import streamlit as st
from typing import List, Dict
from datetime import datetime
from utils.db import get_messages, send_message, mark_messages_read
from components.profile_card import get_avatar_url


def render_chat_box(match_id: str, current_user: Dict, other_user: Dict):
    uid      = current_user["id"]
    other_id = other_user["id"]

    mark_messages_read(match_id, uid)

    # ── Header ────────────────────────────────────────────────────────────────
    other_img = get_avatar_url(other_user)
    other_name = other_user.get("name") or "?"

    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:12px;padding:12px 16px;
         background:linear-gradient(135deg,#FF6B6B,#FF8E53);border-radius:12px;
         margin-bottom:1rem;color:white;">
        <img src="{other_img}" style="width:44px;height:44px;border-radius:50%;
             object-fit:cover;border:2px solid white;">
        <div>
            <div style="font-weight:700;font-size:1rem;">{other_name}</div>
            <div style="font-size:0.78rem;opacity:0.85;">💞 Matched</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Messages ──────────────────────────────────────────────────────────────
    messages: List[Dict] = get_messages(match_id, limit=50)

    if not messages:
        st.info(f"Say hello to {other_name}! 👋")
    else:
        for msg in messages:
            is_mine = msg["sender_id"] == uid
            text    = msg.get("message") or ""
            media   = msg.get("media_url") or ""
            ts      = _fmt_time(msg.get("created_at", ""))
            read    = " ✓✓" if (is_mine and msg.get("is_read")) else ""

            if is_mine:
                with st.chat_message("user"):
                    if media:
                        st.image(media, width=200)
                    if text:
                        st.write(text)
                    st.caption(f"{ts}{read}")
            else:
                with st.chat_message("assistant"):
                    if media:
                        st.image(media, width=200)
                    if text:
                        st.write(text)
                    st.caption(ts)

    # ── Input — st.chat_input clears itself automatically after send ──────────
    msg_text = st.chat_input(f"Message {other_name}...")
    if msg_text:
        send_message(match_id, uid, other_id, msg_text.strip())
        st.rerun()

    # ── Image upload ──────────────────────────────────────────────────────────
    with st.expander("📎 Send image"):
        img_file = st.file_uploader(
            "Choose image",
            type=["jpg", "jpeg", "png"],
            key=f"chat_img_{match_id}",
            label_visibility="collapsed",
        )
        if img_file:
            if st.button("Send image", key=f"send_img_{match_id}", type="primary"):
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
        if delta.days == 0:
            return dt.strftime("%H:%M")
        elif delta.days == 1:
            return "Yesterday"
        return dt.strftime("%b %d")
    except Exception:
        return ""

# Alias for backwards compatibility
_format_time = _fmt_time
