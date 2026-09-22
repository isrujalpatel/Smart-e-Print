from flask import Blueprint, request, jsonify
from extensions import db
from middleware.auth_required import token_required, role_required
from models.shop_config import ShopConfig
from models.audit_log import AuditLog

shop_bp = Blueprint("shop", __name__)

@shop_bp.route('/rates', methods=['GET'])
def get_rates():
    """Public endpoint to fetch current print rates."""
    rates_config = ShopConfig.query.filter_by(config_key="rate_card").first()
    if rates_config and rates_config.config_val:
        return jsonify(rates_config.config_val), 200
    
    # Fallback default
    return jsonify({
        "PRICE_RATES": {"bw": 2.0, "color": 5.0},
        "PAPER_MULTIPLIERS": {"A4": 1.0, "A3": 1.25, "Letter": 1.1}
    }), 200


@shop_bp.route('/rates', methods=['PUT'])
@role_required('admin', 'super_admin')
def update_rates(current_user):
    """Admin endpoint to update print rates."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON."}), 400
    
    if "PRICE_RATES" not in data or "PAPER_MULTIPLIERS" not in data:
        return jsonify({"error": "PRICE_RATES and PAPER_MULTIPLIERS are required."}), 400
        
    rates_config = ShopConfig.query.filter_by(config_key="rate_card").first()
    if not rates_config:
        rates_config = ShopConfig(config_key="rate_card", config_val=data)
        db.session.add(rates_config)
    else:
        rates_config.config_val = data
        
    db.session.commit()
    
    ip_addr = request.headers.get("X-Forwarded-For", request.remote_addr)
    AuditLog.log(
        action="RATES_UPDATED",
        user=current_user,
        details="Updated shop rate card.",
        ip_address=ip_addr,
    )
    
    return jsonify({"message": "Rate card updated successfully.", "rates": rates_config.config_val}), 200
