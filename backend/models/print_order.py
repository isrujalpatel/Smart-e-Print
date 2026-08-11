from extensions import db
from datetime import datetime, timezone
import uuid


class PrintOrder(db.Model):
    """Store customer print orders and upload metadata."""

    __tablename__ = "print_orders"

    id = db.Column(db.String(36), primary_key=True,
                   default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(512), nullable=False)
    file_type = db.Column(db.String(20), nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    page_count = db.Column(db.Integer, nullable=False)
    print_mode = db.Column(db.String(20), nullable=False)
    copies = db.Column(db.Integer, nullable=False, default=1)
    page_range = db.Column(db.String(100), nullable=False)
    paper_size = db.Column(db.String(20), nullable=True)
    printed_pages = db.Column(db.Integer, nullable=False)
    unit_rate = db.Column(db.Float, nullable=False)
    multiplier = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(30), nullable=False, default="Submitted")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", backref="print_orders")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "file_name": self.file_name,
            "file_type": self.file_type,
            "mime_type": self.mime_type,
            "file_size": self.file_size,
            "page_count": self.page_count,
            "print_mode": self.print_mode,
            "copies": self.copies,
            "page_range": self.page_range,
            "paper_size": self.paper_size,
            "printed_pages": self.printed_pages,
            "unit_rate": self.unit_rate,
            "multiplier": self.multiplier,
            "total_price": self.total_price,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
