import os
import re
import uuid
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, current_app, send_file
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader

from extensions import db
from middleware.auth_required import token_required, role_required
from models.print_order import PrintOrder
from models.audit_log import AuditLog
from models.shop_config import ShopConfig

orders_bp = Blueprint("orders", __name__)

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
ALLOWED_MIME = {
    "pdf": ["application/pdf"],
    "png": ["image/png"],
    "jpg": ["image/jpeg", "image/pjpeg"],
    "jpeg": ["image/jpeg", "image/pjpeg"],
}
FILE_SIZE_LIMIT = 10 * 1024 * 1024
VALID_STATUSES = {"Submitted", "Accepted", "Rejected", "Printing", "Completed"}


def _detect_image_type(file_header: bytes) -> str:
    """Detect image type from file header signature (Python 3.13 compatible)."""
    if file_header.startswith(b'\x89PNG'):
        return 'png'
    elif file_header.startswith(b'\xff\xd8\xff'):
        return 'jpeg'
    return None


def _get_extension(filename: str) -> str:
    return filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''


def _validate_file(file_storage):
    if file_storage is None or file_storage.filename == "":
        return "No file selected."

    filename = secure_filename(file_storage.filename)
    extension = _get_extension(filename)
    if extension not in ALLOWED_EXTENSIONS:
        return "Only PDF, PNG, JPG and JPEG files are supported."

    content_type = file_storage.mimetype or ''
    if content_type not in ALLOWED_MIME.get(extension, []):
        return f"Invalid file type. Expected a {extension.upper()} file."

    file_storage.stream.seek(0, os.SEEK_END)
    file_size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    if file_size > FILE_SIZE_LIMIT:
        return "File size must be 10MB or smaller."

    if extension == 'pdf':
        header = file_storage.stream.read(6)
        file_storage.stream.seek(0)
        if not header.startswith(b'%PDF-'):
            return "The uploaded PDF file appears to be invalid."
    else:
        header = file_storage.stream.read(512)
        file_storage.stream.seek(0)
        kind = _detect_image_type(header)
        if extension in {'jpg', 'jpeg'} and kind != 'jpeg':
            return "The uploaded image is not a valid JPEG file."
        if extension == 'png' and kind != 'png':
            return "The uploaded image is not a valid PNG file."

    return None


def _get_pdf_page_count(file_storage):
    file_storage.stream.seek(0)
    reader = PdfReader(file_storage.stream)
    page_count = len(reader.pages)
    file_storage.stream.seek(0)
    return page_count


def _parse_page_range(raw_range: str, page_count: int) -> int:
    if not raw_range or raw_range.strip() == '':
        return page_count

    raw_range = raw_range.strip()
    items = set()
    for part in raw_range.split(','):
        part = part.strip()
        if not part:
            continue
        if '-' in part:
            start_text, end_text = part.split('-', 1)
            if not start_text.isdigit() or not end_text.isdigit():
                raise ValueError("Page range must contain only numbers and hyphens.")
            start = int(start_text)
            end = int(end_text)
            if start < 1 or end < 1 or start > end or end > page_count:
                raise ValueError(f"Page range values must be between 1 and {page_count}.")
            items.update(range(start, end + 1))
        elif part.isdigit():
            page = int(part)
            if page < 1 or page > page_count:
                raise ValueError(f"Page numbers must be between 1 and {page_count}.")
            items.add(page)
        else:
            raise ValueError("Page range format is invalid. Use values like 1-3, 5, 8-10.")

    if not items:
        raise ValueError("Page range cannot be empty.")

    return len(items)


def _calculate_price(print_mode: str, printed_pages: int, copies: int, paper_size: str):
    rates_config = ShopConfig.query.filter_by(config_key="rate_card").first()
    if rates_config and rates_config.config_val:
        price_rates = rates_config.config_val.get("PRICE_RATES", {"bw": 2.0, "color": 5.0})
        paper_multipliers = rates_config.config_val.get("PAPER_MULTIPLIERS", {"A4": 1.0, "A3": 1.25, "Letter": 1.1})
    else:
        price_rates = {"bw": 2.0, "color": 5.0}
        paper_multipliers = {"A4": 1.0, "A3": 1.25, "Letter": 1.1}

    rate = price_rates.get(print_mode, price_rates.get('bw', 2.0))
    multiplier = paper_multipliers.get(paper_size, 1.0)
    total = printed_pages * copies * rate * multiplier
    return rate, multiplier, round(total, 2)


# ── POST /api/orders ─────────────────────────────────────────────────────────
@orders_bp.route('', methods=['POST'])
@token_required
def create_order(current_user):
    uploaded_file = request.files.get('file')
    validation_error = _validate_file(uploaded_file)
    if validation_error:
        return jsonify({"error": validation_error}), 400

    filename = secure_filename(uploaded_file.filename)
    extension = _get_extension(filename)
    content_type = uploaded_file.mimetype or ''

    print_mode = request.form.get('print_mode', 'bw').lower()
    if print_mode not in {'bw', 'color'}:
        return jsonify({"error": "Print mode must be 'color' or 'bw'."}), 400

    copies_raw = request.form.get('copies', '1')
    if not copies_raw.isdigit() or int(copies_raw) < 1:
        return jsonify({"error": "Number of copies must be 1 or greater."}), 400
    copies = int(copies_raw)

    paper_size = request.form.get('paper_size', '').strip()
    if paper_size == '':
        paper_size = None

    payment_method = request.form.get('payment_method', 'cash').lower()
    if payment_method not in {'cash', 'online'}:
        return jsonify({"error": "Payment method must be 'cash' or 'online'."}), 400

    page_range_type = request.form.get('range_type', 'full').lower()
    page_range_value = request.form.get('page_range', '').strip()

    if extension == 'pdf':
        page_count = _get_pdf_page_count(uploaded_file)
    else:
        page_count = 1

    if page_count < 1:
        return jsonify({"error": "Unable to determine the document page count."}), 400

    if page_range_type == 'custom':
        try:
            printed_pages = _parse_page_range(page_range_value, page_count)
            page_range = page_range_value
        except ValueError as err:
            return jsonify({"error": str(err)}), 400
    else:
        printed_pages = page_count
        page_range = f"1-{page_count}" if page_count > 1 else '1'

    if printed_pages < 1:
        return jsonify({"error": "At least one page must be selected for printing."}), 400

    rate, multiplier, total_price = _calculate_price(print_mode, printed_pages, copies, paper_size)

    upload_folder = current_app.config.get('UPLOAD_FOLDER')
    os.makedirs(upload_folder, exist_ok=True)
    unique_id = str(uuid.uuid4())
    saved_filename = f"{unique_id}_{filename}"
    saved_path = os.path.join(upload_folder, saved_filename)

    uploaded_file.stream.seek(0)
    uploaded_file.save(saved_path)

    order = PrintOrder(
        user_id=current_user.id,
        customer_name=current_user.name,
        customer_email=current_user.email,
        file_name=filename,
        file_path=saved_path,
        file_type=extension,
        mime_type=content_type,
        file_size=os.path.getsize(saved_path),
        page_count=page_count,
        print_mode=print_mode,
        copies=copies,
        page_range=page_range,
        paper_size=paper_size,
        printed_pages=printed_pages,
        unit_rate=rate,
        multiplier=multiplier,
        total_price=total_price,
        payment_method=payment_method,
        payment_status="pending" if payment_method == "online" else "pending_cash",
        status="Submitted",
        created_at=datetime.now(timezone.utc),
    )

    db.session.add(order)
    db.session.commit()

    ip_addr = request.headers.get("X-Forwarded-For", request.remote_addr)
    try:
        AuditLog.log(
            action="ORDER_CREATED",
            user=current_user,
            details=f"Created order {str(order.id)[:8]} for '{filename}' (₹{total_price})",
            ip_address=ip_addr,
        )
    except Exception as log_err:
        print(f"[WARN] AuditLog failed (non-fatal): {log_err}")

    return jsonify({"message": "Order submitted successfully.", "order": order.to_dict()}), 201


# ── GET /api/orders ──────────────────────────────────────────────────────────
@orders_bp.route('', methods=['GET'])
@token_required
def list_orders(current_user):
    """
    List orders.
    - Customer: gets only their own orders.
    - Admin / Super Admin: gets all orders in the system.
    """
    status_filter = request.args.get('status', '').strip()

    if current_user.role == 'customer':
        query = PrintOrder.query.filter_by(user_id=current_user.id)
    else:
        query = PrintOrder.query

    if status_filter and status_filter in VALID_STATUSES:
        query = query.filter_by(status=status_filter)

    orders = query.order_by(PrintOrder.created_at.desc()).all()
    return jsonify({"orders": [o.to_dict() for o in orders]}), 200


# ── GET /api/orders/<order_id>/download ──────────────────────────────────────
@orders_bp.route('/<order_id>/download', methods=['GET'])
@token_required
def download_order_file(current_user, order_id):
    """Securely download an order's file."""
    order = db.session.get(PrintOrder, order_id)
    if not order:
        return jsonify({"error": "Order not found."}), 404
        
    # Check authorization: Only the customer who owns it, or an admin/super_admin
    if current_user.role == 'customer' and order.user_id != current_user.id:
        return jsonify({"error": "Unauthorized to download this file."}), 403

    if not os.path.exists(order.file_path):
        return jsonify({"error": "File not found on server."}), 404

    # Audit log the download for admin
    if current_user.role in {'admin', 'super_admin'}:
        ip_addr = request.headers.get("X-Forwarded-For", request.remote_addr)
        AuditLog.log(
            action="FILE_DOWNLOADED",
            user=current_user,
            details=f"Downloaded file for order {order.id[:8]}",
            ip_address=ip_addr,
        )

    return send_file(
        order.file_path, 
        as_attachment=True, 
        download_name=order.file_name,
        mimetype=order.mime_type
    )

# ── POST /api/orders/<order_id>/cancel ────────────────────────────────────────
@orders_bp.route('/<order_id>/cancel', methods=['POST'])
@token_required
def cancel_order(current_user, order_id):
    """Allow customer to cancel their own order (only if Submitted or Accepted)."""
    order = db.session.get(PrintOrder, order_id)
    if not order:
        return jsonify({"error": "Order not found."}), 404

    # Customers can only cancel their own orders
    if current_user.role == 'customer' and order.user_id != current_user.id:
        return jsonify({"error": "Unauthorized."}), 403

    if order.status not in {'Submitted', 'Accepted'}:
        return jsonify({"error": f"Cannot cancel order with status '{order.status}'."}), 400

    old_status = order.status
    order.status = 'Rejected'
    order.rejection_reason = 'Cancelled by customer'
    order.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    ip_addr = request.headers.get("X-Forwarded-For", request.remote_addr)
    try:
        AuditLog.log(
            action="ORDER_CANCELLED",
            user=current_user,
            details=f"Customer cancelled order {order.id[:8]} (was '{old_status}')",
            ip_address=ip_addr,
        )
    except Exception as log_err:
        print(f"[WARN] AuditLog failed (non-fatal): {log_err}")

    return jsonify({
        "message": "Order cancelled successfully.",
        "order": order.to_dict()
    }), 200


# ── PATCH /api/orders/<order_id>/status ──────────────────────────────────────
@orders_bp.route('/<order_id>/status', methods=['PATCH'])
@role_required('admin', 'super_admin')
def update_order_status(current_user, order_id):
    """
    Update order status (Admin and Super Admin only).
    Statuses: Submitted, Accepted, Rejected, Printing, Completed
    """
    data = request.get_json(silent=True) or {}
    new_status = data.get('status', '').strip()
    rejection_reason = data.get('rejection_reason', '').strip() or None

    if new_status not in VALID_STATUSES:
        return jsonify({
            "error": f"Invalid status. Must be one of: {', '.join(sorted(VALID_STATUSES))}."
        }), 400

    order = db.session.get(PrintOrder, order_id)
    if not order:
        return jsonify({"error": "Order not found."}), 404

    old_status = order.status
    order.status = new_status
    if new_status == 'Rejected':
        order.rejection_reason = rejection_reason or "Rejected by shop admin"
    elif new_status in {'Accepted', 'Printing', 'Completed'}:
        order.rejection_reason = None

    order.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    ip_addr = request.headers.get("X-Forwarded-For", request.remote_addr)
    try:
        AuditLog.log(
            action="ORDER_STATUS_UPDATED",
            user=current_user,
            details=f"Updated order {order.id[:8]} status from '{old_status}' to '{new_status}'" + (f" (Reason: {rejection_reason})" if rejection_reason else ""),
            ip_address=ip_addr,
        )
    except Exception as log_err:
        print(f"[WARN] AuditLog failed (non-fatal): {log_err}")

    return jsonify({
        "message": f"Order status updated to {new_status}.",
        "order": order.to_dict()
    }), 200


# ── GET /api/orders/stats ───────────────────────────────────────────────────
@orders_bp.route('/stats', methods=['GET'])
@role_required('admin', 'super_admin')
def get_order_stats(current_user):
    """Operational statistics for Admin and Super Admin."""
    orders = PrintOrder.query.all()
    total_orders = len(orders)
    submitted = sum(1 for o in orders if o.status == 'Submitted')
    accepted = sum(1 for o in orders if o.status == 'Accepted')
    printing = sum(1 for o in orders if o.status == 'Printing')
    completed = sum(1 for o in orders if o.status == 'Completed')
    rejected = sum(1 for o in orders if o.status == 'Rejected')

    total_revenue = sum(o.total_price for o in orders if o.status in {'Accepted', 'Printing', 'Completed'})
    
    # Today's orders
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_orders = [o for o in orders if o.created_at and o.created_at >= today_start]
    today_revenue = sum(o.total_price for o in today_orders if o.status in {'Accepted', 'Printing', 'Completed'})

    return jsonify({
        "stats": {
            "total_orders": total_orders,
            "submitted": submitted,
            "accepted": accepted,
            "printing": printing,
            "completed": completed,
            "rejected": rejected,
            "total_revenue": round(total_revenue, 2),
            "today_revenue": round(today_revenue, 2),
            "today_orders": len(today_orders),
        }
    }), 200
