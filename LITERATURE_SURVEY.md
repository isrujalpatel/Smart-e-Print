# Literature Survey

## Project Title
**Smart E-Printing Software**

---

## 1. Overview of Web-to-Print (W2P) & Digital Print Management
Web-to-Print (W2P) systems have transformed commercial printing by migrating print order submission, customization, and proofing to web applications. Research and industry implementations highlight several approaches to digitizing print shop workflows:

1. **Enterprise Web-to-Print Systems (e.g., Gelato, VistaPrint):**
   - High-capacity platforms designed for global e-commerce and mass merchandise printing.
   - *Limitations for Local Shops:* Complex setup, expensive license fees, lack of support for walk-in/cash payments, and overly complex for single-shop operations.

2. **Messaging & Cloud-Drive Submissions (WhatsApp/Google Drive):**
   - Local shops often rely on ad-hoc messaging or cloud links for remote document receiving.
   - *Limitations:* No structured print settings configuration (e.g., custom page range, paper weight), manual pricing required for every job, privacy risks, and poor order tracking.

3. **Self-Service Kiosk Printing Systems:**
   - Dedicated physical kiosks connected to printers with card readers.
   - *Limitations:* Requires expensive specialized hardware and space inside the store, failing to reduce pre-arrival queueing.

---

## 2. Technical Component Survey

### 2.1 PDF Parsing & Automatic Page Detection
- **PDF Specifications (Adobe PDF Reference):** PDFs store page trees containing page counts, media boxes, and object streams.
- **Server-Side Extraction:** Libraries like `pdf-lib`, `pdf-parse`, or `pdf2image` parse binary headers to extract page numbers instantly without rendering the full document, ensuring high throughput and low bandwidth overhead.

### 2.2 Pricing Engine & Rate Cards
- Dynamic pricing algorithms compute sub-totals based on variables:
  $$\text{Total Cost} = (\text{Page Count} \times \text{Rate per Page (B&W/Color)}) \times \text{Copies}$$
- Custom page range parsing ensures sub-ranges (e.g., `1-5, 8, 11-15`) accurately compute total pages printed.

### 2.3 Real-Time Notification & Order Tracking
- **WebSocket / Server-Sent Events (SSE):** Provides bidirectional low-latency status updates (`Submitted` $\rightarrow$ `Accepted` $\rightarrow$ `Printing` $\rightarrow$ `Ready for Pickup`) without requiring client page refreshes.

---

## 3. Comparative Analysis

| Feature / Aspect | Ad-Hoc Submission (WhatsApp/Email) | Commercial W2P Enterprise | Smart E-Printing Software (Proposed) |
| :--- | :--- | :--- | :--- |
| **Cost to Local Shop** | Free | High SaaS Fee | Tailored & Cost-effective |
| **Auto Page Count** | No (Manual check) | Yes | Yes (PDF & Image support) |
| **Custom Rate Management** | Manual negotiation | Complex catalog rules | Simple Shopkeeper Dashboard |
| **Payment Modes** | Cash only / Manual UPI | Online only | Dual (Cash & Online Payment Gateway) |
| **Order Rejection Workflow** | Informal text message | Cancelled order | Structured rejection with reason input |
| **Business Analytics** | Manual ledger | Advanced | Automated daily & monthly revenue reports |

---

## 4. Research Gap & Novelty
While high-end W2P solutions exist for large commercial printers, local graphics and printing shops like **Umiya Graphics and Printing** require a lightweight, shop-centric web solution that:
1. Simplifies document submission without complex design toolchains.
2. Supports hybrid payment models (Cash on Pickup and Online Payment).
3. Provides immediate, automated cost calculation tailored specifically to the shop owner's customizable rate card.
4. Generates automated revenue and volume analytics for local business management.
