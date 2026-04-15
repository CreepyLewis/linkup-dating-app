"""
utils/payments.py
M-Pesa Daraja API integration for premium subscriptions
"""

import os
import base64
import requests
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
from dotenv import load_dotenv
from utils.db import get_client, update_user

load_dotenv()

MPESA_BASE_URL = "https://sandbox.safaricom.co.ke"  # Change to live URL in production


def _get_access_token() -> Optional[str]:
    consumer_key = os.getenv("MPESA_CONSUMER_KEY")
    consumer_secret = os.getenv("MPESA_CONSUMER_SECRET")
    credentials = base64.b64encode(f"{consumer_key}:{consumer_secret}".encode()).decode()
    try:
        res = requests.get(
            f"{MPESA_BASE_URL}/oauth/v1/generate?grant_type=client_credentials",
            headers={"Authorization": f"Basic {credentials}"},
            timeout=10,
        )
        return res.json().get("access_token")
    except Exception:
        return None


def _get_password_and_timestamp() -> tuple:
    shortcode = os.getenv("MPESA_SHORTCODE")
    passkey = os.getenv("MPESA_PASSKEY")
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    raw = f"{shortcode}{passkey}{timestamp}"
    password = base64.b64encode(raw.encode()).decode()
    return password, timestamp


PLANS = {
    "boost": {"name": "Profile Boost", "amount": 100, "days": 7},
    "premium": {"name": "Premium", "amount": 500, "days": 30},
}


def initiate_stk_push(phone: str, plan: str, user_id: str) -> Dict:
    """
    Initiate M-Pesa STK Push.
    Returns {"success": bool, "checkout_id": str | None, "error": str | None}
    """
    if plan not in PLANS:
        return {"success": False, "error": "Invalid plan."}

    token = _get_access_token()
    if not token:
        return {"success": False, "error": "Could not connect to M-Pesa."}

    password, timestamp = _get_password_and_timestamp()
    shortcode = os.getenv("MPESA_SHORTCODE")
    amount = PLANS[plan]["amount"]

    # Normalize phone number
    phone = phone.replace("+", "").replace(" ", "")
    if phone.startswith("0"):
        phone = "254" + phone[1:]

    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone,
        "PartyB": shortcode,
        "PhoneNumber": phone,
        "CallBackURL": os.getenv("MPESA_CALLBACK_URL"),
        "AccountReference": f"LinkUp-{user_id[:8]}",
        "TransactionDesc": f"LinkUp {PLANS[plan]['name']}",
    }

    try:
        res = requests.post(
            f"{MPESA_BASE_URL}/mpesa/stkpush/v1/processrequest",
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=15,
        )
        data = res.json()
        if data.get("ResponseCode") == "0":
            return {"success": True, "checkout_id": data.get("CheckoutRequestID")}
        return {"success": False, "error": data.get("ResponseDescription", "Payment failed.")}
    except Exception as e:
        return {"success": False, "error": str(e)}


def activate_premium(user_id: str, plan: str, receipt: str = ""):
    """Activate premium/boost after successful payment."""
    plan_info = PLANS.get(plan, PLANS["premium"])
    expires = datetime.now(timezone.utc) + timedelta(days=plan_info["days"])

    db = get_client()

    # Update user
    updates = {"is_premium": True}
    if plan == "boost":
        updates["is_boosted"] = True
        updates["boost_expires_at"] = expires.isoformat()
    update_user(user_id, updates)

    # Record subscription
    db.table("subscriptions").insert({
        "user_id": user_id,
        "plan": plan,
        "amount": plan_info["amount"],
        "mpesa_receipt": receipt,
        "expires_at": expires.isoformat(),
    }).execute()
