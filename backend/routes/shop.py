from flask import Blueprint, request, jsonify
from extensions import db
from middleware.auth_required import token_required, role_required
from models.shop_config import ShopConfig
from models.audit_log import AuditLog

shop_bp = Blueprint("shop", __name__)

# ── Default rate card ────────────────────────────────────────────────────────
# New format: per paper-size, per print-mode rates
DEFAULT_RATE_CARD = {
    "A4":     {"bw": 2.0, "color": 5.0},
    "A3":     {"bw": 10.0, "color": 10.0},
    "Letter": {"bw": 2.5, "color": 6.0},
}


def _normalise_rate_card(raw):
    """
    Accept both old format (PRICE_RATES + PAPER_MULTIPLIERS) and the new
    per-paper-size format and always return the new format.
    """
    if not raw:
        return dict(DEFAULT_RATE_CARD)

    # Already in new format (top-level keys are paper sizes)
    if any(k in raw for k in ("A4", "A3", "Letter")):
        return raw

    # Old format: convert  PRICE_RATES × PAPER_MULTIPLIERS → per-size rates
    pr = raw.get("PRICE_RATES", {"bw": 2.0, "color": 5.0})
    pm = raw.get("PAPER_MULTIPLIERS", {"A4": 1.0, "A3": 1.25, "Letter": 1.1})
    result = {}
    for paper, mult in pm.items():
        result[paper] = {
            "bw":    round(pr.get("bw", 2.0) * mult, 2),
            "color": round(pr.get("color", 5.0) * mult, 2),
        }
    return result


@shop_bp.route('/rates', methods=['GET'])
def get_rates():
    """
    Public endpoint — returns current print rates.
    Always returns the new per-paper-size format AND a backward-compatible
    PRICE_RATES / PAPER_MULTIPLIERS block so existing code keeps working.
    """
    rates_config = ShopConfig.query.filter_by(config_key="rate_card").first()
    card = _normalise_rate_card(rates_config.config_val if rates_config else None)

    # Build backward-compatible flat keys from A4 row (the base size)
    a4 = card.get("A4", {"bw": 2.0, "color": 5.0})
    price_rates = {"bw": a4["bw"], "color": a4["color"]}
    paper_multipliers = {}
    for paper, modes in card.items():
        if a4["bw"] > 0:
            paper_multipliers[paper] = round(modes["bw"] / a4["bw"], 4)
        else:
            paper_multipliers[paper] = 1.0

    return jsonify({
        "rate_card":         card,
        "PRICE_RATES":       price_rates,
        "PAPER_MULTIPLIERS": paper_multipliers,
    }), 200


@shop_bp.route('/rates', methods=['PUT'])
@role_required('admin', 'super_admin')
def update_rates(current_user):
    """
    Admin endpoint — accepts the new per-paper-size format:
      { "A4": {"bw": 2, "color": 5}, "A3": {...}, ... }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON."}), 400

    # Accept the new format directly under "rate_card" key or as top-level
    card = data.get("rate_card", data)

    # Validate structure
    if not isinstance(card, dict) or len(card) == 0:
        return jsonify({"error": "rate_card must be a non-empty object."}), 400

    for paper, modes in card.items():
        if not isinstance(modes, dict):
            return jsonify({"error": f"Rates for '{paper}' must be an object with 'bw' and 'color'."}), 400
        if "bw" not in modes or "color" not in modes:
            return jsonify({"error": f"Each paper size must have 'bw' and 'color' rates."}), 400
        try:
            card[paper]["bw"] = round(float(modes["bw"]), 2)
            card[paper]["color"] = round(float(modes["color"]), 2)
        except (ValueError, TypeError):
            return jsonify({"error": f"Rates must be numbers."}), 400

    rates_config = ShopConfig.query.filter_by(config_key="rate_card").first()
    if not rates_config:
        rates_config = ShopConfig(config_key="rate_card", config_val=card)
        db.session.add(rates_config)
    else:
        rates_config.config_val = card
        # SQLAlchemy needs to know the JSON changed
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(rates_config, "config_val")

    db.session.commit()

    ip_addr = request.headers.get("X-Forwarded-For", request.remote_addr)
    AuditLog.log(
        action="RATES_UPDATED",
        user=current_user,
        details="Updated shop rate card.",
        ip_address=ip_addr,
    )

    return jsonify({"message": "Rate card updated successfully.", "rate_card": card}), 200
