"""
Razorpay Payment Routes
─────────────────────────────────────────────────────────────────────────────
POST /api/payment/create-order  → Create a Razorpay order (server-side)
POST /api/payment/verify        → Verify payment signature after checkout
GET  /api/payment/key           → Return the public key_id to the frontend
"""

import hmac
import hashlib
import json
import base64
import urllib.request
import urllib.error

from flask import Blueprint, request, jsonify, current_app
from middleware.auth_required import token_required

payment_bp = Blueprint("payment", __name__)


def _get_credentials():
    """Retrieve Razorpay credentials from Flask app config."""
    key_id = current_app.config.get("RAZORPAY_KEY_ID", "")
    key_secret = current_app.config.get("RAZORPAY_KEY_SECRET", "")
    if not key_id or not key_secret:
        raise RuntimeError("Razorpay API keys are not configured.")
    return key_id, key_secret


# ── Return public key to frontend ────────────────────────────────────────────
@payment_bp.route("/key", methods=["GET"])
def get_razorpay_key():
    key_id = current_app.config.get("RAZORPAY_KEY_ID", "")
    if not key_id:
        return jsonify({"error": "Razorpay not configured"}), 500
    return jsonify({"key_id": key_id})


# ── Create Razorpay Order ────────────────────────────────────────────────────
@payment_bp.route("/create-order", methods=["POST"])
@token_required
def create_order(current_user):
    """
    Expects JSON: { "amount": <float in INR>, "receipt": "<optional string>" }
    Calls Razorpay REST API directly without deprecated pkg_resources dependencies.
    """
    data = request.get_json(silent=True) or {}
    amount = data.get("amount")

    if not amount or float(amount) <= 0:
        return jsonify({"error": "Invalid amount"}), 400

    try:
        key_id, key_secret = _get_credentials()
        amount_paise = int(round(float(amount) * 100))
        receipt_val = str(data.get("receipt", f"order_{current_user.id}"))[:40]

        payload = json.dumps({
            "amount": amount_paise,
            "currency": "INR",
            "receipt": receipt_val,
            "payment_capture": 1,
        }).encode("utf-8")

        auth_str = base64.b64encode(f"{key_id}:{key_secret}".encode("utf-8")).decode("utf-8")
        req = urllib.request.Request(
            "https://api.razorpay.com/v1/orders",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Basic {auth_str}",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=15) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))

        return jsonify({
            "order_id": resp_data["id"],
            "amount": resp_data["amount"],
            "currency": resp_data["currency"],
            "key_id": key_id,
        })
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        return jsonify({"error": f"Razorpay API error ({e.code}): {err_body}"}), 500
    except Exception as e:
        return jsonify({"error": f"Failed to create order: {str(e)}"}), 500


# ── Verify Payment Signature ─────────────────────────────────────────────────
@payment_bp.route("/verify", methods=["POST"])
@token_required
def verify_payment(current_user):
    """
    Expects JSON: {
        "razorpay_order_id": "...",
        "razorpay_payment_id": "...",
        "razorpay_signature": "..."
    }
    Verifies HMAC-SHA256 signature using Python's native hmac and hashlib.
    Formula: HMAC_SHA256(order_id + "|" + payment_id, secret) == signature
    """
    data = request.get_json(silent=True) or {}
    order_id = data.get("razorpay_order_id")
    payment_id = data.get("razorpay_payment_id")
    signature = data.get("razorpay_signature")

    if not all([order_id, payment_id, signature]):
        return jsonify({"error": "Missing payment verification fields"}), 400

    try:
        _, key_secret = _get_credentials()

        message = f"{order_id}|{payment_id}".encode("utf-8")
        expected_sig = hmac.new(
            key_secret.encode("utf-8"),
            message,
            hashlib.sha256
        ).hexdigest()

        if hmac.compare_digest(expected_sig, signature):
            return jsonify({
                "verified": True,
                "payment_id": payment_id,
                "order_id": order_id,
            })
        else:
            return jsonify({"verified": False, "error": "Payment signature verification failed"}), 400
    except Exception as e:
        return jsonify({"verified": False, "error": str(e)}), 500
