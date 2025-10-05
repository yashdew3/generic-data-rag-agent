# backend/app/routers/files.py
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from typing import List
from fastapi.responses import FileResponse
from ..storage import save_upload, list_uploaded_files, get_file_path, delete_file
from ..models import UploadResponse, FileMeta
from ..services.indexer import process_and_index_file, delete_file_from_index
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
):
    """
    Upload one or more files. Files are stored under backend/uploads/ and metadata saved.
    After saving each file, a background task is scheduled to parse & index it.
    """
    saved = []
    for f in files:
        meta = await save_upload(f)
        saved.append(FileMeta(**meta))
        # schedule background indexing task
        logger.info("Scheduling background index for file_id=%s (%s)", meta["id"], meta["original_name"])
        background_tasks.add_task(process_and_index_file, meta["id"])
    return UploadResponse(success=True, files=saved)

@router.get("/", response_model=List[FileMeta])
async def list_files():
    """List uploaded files (metadata)."""
    metas = list_uploaded_files()
    return [FileMeta(**m) for m in metas]

@router.get("/download/{file_id}")
def download_file(file_id: str):
    """Download the raw file by file id."""
    path = get_file_path(file_id)
    if path is None or not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(path), media_type="application/octet-stream", filename=path.name)

@router.delete("/{file_id}")
async def delete_file_endpoint(file_id: str):
    """Delete a file and remove it from the index."""
    try:
        # Get file metadata before deletion
        files = list_uploaded_files()
        file_meta = next((f for f in files if f["id"] == file_id), None)
        
        if not file_meta:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Delete from storage and metadata
        success = delete_file(file_id)
        if not success:
            raise HTTPException(status_code=404, detail="File not found or could not be deleted")
        
        # Delete from vector index
        try:
            delete_file_from_index(file_id)
            logger.info(f"Successfully deleted file {file_id} ({file_meta['original_name']}) from storage and index")
        except Exception as e:
            logger.warning(f"File {file_id} deleted from storage but failed to remove from index: {e}")
        
        return {"success": True, "message": f"File '{file_meta['original_name']}' deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file {file_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
