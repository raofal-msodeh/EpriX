"""
FastAPI interface for eprtool.
"""

import logging
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Optional, Dict, Any
import shutil
import os

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from pydantic import BaseModel

from .pack import pack_directory
from .unpack import unpack_directory
from .utils import setup_logging

logger = logging.getLogger(__name__)

app = FastAPI(
    title="EPRTool API",
    description="Secure file packing/unpacking tool with six-layer encryption",
    version="1.0.0"
)

static_path = os.path.join(os.path.dirname(__file__), 'static')

# Request/Response models
class PackRequest(BaseModel):
    source_dir: str
    output_file: str = "archive.epr"
    keys_file: str = "keys.json"
    passphrase: str
    follow_symlinks: bool = False
    preserve_perms: bool = True
    include_binaries: bool = False

class UnpackRequest(BaseModel):
    input_file: str
    keys_file: str
    passphrase: str
    target_dir: str
    overwrite: bool = False

class OperationResponse(BaseModel):
    success: bool
    message: str
    operation_id: Optional[str] = None
    file_path: Optional[str] = None

# Store ongoing operations (in production, use Redis or database)
operations: Dict[str, Dict[str, Any]] = {}


# Mount static files directory
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

@app.get("/operations", response_class=HTMLResponse)
async def home_page():
    """Serve the main operations dashboard page."""
    try:
        with open(get_path_page("operations.html"), "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Operations page not found")

@app.get("/pack", response_class=HTMLResponse)
async def pack_page():
    """Serve the pack files page."""
    try:
        with open(get_path_page("pack.html"), "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Pack page not found")

@app.get("/pack/upload", response_class=HTMLResponse)
async def pack_upload_page():
    """Serve the upload and pack files page."""
    try:
        with open(get_path_page("pack_upload.html"), "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Pack upload page not found")

@app.get("/unpack", response_class=HTMLResponse)
async def unpack_page():
    """Serve the unpack files page."""
    try:
        with open(get_path_page("unpack.html"), "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Unpack page not found")

@app.get("/unpack/upload", response_class=HTMLResponse)
async def unpack_upload_page():
    """Serve the upload and unpack files page."""
    try:
        with open(get_path_page("unpack_upload.html"), "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Unpack upload page not found")

@app.get("/status", response_class=HTMLResponse)
async def status_page():
    """Serve the operation status page."""
    try:
        with open(get_path_page("status.html"), "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Status page not found")

@app.get("/operations", response_class=HTMLResponse)
async def operations_page():
    """Serve the operations list page (alternative to home)."""
    try:
        with open(get_path_page("operations.html"), "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Operations page not found")


@app.on_event("startup")
async def startup_event():
    """Initialize logging on startup."""
    setup_logging()

@app.get("/")
async def root():
    """Root endpoint with API information."""
    try:
        with open(get_path_page("home.html"), "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Home page not found")

@app.post("/api/v1/pack", response_model=OperationResponse)
async def pack_files(
    background_tasks: BackgroundTasks,
    source_dir: str = Form(...),
    output_file: str = Form("archive.epr"),
    keys_file: str = Form("keys.json"),
    passphrase: str = Form(...),
    follow_symlinks: bool = Form(False),
    preserve_perms: bool = Form(True),
    include_binaries: bool = Form(False)
):
    """
    Pack a directory into an encrypted .epr file.
    
    Note: In production, you might want to handle file uploads differently.
    This assumes the source directory is already accessible on the server.
    """
    try:
        # Validate paths
        source_path = Path(source_dir)
        if not source_path.exists():
            raise HTTPException(status_code=400, detail="Source directory does not exist")

        output_path = Path(output_file)
        keys_path = Path(keys_file)

        # Generate operation ID
        import uuid
        operation_id = str(uuid.uuid4())

        # Store operation
        operations[operation_id] = {
            "status": "processing",
            "type": "pack",
            "source": str(source_path),
            "output": str(output_path)
        }

        # Run packing in background
        background_tasks.add_task(
            execute_pack,
            operation_id,
            source_path,
            output_path,
            keys_path,
            passphrase,
            follow_symlinks,
            preserve_perms,
            include_binaries
        )

        return OperationResponse(
            success=True,
            message="Packing operation started",
            operation_id=operation_id
        )

    except Exception as e:
        logger.error(f"Error starting pack operation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/unpack", response_model=OperationResponse)
async def unpack_files(
    background_tasks: BackgroundTasks,
    input_file: str = Form(...),
    keys_file: str = Form(...),
    passphrase: str = Form(...),
    target_dir: str = Form(...),
    overwrite: bool = Form(False)
):
    """
    Unpack an encrypted .epr file.
    """
    try:
        # Validate paths
        input_path = Path(input_file)
        if not input_path.exists():
            raise HTTPException(status_code=400, detail="Input file does not exist")

        keys_path = Path(keys_file)
        if not keys_path.exists():
            raise HTTPException(status_code=400, detail="Keys file does not exist")

        target_path = Path(target_dir)

        # Generate operation ID
        import uuid
        operation_id = str(uuid.uuid4())

        # Store operation
        operations[operation_id] = {
            "status": "processing",
            "type": "unpack",
            "input": str(input_path),
            "target": str(target_path)
        }

        # Run unpacking in background
        background_tasks.add_task(
            execute_unpack,
            operation_id,
            input_path,
            keys_path,
            passphrase,
            target_path,
            overwrite
        )

        return OperationResponse(
            success=True,
            message="Unpacking operation started",
            operation_id=operation_id
        )

    except Exception as e:
        logger.error(f"Error starting unpack operation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/pack/upload")
async def pack_upload_files(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    output_file: str = Form("archive.epr"),
    keys_file: str = Form("keys.json"),
    passphrase: str = Form(...),
    include_binaries: bool = Form(False)
):
    """
    Pack uploaded files into an encrypted .epr file.
    """
    try:
        # Create temporary directory for uploaded files. The directory is
        # kept alive for the duration of the background task and removed by
        # execute_pack on completion.
        temp_path = Path(tempfile.mkdtemp())
        # Save uploaded files
        for uploaded_file in files:
            file_path = temp_path / uploaded_file.filename
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(uploaded_file.file, buffer)

        # Generate operation ID
        import uuid
        operation_id = str(uuid.uuid4())

        output_path = Path(output_file)
        keys_path = Path(keys_file)

        # Store operation
        operations[operation_id] = {
            "status": "processing",
            "type": "pack_upload",
            "source": str(temp_path),
            "output": str(output_path)
        }

        # Run packing in background
        background_tasks.add_task(
            execute_pack,
            operation_id,
            temp_path,
            output_path,
            keys_path,
            passphrase,
            False,  # follow_symlinks
            True,   # preserve_perms
            include_binaries
        )

        return OperationResponse(
            success=True,
            message="Packing operation started from uploaded files",
            operation_id=operation_id
        )

    except Exception as e:
        logger.error(f"Error starting pack upload operation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/unpack/upload", response_model=OperationResponse)
async def unpack_upload_files(
    background_tasks: BackgroundTasks,
    archive_file: UploadFile = File(..., description="Encrypted .epr file to unpack"),
    keys_file: UploadFile = File(..., description="Keys JSON file for decryption"),
    passphrase: str = Form(..., description="Passphrase for decryption"),
    target_dir: str = Form(..., description="Target directory for unpacked files"),
    overwrite: bool = Form(False, description="Overwrite existing files"),
    create_target: bool = Form(True, description="Create target directory if not exists")
):
    """
    Upload and unpack an encrypted .epr file.
    
    This endpoint allows you to upload both the encrypted archive and keys file,
    then unpack them to the specified target directory.
    """
    try:
        # Validate uploaded files
        if not archive_file.filename or not archive_file.filename.endswith('.epr'):
            raise HTTPException(
                status_code=400, 
                detail="Uploaded file must be a .epr archive"
            )

        if not keys_file.filename or not keys_file.filename.endswith('.json'):
            raise HTTPException(
                status_code=400,
                detail="Keys file must be a JSON file"
            )

        # Create temporary directory for processing
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Save uploaded archive file
            archive_path = temp_path / "uploaded_archive.epr"
            with open(archive_path, "wb") as buffer:
                shutil.copyfileobj(archive_file.file, buffer)

            # Save uploaded keys file
            keys_path = temp_path / "uploaded_keys.json"
            with open(keys_path, "wb") as buffer:
                shutil.copyfileobj(keys_file.file, buffer)

            # Validate target directory
            target_path = Path(target_dir)
            if create_target:
                target_path.mkdir(parents=True, exist_ok=True)
            elif not target_path.exists():
                raise HTTPException(
                    status_code=400,
                    detail="Target directory does not exist and create_target is False"
                )

            # Generate operation ID
            operation_id = str(uuid.uuid4())

            # Store operation
            operations[operation_id] = {
                "status": "processing",
                "type": "unpack_upload",
                "archive_file": archive_file.filename,
                "target_dir": str(target_path),
                "file_size": archive_path.stat().st_size
            }

            # Run unpacking in background
            background_tasks.add_task(
                execute_unpack_upload,
                operation_id,
                archive_path,
                keys_path,
                passphrase,
                target_path,
                overwrite
            )

            return OperationResponse(
                success=True,
                message="Unpacking operation started from uploaded files",
                operation_id=operation_id,
                file_path=str(target_path)
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting unpack upload operation: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/v1/status/{operation_id}")
async def get_operation_status(operation_id: str):
    """Get the status of an operation."""
    operation = operations.get(operation_id)
    if not operation:
        raise HTTPException(status_code=404, detail="Operation not found")

    return {
        "operation_id": operation_id,
        "status": operation["status"],
        "type": operation["type"],
        "details": operation.get("details", {}),
        "error": operation.get("error")
    }



@app.get("/api/v1/operations")
async def list_operations():
    """List all operations (for debugging)."""
    return {
        "operations": [
            {
                "id": op_id,
                "type": op_data["type"],
                "status": op_data["status"]
            }
            for op_id, op_data in operations.items()
        ]
    }

# Background task functions
def execute_pack(
    operation_id: str,
    source: Path,
    output: Path,
    keys_file: Path,
    passphrase: str,
    follow_symlinks: bool,
    preserve_perms: bool,
    include_binaries: bool
):
    """Execute packing in background."""
    try:
        operations[operation_id]["details"] = {"stage": "Starting packing process"}

        pack_directory(
            source=source,
            output=output,
            keys_file=keys_file,
            passphrase=passphrase,
            follow_symlinks=follow_symlinks,
            preserve_perms=preserve_perms,
            include_binaries=include_binaries
        )

        operations[operation_id].update({
            "status": "completed",
            "details": {
                "stage": "Completed",
                "output_file": str(output),
                "keys_file": str(keys_file)
            }
        })

        logger.info(f"Packing operation {operation_id} completed successfully")

        logger.info(f"Packing operation {operation_id} completed successfully")
    except Exception as e:
        operations[operation_id].update({
            "status": "failed",
            "error": str(e)
        })
        logger.error(f"Packing operation {operation_id} failed: {e}")
    finally:
        # Clean up the temporary source directory created by pack_upload
        if source.exists() and source.is_dir():
            shutil.rmtree(source, ignore_errors=True)


def execute_unpack_upload(    operation_id: str,
    archive_file: Path,
    keys_file: Path,
    passphrase: str,
    target: Path,
    overwrite: bool
):
    """Execute unpacking of uploaded files in background."""
    try:
        operations[operation_id]["details"] = {"stage": "Validating uploaded files"}

        # Validate files exist
        if not archive_file.exists():
            raise Exception("Uploaded archive file not found")
        if not keys_file.exists():
            raise Exception("Uploaded keys file not found")

        operations[operation_id]["details"] = {"stage": "Starting decryption process"}

        # Perform unpacking
        unpack_directory(
            input_file=archive_file,
            keys_file=keys_file,
            passphrase=passphrase,
            target=target,
            dry_run=False,
            overwrite=overwrite
        )

        # Get unpacked files count
        unpacked_files = list(target.rglob("*"))
        file_count = len([f for f in unpacked_files if f.is_file()])

        operations[operation_id].update({
            "status": "completed",
            "details": {
                "stage": "Completed",
                "target_dir": str(target),
                "files_extracted": file_count,
                "total_files": len(unpacked_files),
                "archive_size": archive_file.stat().st_size
            }
        })

        logger.info(f"Unpack upload operation {operation_id} completed successfully")

    except Exception as e:
        operations[operation_id].update({
            "status": "failed",
            "error": str(e),
            "details": {"stage": "Failed during unpacking"}
        })
        logger.error(f"Unpack upload operation {operation_id} failed: {e}")

    finally:
        # Clean up the temporary directory created by unpack_upload
        upload_dir = archive_file.parent if archive_file.exists() else None
        if upload_dir is not None and str(upload_dir).startswith(
            tempfile.gettempdir()
        ):
            shutil.rmtree(upload_dir, ignore_errors=True)
def execute_unpack(
    operation_id: str,
    input_file: Path,
    keys_file: Path,
    passphrase: str,
    target: Path,
    overwrite: bool
):
    """Execute unpacking in background."""
    try:
        operations[operation_id]["details"] = {"stage": "Starting unpacking process"}

        unpack_directory(
            input_file=input_file,
            keys_file=keys_file,
            passphrase=passphrase,
            target=target,
            dry_run=False,
            overwrite=overwrite
        )

        operations[operation_id].update({
            "status": "completed",
            "details": {
                "stage": "Completed",
                "target_dir": str(target),
                "files_extracted": "See directory listing"
            }
        })

        logger.info(f"Unpacking operation {operation_id} completed successfully")

    except Exception as e:
        operations[operation_id].update({
            "status": "failed",
            "error": str(e)
        })
        logger.error(f"Unpacking operation {operation_id} failed: {e}")

def get_path_page(name_page):
    return os.path.join(static_path,name_page)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)