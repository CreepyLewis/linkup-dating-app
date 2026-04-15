"""
utils/media.py
Cloudinary image upload + Supabase Storage fallback
"""

import os
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
from typing import Optional
import streamlit as st

load_dotenv()

_configured = False


def _configure():
    global _configured
    if not _configured:
        cloudinary.config(
            cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
            api_key=os.getenv("CLOUDINARY_API_KEY"),
            api_secret=os.getenv("CLOUDINARY_API_SECRET"),
        )
        _configured = True


def upload_image(file_bytes: bytes, user_id: str, folder: str = "profiles") -> Optional[str]:
    """Upload image to Cloudinary. Returns public URL or None."""
    _configure()
    try:
        result = cloudinary.uploader.upload(
            file_bytes,
            folder=f"linkup/{folder}/{user_id}",
            transformation=[
                {"width": 800, "height": 800, "crop": "fill", "gravity": "face"},
                {"quality": "auto:good"},
            ],
        )
        return result.get("secure_url")
    except Exception as e:
        st.error(f"Image upload failed: {e}")
        return None


def upload_chat_image(file_bytes: bytes, user_id: str) -> Optional[str]:
    """Upload a chat image (smaller transform)."""
    _configure()
    try:
        result = cloudinary.uploader.upload(
            file_bytes,
            folder=f"linkup/chat/{user_id}",
            transformation=[
                {"width": 600, "quality": "auto:good"},
            ],
        )
        return result.get("secure_url")
    except Exception as e:
        st.error(f"Image upload failed: {e}")
        return None


def delete_image(public_id: str):
    _configure()
    try:
        cloudinary.uploader.destroy(public_id)
    except Exception:
        pass


def get_thumbnail_url(url: str, width: int = 200, height: int = 200) -> str:
    """Transform a Cloudinary URL to a thumbnail."""
    if not url or "cloudinary.com" not in url:
        return url
    return url.replace("/upload/", f"/upload/w_{width},h_{height},c_fill,g_face/")
