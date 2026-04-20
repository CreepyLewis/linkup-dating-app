"""
components/chat_box.py
Full chat with: left/right bubbles, day dividers, blue read receipts,
online status, message reactions, voice messages, GIF/image sending.
"""

import streamlit as st
from typing import List, Dict
from datetime import datetime, timezone, timedelta
from utils.db import get_messages, send_message, mark_messages_read, add_reaction
from components.profile_card import get_avatar_url

REACTIONS = ["❤️", "😂", "😮", "👍", "🔥", "😢"]


def render_chat_box(match_id: str, current_user: Dict, other_user: Dict):
    uid        = current_user["id"]
    other_id   = other_user["id"]
    other_name = other_user.get("name") or "?"
    other_img  = get_avatar_url(other_user)
    my_img     = get_avatar_url(current_user)

    mark_messages_read(match_id, uid)

    # ── Online status ─────────────────────────────────────────────────────────
    last_seen_str = other_user.get("last_seen") or ""
    status_html   = _online_status(last_seen_str)

    # ── Header ────────────────────────────────────────────────────────────────
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

    st.markdown("""
    <style>
    .cbubble-sent{background:linear-gradient(135deg,#FF6B6B,#FF8E53);color:white;
        border-radius:18px 18px 4px 18px;padding:9px 14px;max-width:72%;
        font-size:.93rem;line-height:1.45;word-break:break-word;}
    .cbubble-recv{background:#F1F1F1;color:#222;
        border-radius:18px 18px 18px 4px;padding:9px 14px;max-width:72%;
        font-size:.93rem;line-height:1.45;word-break:break-word;}
    .crow-sent{display:flex;justify-content:flex-end;align-items:flex-end;gap:7px;margin:2px 0;}
    .crow-recv{display:flex;justify-content:flex-start;align-items:flex-end;gap:7px;margin:2px 0;}
    .cavatar{width:26px;height:26px;border-radius:50%;object-fit:cover;flex-shrink:0;}
    .ctime-sent{text-align:right;font-size:.68rem;color:#BBB;margin:0 33px 3px 0;}
    .ctime-recv{text-align:left;font-size:.68rem;color:#BBB;margin:0 0 3px 33px;}
    .day-div{text-align:center;color:#BBB;font-size:.75rem;
        margin:10px 0 6px;border-top:1px solid #EEE;padding-top:8px;}
    .reaction-bar{display:flex;gap:4px;flex-wrap:wrap;margin-top:3px;}
    .rpill{background:#F5F5F5;border:1px solid #EEE;border-radius:20px;
        padding:1px 7px;font-size:.8rem;cursor:pointer;}
    .rpill:hover{background:#FFE4E4;}
    </style>
    """, unsafe_allow_html=True)

    if not messages:
        st.markdown(
            f"<div style='text-align:center;color:#AAA;padding:2rem;'>"
            f"Say hello to {other_name}! 👋</div>",
            unsafe_allow_html=True,
        )
    else:
        last_day = None
        for msg in messages:
            is_mine  = msg["sender_id"] == uid
            text     = (msg.get("message") or "").strip()
            media    = msg.get("media_url") or ""
            ts       = _fmt_time(msg.get("created_at", ""))
            is_read  = msg.get("is_read", False)
            reactions = msg.get("reactions") or {}
            msg_id   = msg.get("id", "")

            # Day divider
            day = _day_label(msg.get("created_at", ""))
            if day and day != last_day:
                st.markdown(f'<div class="day-div">{day}</div>', unsafe_allow_html=True)
                last_day = day

            # Content
            content = ""
            if media:
                if media.endswith(".ogg") or media.endswith(".mp3") or "audio/" in media:
                    content += f'<audio controls style="max-width:200px;"><source src="{media}"></audio>'
                else:
                    content += f'<img src="{media}" style="max-width:180px;border-radius:10px;display:block;margin-bottom:4px;">'
            if text:
                content += f"<span>{text}</span>"

            # Reaction pills
            reaction_html = ""
            if reactions:
                pills = " ".join(
                    f'<span class="rpill">{e} {len(uids)}</span>'
                    for e, uids in reactions.items() if uids
                )
                reaction_html = f'<div class="reaction-bar">{pills}</div>'

            if is_mine:
                tick_color = "#60A5FA" if is_read else "#FFFFFF88"
                tick = f'<span style="color:{tick_color};font-size:.7rem;"> ✓✓</span>'
                st.markdown(f"""
                <div class="crow-sent">
                    <div class="cbubble-sent">{content}{tick}</div>
                    <img class="cavatar" src="{my_img}">
                </div>
                {f'<div style="text-align:right;padding-right:33px;">{reaction_html}</div>' if reaction_html else ''}
                <div class="ctime-sent">{ts}</div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="crow-recv">
                    <img class="cavatar" src="{other_img}">
                    <div class="cbubble-recv">{content}</div>
                </div>
                {f'<div style="padding-left:33px;">{reaction_html}</div>' if reaction_html else ''}
                <div class="ctime-recv">{ts}</div>
                """, unsafe_allow_html=True)

            # Reaction picker for received messages
            if not is_mine and msg_id:
                react_cols = st.columns(len(REACTIONS) + 1)
                with react_cols[0]:
                    st.markdown("<small style='color:#CCC;font-size:0.7rem;'>React:</small>",
                                unsafe_allow_html=True)
                for i, emoji in enumerate(REACTIONS):
                    with react_cols[i + 1]:
                        if st.button(emoji, key=f"react_{msg_id}_{emoji}",
                                     help=f"React with {emoji}"):
                            add_reaction(msg_id, uid, emoji)
                            st.rerun()

    # ── Text input ────────────────────────────────────────────────────────────
    msg_text = st.chat_input(f"Message {other_name}...")
    if msg_text:
        send_message(match_id, uid, other_id, msg_text.strip())
        st.rerun()

    # ── Media / Voice ─────────────────────────────────────────────────────────
    with st.expander("📎 Send media"):
        tab_img, tab_voice, tab_gif = st.tabs(["🖼️ Image", "🎙️ Voice", "GIF"])

        with tab_img:
            img_file = st.file_uploader(
                "Image", type=["jpg","jpeg","png","gif","webp"],
                key=f"chat_img_{match_id}", label_visibility="collapsed",
            )
            if img_file and st.button("Send image", key=f"send_img_{match_id}", type="primary"):
                from utils.media import upload_chat_image
                url = upload_chat_image(img_file.getvalue(), uid)
                if url:
                    send_message(match_id, uid, other_id, "", media_url=url)
                    st.rerun()

        with tab_voice:
            st.caption("Record a voice note and upload it:")
            audio_file = st.file_uploader(
                "Audio file (.ogg, .mp3, .m4a, .wav)",
                type=["ogg","mp3","m4a","wav"],
                key=f"chat_audio_{match_id}", label_visibility="collapsed",
            )
            if audio_file and st.button("Send voice note", key=f"send_audio_{match_id}", type="primary"):
                from utils.media import upload_audio
                url = upload_audio(audio_file.getvalue(), uid, match_id)
                if url:
                    send_message(match_id, uid, other_id, "🎙️ Voice message", media_url=url)
                    st.rerun()

        with tab_gif:
            gif_url = st.text_input("Paste a GIF URL (e.g. from Giphy):",
                                     key=f"gif_url_{match_id}", placeholder="https://media.giphy.com/...")
            if gif_url and st.button("Send GIF", key=f"send_gif_{match_id}", type="primary"):
                if gif_url.startswith("http"):
                    send_message(match_id, uid, other_id, "", media_url=gif_url)
                    st.rerun()
                else:
                    st.error("Must be a valid URL starting with https://")


def _online_status(last_seen_str: str) -> str:
    try:
        dt    = datetime.fromisoformat(last_seen_str.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - dt
        if delta < timedelta(minutes=10):
            return '<span style="color:#22C55E;font-size:.78rem;">● Online now</span>'
        if delta < timedelta(hours=1):
            return f'<span style="color:#F59E0B;font-size:.78rem;">● {int(delta.total_seconds()//60)}m ago</span>'
        if delta < timedelta(days=1):
            return f'<span style="color:#9CA3AF;font-size:.78rem;">● {int(delta.total_seconds()//3600)}h ago</span>'
        return '<span style="color:#D1D5DB;font-size:.78rem;">● Offline</span>'
    except Exception:
        return '<span style="color:#D1D5DB;font-size:.78rem;">💞 Matched</span>'


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
        diff  = (now.date() - dt.date()).days
        if diff == 0: return "Today"
        if diff == 1: return "Yesterday"
        return dt.strftime("%A, %b %d")
    except Exception:
        return ""

# Backwards compatibility
_format_time = _fmt_time
