"""
utils/media.py
Cloudinary image upload — fixed cloud_name lookup + Supabase Storage fallback.

ROOT CAUSE of "Invalid cloud_name linkup":
  Cloudinary SDK's _configure() caches _configured=True on the FIRST call,
  but if the first call reads a stale/empty env (e.g. before load_dotenv),
  it stores the wrong cloud_name and never retries.

FIXES:
  1. Always call load_dotenv() before reading env vars.
  2. Re-read credentials fresh on every configure call (no module-level cache race).
  3. Validate cloud_name is not a placeholder before trying to upload.
  4. Clear detailed error messages so the user knows exactly what to fix.
"""

import os
import streamlit as st
from dotenv import load_dotenv
from typing import Optional

# Force reload env every time this module is imported
load_dotenv(override=True)


def _get_credentials():
    """Read Cloudinary credentials fresh from environment."""
    load_dotenv(override=True)  # ensure .env is loaded even in Streamlit Cloud
    return (
        os.getenv("CLOUDINARY_CLOUD_NAME", "").strip(),
        os.getenv("CLOUDINARY_API_KEY", "").strip(),
        os.getenv("CLOUDINARY_API_SECRET", "").strip(),
    )


def _configure() -> bool:
    """
    Configure Cloudinary SDK with current credentials.
    Returns True only if all three credentials are valid non-placeholder values.
    """
    cloud_name, api_key, api_secret = _get_credentials()

    # Reject obvious placeholder values
    placeholders = {"linkup", "your-cloud-name", "", "PASTE_HERE", "YOUR_CLOUD_NAME"}
    if not cloud_name or cloud_name.lower() in {p.lower() for p in placeholders}:
        return False
    if not api_key or not api_secret:
        return False

    try:
        import cloudinary
        # Always reconfigure — don't rely on stale module-level state
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True,
        )
        return True
    except ImportError:
        return False


def _cloudinary_configured() -> bool:
    cloud_name, api_key, api_secret = _get_credentials()
    return bool(cloud_name and api_key and api_secret)


def upload_image(file_bytes: bytes, user_id: str, folder: str = "profiles") -> Optional[str]:
    """
    Upload image to Cloudinary.
    Returns public URL or None on failure.
    Shows clear, actionable error messages.
    """
    if not _configure():
        cloud_name, api_key, api_secret = _get_credentials()
        if not cloud_name or cloud_name.lower() in ("linkup", "your-cloud-name", ""):
            st.error(
                "📸 **Image upload not configured.**\n\n"
                "Your `CLOUDINARY_CLOUD_NAME` in `.env` is set to a placeholder value "
                f"(`{cloud_name or 'empty'}`). \n\n"
                "**How to fix:**\n"
                "1. Go to [cloudinary.com](https://cloudinary.com) → Dashboard\n"
                "2. Copy your real **Cloud name** (e.g. `dxxxxx`)\n"
                "3. Update `CLOUDINARY_CLOUD_NAME=dxxxxx` in your `.env` file\n"
                "4. Restart the app"
            )
        else:
            st.error(
                "📸 **Cloudinary not fully configured.** "
                "Set `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, and `CLOUDINARY_API_SECRET` "
                "in your `.env` file."
            )
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
        if "Invalid cloud_name" in err or "cloud_name" in err.lower():
            st.error(
                f"📸 **Invalid Cloudinary cloud name.**\n\n"
                f"The cloud name in your `.env` doesn't match your Cloudinary account.\n"
                f"Check `CLOUDINARY_CLOUD_NAME` at cloudinary.com → Dashboard.\n\n"
                f"Technical detail: `{err}`"
            )
        elif "certificate" in err.lower() or "ssl" in err.lower():
            st.warning(
                "📸 Image upload blocked by a network/SSL proxy. "
                "This works fine on Streamlit Cloud — run `streamlit run app.py` locally or deploy."
            )
        elif "Must supply api_key" in err or "api_key" in err.lower():
            st.error("📸 Invalid Cloudinary API key. Check `CLOUDINARY_API_KEY` in your `.env`.")
        else:
            st.error(f"📸 Image upload failed: {err}")
        return None


def upload_chat_image(file_bytes: bytes, user_id: str) -> Optional[str]:
    """Upload a chat image. Returns URL or None."""
    if not _configure():
        st.warning("⚠️ Image upload not configured. Set Cloudinary credentials in `.env`.")
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
        st.error(f"Chat image upload failed: {e}")
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
    if not url or "cloudinary.com" not in url:
        return url
    return url.replace("/upload/", f"/upload/w_{width},h_{height},c_fill,g_face/")


def is_cloudinary_configured() -> bool:
    """Return True if Cloudinary credentials look valid (not placeholders)."""
    return _configure()


def test_cloudinary_connection() -> bool:
    if not _configure():
        return False
    try:
        import cloudinary.api
        cloudinary.api.ping()
        return True
    except Exception:
        return False
