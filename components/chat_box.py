"""
components/chat_box.py
Full chat with:
- Click to select message → floating action bar (react, copy, edit, delete)
- Auto-refresh every 4 seconds for new messages
- Left/right bubbles, day dividers, blue read receipts, online status
"""

import streamlit as st
from typing import List, Dict
from datetime import datetime, timezone, timedelta
from utils.db import (
    get_messages, send_message, mark_messages_read,
    add_reaction, delete_message, edit_message,
)
from components.profile_card import get_avatar_url

REACTIONS = ["❤️", "😂", "😮", "👍", "🔥", "😢"]


def render_chat_box(match_id: str, current_user: Dict, other_user: Dict):
    uid        = current_user["id"]
    other_id   = other_user["id"]
    other_name = other_user.get("name") or "?"
    other_img  = get_avatar_url(other_user)
    my_img     = get_avatar_url(current_user)

    mark_messages_read(match_id, uid)

    # ── Session keys ──────────────────────────────────────────────────────────
    sel_key    = f"sel_msg_{match_id}"     # selected message id
    edit_key   = f"edit_msg_{match_id}"   # message being edited
    refresh_key = f"last_refresh_{match_id}"

    # ── Auto-refresh every 4 seconds ─────────────────────────────────────────
    import time
    now_ts = time.time()
    last   = st.session_state.get(refresh_key, 0)
    if now_ts - last > 4:
        st.session_state[refresh_key] = now_ts
        # Only rerun if we're not in the middle of editing
        if not st.session_state.get(edit_key):
            st.rerun()

    # ── Online status ─────────────────────────────────────────────────────────
    status_html = _online_status(other_user.get("last_seen") or "")

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:12px;padding:12px 16px;
         background:linear-gradient(135deg,#FF6B6B,#FF8E53);border-radius:12px;
         margin-bottom:1rem;color:white;">
        <img src="{other_img}" style="width:44px;height:44px;border-radius:50%;
             object-fit:cover;border:2px solid white;flex-shrink:0;">
        <div style="flex:1;">
            <div style="font-weight:700;font-size:1rem;">{other_name}</div>
            <div>{status_html}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── CSS ───────────────────────────────────────────────────────────────────
    st.markdown("""
    <style>
    .cbubble-sent {
        background: linear-gradient(135deg,#FF6B6B,#FF8E53);
        color: white;
        border-radius: 18px 18px 4px 18px;
        padding: 9px 14px; max-width: 72%;
        font-size: .93rem; line-height: 1.45;
        word-break: break-word; cursor: pointer;
        transition: opacity .15s;
    }
    .cbubble-recv {
        background: #F1F1F1; color: #222;
        border-radius: 18px 18px 18px 4px;
        padding: 9px 14px; max-width: 72%;
        font-size: .93rem; line-height: 1.45;
        word-break: break-word; cursor: pointer;
        transition: opacity .15s;
    }
    .cbubble-sent:hover, .cbubble-recv:hover { opacity: .88; }
    .cbubble-selected { outline: 2px solid #FF6B6B; outline-offset: 2px; }
    .crow-sent  { display:flex; justify-content:flex-end;  align-items:flex-end; gap:7px; margin:2px 0; }
    .crow-recv  { display:flex; justify-content:flex-start; align-items:flex-end; gap:7px; margin:2px 0; }
    .cavatar    { width:26px;height:26px;border-radius:50%;object-fit:cover;flex-shrink:0; }
    .ctime-sent { text-align:right;  font-size:.68rem; color:#BBB; margin:0 33px 2px 0; }
    .ctime-recv { text-align:left;   font-size:.68rem; color:#BBB; margin:0 0 2px 33px; }
    .day-div    { text-align:center; font-size:.75rem; color:#BBB;
                  margin:10px 0 6px; border-top:1px solid #EEE; padding-top:8px; }
    .deleted-msg { color:#CCC; font-style:italic; font-size:.85rem; }

    /* ── Floating action bar ─────────────────── */
    .action-bar {
        display: flex; align-items: center; gap: 6px;
        background: white; border-radius: 28px;
        padding: 6px 10px; margin: 4px 33px;
        box-shadow: 0 4px 20px rgba(0,0,0,.14);
        flex-wrap: wrap; width: fit-content;
    }
    .action-bar.right { margin-left: auto; }
    .react-btn {
        font-size: 1.2rem; cursor: pointer;
        border: none; background: transparent;
        border-radius: 50%; width: 34px; height: 34px;
        display: flex; align-items: center; justify-content: center;
        transition: transform .15s, background .15s;
    }
    .react-btn:hover { transform: scale(1.25); background: #F5F5F5; }
    .action-pill {
        font-size: .75rem; font-weight: 600;
        padding: 4px 10px; border-radius: 20px;
        border: 1px solid #EEE; background: #FAFAFA;
        cursor: pointer; color: #555;
        transition: background .15s;
    }
    .action-pill:hover { background: #FFE4E4; color: #FF6B6B; border-color: #FFCCCC; }
    .action-pill.danger:hover { background: #FEE2E2; color: #EF4444; border-color: #FECACA; }
    </style>
    """, unsafe_allow_html=True)

    # ── Messages ──────────────────────────────────────────────────────────────
    messages: List[Dict] = get_messages(match_id, limit=50)
    selected_id = st.session_state.get(sel_key)
    editing_id  = st.session_state.get(edit_key)

    if not messages:
        st.markdown(
            f"<div style='text-align:center;color:#AAA;padding:2rem;'>"
            f"Say hello to {other_name}! 👋</div>",
            unsafe_allow_html=True,
        )
    else:
        last_day = None
        for msg in messages:
            msg_id   = msg.get("id","")
            is_mine  = msg["sender_id"] == uid
            deleted  = msg.get("deleted", False)
            text     = (msg.get("message") or "").strip()
            media    = msg.get("media_url") or ""
            ts       = _fmt_time(msg.get("created_at",""))
            is_read  = msg.get("is_read", False)
            edited   = msg.get("edited", False)
            reactions = msg.get("reactions") or {}
            is_selected = selected_id == msg_id

            # Day divider
            day = _day_label(msg.get("created_at",""))
            if day and day != last_day:
                st.markdown(f'<div class="day-div">{day}</div>', unsafe_allow_html=True)
                last_day = day

            # ── Editing mode ──────────────────────────────────────────────────
            if editing_id == msg_id and is_mine and not deleted:
                with st.container():
                    new_txt = st.text_input(
                        "Edit message", value=text,
                        key=f"edit_input_{msg_id}",
                        label_visibility="collapsed",
                    )
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        if st.button("Save", key=f"esave_{msg_id}", type="primary", use_container_width=True):
                            if new_txt.strip():
                                edit_message(msg_id, uid, new_txt.strip())
                            st.session_state.pop(edit_key, None)
                            st.rerun()
                    with ec2:
                        if st.button("Cancel", key=f"ecancel_{msg_id}", use_container_width=True):
                            st.session_state.pop(edit_key, None)
                            st.rerun()
                continue

            # ── Bubble content ────────────────────────────────────────────────
            if deleted:
                content = '<span class="deleted-msg">🚫 Message deleted</span>'
            else:
                content = ""
                if media:
                    if any(media.endswith(ext) for ext in [".ogg",".mp3",".m4a",".wav"]):
                        content += f'<audio controls style="max-width:200px;"><source src="{media}"></audio>'
                    else:
                        content += f'<img src="{media}" style="max-width:180px;border-radius:10px;display:block;margin-bottom:4px;">'
                if text:
                    content += f"<span>{text}</span>"
                if edited:
                    content += ' <span style="font-size:.65rem;opacity:.6;">(edited)</span>'

            # ── Reactions display ─────────────────────────────────────────────
            reaction_html = ""
            if reactions:
                pills = " ".join(
                    f'<span style="background:#F5F5F5;border:1px solid #EEE;border-radius:20px;'
                    f'padding:1px 7px;font-size:.8rem;">{e} {len(uids)}</span>'
                    for e, uids in reactions.items() if uids
                )
                reaction_html = f'<div style="margin-top:3px;">{pills}</div>'

            # ── Tick ──────────────────────────────────────────────────────────
            tick = ""
            if is_mine and not deleted:
                tick_color = "#60A5FA" if is_read else "#FFFFFF88"
                tick = f'<span style="color:{tick_color};font-size:.7rem;"> ✓✓</span>'

            sel_cls = " cbubble-selected" if is_selected else ""

            if is_mine:
                st.markdown(f"""
                <div class="crow-sent">
                    <div class="cbubble-sent{sel_cls}">{content}{tick}</div>
                    <img class="cavatar" src="{my_img}">
                </div>
                {"<div style='text-align:right;padding-right:33px;'>" + reaction_html + "</div>" if reaction_html else ""}
                <div class="ctime-sent">{ts}</div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="crow-recv">
                    <img class="cavatar" src="{other_img}">
                    <div class="cbubble-recv{sel_cls}">{content}</div>
                </div>
                {"<div style='padding-left:33px;'>" + reaction_html + "</div>" if reaction_html else ""}
                <div class="ctime-recv">{ts}</div>
                """, unsafe_allow_html=True)

            # ── Select button (tap to show actions) ───────────────────────────
            if not deleted:
                btn_label = "▾ actions" if not is_selected else "✕ close"
                if st.button(
                    btn_label,
                    key=f"sel_{msg_id}",
                    help="Tap to react or manage this message",
                ):
                    if is_selected:
                        st.session_state.pop(sel_key, None)
                    else:
                        st.session_state[sel_key] = msg_id
                    st.rerun()

            # ── Floating action bar (when message is selected) ─────────────────
            if is_selected and not deleted:
                align = "right" if is_mine else ""
                st.markdown(f'<div class="action-bar {align}">', unsafe_allow_html=True)

                # Reaction buttons
                rcols = st.columns(len(REACTIONS) + (3 if is_mine else 2))
                for i, emoji in enumerate(REACTIONS):
                    with rcols[i]:
                        if st.button(emoji, key=f"r_{msg_id}_{emoji}",
                                     help=f"React {emoji}"):
                            add_reaction(msg_id, uid, emoji)
                            st.session_state.pop(sel_key, None)
                            st.rerun()

                # Copy (just shows the text — clipboard API not available in Streamlit)
                with rcols[len(REACTIONS)]:
                    if st.button("📋", key=f"copy_{msg_id}", help="Copy text"):
                        if text:
                            st.toast(f"Copied: {text[:40]}{'...' if len(text)>40 else ''}")
                        st.session_state.pop(sel_key, None)
                        st.rerun()

                # Edit (only my messages)
                if is_mine:
                    with rcols[len(REACTIONS) + 1]:
                        if st.button("✏️", key=f"edit_{msg_id}", help="Edit message"):
                            st.session_state[edit_key] = msg_id
                            st.session_state.pop(sel_key, None)
                            st.rerun()

                    with rcols[len(REACTIONS) + 2]:
                        if st.button("🗑️", key=f"del_{msg_id}", help="Delete message"):
                            delete_message(msg_id, uid)
                            st.session_state.pop(sel_key, None)
                            st.rerun()

                st.markdown('</div>', unsafe_allow_html=True)

    # ── Text input ────────────────────────────────────────────────────────────
    msg_text = st.chat_input(f"Message {other_name}...")
    if msg_text:
        send_message(match_id, uid, other_id, msg_text.strip())
        st.session_state[refresh_key] = time.time()
        st.rerun()

    # ── Media ─────────────────────────────────────────────────────────────────
    with st.expander("📎 Send media"):
        tab_img, tab_voice, tab_gif = st.tabs(["🖼️ Image", "🎙️ Voice", "GIF"])

        with tab_img:
            img_file = st.file_uploader(
                "Image", type=["jpg","jpeg","png","gif","webp"],
                key=f"chat_img_{match_id}", label_visibility="collapsed",
            )
            if img_file and st.button("Send image", key=f"simg_{match_id}", type="primary"):
                from utils.media import upload_chat_image
                url = upload_chat_image(img_file.getvalue(), uid)
                if url:
                    send_message(match_id, uid, other_id, "", media_url=url)
                    st.rerun()

        with tab_voice:
            st.caption("Record a voice note, then upload the file:")
            audio_file = st.file_uploader(
                "Audio", type=["ogg","mp3","m4a","wav"],
                key=f"chat_audio_{match_id}", label_visibility="collapsed",
            )
            if audio_file and st.button("Send voice note", key=f"saudio_{match_id}", type="primary"):
                from utils.media import upload_audio
                url = upload_audio(audio_file.getvalue(), uid, match_id)
                if url:
                    send_message(match_id, uid, other_id, "🎙️ Voice message", media_url=url)
                    st.rerun()

        with tab_gif:
            gif_url = st.text_input(
                "GIF URL", key=f"gifurl_{match_id}",
                placeholder="https://media.giphy.com/...",
                label_visibility="collapsed",
            )
            if gif_url and st.button("Send GIF", key=f"sgif_{match_id}", type="primary"):
                if gif_url.startswith("http"):
                    send_message(match_id, uid, other_id, "", media_url=gif_url)
                    st.rerun()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _online_status(last_seen_str: str) -> str:
    try:
        dt    = datetime.fromisoformat(last_seen_str.replace("Z","+00:00"))
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
        dt    = datetime.fromisoformat(ts.replace("Z","+00:00"))
        now   = datetime.now(dt.tzinfo)
        delta = now - dt
        if delta.days == 0: return dt.strftime("%H:%M")
        if delta.days == 1: return "Yesterday " + dt.strftime("%H:%M")
        return dt.strftime("%b %d %H:%M")
    except Exception:
        return ""


def _day_label(ts: str) -> str:
    try:
        dt   = datetime.fromisoformat(ts.replace("Z","+00:00"))
        now  = datetime.now(dt.tzinfo)
        diff = (now.date() - dt.date()).days
        if diff == 0: return "Today"
        if diff == 1: return "Yesterday"
        return dt.strftime("%A, %b %d")
    except Exception:
        return ""

# Backwards compat
_format_time = _fmt_time
