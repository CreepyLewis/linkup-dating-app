"""
utils/media.py
Image AND video uploads via Supabase Storage.
"""

import os, uuid, io
import streamlit as st
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

BUCKET_AVATARS = "avatars"
BUCKET_CHAT    = "chat-images"
BUCKET_VIDEOS  = "profile-videos"


def _storage():
    from utils.db import get_service_client
    return get_service_client().storage


def _resize(file_bytes: bytes, max_size: int = 800) -> bytes:
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        img.thumbnail((max_size, max_size))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85, optimize=True)
        return buf.getvalue()
    except Exception:
        return file_bytes


def upload_image(file_bytes: bytes, user_id: str, folder: str = "profiles") -> Optional[str]:
    try:
        data     = _resize(file_bytes)
        filename = f"{folder}/{user_id}/{uuid.uuid4().hex}.jpg"
        _storage().from_(BUCKET_AVATARS).upload(
            path=filename, file=data,
            file_options={"content-type": "image/jpeg", "upsert": "true"},
        )
        return _storage().from_(BUCKET_AVATARS).get_public_url(filename)
    except Exception as e:
        _bucket_error(e, BUCKET_AVATARS)
        return None


def upload_chat_image(file_bytes: bytes, user_id: str) -> Optional[str]:
    try:
        data     = _resize(file_bytes, 600)
        filename = f"chat/{user_id}/{uuid.uuid4().hex}.jpg"
        _storage().from_(BUCKET_CHAT).upload(
            path=filename, file=data,
            file_options={"content-type": "image/jpeg", "upsert": "true"},
        )
        return _storage().from_(BUCKET_CHAT).get_public_url(filename)
    except Exception as e:
        st.error(f"Image upload failed: {e}")
        return None


def upload_video(file_bytes: bytes, user_id: str) -> Optional[str]:
    """Upload a profile video (mp4/webm, max ~30MB)."""
    try:
        filename = f"videos/{user_id}/{uuid.uuid4().hex}.mp4"
        _storage().from_(BUCKET_VIDEOS).upload(
            path=filename, file=file_bytes,
            file_options={"content-type": "video/mp4", "upsert": "true"},
        )
        return _storage().from_(BUCKET_VIDEOS).get_public_url(filename)
    except Exception as e:
        _bucket_error(e, BUCKET_VIDEOS)
        return None


def upload_audio(file_bytes: bytes, user_id: str, match_id: str) -> Optional[str]:
    """Upload a voice message (stored in chat-images bucket)."""
    try:
        filename = f"audio/{user_id}/{uuid.uuid4().hex}.ogg"
        _storage().from_(BUCKET_CHAT).upload(
            path=filename, file=file_bytes,
            file_options={"content-type": "audio/ogg", "upsert": "true"},
        )
        return _storage().from_(BUCKET_CHAT).get_public_url(filename)
    except Exception as e:
        st.error(f"Audio upload failed: {e}")
        return None


def get_thumbnail_url(url: str, w: int = 200, h: int = 200) -> str:
    if not url:
        return url
    if "supabase.co/storage" in url:
        return url + f"?width={w}&height={h}&resize=cover"
    return url


def test_storage_connection() -> bool:
    try:
        _storage().from_(BUCKET_AVATARS).list()
        return True
    except Exception:
        return False


def _bucket_error(e: Exception, bucket: str):
    err = str(e)
    if "not found" in err.lower() or "Bucket not found" in err:
        st.error(
            f"Storage bucket **`{bucket}`** missing.  \n"
            f"Go to Supabase → Storage → New bucket → Name: `{bucket}` → Public ✓"
        )
    else:
        st.error(f"Upload failed: {err}")
