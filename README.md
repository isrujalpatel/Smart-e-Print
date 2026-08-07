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
