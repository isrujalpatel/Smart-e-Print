"""
Smart E-Print — Cloud Storage Service (Supabase Storage)
Ensures uploaded files persist across Render restarts/deployments.
"""

import os
import urllib.request
import urllib.error
import logging

log = logging.getLogger("seprint-storage")

BUCKET_NAME = "order-documents"


def _get_supabase_config():
    """Retrieve Supabase URL and service role key."""
    url = os.getenv("SUPABASE_URL", "https://rlboymsssxbqksevgxij.supabase.co").rstrip("/")
    key = os.getenv("DATABASE_SERVICE_ROLE", "")
    if not key:
        key = os.getenv("DATABASE_ANON", "")
    return url, key


def upload_to_cloud(local_file_path: str, storage_filename: str, content_type: str = "application/octet-stream") -> bool:
    """
    Upload a local file to Supabase Storage bucket 'order-documents'.
    Returns True on success, False on failure.
    """
    url_base, key = _get_supabase_config()
    if not key:
        log.warning("Supabase key not configured; skipping cloud upload.")
        return False

    upload_url = f"{url_base}/storage/v1/object/{BUCKET_NAME}/{storage_filename}"
    try:
        with open(local_file_path, "rb") as f:
            data = f.read()

        req = urllib.request.Request(
            upload_url,
            data=data,
            headers={
                "Authorization": f"Bearer {key}",
                "apikey": key,
                "Content-Type": content_type or "application/octet-stream",
                "x-upsert": "true",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status in (200, 201):
                log.info(f"Uploaded {storage_filename} to cloud storage.")
                return True
    except Exception as exc:
        log.warning(f"Failed to upload {storage_filename} to Supabase storage: {exc}")
    return False


def download_from_cloud(storage_filename: str, local_dest_path: str) -> bool:
    """
    Download a file from Supabase Storage bucket 'order-documents' to local_dest_path.
    Returns True on success, False if not found or on failure.
    """
    url_base, key = _get_supabase_config()
    if not key:
        return False

    download_url = f"{url_base}/storage/v1/object/{BUCKET_NAME}/{storage_filename}"
    try:
        req = urllib.request.Request(
            download_url,
            headers={
                "Authorization": f"Bearer {key}",
                "apikey": key,
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status == 200:
                os.makedirs(os.path.dirname(local_dest_path), exist_ok=True)
                with open(local_dest_path, "wb") as f:
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
                log.info(f"Downloaded {storage_filename} from cloud storage to {local_dest_path}")
                return True
    except urllib.error.HTTPError as err:
        if err.code == 404:
            log.warning(f"File {storage_filename} not found in cloud storage.")
        else:
            log.warning(f"Cloud download HTTP {err.code} for {storage_filename}: {err}")
    except Exception as exc:
        log.warning(f"Failed to download {storage_filename} from cloud storage: {exc}")
    return False
