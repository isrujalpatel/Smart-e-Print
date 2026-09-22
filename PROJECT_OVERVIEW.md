# Smart E-Printing Software

**Client:** Umiya Graphics and Printing (Owner: Mr. Manojbhai Patel)  
**Project Type:** Client Project  
**Team Members:**  
- Prince Patel (24CS072)  
- Manav Patel (24CS067)  
- Srujal Patel (24CS076)  

---

## 1. Problem Definition Statement
The **Smart E-Printing Software** is a web-based application designed to digitize the printing order process for **Umiya Graphics and Printing**. The system enables customers to place print orders remotely while providing the shopkeeper with a centralized platform to manage orders, payments, and business records. The goal is to improve operational efficiency, eliminate manual workflow bottlenecks, and enhance customer convenience.

---

## 2. System Overview & Functionality

### Customer (User) Features
- [x] **Secure Authentication:** Registration and Google OAuth (mocked) integration.
- [x] **Document Upload:** Support for PDF and common image formats.
- [x] **Print Configuration:** Select color/B&W, copies, and specific page ranges.
- [x] **Smart Pricing Engine:** Real-time price estimation based on page count and settings.
- [x] **Live Order Tracking:** Status updates (Submitted, Printing, Completed, Rejected).
- [x] **Payment Selection:** Choose between Cash on Pickup or Online.

### Shop Owner (Admin) Features
- [x] **Role-Based Access Control:** Secure routes for shop management.
- [x] **Live Print Queue:** Real-time dashboard to manage incoming orders.
- [x] **Order Fulfillment:** Approve, Reject (with reason), and mark jobs as Completed.
- [x] **File Access:** Secure preview/download of customer documents.
- [x] **Rate Card Management:** Dynamically adjust pricing for color, B&W, and paper sizes.
- [x] **Business Analytics:** Basic stats on revenue, pending orders, and total volume.d daily and monthly revenue dashboards and print volume metrics.

---

## 3. Core Features
- **Role-Based Authentication:** Secure access control for Customers and Shop Owner.
- **Automated Page Count Detection:** Server-side parsing of uploaded PDFs/images to determine exact page counts.
- **Dynamic Price Engine:** Instant price calculation based on shopkeeper rate configuration.
- **File Validation & Safety:** File type verification and upload integrity checks.
- **Real-Time Order Tracking:** Synchronized status updates (e.g. Received -> Accepted -> Printing -> Ready -> Completed).
- **Dual Payment Support:** Flexible payment workflows for online payments and cash payments.
- **Revenue Analytics Dashboard:** Visual graphs and report exports for daily/monthly sales and volume.

---

## 4. Technical Challenges & Mitigations
- **Page Count Extraction:** Handling multi-page PDFs, complex document structures, and image files reliably.
- **Large File Uploads:** Optimized streaming or chunked uploads for large documents.
- **Real-Time Updates:** WebSockets or server-sent events to instantly push order updates to customer & owner dashboards.
- **Security & Privacy:** Restricting access to uploaded documents so only the owner and document owner can view them.

---

## 5. Future Roadmap
- AI-based file resolution and print quality check.
- WhatsApp & Email status notifications.
- QR / Barcode scanning for fast order lookup at pickup.
- Customer loyalty and rewards program.
- Cloud backup & document archiving.
- Scheduled pickup time slots.
