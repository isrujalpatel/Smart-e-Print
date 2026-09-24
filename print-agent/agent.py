"""
Smart E-Print — Windows Print Agent
====================================
Run on the Admin's Windows PC:
    uvicorn agent:app --host 127.0.0.1 --port 8765

Exposes three endpoints:
    GET  /status          — liveness / version check
    GET  /printers        — list all installed Windows printers + status
    POST /print           — download the order file from the backend and print it
    GET  /print/{job_id}  — poll a print job's status

Security:
  * Only binds to 127.0.0.1 (never exposed to the internet)
  * Every request must carry the X-Agent-Token header matching AGENT_TOKEN
  * CORS origin is locked to the deployed frontend domain
"""

import os
import sys
import uuid
import time
import tempfile
import threading
import urllib.request
import subprocess
from pathlib import Path
from typing import Optional

# ── FastAPI ────────────────────────────────────────────────────────────────────
from fastapi import FastAPI, HTTPException, Header, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── Windows-specific imports (graceful fallback for dev on non-Windows) ────────
IS_WINDOWS = sys.platform == "win32"
if IS_WINDOWS:
    import win32print
    import win32api
    import win32con

# ══════════════════════════════════════════════════════════════════════════════
#  CONFIGURATION  — edit AGENT_TOKEN and BACKEND_URL before running
# ══════════════════════════════════════════════════════════════════════════════

# Secret token — must match the value stored in the admin browser's localStorage
# under key "seprint_agent_token".  Set via environment variable or change here.
AGENT_TOKEN = os.getenv("AGENT_TOKEN", "seprint-agent-secret-2026")

# Your deployed Smart E-Print backend base URL (used to download order files)
BACKEND_URL = os.getenv("BACKEND_URL", "https://smart-e-print.onrender.com/api")

# Your deployed frontend origin (CORS).  Add your Vercel domain here.
ALLOWED_ORIGINS = [
    "https://smart-e-print.vercel.app",
    # also allow local file:// and dev servers for testing
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:3000",
    "null",
]

# ══════════════════════════════════════════════════════════════════════════════

AGENT_VERSION = "1.0.0"

app = FastAPI(
    title="Smart E-Print Agent",
    description="Local Windows print agent for Smart E-Print admin dashboard",
    version=AGENT_VERSION,
    docs_url=None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Agent-Token"],
)

# ── In-memory job tracking ─────────────────────────────────────────────────────
_jobs: dict = {}
_jobs_lock = threading.Lock()


# ══════════════════════════════════════════════════════════════════════════════
#  AUTH DEPENDENCY
# ══════════════════════════════════════════════════════════════════════════════

def verify_token(x_agent_token: Optional[str] = Header(None)):
    if x_agent_token != AGENT_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing agent token.")
    return True


# ══════════════════════════════════════════════════════════════════════════════
#  REQUEST MODEL
# ══════════════════════════════════════════════════════════════════════════════

class PrintRequest(BaseModel):
    order_id: str          # UUID of the order
    order_token: str       # Admin's JWT (to download the order file)
    printer_name: str      # Exact printer name from /printers
    file_name: str         # Original file name (e.g. report.pdf)
    # Print settings — pulled straight from the existing order object
    copies: int = 1
    print_mode: str = "bw"        # "bw" | "color"
    paper_size: str = "A4"        # "A4" | "A3" | "Letter"
    orientation: str = "portrait" # "portrait" | "landscape"
    duplex: bool = False


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _get_windows_printers() -> list:
    """Return all installed Windows printers with name and status string."""
    if not IS_WINDOWS:
        return [
            {"name": "Demo PDF Printer",   "status": "Ready", "is_default": True,  "driver": "Demo"},
            {"name": "Demo Virtual Printer","status": "Ready", "is_default": False, "driver": "Demo"},
        ]

    STATUS_MAP = {
        0:                                     "Ready",
        win32print.PRINTER_STATUS_PAUSED:      "Paused",
        win32print.PRINTER_STATUS_ERROR:       "Error",
        win32print.PRINTER_STATUS_OFFLINE:     "Offline",
        win32print.PRINTER_STATUS_PRINTING:    "Printing",
        win32print.PRINTER_STATUS_BUSY:        "Busy",
        win32print.PRINTER_STATUS_PAPER_JAM:   "Paper Jam",
        win32print.PRINTER_STATUS_PAPER_OUT:   "Paper Out",
        win32print.PRINTER_STATUS_NO_TONER:    "No Toner",
    }

    default_printer = ""
    try:
        default_printer = win32print.GetDefaultPrinter()
    except Exception:
        pass

    printers = []
    seen = set()
    for flags in (win32print.PRINTER_ENUM_LOCAL, win32print.PRINTER_ENUM_CONNECTIONS):
        try:
            for p in win32print.EnumPrinters(flags, None, 2):
                info = p[2] if isinstance(p, (tuple, list)) else p
                name   = info.get("pPrinterName", "Unknown")
                status = info.get("Status", 0)
                driver = info.get("pDriverName", "")
                if name not in seen:
                    seen.add(name)
                    printers.append({
                        "name":       name,
                        "status":     STATUS_MAP.get(status, f"Status {status}"),
                        "is_default": name == default_printer,
                        "driver":     driver,
                    })
        except Exception:
            pass

    return printers


def _download_order_file(order_id: str, token: str, dest_path: str) -> None:
    """Download the order's file from the Smart E-Print backend."""
    url = f"{BACKEND_URL}/orders/{order_id}/download"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        with open(dest_path, "wb") as f:
            f.write(resp.read())


def _find_sumatra() -> Optional[str]:
    """Locate SumatraPDF.exe on common installation paths."""
    candidates = [
        r"C:\Program Files\SumatraPDF\SumatraPDF.exe",
        r"C:\Program Files (x86)\SumatraPDF\SumatraPDF.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "SumatraPDF", "SumatraPDF.exe"),
        os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Local", "SumatraPDF", "SumatraPDF.exe"),
        "SumatraPDF.exe",  # in PATH
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    # Try PATH
    try:
        result = subprocess.run(["where", "SumatraPDF.exe"], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip().split("\n")[0]
    except Exception:
        pass
    return None


def _print_document(file_path: str, req: PrintRequest, job_id: str) -> None:
    """
    Core print logic.  Uses SumatraPDF for PDFs (silent, no dialog) and
    win32api.ShellExecute as universal fallback.
    """
    with _jobs_lock:
        _jobs[job_id]["status"]  = "printing"
        _jobs[job_id]["message"] = f"Sending to printer: {req.printer_name}"

    try:
        ext = Path(file_path).suffix.lower()

        if ext == ".pdf":
            sumatra = _find_sumatra()
            if sumatra:
                # SumatraPDF silent printing — no browser dialog, no UI
                print_settings_parts = [f"{req.copies}x", req.paper_size.lower()]
                if req.duplex:
                    print_settings_parts.append("duplexlong")
                if req.orientation == "landscape":
                    print_settings_parts.append("landscape")

                cmd = [
                    sumatra,
                    "-print-to", req.printer_name,
                    "-print-settings", ",".join(print_settings_parts),
                    "-silent",
                    file_path,
                ]
                result = subprocess.run(cmd, capture_output=True, timeout=120)
                if result.returncode not in (0, 1):   # Sumatra returns 1 on success too
                    stderr = result.stderr.decode(errors="replace")
                    if stderr:
                        raise RuntimeError(f"SumatraPDF error: {stderr}")
            else:
                # Fallback: ShellExecute printto verb
                win32api.ShellExecute(
                    0, "printto", file_path,
                    f'"{req.printer_name}"',
                    ".", win32con.SW_HIDE,
                )
                time.sleep(6)

        elif ext in {".png", ".jpg", ".jpeg"}:
            # Use ShellExecute for images
            win32api.ShellExecute(
                0, "printto", file_path,
                f'"{req.printer_name}"',
                ".", win32con.SW_HIDE,
            )
            time.sleep(4)

        else:
            # Generic fallback
            win32api.ShellExecute(
                0, "printto", file_path,
                f'"{req.printer_name}"',
                ".", win32con.SW_HIDE,
            )
            time.sleep(4)

        with _jobs_lock:
            _jobs[job_id]["status"]      = "completed"
            _jobs[job_id]["message"]     = "✅ Print job sent successfully."
            _jobs[job_id]["finished_at"] = time.time()

    except Exception as exc:
        with _jobs_lock:
            _jobs[job_id]["status"]      = "failed"
            _jobs[job_id]["message"]     = f"❌ Print failed: {exc}"
            _jobs[job_id]["finished_at"] = time.time()
    finally:
        try:
            os.remove(file_path)
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
#  ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/status")
def get_status(_: bool = Depends(verify_token)):
    """Liveness check — call this first to verify the agent is running."""
    return {
        "status":    "online",
        "agent":     "Smart E-Print Print Agent",
        "version":   AGENT_VERSION,
        "platform":  sys.platform,
        "is_windows": IS_WINDOWS,
    }


@app.get("/printers")
def list_printers(_: bool = Depends(verify_token)):
    """Return all Windows printers visible to this machine, with live status."""
    try:
        printers = _get_windows_printers()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Failed to enumerate printers: {exc}")

    if not printers:
        raise HTTPException(status_code=503, detail="No printers found on this system.")

    return {"printers": printers, "count": len(printers)}


@app.post("/print")
def submit_print_job(
    req: PrintRequest,
    background_tasks: BackgroundTasks,
    _: bool = Depends(verify_token),
):
    """
    Validate the request, queue the print job, and return a job_id immediately.
    The actual download + printing happens in a background thread.
    Poll GET /print/{job_id} to track progress.
    """
    # Validate printer name exists on this machine
    available = [p["name"] for p in _get_windows_printers()]
    if req.printer_name not in available:
        raise HTTPException(
            status_code=400,
            detail=f"Printer '{req.printer_name}' not found. Available: {available}",
        )

    # Validate copies
    if not (1 <= req.copies <= 99):
        raise HTTPException(status_code=400, detail="Copies must be between 1 and 99.")

    # Validate print mode
    if req.print_mode not in {"bw", "color"}:
        raise HTTPException(status_code=400, detail="print_mode must be 'bw' or 'color'.")

    # Build temp file path
    ext = Path(req.file_name).suffix.lower() or ".pdf"
    if ext not in {".pdf", ".png", ".jpg", ".jpeg"}:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")
    tmp_path = os.path.join(tempfile.gettempdir(), f"seprint_{uuid.uuid4().hex}{ext}")

    # Create job record
    job_id = str(uuid.uuid4())
    with _jobs_lock:
        _jobs[job_id] = {
            "job_id":      job_id,
            "order_id":    req.order_id,
            "printer":     req.printer_name,
            "file_name":   req.file_name,
            "copies":      req.copies,
            "status":      "queued",
            "message":     "Job queued, downloading file…",
            "created_at":  time.time(),
            "finished_at": None,
        }

    def _run():
        # 1. Download file from backend
        try:
            _download_order_file(req.order_id, req.order_token, tmp_path)
        except Exception as exc:
            with _jobs_lock:
                _jobs[job_id]["status"]      = "failed"
                _jobs[job_id]["message"]     = f"❌ Download failed: {exc}"
                _jobs[job_id]["finished_at"] = time.time()
            return

        # 2. Print it
        if IS_WINDOWS:
            _print_document(tmp_path, req, job_id)
        else:
            # Non-Windows dev mode — simulate
            time.sleep(2)
            with _jobs_lock:
                _jobs[job_id]["status"]      = "completed"
                _jobs[job_id]["message"]     = "✅ Print simulated (non-Windows dev mode)."
                _jobs[job_id]["finished_at"] = time.time()
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    background_tasks.add_task(_run)

    return {
        "job_id":  job_id,
        "status":  "queued",
        "message": "Print job queued. Poll /print/{job_id} for status.",
    }


@app.get("/print/{job_id}")
def get_job_status(job_id: str, _: bool = Depends(verify_token)):
    """Poll this endpoint to get the current status of a submitted print job."""
    with _jobs_lock:
        job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job
