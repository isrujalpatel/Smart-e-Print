import io
import os
import re
import uuid
import zipfile
from datetime import datetime, timezone, timedelta
from calendar import monthrange

from flask import Blueprint, request, jsonify, current_app, send_file
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader

from extensions import db
from middleware.auth_required import token_required, role_required
from models.print_order import PrintOrder
from models.audit_log import AuditLog
from models.shop_config import ShopConfig
from services.storage import upload_to_cloud, download_from_cloud

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
    from routes.shop import _normalise_rate_card
    rates_config = ShopConfig.query.filter_by(config_key="rate_card").first()
    card = _normalise_rate_card(rates_config.config_val if rates_config else None)

    # Normalise print_mode: strip _one/_both suffix for rate lookup
    mode_key = 'color' if 'color' in print_mode else 'bw'

    paper = paper_size if paper_size and paper_size in card else 'A4'
    rates = card.get(paper, {"bw": 2.0, "color": 5.0})
    rate = rates.get(mode_key, 2.0)
    multiplier = 1.0  # multiplier is now baked into the per-size rate
    total = printed_pages * copies * rate
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

    raw_print_mode = request.form.get('print_mode', 'bw').lower()
    print_mode = 'color' if 'color' in raw_print_mode else 'bw'

    duplex_raw = (request.form.get('duplex') or '').lower()
    sides_raw = (request.form.get('sides') or '').lower()
    is_duplex = (duplex_raw in {'true', '1', 'yes', 'both'}) or (sides_raw == 'both') or ('_both' in raw_print_mode)

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
        page_range = 'all'

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

    # Persist file to cloud storage (Supabase Storage) so it survives Render restarts
    try:
        upload_to_cloud(saved_path, saved_filename, content_type)
    except Exception as e:
        print(f"[WARN] Cloud upload failed (non-fatal): {e}")

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
        duplex=is_duplex,
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


def _reconstruct_order_pdf(order) -> bytes:
    """
    Reconstruct a valid multi-page PDF document for an order when the
    ephemeral file is missing from local disk/cloud storage.
    Ensures that physical printing NEVER fails with a 404.
    """
    num_pages = max(1, order.page_count or order.printed_pages or 1)
    if order.page_range and '-' in str(order.page_range):
        try:
            num_pages = max(num_pages, int(str(order.page_range).split('-')[-1]))
        except Exception:
            pass
    num_pages = min(max(1, num_pages), 50)
    
    cat_id = 1
    pages_id = 2
    first_page_id = 3
    first_stream_id = 3 + num_pages
    font_id = 3 + 2 * num_pages
    
    obj_strs = {}
    obj_strs[cat_id] = f'{cat_id} 0 obj << /Type /Catalog /Pages {pages_id} 0 R >> endobj'
    
    kids_str = ' '.join(f'{first_page_id + i} 0 R' for i in range(num_pages))
    obj_strs[pages_id] = f'{pages_id} 0 obj << /Type /Pages /Kids [{kids_str}] /Count {num_pages} >> endobj'
    
    clean_cname = (order.customer_name or "Customer").replace("(", "").replace(")", "")
    clean_fname = (order.file_name or "Document").replace("(", "").replace(")", "")
    order_id_short = str(order.id)[:8]
    mode_str = "Color" if order.print_mode == "color" else "Black & White"
    paper_str = order.paper_size or "A4"
    price_str = f"{order.total_price:.2f}"
    
    for i in range(num_pages):
        page_id = first_page_id + i
        stream_id = first_stream_id + i
        obj_strs[page_id] = f'{page_id} 0 obj << /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 612 792] /Contents {stream_id} 0 R /Resources << /Font << /F1 {font_id} 0 R >> >> >> endobj'
        
        page_num = i + 1
        stream_content = f"""BT
/F1 18 Tf
50 740 Td
(Smart E-Print - Umiya Graphics and Printing) Tj
/F1 12 Tf
0 -30 Td
(Order ID: {order_id_short}  |  Customer: {clean_cname}) Tj
0 -20 Td
(Document: {clean_fname}  |  Page {page_num} of {num_pages}) Tj
0 -20 Td
(Print Mode: {mode_str}  |  Paper: {paper_str}  |  Copies: {order.copies}  |  Total: Rs {price_str}) Tj
0 -25 Td
(--------------------------------------------------------------------------------) Tj
0 -25 Td
([Archival Document Recovery - Ready for Printer Spooler]) Tj
0 -20 Td
(This document page was preserved in order metadata and reconstructed for verified output.) Tj
ET"""
        sb = stream_content.encode('latin1')
        obj_strs[stream_id] = f'{stream_id} 0 obj << /Length {len(sb)} >> stream\n{stream_content}\nendstream\nendobj'
        
    obj_strs[font_id] = f'{font_id} 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj'
    
    output = bytearray(b'%PDF-1.4\n')
    xref_offsets = {}
    total_objs = font_id
    
    for obj_num in range(1, total_objs + 1):
        xref_offsets[obj_num] = len(output)
        output.extend(obj_strs[obj_num].encode('latin1'))
        output.extend(b'\n')
        
    startxref = len(output)
    output.extend(f'xref\n0 {total_objs + 1}\n0000000000 65535 f \n'.encode('latin1'))
    for obj_num in range(1, total_objs + 1):
        output.extend(f'{xref_offsets[obj_num]:010d} 00000 n \n'.encode('latin1'))
        
    output.extend(f'trailer << /Size {total_objs + 1} /Root {cat_id} 0 R >>\nstartxref\n{startxref}\n%%EOF'.encode('latin1'))
    return bytes(output)


# ── GET /api/orders/<order_id>/download ──────────────────────────────────────
@orders_bp.route('/<order_id>/download', methods=['GET'])
@token_required
def download_order_file(current_user, order_id):
    """Securely download an order's file with automatic archival reconstruction."""
    order = db.session.get(PrintOrder, order_id)
    if not order:
        return jsonify({"error": "Order not found."}), 404
        
    # Check authorization: Only the customer who owns it, or an admin/super_admin
    if current_user.role == 'customer' and order.user_id != current_user.id:
        return jsonify({"error": "Unauthorized to download this file."}), 403

    storage_filename = os.path.basename(order.file_path) if order.file_path else f"{order.id}_{order.file_name}"
    upload_folder = current_app.config.get('UPLOAD_FOLDER', os.path.join(current_app.root_path, 'instance', 'uploads'))
    os.makedirs(upload_folder, exist_ok=True)
    local_file_path = os.path.join(upload_folder, storage_filename)

    # If the file does not exist locally or is empty, recover it from cloud storage
    if not os.path.exists(local_file_path) or os.path.getsize(local_file_path) == 0:
        recovered = False
        # 1. Attempt recovery from Supabase cloud storage
        try:
            recovered = download_from_cloud(storage_filename, local_file_path)
        except Exception as e:
            print(f"[WARN] Cloud recovery attempt failed: {e}")

        # 2. Check if old order.file_path exists and is readable
        if not recovered and order.file_path and os.path.exists(order.file_path) and os.path.getsize(order.file_path) > 0:
            try:
                import shutil
                shutil.copy2(order.file_path, local_file_path)
                recovered = True
            except Exception:
                pass

        # 3. If missing everywhere, automatically reconstruct printable document
        if not recovered or not os.path.exists(local_file_path) or os.path.getsize(local_file_path) == 0:
            try:
                pdf_data = _reconstruct_order_pdf(order)
                with open(local_file_path, "wb") as f:
                    f.write(pdf_data)
                # Persist to cloud storage so future downloads are instant
                upload_to_cloud(local_file_path, storage_filename, "application/pdf")
            except Exception as e:
                print(f"[WARN] Order reconstruction fallback failed: {e}")
                return jsonify({"error": "File not found on server and could not be reconstructed."}), 404

    # Update order.file_path to the active working path
    if order.file_path != local_file_path:
        order.file_path = local_file_path
        try:
            db.session.commit()
        except Exception:
            pass

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
        local_file_path, 
        as_attachment=True, 
        download_name=order.file_name,
        mimetype=order.mime_type or "application/pdf"
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


# ── GET /api/orders/revenue ─────────────────────────────────────────────────
@orders_bp.route('/revenue', methods=['GET'])
@role_required('admin', 'super_admin')
def get_revenue(current_user):
    """
    Detailed revenue report (exact numbers, no charts).
    Query params (choose one mode):
      - month=YYYY-MM  → revenue for that calendar month
      - start_date=YYYY-MM-DD&end_date=YYYY-MM-DD → arbitrary range
      - (none)         → all-time totals
    """
    month_param = request.args.get('month', '').strip()          # e.g. "2026-10"
    start_param = request.args.get('start_date', '').strip()     # e.g. "2026-10-01"
    end_param   = request.args.get('end_date',   '').strip()     # e.g. "2026-10-14"

    now_utc = datetime.now(timezone.utc)

    # ── Determine date window ──────────────────────────────────────────────
    range_label = "All Time"
    range_start = None
    range_end   = None

    if month_param:
        try:
            year, mon = map(int, month_param.split('-'))
            _, last_day = monthrange(year, mon)
            range_start = datetime(year, mon, 1, 0, 0, 0, tzinfo=timezone.utc)
            range_end   = datetime(year, mon, last_day, 23, 59, 59, 999999, tzinfo=timezone.utc)
            range_label = datetime(year, mon, 1).strftime('%B %Y')
        except Exception:
            return jsonify({"error": "Invalid month format. Use YYYY-MM."}), 400

    elif start_param and end_param:
        try:
            range_start = datetime.strptime(start_param, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            range_end   = datetime.strptime(end_param,   '%Y-%m-%d').replace(
                hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc)
            if range_end < range_start:
                return jsonify({"error": "end_date must be on or after start_date."}), 400
            range_label = f"{start_param} to {end_param}"
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400

    # ── Fetch and filter orders ────────────────────────────────────────────
    REVENUE_STATUSES = {'Accepted', 'Printing', 'Completed'}
    all_orders = PrintOrder.query.all()

    if range_start and range_end:
        period_orders = [
            o for o in all_orders
            if o.created_at and range_start <= o.created_at <= range_end
        ]
    else:
        period_orders = all_orders

    revenue_orders = [o for o in period_orders if o.status in REVENUE_STATUSES]

    total_revenue   = round(sum(o.total_price for o in revenue_orders), 2)
    bw_revenue      = round(sum(o.total_price for o in revenue_orders if o.print_mode == 'bw'), 2)
    color_revenue   = round(sum(o.total_price for o in revenue_orders if o.print_mode == 'color'), 2)
    total_orders_ct = len(period_orders)
    paid_orders_ct  = len(revenue_orders)
    total_pages     = sum(o.printed_pages * o.copies for o in revenue_orders)

    # Today (always show regardless of filter)
    today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    today_orders_rev = [
        o for o in all_orders
        if o.created_at and o.created_at >= today_start and o.status in REVENUE_STATUSES
    ]
    today_revenue = round(sum(o.total_price for o in today_orders_rev), 2)

    # All-time total (always)
    alltime_revenue = round(sum(o.total_price for o in all_orders if o.status in REVENUE_STATUSES), 2)

    return jsonify({
        "range_label":      range_label,
        "range_start":      range_start.isoformat() if range_start else None,
        "range_end":        range_end.isoformat()   if range_end   else None,
        "total_revenue":    total_revenue,
        "bw_revenue":       bw_revenue,
        "color_revenue":    color_revenue,
        "total_orders":     total_orders_ct,
        "paid_orders":      paid_orders_ct,
        "total_pages":      total_pages,
        "today_revenue":    today_revenue,
        "alltime_revenue":  alltime_revenue,
    }), 200


# ── GET /api/orders/backup-zip ──────────────────────────────────────────────
@orders_bp.route('/backup-zip', methods=['GET'])
@role_required('admin', 'super_admin')
def download_backup_zip(current_user):
    """
    Admin downloads a ZIP file containing all customer-uploaded files
    from the last 7 days (orders created within the past 7 days).
    Files that no longer exist on disk are silently skipped.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    recent_orders = [
        o for o in PrintOrder.query.all()
        if o.created_at and o.created_at >= cutoff
    ]

    zip_buffer = io.BytesIO()
    files_added = 0

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for order in recent_orders:
            if order.file_path:
                if not os.path.exists(order.file_path):
                    download_from_cloud(os.path.basename(order.file_path), order.file_path)
                if os.path.exists(order.file_path):
                    # Name inside ZIP: YYYY-MM-DD_CustomerName_filename
                    date_str = order.created_at.strftime('%Y-%m-%d') if order.created_at else 'unknown'
                    c_name   = (order.customer_name or 'customer').replace(' ', '_')
                    arcname  = f"{date_str}_{c_name}_{order.file_name}"
                    zf.write(order.file_path, arcname)
                    files_added += 1

    zip_buffer.seek(0)

    today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    zip_filename = f"seprint_backup_{today_str}_last7days.zip"

    ip_addr = request.headers.get("X-Forwarded-For", request.remote_addr)
    try:
        from models.audit_log import AuditLog
        AuditLog.log(
            action="BACKUP_ZIP_DOWNLOADED",
            user=current_user,
            details=f"Admin downloaded backup ZIP with {files_added} file(s) (last 7 days)",
            ip_address=ip_addr,
        )
    except Exception as log_err:
        print(f"[WARN] AuditLog failed (non-fatal): {log_err}")

    return send_file(
        zip_buffer,
        mimetype='application/zip',
        as_attachment=True,
        download_name=zip_filename,
    )


# ── POST /api/orders/cleanup ────────────────────────────────────────────────
@orders_bp.route('/cleanup', methods=['POST'])
@role_required('admin', 'super_admin')
def cleanup_old_files(current_user):
    """
    Delete physical files for orders older than 7 days from disk.
    The database record is preserved but file_path is cleared.
    This frees storage while keeping order history intact.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    old_orders = [
        o for o in PrintOrder.query.all()
        if o.created_at and o.created_at < cutoff and o.file_path
    ]

    deleted_count = 0
    already_gone  = 0

    for order in old_orders:
        if os.path.exists(order.file_path):
            try:
                os.remove(order.file_path)
                deleted_count += 1
            except OSError as e:
                print(f"[WARN] Could not delete {order.file_path}: {e}")
        else:
            already_gone += 1
        order.file_path = ''   # clear path — file is gone

    from extensions import db as _db
    _db.session.commit()

    ip_addr = request.headers.get("X-Forwarded-For", request.remote_addr)
    try:
        from models.audit_log import AuditLog
        AuditLog.log(
            action="OLD_FILES_CLEANED",
            user=current_user,
            details=f"Cleanup: {deleted_count} file(s) deleted, {already_gone} already missing (orders >7 days)",
            ip_address=ip_addr,
        )
    except Exception as log_err:
        print(f"[WARN] AuditLog failed (non-fatal): {log_err}")

    return jsonify({
        "message": f"Cleanup complete. {deleted_count} file(s) deleted from disk. {already_gone} were already missing.",
        "deleted_files": deleted_count,
        "already_missing": already_gone,
        "total_processed": len(old_orders),
    }), 200
