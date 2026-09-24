# Smart E-Print — Windows Print Agent

A lightweight local FastAPI service that runs on the **Admin's Windows PC**.
It lets the deployed Smart E-Print admin dashboard print documents directly
to any installed Windows printer — with **no browser print dialog**.

---

## Quick Start (Admin Windows PC)

### 1. Install dependencies

```bash
cd print-agent
pip install -r requirements.txt
```

> **SumatraPDF** (recommended for PDF printing):
> Download from https://www.sumatrapdfreader.org/free-pdf-reader
> Install to `C:\Program Files\SumatraPDF\` (default path).

### 2. Configure

Edit `agent.py` top section **or** set environment variables:

| Variable | Default | Description |
|---|---|---|
| `AGENT_TOKEN` | `seprint-agent-secret-2026` | Secret shared with the browser |
| `BACKEND_URL` | `https://smart-e-print.onrender.com/api` | Your deployed backend |
| `ALLOWED_ORIGIN` | `https://smart-e-print.vercel.app` | Your Vercel frontend domain |

### 3. Run

**Double-click** `start-agent.bat`, or run manually:

```bash
uvicorn agent:app --host 127.0.0.1 --port 8765
```

> The agent only listens on `127.0.0.1` — it is **never accessible** from outside the PC.

---

## Browser Setup (Admin side — one time)

The admin browser must send the agent token with every request.
By default it reads from `localStorage`:

```js
localStorage.setItem('seprint_agent_token', 'seprint-agent-secret-2026');
```

This is set automatically when the admin opens the Settings modal and saves the token there.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/status` | Liveness check — confirms agent is running |
| `GET` | `/printers` | Lists all Windows printers with status |
| `POST` | `/print` | Queues a print job (returns `job_id`) |
| `GET` | `/print/{job_id}` | Polls a job's current status |

All endpoints require the header: `X-Agent-Token: <your-token>`

---

## Print Flow

```
Admin clicks PRINT
      ↓
openPrintAgentModal() — opens modal
      ↓
GET /status  →  agent online?  →  yes
      ↓
GET /printers  →  [HP LaserJet, Canon G3010, ...]
      ↓
Admin selects printer (click)
      ↓
gotoStep2() — shows existing order config pills
  [A4] [Black & White] [2 Copies] [Portrait] [Duplex OFF]
      ↓
Admin clicks Print Now
      ↓
POST /print  →  agent downloads file from backend
      ↓
SumatraPDF (silent)  →  selected printer
      ↓
Poll GET /print/{job_id}  →  ✅ Print Job Sent Successfully!
```

---

## Security

- **localhost-only**: `--host 127.0.0.1` means the agent is never on the internet
- **Token auth**: Every request requires `X-Agent-Token` header
- **CORS**: Locked to your Vercel domain — other origins are rejected
- **File cleanup**: Temp files are deleted immediately after printing
- **JWT passthrough**: The admin's existing JWT is used by the agent to download
  the order file from the backend — no separate credentials needed
