"""
components/chat_box.py
Chat with:
- Long-press simulation: click ⋯ on message for Edit / Delete / Copy
- Reactions shown as pill counts on bubbles (no reaction buttons)
- Auto-refresh every 4s
- Left/right bubbles, day dividers, blue read receipts, online status
"""

import streamlit as st
import time
from typing import List, Dict
from datetime import datetime, timezone, timedelta
from utils.db import (
    get_messages, send_message, mark_messages_read,
    add_reaction, delete_message, edit_message,
)
from components.profile_card import get_avatar_url


def render_chat_box(match_id: str, current_user: Dict, other_user: Dict):
    uid        = current_user["id"]
    other_id   = other_user["id"]
    other_name = other_user.get("name") or "?"
    other_img  = get_avatar_url(other_user)
    my_img     = get_avatar_url(current_user)

    mark_messages_read(match_id, uid)

    sel_key     = f"sel_{match_id}"
    edit_key    = f"edt_{match_id}"
    refresh_key = f"rfr_{match_id}"

    # ── Auto-refresh every 4 seconds (pause while editing) ───────────────────
    now_ts = time.time()
    if now_ts - st.session_state.get(refresh_key, 0) > 4:
        st.session_state[refresh_key] = now_ts
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
        <div>
            <div style="font-weight:700;font-size:1rem;">{other_name}</div>
            <div>{status_html}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── CSS ───────────────────────────────────────────────────────────────────
    st.markdown("""
    <style>
    .cbubble-sent {
        background:linear-gradient(135deg,#FF6B6B,#FF8E53);color:white;
        border-radius:18px 18px 4px 18px;padding:9px 14px;max-width:72%;
        font-size:.93rem;line-height:1.45;word-break:break-word;
    }
    .cbubble-recv {
        background:#F1F1F1;color:#222;
        border-radius:18px 18px 18px 4px;padding:9px 14px;max-width:72%;
        font-size:.93rem;line-height:1.45;word-break:break-word;
    }
    .crow-sent { display:flex;justify-content:flex-end; align-items:flex-end;gap:7px;margin:2px 0; }
    .crow-recv { display:flex;justify-content:flex-start;align-items:flex-end;gap:7px;margin:2px 0; }
    .cavatar   { width:26px;height:26px;border-radius:50%;object-fit:cover;flex-shrink:0; }
    .ctime-sent{ text-align:right; font-size:.68rem;color:#BBB;margin:0 33px 2px 0; }
    .ctime-recv{ text-align:left;  font-size:.68rem;color:#BBB;margin:0 0 2px 33px; }
    .day-div   { text-align:center;font-size:.75rem;color:#BBB;
                 margin:10px 0 6px;border-top:1px solid #EEE;padding-top:8px; }
    .deleted-msg { color:#CCC;font-style:italic;font-size:.85rem; }
    .rpill { background:#F0F0F0;border:1px solid #E0E0E0;border-radius:20px;
             padding:1px 7px;font-size:.78rem;margin-right:3px;display:inline-block; }

    /* ⋯ menu button — tiny, unobtrusive */
    .msg-menu-btn {
        background:transparent;border:none;cursor:pointer;
        color:#CCC;font-size:.9rem;padding:0 4px;
        line-height:1;border-radius:4px;
    }
    .msg-menu-btn:hover { color:#888;background:#F5F5F5; }

    /* Action popover */
    .action-popover {
        display:inline-flex;align-items:center;gap:4px;
        background:white;border-radius:20px;padding:5px 10px;
        box-shadow:0 4px 18px rgba(0,0,0,.14);
        margin:2px 33px 6px;
    }
    .action-popover.right { float:right;margin:2px 33px 6px; clear:both; }
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
            msg_id  = msg.get("id","")
            is_mine = msg["sender_id"] == uid
            deleted = msg.get("deleted", False)
            text    = (msg.get("message") or "").strip()
            media   = msg.get("media_url") or ""
            ts      = _fmt_time(msg.get("created_at",""))
            is_read = msg.get("is_read", False)
            edited  = msg.get("edited", False)
            reactions = msg.get("reactions") or {}
            is_selected = selected_id == msg_id

            # Day divider
            day = _day_label(msg.get("created_at",""))
            if day and day != last_day:
                st.markdown(f'<div class="day-div">{day}</div>', unsafe_allow_html=True)
                last_day = day

            # ── Editing mode ──────────────────────────────────────────────────
            if editing_id == msg_id and is_mine and not deleted:
                new_txt = st.text_input(
                    "Edit", value=text, key=f"einput_{msg_id}",
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

            # ── Bubble ────────────────────────────────────────────────────────
            if deleted:
                content = '<span class="deleted-msg">🚫 Deleted</span>'
            else:
                content = ""
                if media:
                    if any(media.endswith(e) for e in [".ogg",".mp3",".m4a",".wav"]):
                        content += f'<audio controls style="max-width:190px;"><source src="{media}"></audio>'
                    else:
                        content += f'<img src="{media}" style="max-width:180px;border-radius:10px;display:block;margin-bottom:4px;">'
                if text:
                    content += f"<span>{text}</span>"
                if edited:
                    content += ' <span style="font-size:.63rem;opacity:.55;">(edited)</span>'

            # Reaction pills (just display counts, no buttons)
            rpills = ""
            if reactions:
                rpills = " ".join(
                    f'<span class="rpill">{e} {len(uids)}</span>'
                    for e, uids in reactions.items() if uids
                )

            # Tick
            tick = ""
            if is_mine and not deleted:
                tc = "#60A5FA" if is_read else "#FFFFFF88"
                tick = f'<span style="color:{tc};font-size:.7rem;"> ✓✓</span>'

            # Layout: bubble row + optional ⋯ button beside it
            if is_mine:
                c_menu, c_bub = st.columns([1, 10])
                with c_bub:
                    st.markdown(f"""
                    <div class="crow-sent">
                        <div class="cbubble-sent">{content}{tick}</div>
                        <img class="cavatar" src="{my_img}">
                    </div>
                    {"<div style='text-align:right;padding-right:33px;'>" + rpills + "</div>" if rpills else ""}
                    <div class="ctime-sent">{ts}</div>
                    """, unsafe_allow_html=True)
                with c_menu:
                    st.markdown("<div style='padding-top:12px;'>", unsafe_allow_html=True)
                    if not deleted:
                        if st.button("⋯", key=f"menu_{msg_id}", help="Options"):
                            if is_selected:
                                st.session_state.pop(sel_key, None)
                            else:
                                st.session_state[sel_key] = msg_id
                            st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)
            else:
                c_bub, c_menu = st.columns([10, 1])
                with c_bub:
                    st.markdown(f"""
                    <div class="crow-recv">
                        <img class="cavatar" src="{other_img}">
                        <div class="cbubble-recv">{content}</div>
                    </div>
                    {"<div style='padding-left:33px;'>" + rpills + "</div>" if rpills else ""}
                    <div class="ctime-recv">{ts}</div>
                    """, unsafe_allow_html=True)
                with c_menu:
                    st.markdown("<div style='padding-top:12px;'>", unsafe_allow_html=True)
                    if not deleted:
                        if st.button("⋯", key=f"menu_{msg_id}", help="Options"):
                            if is_selected:
                                st.session_state.pop(sel_key, None)
                            else:
                                st.session_state[sel_key] = msg_id
                            st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

            # ── Action popover (shown when ⋯ is clicked) ──────────────────────
            if is_selected and not deleted:
                if is_mine:
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        if st.button("✏️ Edit", key=f"act_edit_{msg_id}", use_container_width=True):
                            st.session_state[edit_key] = msg_id
                            st.session_state.pop(sel_key, None)
                            st.rerun()
                    with c2:
                        if st.button("🗑️ Delete", key=f"act_del_{msg_id}", use_container_width=True):
                            delete_message(msg_id, uid)
                            st.session_state.pop(sel_key, None)
                            st.rerun()
                    with c3:
                        if st.button("✕ Close", key=f"act_cls_{msg_id}", use_container_width=True):
                            st.session_state.pop(sel_key, None)
                            st.rerun()
                else:
                    # For received messages: just close
                    if st.button("✕ Close", key=f"act_cls_{msg_id}"):
                        st.session_state.pop(sel_key, None)
                        st.rerun()

    # ── Send ──────────────────────────────────────────────────────────────────
    msg_text = st.chat_input(f"Message {other_name}...")
    if msg_text:
        send_message(match_id, uid, other_id, msg_text.strip())
        st.session_state[refresh_key] = time.time()
        st.rerun()

    # ── Media ─────────────────────────────────────────────────────────────────
    with st.expander("📎 Send media"):
        t1, t2, t3 = st.tabs(["🖼️ Image", "🎙️ Voice", "GIF"])
        with t1:
            f = st.file_uploader("Image", type=["jpg","jpeg","png","gif","webp"],
                                  key=f"ci_{match_id}", label_visibility="collapsed")
            if f and st.button("Send", key=f"si_{match_id}", type="primary"):
                from utils.media import upload_chat_image
                url = upload_chat_image(f.getvalue(), uid)
                if url:
                    send_message(match_id, uid, other_id, "", media_url=url)
                    st.rerun()
        with t2:
            st.caption("Record on your phone, then upload the file:")
            a = st.file_uploader("Audio", type=["ogg","mp3","m4a","wav"],
                                  key=f"ca_{match_id}", label_visibility="collapsed")
            if a and st.button("Send voice", key=f"sa_{match_id}", type="primary"):
                from utils.media import upload_audio
                url = upload_audio(a.getvalue(), uid, match_id)
                if url:
                    send_message(match_id, uid, other_id, "🎙️ Voice message", media_url=url)
                    st.rerun()
        with t3:
            g = st.text_input("GIF URL (from giphy.com)", key=f"cg_{match_id}",
                               label_visibility="collapsed", placeholder="https://media.giphy.com/...")
            if g and st.button("Send GIF", key=f"sg_{match_id}", type="primary"):
                if g.startswith("http"):
                    send_message(match_id, uid, other_id, "", media_url=g)
                    st.rerun()


def _online_status(s):
    try:
        dt    = datetime.fromisoformat(s.replace("Z","+00:00"))
        delta = datetime.now(timezone.utc) - dt
        if delta < timedelta(minutes=10): return '<span style="color:#22C55E;font-size:.78rem;">● Online now</span>'
        if delta < timedelta(hours=1):    return f'<span style="color:#F59E0B;font-size:.78rem;">● {int(delta.total_seconds()//60)}m ago</span>'
        if delta < timedelta(days=1):     return f'<span style="color:#9CA3AF;font-size:.78rem;">● {int(delta.total_seconds()//3600)}h ago</span>'
        return '<span style="color:#D1D5DB;font-size:.78rem;">● Offline</span>'
    except: return '<span style="color:#D1D5DB;font-size:.78rem;">💞 Matched</span>'

def _fmt_time(ts):
    try:
        dt = datetime.fromisoformat(ts.replace("Z","+00:00"))
        now = datetime.now(dt.tzinfo)
        delta = now - dt
        if delta.days == 0: return dt.strftime("%H:%M")
        if delta.days == 1: return "Yesterday " + dt.strftime("%H:%M")
        return dt.strftime("%b %d %H:%M")
    except: return ""

def _day_label(ts):
    try:
        dt   = datetime.fromisoformat(ts.replace("Z","+00:00"))
        now  = datetime.now(dt.tzinfo)
        diff = (now.date() - dt.date()).days
        if diff == 0: return "Today"
        if diff == 1: return "Yesterday"
        return dt.strftime("%A, %b %d")
    except: return ""

_format_time = _fmt_time
