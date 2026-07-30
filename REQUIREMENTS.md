# Software Requirements Specification (SRS)

## Project Title
**Smart E-Printing Software**

---

## 1. Functional Requirements

### 1.1 Authentication & User Management
- **FR-1.1:** Role-based access control supporting **Customer** and **Owner/Admin** accounts.
- **FR-1.2:** Customer registration and login via email/password or shop code.
- **FR-1.3:** Secure owner login for shop administration.

### 1.2 Document Upload & Validation
- **FR-2.1:** Upload support for PDF (`.pdf`) and Image formats (`.png`, `.jpg`, `.jpeg`).
- **FR-2.2:** File size validation and mime-type verification before upload processing.
- **FR-2.3:** Automated server-side extraction of total page count for PDF documents.

### 1.3 Print Configuration & Automatic Pricing Engine
- **FR-3.1:** Customer configuration options:
  - Print Mode: Color vs. Black & White (B&W).
  - Copies: Integer selection ($\ge 1$).
  - Page Range: Full document or custom range selection (e.g., `1-3, 5, 8-10`).
  - Paper Size: A4, A3, Letter (optional selection).
- **FR-3.2:** Dynamic price calculation using the formula:
  $$\text{Estimated Price} = (\text{Selected Pages} \times \text{Per Page Rate}) \times \text{Number of Copies}$$
- **FR-3.3:** Shop owner rate card management (configurable rates per page for B&W vs. Color).

### 1.4 Order Processing & Rejection Handling
- **FR-4.1:** Customer order submission with real-time receipt generation.
- **FR-4.2:** Owner dashboard displaying incoming pending print requests with preview/download capability.
- **FR-4.3:** Owner actions:
  - **Accept Order:** Moves order to printing queue.
  - **Reject Order:** Requires mandatory reason input (e.g., corrupted file, unreadable resolution).
- **FR-4.4:** Real-time order status updates for customers (`Submitted`, `Accepted`, `Printing`, `Ready for Pickup`, `Rejected`, `Completed`).

### 1.5 Payment & Revenue Reporting
- **FR-5.1:** Payment method selection: Cash on Pickup or Online Payment Gateway.
- **FR-5.2:** Automated record keeping of transaction history.
- **FR-5.3:** Owner revenue analytics: Daily/Monthly revenue metrics and print volume reports.

---

## 2. Non-Functional Requirements

### 2.1 Performance
- **NFR-1.1:** Page count calculation for standard PDFs ($< 50$ pages) should complete in under 2 seconds.
- **NFR-1.2:** System should handle concurrent file uploads gracefully without dropping connections.

### 2.2 Security & Privacy
- **NFR-2.1:** Uploaded customer documents must be isolated and accessible only by the document owner and the shop owner.
- **NFR-2.2:** Passwords must be hashed using industry-standard hashing algorithms (e.g., bcrypt/Argon2).
- **NFR-2.3:** Environment variables must protect all sensitive credentials and API keys.

### 2.3 Reliability & Availability
- **NFR-3.1:** Order state transitions must be persistent and synced across sessions.
- **NFR-3.2:** Data integrity must be preserved for order history and daily financial records.

### 2.4 Usability & Accessibility
- **NFR-4.1:** Responsive user interface optimized for mobile and desktop screens.
- **NFR-4.2:** Clear UI alerts for order state changes, invalid file uploads, and rejection feedback.

---

## 3. System Environment & Technology Stack
- **Frontend:** HTML, JavaScript, CSS (Vanilla / Modern framework like React or Vite).
- **Backend:** Node.js (Express) or Python server.
- **Database:** Relational (PostgreSQL / MySQL / SQLite) or NoSQL (MongoDB).
- **Document Parser:** `pdf-lib` / `pdf-parse` / image handling libraries.
