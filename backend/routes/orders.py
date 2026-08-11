import os
import re
import uuid
import imghdr
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader

from extensions import db
from middleware.auth_required import token_required
from models.print_order import PrintOrder

orders_bp = Blueprint("orders", __name__)

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
ALLOWED_MIME = {
    "pdf": ["application/pdf"],
    "png": ["image/png"],
    "jpg": ["image/jpeg", "image/pjpeg"],
    "jpeg": ["image/jpeg", "image/pjpeg"],
}
FILE_SIZE_LIMIT = 10 * 1024 * 1024
PRICE_RATES = {"bw": 2.0, "color": 5.0}
PAPER_MULTIPLIERS = {"A4": 1.0, "A3": 1.25, "Letter": 1.1}


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
        kind = imghdr.what(None, header)
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
    rate = PRICE_RATES.get(print_mode, PRICE_RATES['bw'])
    multiplier = PAPER_MULTIPLIERS.get(paper_size, 1.0)
    total = printed_pages * copies * rate * multiplier
    return rate, multiplier, round(total, 2)


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
    elif paper_size not in PAPER_MULTIPLIERS:
        return jsonify({"error": "Invalid paper size selection."}), 400

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
        created_at=datetime.now(timezone.utc),
    )

    db.session.add(order)
    db.session.commit()

    return jsonify({"message": "Order submitted successfully.", "order": order.to_dict()}), 201
