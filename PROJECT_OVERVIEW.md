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

### User Roles & Capabilities

#### 1. Customer
- **Document Upload:** Upload PDF files and images.
- **Print Configuration:** Select Color / Black & White, number of copies, page ranges, and optional paper sizes.
- **Cost Estimation:** View instant, automatically calculated price breakdown.
- **Order Tracking:** Follow live status updates of submitted orders.
- **Payment Options:** Pay via online payment gateway or cash on pickup.
- **Order History:** Access previous print order records.

#### 2. Owner / Admin
- **Order Management:** View incoming print requests and inspect uploaded documents.
- **Order Action:** Accept orders or reject them with mandatory rejection reasons.
- **Pricing & Rate Management:** Set and adjust rate cards for B&W, Color, paper sizes, etc.
- **Analytics & Reporting:** Access automated daily and monthly revenue dashboards and print volume metrics.

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
