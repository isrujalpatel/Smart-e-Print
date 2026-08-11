# Project Context: Smart E-Printing Software

## Overview
**Smart E-Printing Software** is a web-based application designed to digitize and automate the print order management process for **Umiya Graphics and Printing** (Owner: Mr. Manojbhai Patel).

## Team Members
- Prince Patel (24CS072)
- Manav Patel (24CS067)
- Srujal Patel (24CS076)

## System Architecture & User Roles
1. **Customer Role**:
   - Register/login and join the specific printing shop.
   - Upload PDF and Image documents.
   - Configure print options:
     - Color vs. Black & White
     - Number of copies
     - Custom page range selection
     - Optional paper size selection
   - View automatic cost calculation.
   - Track order status in real-time.
   - Select payment method (Cash / Online).
   - View complete order history.

2. **Owner / Admin Role**:
   - Dashboard to view, manage, and verify print requests and uploaded files.
   - Accept or Reject orders (with reason input on rejection).
   - Execute/print document jobs upon acceptance.
   - Manage shop rates for automated pricing calculation.
   - Access automated business analytics: daily/monthly revenue reports and print volume metrics.

## Key Technical Requirements
- **Authentication**: Role-based access control (Customer vs. Shop Owner).
- **Document Handling**: Support PDF and image uploads, automatic page count extraction, format validation, efficient handling of large files.
- **Pricing Engine**: Automated calculation based on configured shop rates, print settings (B&W vs Color), and page counts.
- **Real-Time Synchronization**: Live updates for order status changes.
- **Payments**: Support for both Cash-on-pickup and Online Payment Gateway integrations.
- **Reporting & Analytics**: Interactive revenue analytics dashboard and exportable business reports.

## Development Considerations & Future Roadmap
- Core challenges to address: Accurate PDF/image page detection, secure upload handling, real-time sync, intuitive UX.
- Future Enhancements planned: AI file quality check, QR/Barcode order tracking, WhatsApp/Email alerts, loyalty points, pickup scheduling.
