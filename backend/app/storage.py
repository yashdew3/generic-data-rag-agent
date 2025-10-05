# backend/app/storage.py

from pathlib import Path
import uuid
import json
from datetime import datetime
import aiofiles
from fastapi import UploadFile
from .core.config import settings

def ensure_dirs():
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    if not settings.META_FILE.exists():
        settings.META_FILE.write_text("[]", encoding="utf-8")

async def save_upload(upload_file: UploadFile) -> dict:
    """
    Save an UploadFile to disk and append metadata to uploads.json
    Returns the metadata dict.
    """
    ensure_dirs()
    ext = Path(upload_file.filename).suffix
    file_id = uuid.uuid4().hex
    stored_name = f"{file_id}{ext}"
    dest = settings.UPLOAD_DIR / stored_name

    # async write file content
    async with aiofiles.open(dest, "wb") as out_file:
        content = await upload_file.read()
        await out_file.write(content)

    meta = {
        "id": file_id,
        "original_name": upload_file.filename,
        "stored_name": stored_name,
        "content_type": upload_file.content_type,
        "size": dest.stat().st_size,
        "uploaded_at": datetime.utcnow().isoformat() + "Z"
    }

    # append to metadata file (simple read-write)
    data = []
    if settings.META_FILE.exists():
        raw = settings.META_FILE.read_text(encoding="utf-8")
        data = json.loads(raw) if raw.strip() else []
    data.append(meta)
    settings.META_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return meta

def list_uploaded_files() -> list:
    ensure_dirs()
    raw = settings.META_FILE.read_text(encoding="utf-8")
    return json.loads(raw) if raw.strip() else []

def get_file_path(file_id: str) -> Path | None:
    """Return Path to stored file for a given file id, or None if not found."""
    entries = list_uploaded_files()
    for e in entries:
        if e["id"] == file_id:
            return settings.UPLOAD_DIR / e["stored_name"]
    return None

def delete_file(file_id: str) -> bool:
    """
    Delete a file from storage and remove its metadata.
    Returns True if successful, False if file not found.
    """
    ensure_dirs()
    
    # Load current metadata
    entries = list_uploaded_files()
    file_meta = None
    new_entries = []
    
    # Find the file and create new list without it
    for entry in entries:
        if entry["id"] == file_id:
            file_meta = entry
        else:
            new_entries.append(entry)
    
    if not file_meta:
        return False
    
    # Delete the physical file
    file_path = settings.UPLOAD_DIR / file_meta["stored_name"]
    try:
        if file_path.exists():
            file_path.unlink()
    except Exception as e:
        # Log the error but continue with metadata removal
        print(f"Warning: Could not delete physical file {file_path}: {e}")
    
    # Update metadata file
    settings.META_FILE.write_text(json.dumps(new_entries, indent=2), encoding="utf-8")
    return True
