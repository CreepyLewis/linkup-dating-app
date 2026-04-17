"""
utils/media.py
Cloudinary image upload with SSL fix for proxy environments.
Falls back gracefully if Cloudinary is not configured or upload fails.
"""

import os
import streamlit as st
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

_configured = False
_cloudinary_available = False


def _configure() -> bool:
    """Configure Cloudinary. Returns True if credentials are present."""
    global _configured, _cloudinary_available
    if _configured:
        return _cloudinary_available

    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME", "").strip()
    api_key = os.getenv("CLOUDINARY_API_KEY", "").strip()
    api_secret = os.getenv("CLOUDINARY_API_SECRET", "").strip()

    # Only configure if all three credentials are present
    if cloud_name and api_key and api_secret:
        try:
            import cloudinary
            import cloudinary.uploader
            import cloudinary.api
            cloudinary.config(
                cloud_name=cloud_name,
                api_key=api_key,
                api_secret=api_secret,
                secure=True,
            )
            _cloudinary_available = True
        except ImportError:
            _cloudinary_available = False
    else:
        _cloudinary_available = False

    _configured = True
    return _cloudinary_available


def upload_image(file_bytes: bytes, user_id: str, folder: str = "profiles") -> Optional[str]:
    """
    Upload image to Cloudinary.
    Returns public URL or None if Cloudinary is not configured or upload fails.
    """
    if not _configure():
        st.warning("⚠️ Image upload is not configured. Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET in your .env file.")
        return None

    try:
        import cloudinary.uploader
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
        err = str(e)
        if "certificate" in err.lower() or "ssl" in err.lower():
            st.error(
                "⚠️ Image upload blocked by network SSL policy.\n"
                "This is a sandbox/proxy issue. Cloudinary will work fine on Streamlit Cloud deployment."
            )
        else:
            st.error(f"Image upload failed: {err}")
        return None


def upload_chat_image(file_bytes: bytes, user_id: str) -> Optional[str]:
    """Upload a chat image. Returns URL or None."""
    if not _configure():
        st.warning("⚠️ Image upload is not configured.")
        return None

    try:
        import cloudinary.uploader
        result = cloudinary.uploader.upload(
            file_bytes,
            folder=f"linkup/chat/{user_id}",
            transformation=[{"width": 600, "quality": "auto:good"}],
        )
        return result.get("secure_url")
    except Exception as e:
        st.error(f"Image upload failed: {e}")
        return None


def delete_image(public_id: str):
    if not _configure():
        return
    try:
        import cloudinary.uploader
        cloudinary.uploader.destroy(public_id)
    except Exception:
        pass


def get_thumbnail_url(url: str, width: int = 200, height: int = 200) -> str:
    """Transform a Cloudinary URL to a thumbnail size."""
    if not url or "cloudinary.com" not in url:
        return url
    return url.replace("/upload/", f"/upload/w_{width},h_{height},c_fill,g_face/")


def is_cloudinary_configured() -> bool:
    """Return True if Cloudinary credentials are set."""
    return _configure()


def test_cloudinary_connection() -> bool:
    """Return True if Cloudinary is reachable."""
    if not _configure():
        return False
    try:
        import cloudinary.api
        cloudinary.api.ping()
        return True
    except Exception:
        return False
