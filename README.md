# Smart e-Print — Base Model Setup Guide

## Tech Stack
- **Frontend**: HTML + CSS + Bootstrap 5 + Vanilla JS
- **Backend**: Python Flask + JWT Auth
- **Database**: Supabase PostgreSQL

---

## 1. Supabase Database Setup

1. Go to [supabase.com](https://supabase.com) → create a project
2. Navigate to **SQL Editor**
3. Copy the contents of `database/schema.sql` and run it
4. Go to **Settings → Database → Connection String (URI mode)**
5. Copy the connection URI — you'll need it in the next step

---

## Backend Implementation Status
- **`routes/`**:
  - - [x] `routes/orders.py` — File upload handling, pricing engine, queue management, secure downloads
  - - [ ] `routes/super_admin.py` — System-wide analytics and user management
  - - [x] `routes/shop.py` — Rate card management
- **`models/`**:
  - `user.py` — Authentication and RBAC
  - `print_order.py` — Core transaction and file metadata
  - `shop_config.py` — Dynamic rate cards
  - `audit_log.py` — Security tracking

---

## 2. Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate       # Mac/Linux
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Open .env and fill in your values (DATABASE_URL, SECRET_KEY, JWT_SECRET_KEY)

# Start the server
python app.py
# → Running on http://localhost:5000
```

The backend will automatically create database tables on first run.

---

## 3. Frontend Setup

No build step needed — it's plain HTML/CSS/JS.

```bash
# Option 1: VS Code Live Server
# Install "Live Server" extension → right-click index.html → Open with Live Server

# Option 2: Python simple server
cd frontend
python3 -m http.server 5500
# → http://localhost:5500
```

> **Important**: Make sure `js/config.js` has `API_BASE: 'http://localhost:5000/api'` during development.

---

## 4. API Endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET`  | `/api/health`        | ❌ | Server health check |
| `POST` | `/api/auth/register` | ❌ | Register a new user |
| `POST` | `/api/auth/login`    | ❌ | Login and get JWT |
| `GET`  | `/api/auth/me`       | ✅ Bearer | Get current user |
| `POST` | `/api/auth/logout`   | ✅ Bearer | Logout acknowledgement |

### Register Request Body
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "mypassword",
  "role": "customer"
}
```
`role` must be `"customer"` or `"owner"`.

---

## 5. Deployment

### Frontend → Vercel
1. Push `frontend/` to GitHub
2. Import to [vercel.com](https://vercel.com)
3. Set root directory to `frontend`
4. Update `js/config.js`: `API_BASE: 'https://your-render-app.onrender.com/api'`

### Backend → Render
1. Push `backend/` to GitHub
2. Create a new **Web Service** on [render.com](https://render.com)
3. Set **Build Command**: `pip install -r requirements.txt`
4. Set **Start Command**: `gunicorn app:create_app()`  or `python app.py`
5. Add environment variables (DATABASE_URL, SECRET_KEY, JWT_SECRET_KEY)

---

## Team
- Prince Patel (24CS072)
- Manav Patel (24CS067)
- Srujal Patel (24CS076)


```mermaid
flowchart TD
    %% Global Styling
    classDef startEnd fill:#0F2744,stroke:#0F2744,stroke-width:2px,color:#FFFFFF,font-weight:bold,font-size:14px;
    classDef step fill:#FFFFFF,stroke:#334155,stroke-width:1.5px,color:#0F172A,font-size:13px;
    classDef decision fill:#FFFFFF,stroke:#1E3A8A,stroke-width:2px,color:#0F172A,font-size:13px,font-weight:600;
    classDef redirect fill:#E0ECFB,stroke:#3B82F6,stroke-width:1.5px,color:#1E3A8A,font-weight:bold,font-size:13px;
    classDef roleBox fill:#FFFFFF,stroke:#2563EB,stroke-width:2px,color:#0F172A,font-size:12px;
    classDef layerBox fill:#F8FAFC,stroke:#475569,stroke-width:1.5px,color:#0F172A,font-size:13px,font-weight:600;
    classDef errorBox fill:#FEF2F2,stroke:#EF4444,stroke-width:1.5px,color:#991B1B,font-size:12px;

    %% Workflow Nodes
    A(["<b>User Opens Web App</b>"]):::startEnd
    B["<b>Login / Registration</b><br/>(Email + Password / JWT Authentication)"]:::step
    C{"<b>Valid<br/>Credentials?</b>"}:::decision
    Err["<b>Invalid Login / Error</b><br/>Show alert & prompt retry"]:::errorBox
    R["<b>Redirect by User Role</b>"]:::redirect

    %% Role Action Cards
    subgraph SuperAdminRole [" "]
        SA["<b>Super Admin</b><hr/>• Create & manage Admin/Shop accounts<br/>• Configure platform-wide pricing rules<br/>• View global analytics & system logs"]:::roleBox
    end

    subgraph AdminRole [" "]
        AD["<b>Admin (Shop Owner - Manojbhai Patel)</b><hr/>• Review incoming print queue & files<br/>• Accept order or Reject with reasons<br/>• Configure shop pricing rate-cards<br/>• Track daily/monthly revenue & metrics"]:::roleBox
    end

    subgraph CustomerRole [" "]
        CU["<b>Customer</b><hr/>• Upload documents (PDF / Images)<br/>• Select Color/B&W, copies, page range<br/>• Automated price estimation engine<br/>• Choose Payment (Online / Cash)<br/>• Track real-time order status"]:::roleBox
    end

    %% Tech Infrastructure Layers
    API["<b>Backend REST API</b> • Python Flask / PyPDF2 Engine / JWT Middleware (Gunicorn Hosted)"]:::layerBox
    DB["<b>Database & Cloud Storage</b> • PostgreSQL (SQLAlchemy ORM) + Secure Upload File Storage"]:::layerBox

    %% Connections
    A --> B
    B --> C
    C -- No --> Err
    Err --> B
    C -- Yes --> R

    R --> SA
    R --> AD
    R --> CU

    SA --> API
    AD --> API
    CU --> API

    API --> DB
