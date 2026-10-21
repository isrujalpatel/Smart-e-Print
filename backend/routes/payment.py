"""
Razorpay Payment Routes
─────────────────────────────────────────────────────────────────────────────
POST /api/payment/create-order  → Create a Razorpay order (server-side)
POST /api/payment/verify        → Verify payment signature after checkout
GET  /api/payment/key           → Return the public key_id to the frontend
"""

import hmac
import hashlib

import razorpay
from flask import Blueprint, request, jsonify, current_app
from middleware.auth_required import token_required

payment_bp = Blueprint("payment", __name__)


def _get_razorpay_client():
    """Instantiate a Razorpay client from Flask app config."""
    key_id = current_app.config["RAZORPAY_KEY_ID"]
    key_secret = current_app.config["RAZORPAY_KEY_SECRET"]
    if not key_id or not key_secret:
        raise RuntimeError("Razorpay API keys are not configured.")
    return razorpay.Client(auth=(key_id, key_secret))


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
    Returns the Razorpay order object so the frontend can open checkout.
    """
    data = request.get_json(silent=True) or {}
    amount = data.get("amount")

    if not amount or float(amount) <= 0:
        return jsonify({"error": "Invalid amount"}), 400

    try:
        client = _get_razorpay_client()
        order_data = {
            "amount": int(float(amount) * 100),  # Razorpay expects paise
            "currency": "INR",
            "receipt": data.get("receipt", f"order_{current_user.id}"),
            "payment_capture": 1,  # Auto-capture payment
        }
        order = client.order.create(data=order_data)
        return jsonify({
            "order_id": order["id"],
            "amount": order["amount"],
            "currency": order["currency"],
            "key_id": current_app.config["RAZORPAY_KEY_ID"],
        })
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
    Verifies the HMAC-SHA256 signature to confirm payment is genuine.
    """
    data = request.get_json(silent=True) or {}
    order_id = data.get("razorpay_order_id")
    payment_id = data.get("razorpay_payment_id")
    signature = data.get("razorpay_signature")

    if not all([order_id, payment_id, signature]):
        return jsonify({"error": "Missing payment verification fields"}), 400

    try:
        client = _get_razorpay_client()
        # Razorpay SDK's built-in signature verification
        client.utility.verify_payment_signature({
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        })
        return jsonify({
            "verified": True,
            "payment_id": payment_id,
            "order_id": order_id,
        })
    except razorpay.errors.SignatureVerificationError:
        return jsonify({"verified": False, "error": "Payment signature verification failed"}), 400
    except Exception as e:
        return jsonify({"verified": False, "error": str(e)}), 500
