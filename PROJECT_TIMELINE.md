# Project Timeline & Milestones

## Project Title
**Smart E-Printing Software**

## Team Allocation
- **Prince Patel (24CS072):** Backend Architecture, PDF Parsing Engine, Database & Payment Gateway.
- **Manav Patel (24CS067):** Frontend UI/UX, Customer Portal & Real-time Order Tracking.
- **Srujal Patel (24CS076):** Admin/Owner Dashboard, Revenue Analytics & Business Reporting.

---

## 1. Project Phases & Schedule

```mermaid
gantt
    title Smart E-Printing Software Development Schedule
    dateFormat  YYYY-MM-DD
    section Requirement & Design
    Requirements & Proposal Approval  :done, req, 2026-08-01, 7d
    UI/UX Mockups & Database Schema   :active, des, 2026-08-08, 10d
    section Core Development
    Auth & Role-based Security        :dev1, 2026-08-18, 7d
    PDF Parsing & Pricing Engine      :dev2, 2026-08-25, 10d
    Customer Portal & Upload Flow     :dev3, 2026-09-04, 12d
    Owner Dashboard & Order Management:dev4, 2026-09-16, 12d
    Payment Gateway & Real-time Sync  :dev5, 2026-09-28, 10d
    section Reporting & Analytics
    Daily/Monthly Revenue Reports     :rep, 2026-10-08, 8d
    section Testing & Deployment
    System Integration & UAT          :test, 2026-10-16, 10d
    Final Deployment & Client Handover:dep, 2026-10-26, 5d
```

---

## 2. Milestone Deliverables

| Milestone | Deliverables | Target Completion | Responsible |
| :--- | :--- | :--- | :--- |
| **M1: Proposal & Specs** | Project proposal, System Architecture, Repository Initialization | Week 1 | Team |
| **M2: Database & Auth** | User/Owner schemas, JWT/Session Authentication, Role guards | Week 3 | Prince Patel |
| **M3: Upload & Pricing** | PDF page count extractor, Image handler, Dynamic pricing calculator | Week 5 | Prince & Manav |
| **M4: Order & Tracking** | Order submission, Customer dashboard, Real-time status update engine | Week 7 | Manav Patel |
| **M5: Owner Dashboard** | Request management, Order accept/reject with reason, Printer queue | Week 9 | Srujal Patel |
| **M6: Payments & Reports** | Cash/Online payment integration, Revenue analytics charts & exportable reports | Week 11 | Srujal & Prince |
| **M7: Testing & Delivery** | End-to-end testing, User Acceptance Testing (UAT) with Mr. Manojbhai Patel, Deployment | Week 13 | Team |
