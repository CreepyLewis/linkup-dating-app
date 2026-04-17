"""
utils/media.py
Image uploads using Supabase Storage (uses service role key).
"""

import os
import uuid
import io
import streamlit as st
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

BUCKET_AVATARS = "avatars"
BUCKET_CHAT    = "chat-images"


def _storage():
    """Get storage client using service role for write access."""
    from utils.db import get_service_client
    return get_service_client().storage


def _resize_image(file_bytes: bytes, max_size: int = 800) -> bytes:
    """Resize image to max_size x max_size, convert to JPEG."""
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(file_bytes))
        img = img.convert("RGB")
        img.thumbnail((max_size, max_size), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85, optimize=True)
        return buf.getvalue()
    except Exception:
        return file_bytes  # return original if resize fails


def upload_image(file_bytes: bytes, user_id: str, folder: str = "profiles") -> Optional[str]:
    """Upload profile image. Returns public URL or None."""
    try:
        img_bytes = _resize_image(file_bytes)
        filename  = f"{folder}/{user_id}/{uuid.uuid4().hex}.jpg"
        storage   = _storage()
        storage.from_(BUCKET_AVATARS).upload(
            path=filename,
            file=img_bytes,
            file_options={"content-type": "image/jpeg", "upsert": "true"},
        )
        return storage.from_(BUCKET_AVATARS).get_public_url(filename)
    except Exception as e:
        err = str(e)
        if "Bucket not found" in err or "not found" in err.lower():
            st.error(
                "**Storage bucket missing.**  \n"
                "Go to → Supabase → Storage → New bucket  \n"
                "Name: **avatars** · Tick: **Public bucket** · Save  \n"
                "Then try again."
            )
        elif "row-level security" in err.lower() or "policy" in err.lower():
            st.error("Storage permission error. Make sure the bucket is set to Public.")
        else:
            st.error(f"Upload failed: {err}")
        return None


def upload_chat_image(file_bytes: bytes, user_id: str) -> Optional[str]:
    """Upload chat image. Returns public URL or None."""
    try:
        img_bytes = _resize_image(file_bytes, max_size=600)
        filename  = f"chat/{user_id}/{uuid.uuid4().hex}.jpg"
        storage   = _storage()
        storage.from_(BUCKET_CHAT).upload(
            path=filename,
            file=img_bytes,
            file_options={"content-type": "image/jpeg", "upsert": "true"},
        )
        return storage.from_(BUCKET_CHAT).get_public_url(filename)
    except Exception as e:
        st.error(f"Image upload failed: {e}")
        return None


def get_thumbnail_url(url: str, width: int = 200, height: int = 200) -> str:
    if not url:
        return url
    if "supabase.co/storage" in url:
        return url + f"?width={width}&height={height}&resize=cover"
    return url


def test_storage_connection() -> bool:
    """Return True if avatars bucket is accessible."""
    try:
        _storage().from_(BUCKET_AVATARS).list()
        return True
    except Exception:
        return False
