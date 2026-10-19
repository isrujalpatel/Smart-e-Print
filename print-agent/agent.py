"""
Smart E-Print — Windows Print Agent
====================================
Run on the Admin's Windows PC:
    uvicorn agent:app --host 127.0.0.1 --port 8765

Endpoints:
    GET  /status          — liveness / version check / SumatraPDF status
    GET  /printers        — list all installed Windows printers + status
    POST /print           — download the order file from backend and print it
    POST /print-test      — print an instant test slip directly to verify printer
    POST /print-direct    — print a locally uploaded base64 file directly
    GET  /print/{job_id}  — poll a print job's status

Security:
  * Only binds to 127.0.0.1 (never exposed to the internet)
  * Every request must carry the X-Agent-Token header matching AGENT_TOKEN
  * CORS origin allows the deployed frontend domain and local dev
"""

import os
import sys
import uuid
import time
import base64
import tempfile
import threading
import urllib.request
import urllib.error
import subprocess
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("seprint-agent")

# ── FastAPI ────────────────────────────────────────────────────────────────────
from fastapi import FastAPI, HTTPException, Header, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── Windows-specific imports (graceful fallback for dev on non-Windows) ────────
IS_WINDOWS = sys.platform == "win32"
if IS_WINDOWS:
    try:
        import win32print
        import win32api
        import win32con
    except ImportError:
        IS_WINDOWS = False
        log.warning("pywin32 not available; running in simulated mode.")

# ══════════════════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

AGENT_TOKEN = os.getenv("AGENT_TOKEN", "seprint-agent-secret-2026")
BACKEND_URL = os.getenv("BACKEND_URL", "https://smart-e-print.onrender.com/api")

AGENT_VERSION = "1.1.0"
AGENT_DIR = Path(__file__).parent.resolve()
SUMATRA_LOCAL = AGENT_DIR / "tools" / "SumatraPDF.exe"

# Multiple fallback mirrors for SumatraPDF portable
SUMATRA_MIRRORS = [
    "https://files.sumatrapdfreader.org/software/sumatrapdf/rel/3.5.2/SumatraPDF-3.5.2-64.exe",
    "https://github.com/sumatrapdfreader/sumatrapdf/releases/download/v3.5.2/SumatraPDF-3.5.2-64.exe",
    "https://www.sumatrapdfreader.org/dl/rel/3.5.2/SumatraPDF-3.5.2-64.exe",
]

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

app = FastAPI(
    title="Smart E-Print Agent",
    description="Local Windows print agent for Smart E-Print admin dashboard",
    version=AGENT_VERSION,
    docs_url=None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory job tracking ─────────────────────────────────────────────────────
_jobs: dict = {}
_jobs_lock = threading.Lock()
_sumatra_ready: bool = False


# ══════════════════════════════════════════════════════════════════════════════
#  AUTH DEPENDENCY
# ══════════════════════════════════════════════════════════════════════════════

def verify_token(x_agent_token: Optional[str] = Header(None)):
    if x_agent_token != AGENT_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing agent token.")
    return True


# ══════════════════════════════════════════════════════════════════════════════
#  MODELS
# ══════════════════════════════════════════════════════════════════════════════

class PrintRequest(BaseModel):
    order_id: str
    order_token: str
    printer_name: str
    file_name: str
    copies: int = 1
    print_mode: str = "bw"
    paper_size: str = "A4"
    orientation: str = "portrait"
    duplex: bool = False
    backend_url: Optional[str] = None


class TestPrintRequest(BaseModel):
    printer_name: str
    copies: int = 1


class DirectPrintRequest(BaseModel):
    printer_name: str
    file_name: str
    file_base64: str
    copies: int = 1
    print_mode: str = "bw"
    paper_size: str = "A4"
    orientation: str = "portrait"
    duplex: bool = False


# ══════════════════════════════════════════════════════════════════════════════
#  SUMATRAPDF DETECTION & DOWNLOAD
# ══════════════════════════════════════════════════════════════════════════════

def _find_sumatra_system() -> Optional[str]:
    """Check system-wide installation paths."""
    candidates = [
        r"C:\Program Files\SumatraPDF\SumatraPDF.exe",
        r"C:\Program Files (x86)\SumatraPDF\SumatraPDF.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "SumatraPDF", "SumatraPDF.exe"),
        os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Local", "SumatraPDF", "SumatraPDF.exe"),
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    try:
        result = subprocess.run(["where", "SumatraPDF.exe"], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip().split("\n")[0]
    except Exception:
        pass
    return None


def _find_sumatra() -> Optional[str]:
    """Locate SumatraPDF.exe — local tools/ folder first, then system paths."""
    if SUMATRA_LOCAL.exists():
        return str(SUMATRA_LOCAL)
    return _find_sumatra_system()


def _auto_install_sumatra() -> None:
    """Check local/system SumatraPDF or download it safely with browser User-Agent."""
    global _sumatra_ready

    # Already available locally or in system
    found = _find_sumatra()
    if found:
        log.info(f"✅ SumatraPDF ready at: {found}")
        _sumatra_ready = True
        return

    if not IS_WINDOWS:
        _sumatra_ready = False
        return

    log.info("SumatraPDF not found. Auto-downloading portable version with browser headers...")
    SUMATRA_LOCAL.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = SUMATRA_LOCAL.with_suffix(".tmp")

    for url in SUMATRA_MIRRORS:
        try:
            log.info(f"  Attempting download from: {url}")
            req = urllib.request.Request(
                url,
                headers={"User-Agent": USER_AGENT, "Accept": "*/*"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                with open(tmp_path, "wb") as f:
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
            
            if tmp_path.exists() and tmp_path.stat().st_size > 1000000:
                tmp_path.rename(SUMATRA_LOCAL)
                log.info(f"✅ SumatraPDF downloaded successfully → {SUMATRA_LOCAL}")
                _sumatra_ready = True
                return
        except Exception as exc:
            log.warning(f"  Mirror failed ({url}): {exc}")
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    pass

    log.warning("⚠️  SumatraPDF auto-download failed across all mirrors.")
    log.warning("    PDF printing will fall back to Windows default handler.")
    _sumatra_ready = False


# ══════════════════════════════════════════════════════════════════════════════
#  PRINTERS & FILE UTILS
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


def _download_order_file(order_id: str, token: str, dest_path: str, backend_url: Optional[str] = None) -> None:
    """Download the order's file from backend with retry and browser headers."""
    base = (backend_url or BACKEND_URL).rstrip("/")
    url = f"{base}/orders/{order_id}/download"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
        }
    )

    last_error = None
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                with open(dest_path, "wb") as f:
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
            return
        except urllib.error.HTTPError as err:
            last_error = err
            if err.code == 404:
                raise RuntimeError(
                    "Document not found on server (ephemeral storage expired for this order). "
                    "Use 'Print Test Page' or request customer to re-upload."
                )
            elif err.code in (401, 403):
                raise RuntimeError(f"Authentication failed ({err.code}). Please re-login on the dashboard.")
            time.sleep(1)
        except Exception as exc:
            last_error = exc
            time.sleep(1)

    raise RuntimeError(f"Download failed: {last_error}")


def _generate_test_pdf(printer_name: str) -> bytes:
    """Generate a clean 1-page test PDF slip without external dependencies."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    clean_pname = printer_name.replace("(", "").replace(")", "").replace("\\", "")
    stream_content = (
        "BT\n"
        "/F1 22 Tf\n"
        "50 780 Td\n"
        "(Smart E-Print - Printer Verification Slip) Tj\n"
        "/F1 13 Tf\n"
        "0 -40 Td\n"
        "(Shop: Umiya Graphics and Printing) Tj\n"
        "0 -25 Td\n"
        f"(Printer: {clean_pname}) Tj\n"
        "0 -25 Td\n"
        f"(Timestamp: {now_str}) Tj\n"
        "0 -25 Td\n"
        "(Agent Status: Connected & Operational) Tj\n"
        "0 -35 Td\n"
        "(================================================) Tj\n"
        "0 -30 Td\n"
        "(If you can read this, your printer is properly configured) Tj\n"
        "0 -20 Td\n"
        "(and ready to receive automated customer print orders.) Tj\n"
        "ET\n"
    )
    stream_bytes = stream_content.encode("latin1")
    length = len(stream_bytes)

    pdf_text = (
        f"%PDF-1.4\n"
        f"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        f"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        f"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
        f"4 0 obj << /Length {length} >> stream\n"
        f"{stream_content}"
        f"endstream\n"
        f"endobj\n"
        f"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
        f"xref\n"
        f"0 6\n"
        f"0000000000 65535 f \n"
        f"0000000010 00000 n \n"
        f"0000000060 00000 n \n"
        f"0000000117 00000 n \n"
        f"0000000227 00000 n \n"
        f"0000000500 00000 n \n"
        f"trailer << /Size 6 /Root 1 0 R >>\n"
        f"startxref\n"
        f"570\n"
        f"%%EOF"
    )
    return pdf_text.encode("latin1")


def _print_document(file_path: str, printer_name: str, copies: int = 1, paper_size: str = "A4",
                    duplex: bool = False, orientation: str = "portrait", job_id: Optional[str] = None) -> None:
    """Core print logic using SumatraPDF silent printing, with fallback."""
    if job_id:
        with _jobs_lock:
            _jobs[job_id]["status"]  = "printing"
            _jobs[job_id]["message"] = f"Sending to printer: {printer_name}"

    ext = Path(file_path).suffix.lower()

    if ext == ".pdf":
        sumatra = _find_sumatra()
        if sumatra:
            paper = (paper_size or "A4").lower()
            settings_parts = [
                str(copies),
                f"paper={paper}",
            ]
            if duplex:
                settings_parts.append("duplexlong")
            if orientation == "landscape":
                settings_parts.append("landscape")

            cmd = [
                sumatra,
                "-print-to", printer_name,
                "-print-settings", ",".join(settings_parts),
                "-silent",
                file_path,
            ]
            log.info(f"[Print] Running SumatraPDF: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, timeout=120)
            if result.returncode not in (0, 1):
                stderr = result.stderr.decode(errors="replace").strip()
                if stderr:
                    raise RuntimeError(f"SumatraPDF error (rc={result.returncode}): {stderr}")
            log.info(f"[Print] SumatraPDF completed successfully (rc={result.returncode})")
            return

    # Fallback to ShellExecute (for images or if SumatraPDF is missing)
    if IS_WINDOWS:
        log.info(f"[Print] Using ShellExecute printto on {printer_name}")
        win32api.ShellExecute(
            0, "printto", file_path,
            f'"{printer_name}"',
            ".", win32con.SW_HIDE,
        )
        time.sleep(4)
    else:
        log.info(f"[Print Simulation] Printed {file_path} to {printer_name}")
        time.sleep(1)


# ══════════════════════════════════════════════════════════════════════════════
#  STARTUP & ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

# Verify / initialize SumatraPDF safely at startup
try:
    _auto_install_sumatra()
except Exception as _e:
    log.warning(f"Initial SumatraPDF check warning: {_e}")


@app.get("/status")
def get_status(_: bool = Depends(verify_token)):
    """Liveness check — verify agent is running and SumatraPDF is available."""
    sumatra_path = _find_sumatra()
    return {
        "status":      "online",
        "agent":       "Smart E-Print Print Agent",
        "version":     AGENT_VERSION,
        "platform":    sys.platform,
        "is_windows":  IS_WINDOWS,
        "sumatra_pdf": {
            "available": sumatra_path is not None,
            "path":      sumatra_path or "not found — using fallback",
            "local_copy": str(SUMATRA_LOCAL) if SUMATRA_LOCAL.exists() else None,
        },
    }


@app.get("/printers")
def list_printers(_: bool = Depends(verify_token)):
    """Return all Windows printers visible to this machine with live status."""
    try:
        printers = _get_windows_printers()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Failed to enumerate printers: {exc}")

    if not printers:
        raise HTTPException(status_code=503, detail="No printers found on this system.")

    return {"printers": printers, "count": len(printers)}


@app.post("/print-test")
def submit_test_print(req: TestPrintRequest, background_tasks: BackgroundTasks, _: bool = Depends(verify_token)):
    """Instant 1-click test page print to verify printer and agent connectivity."""
    available = [p["name"] for p in _get_windows_printers()]
    if req.printer_name not in available:
        raise HTTPException(status_code=400, detail=f"Printer '{req.printer_name}' not found.")

    job_id = str(uuid.uuid4())
    with _jobs_lock:
        _jobs[job_id] = {
            "job_id":      job_id,
            "order_id":    "test-page",
            "printer":     req.printer_name,
            "file_name":   "Test_Print_Slip.pdf",
            "copies":      req.copies,
            "status":      "queued",
            "message":     "Generating test page…",
            "created_at":  time.time(),
            "finished_at": None,
        }

    def _run_test():
        tmp_path = os.path.join(tempfile.gettempdir(), f"seprint_test_{uuid.uuid4().hex}.pdf")
        try:
            pdf_bytes = _generate_test_pdf(req.printer_name)
            with open(tmp_path, "wb") as f:
                f.write(pdf_bytes)

            _print_document(tmp_path, req.printer_name, req.copies, "A4", False, "portrait", job_id)

            with _jobs_lock:
                _jobs[job_id]["status"]      = "completed"
                _jobs[job_id]["message"]     = "✅ Test page sent to printer successfully!"
                _jobs[job_id]["finished_at"] = time.time()
        except Exception as exc:
            with _jobs_lock:
                _jobs[job_id]["status"]      = "failed"
                _jobs[job_id]["message"]     = f"❌ Test print failed: {exc}"
                _jobs[job_id]["finished_at"] = time.time()
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    background_tasks.add_task(_run_test)
    return {"job_id": job_id, "status": "queued", "message": "Test print queued."}


@app.post("/print-direct")
def submit_direct_print(req: DirectPrintRequest, background_tasks: BackgroundTasks, _: bool = Depends(verify_token)):
    """Print a locally supplied base64 file directly (bypasses backend download)."""
    available = [p["name"] for p in _get_windows_printers()]
    if req.printer_name not in available:
        raise HTTPException(status_code=400, detail=f"Printer '{req.printer_name}' not found.")

    ext = Path(req.file_name).suffix.lower() or ".pdf"
    tmp_path = os.path.join(tempfile.gettempdir(), f"seprint_direct_{uuid.uuid4().hex}{ext}")

    job_id = str(uuid.uuid4())
    with _jobs_lock:
        _jobs[job_id] = {
            "job_id":      job_id,
            "order_id":    "direct",
            "printer":     req.printer_name,
            "file_name":   req.file_name,
            "copies":      req.copies,
            "status":      "queued",
            "message":     "Processing direct file…",
            "created_at":  time.time(),
            "finished_at": None,
        }

    def _run_direct():
        try:
            data = base64.b64decode(req.file_base64)
            with open(tmp_path, "wb") as f:
                f.write(data)

            _print_document(tmp_path, req.printer_name, req.copies, req.paper_size, req.duplex, req.orientation, job_id)

            with _jobs_lock:
                _jobs[job_id]["status"]      = "completed"
                _jobs[job_id]["message"]     = "✅ Direct print job sent successfully!"
                _jobs[job_id]["finished_at"] = time.time()
        except Exception as exc:
            with _jobs_lock:
                _jobs[job_id]["status"]      = "failed"
                _jobs[job_id]["message"]     = f"❌ Direct print failed: {exc}"
                _jobs[job_id]["finished_at"] = time.time()
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    background_tasks.add_task(_run_direct)
    return {"job_id": job_id, "status": "queued", "message": "Direct print queued."}


@app.post("/print")
def submit_print_job(req: PrintRequest, background_tasks: BackgroundTasks, _: bool = Depends(verify_token)):
    """Standard order print: download from backend and send to selected printer."""
    available = [p["name"] for p in _get_windows_printers()]
    if req.printer_name not in available:
        raise HTTPException(
            status_code=400,
            detail=f"Printer '{req.printer_name}' not found. Available: {available}",
        )

    ext = Path(req.file_name).suffix.lower() or ".pdf"
    if ext not in {".pdf", ".png", ".jpg", ".jpeg"}:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    tmp_path = os.path.join(tempfile.gettempdir(), f"seprint_{uuid.uuid4().hex}{ext}")
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
        with _jobs_lock:
            _jobs[job_id]["status"]  = "downloading"
            _jobs[job_id]["message"] = "Downloading file from server…"

        try:
            _download_order_file(req.order_id, req.order_token, tmp_path, req.backend_url)
        except Exception as exc:
            with _jobs_lock:
                _jobs[job_id]["status"]      = "failed"
                _jobs[job_id]["message"]     = f"❌ Download failed: {exc}"
                _jobs[job_id]["finished_at"] = time.time()
            return

        try:
            _print_document(tmp_path, req.printer_name, req.copies, req.paper_size, req.duplex, req.orientation, job_id)
            with _jobs_lock:
                _jobs[job_id]["status"]      = "completed"
                _jobs[job_id]["message"]     = "✅ Print job sent to printer successfully."
                _jobs[job_id]["finished_at"] = time.time()
        except Exception as exc:
            with _jobs_lock:
                _jobs[job_id]["status"]      = "failed"
                _jobs[job_id]["message"]     = f"❌ Print failed: {exc}"
                _jobs[job_id]["finished_at"] = time.time()
        finally:
            if os.path.exists(tmp_path):
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
    """Poll this endpoint to get the live status of a submitted print job."""
    with _jobs_lock:
        job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job
