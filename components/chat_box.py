"""
components/chat_box.py
Real-time chat UI component
"""

import streamlit as st
from typing import List, Dict
from datetime import datetime
from utils.db import get_messages, send_message, mark_messages_read
from utils.media import upload_chat_image
from components.profile_card import get_avatar_url



def _get_online_status(user: dict) -> str:
    """Return online/last-seen string for a user."""
    from datetime import datetime, timezone
    ls = user.get("last_seen")
    if not ls:
        return "Last seen unknown"
    try:
        dt = datetime.fromisoformat(str(ls).replace("Z", "+00:00"))
        delta = (datetime.now(timezone.utc) - dt).total_seconds()
        if delta < 300:
            return "🟢 Online now"
        elif delta < 3600:
            return f"Last seen {int(delta//60)}m ago"
        elif delta < 86400:
            return f"Last seen {int(delta//3600)}h ago"
        else:
            from datetime import timedelta
            days = int(delta // 86400)
            return f"Last seen {days}d ago"
    except Exception:
        return "Last seen recently"

def render_chat_box(match_id: str, current_user: Dict, other_user: Dict):
    """Full chat interface for a match."""
    uid = current_user["id"]
    other_id = other_user["id"]

    # Mark messages as read
    mark_messages_read(match_id, uid)

    # Auto-refresh toggle
    auto_refresh = st.toggle("🔄 Auto-refresh", value=False, key=f"refresh_{match_id}")
    if auto_refresh:
        import time
        time.sleep(3)
        st.rerun()

    # Load messages
    messages: List[Dict] = get_messages(match_id, limit=50)

    # Chat header
    other_img = get_avatar_url(other_user)
    st.markdown(f"""
    <style>
    .chat-header {{
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.75rem 1rem;
        background: linear-gradient(135deg, #FF6B6B, #FF8E53);
        border-radius: 12px;
        margin-bottom: 1rem;
        color: white;
    }}
    .chat-header img {{
        width: 48px; height: 48px;
        border-radius: 50%;
        object-fit: cover;
        border: 2px solid white;
    }}
    .chat-header-name {{ font-weight: 700; font-size: 1.1rem; }}
    .chat-header-status {{ font-size: 0.8rem; opacity: 0.85; }}
    .chat-container {{
        max-height: 420px;
        overflow-y: auto;
        padding: 1rem;
        background: #F9F9F9;
        border-radius: 12px;
        border: 1px solid #EEE;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }}
    .msg-row {{ display: flex; align-items: flex-end; gap: 0.5rem; }}
    .msg-row.mine {{ flex-direction: row-reverse; }}
    .msg-bubble {{
        max-width: 70%;
        padding: 0.6rem 1rem;
        border-radius: 18px;
        font-size: 0.95rem;
        line-height: 1.4;
        word-break: break-word;
    }}
    .msg-bubble.theirs {{
        background: #fff;
        border: 1px solid #EEE;
        border-bottom-left-radius: 4px;
        color: #222;
    }}
    .msg-bubble.mine {{
        background: linear-gradient(135deg, #FF6B6B, #FF8E53);
        color: white;
        border-bottom-right-radius: 4px;
    }}
    .msg-time {{
        font-size: 0.7rem;
        color: #AAA;
        margin-top: 2px;
        text-align: center;
    }}
    .msg-img {{ max-width: 200px; border-radius: 12px; margin: 4px 0; }}
    </style>

    <div class="chat-header">
        <img src="{other_img}" alt="{other_user.get('name','?')}">
        <div>
            <div class="chat-header-name">{other_user.get('name','?')}</div>
            <div class="chat-header-status">💞 Matched · {_get_online_status(other_user)}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Messages display
    if not messages:
        st.info("👋 Say hello! You've matched - start the conversation.")
    else:
        msgs_html = '<div class="chat-container" id="chat-bottom">'
        for msg in messages:
            is_mine = msg["sender_id"] == uid
            row_class = "mine" if is_mine else "theirs"
            bubble_class = "mine" if is_mine else "theirs"
            time_str = _format_time(msg.get("created_at", ""))
            read_icon = " ✓✓" if (is_mine and msg.get("is_read")) else ""

            content = ""
            if msg.get("media_url"):
                content += f'<img class="msg-img" src="{msg["media_url"]}" alt="image">'
            if msg.get("message"):
                content += f'{msg["message"]}'

            msgs_html += f"""
            <div class="msg-row {row_class}">
                <div class="msg-bubble {bubble_class}">{content}</div>
            </div>
            <div class="msg-time">{time_str}{read_icon}</div>
            """
        msgs_html += "</div>"
        st.markdown(msgs_html, unsafe_allow_html=True)

    # Input area
    st.markdown("---")
    col1, col2, col3 = st.columns([5, 1, 1])

    with col1:
        msg_text = st.text_input(
            "Message",
            placeholder=f"Message {other_user.get('name','?')}...",
            label_visibility="collapsed",
            key=f"msg_input_{match_id}",
        )

    with col2:
        if st.button("📤 Send", key=f"send_{match_id}", use_container_width=True, type="primary"):
            if msg_text.strip():
                send_message(match_id, uid, other_id, msg_text.strip())
                st.session_state[f"msg_input_{match_id}"] = ""
                st.rerun()

    with col3:
        img_file = st.file_uploader(
            "📎", type=["jpg", "jpeg", "png", "gif"],
            label_visibility="collapsed",
            key=f"img_upload_{match_id}",
        )
        if img_file:
            from utils.media import upload_chat_image
            url = upload_chat_image(img_file.getvalue(), uid)
            if url:
                send_message(match_id, uid, other_id, "", media_url=url)
                st.rerun()

    # Scroll to bottom JS
    st.markdown("""
    <script>
    const chatEl = document.getElementById('chat-bottom');
    if (chatEl) chatEl.scrollTop = chatEl.scrollHeight;
    </script>
    """, unsafe_allow_html=True)


def _format_time(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        now = datetime.now(dt.tzinfo)
        delta = now - dt
        if delta.days == 0:
            return dt.strftime("%H:%M")
        elif delta.days == 1:
            return "Yesterday"
        else:
            return dt.strftime("%b %d")
    except Exception:
        return ""
