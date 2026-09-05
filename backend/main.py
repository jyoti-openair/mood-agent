import os
import re
import shutil
import tarfile
from pathlib import Path
from dotenv import load_dotenv
import logging
import litellm

logger = logging.getLogger(__name__)

# 1. Load environment variables from .env
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

# 2. Fix unexpanded `${PWD}` string in env variables BEFORE importing cognee
BASE_DIR = Path(__file__).resolve().parent.parent
for key in ["COGNEE_DATA_ROOT_DIRECTORY", "COGNEE_LOG_DIR", "DATA_ROOT_DIRECTORY"]:
    val = os.environ.get(key, "")
    if "${PWD}" in val:
        os.environ[key] = val.replace("${PWD}", str(BASE_DIR))

# Ensure fallback absolute path if not defined
if not os.environ.get("COGNEE_DATA_ROOT_DIRECTORY"):
    os.environ["COGNEE_DATA_ROOT_DIRECTORY"] = str((BASE_DIR / ".cognee" / "data").resolve())

# 3. NOW import cognee safely
import cognee
import gdown

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, UploadFile, File
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Import SearchType safely from cognee
try:
    from cognee.modules.search.types import SearchType
except ImportError:
    try:
        from cognee import SearchType
    except ImportError:
        SearchType = None

from backend import cognee_service
from backend.drive_ingest import download_pdfs_from_drive
from backend.moods import MOODS, get_mood

app = FastAPI(title="Mood Bridge")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = BASE_DIR / "data"


# ---------------------------------------------------------
# Schemas
# ---------------------------------------------------------

class ReflectRequest(BaseModel):
    mood_id: str
    context: str = ""


class ReflectResponse(BaseModel):
    mood_id: str
    response: str
    image_prompt: str = ""
    image_url: str = ""
    source_excerpt_count: int


class AdminDriveIngestRequest(BaseModel):
    drive_url_or_id: str
    dataset_name: str = "teachings"


# ---------------------------------------------------------
# Helpers & Security
# ---------------------------------------------------------

_ingest_status = {"state": "idle", "detail": None}


def _require_api_key(provided_key: str | None) -> None:
    expected = os.environ.get("INGEST_API_KEY")
    if expected and provided_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")


def extract_drive_id(url_or_id: str) -> str:
    patterns = [
        r"file/d/([a-zA-Z0-9_-]+)",
        r"id=([a-zA-Z0-9_-]+)",
        r"^([a-zA-Z0-9_-]+)$"
    ]
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    raise ValueError("Invalid Google Drive URL or File ID format.")


def _download_single_drive_file(file_id: str) -> str:
    os.makedirs(DATA_DIR, exist_ok=True)
    output_path = os.path.join(DATA_DIR, f"{file_id}.pdf")
    
    # Use id= directly with fuzzy=True to bypass download confirmation screens
    downloaded = gdown.download(
        id=file_id, 
        output=output_path, 
        quiet=False, 
        fuzzy=True
    )
    
    if not downloaded or not os.path.exists(output_path):
        raise RuntimeError("Failed to download file from Google Drive. Ensure link sharing is enabled.")
    return output_path


async def _run_ingestion(dataset_name: str) -> None:
    _ingest_status.update(state="downloading", detail=None)
    try:
        folder_url = os.environ.get("GDRIVE_FOLDER_URL")
        if not folder_url:
            raise RuntimeError("GDRIVE_FOLDER_URL is not configured on the server.")

        # Run blocking gdown I/O in thread pool
        downloaded = await run_in_threadpool(download_pdfs_from_drive, folder_url)
        _ingest_status.update(state="ingesting", detail=f"{len(downloaded)} files downloaded")

        results = []
        for file_path in downloaded:
            res = await cognee_service.chunk_and_ingest_pdf(
                file_path=file_path, 
                dataset_name=dataset_name
            )
            results.append(res)
            
        _ingest_status.update(state="done", detail=f"Processed {len(results)} files")
    except Exception as e:
        _ingest_status.update(state="failed", detail=f"{type(e).__name__}: {e}")


# ---------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------

@app.get("/api/moods")
def list_moods():
    return MOODS


@app.post("/api/admin/run-ingest")
async def run_admin_ingest(
    request: AdminDriveIngestRequest,
    x_api_key: str | None = Header(None)
):
    _require_api_key(x_api_key)

    try:
        file_id = extract_drive_id(request.drive_url_or_id)
        
        # 1. Download file on threadpool to avoid blocking event loop
        file_path = await run_in_threadpool(_download_single_drive_file, file_id)

        # 2. Ingest into Cognee using local chunking & Ollama pipeline
        res = await cognee_service.chunk_and_ingest_pdf(
            file_path=file_path,
            dataset_name=request.dataset_name
        )

        return {
            "status": "success",
            "file_id": file_id,
            "file_path": file_path,
            "dataset_name": request.dataset_name,
            "ingest_result": res,
            "message": "Document downloaded and cognified successfully."
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Admin ingestion failed: {str(e)}")


@app.get("/api/admin/run-ingest", include_in_schema=False)
async def run_manual_ingest(secret: str = ""):
    if secret != "my-one-time-secret":
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        folder_url = os.environ.get("GDRIVE_FOLDER_URL")
        if not folder_url:
            raise HTTPException(status_code=500, detail="GDRIVE_FOLDER_URL missing")

        # 1. Download safely on threadpool
        downloaded = await run_in_threadpool(download_pdfs_from_drive, folder_url)

        # 2. Ingest PDFs one-by-one with page chunking
        results = []
        for file_path in downloaded:
            res = await cognee_service.chunk_and_ingest_pdf(file_path=file_path, dataset_name="teachings")
            results.append(res)

        return {
            "status": "success",
            "files_downloaded": len(downloaded),
            "files_processed": len(results),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/admin/upload-cognee", include_in_schema=False)
async def upload_cognee_backup(secret: str = "", file: UploadFile = File(...)):
    if secret != "my-one-time-secret":
        raise HTTPException(status_code=401, detail="Unauthorized")

    tar_path = BASE_DIR / "temp_cognee.tar.gz"

    try:
        with open(tar_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        with tarfile.open(tar_path, "r:gz") as tar:
            tar.extractall(path=BASE_DIR)

        if tar_path.exists():
            tar_path.unlink()

        return {"status": "success", "message": "Successfully unpacked .cognee archive!"}
    except Exception as e:
        if tar_path.exists():
            tar_path.unlink()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.get("/api/ingest/status")
def ingest_status():
    return _ingest_status


@app.post("/api/reflect", response_model=ReflectResponse)
async def reflect(req: ReflectRequest):
    mood = get_mood(req.mood_id)
    if not mood:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown mood_id '{req.mood_id}'",
        )

    try:
        retrieval = await cognee_service.query_teaching(mood)

        data = cognee_service.generate_teaching_and_prompt(
            mood_label=mood["label"],
            user_context=req.context,
            raw_excerpts=retrieval.get("raw_excerpts", []),
            graph_answers=retrieval.get("graph_answers", []),
        )

        image_url = cognee_service.generate_mood_image(
            data.get("image_prompt", "")
        )

        return ReflectResponse(
            mood_id=mood["id"],
            response=data.get("response", ""),
            image_prompt=data.get("image_prompt", ""),
            image_url=image_url,
            source_excerpt_count=len(retrieval.get("raw_excerpts", [])),
        )

    except litellm.RateLimitError as e:
        logger.error(f"Reflection generation hit rate/billing limit: {e}")
        if "spending cap" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            raise HTTPException(
                status_code=503,
                detail="Our AI brain has hit its daily snack budget. Please come back tomorrow.",
            )
        raise HTTPException(
            status_code=429,
            detail="We're getting a lot of requests right now — try again in a moment.",
        )

    except Exception as e:
        logger.error(f"Reflection generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Something went wrong while generating your reflection. Please try again shortly.",
        )

# ---------------------------------------------------------
# Frontend Static Mounting (Must remain at the bottom)
# ---------------------------------------------------------

frontend_dir = BASE_DIR / "frontend"

if not frontend_dir.exists():
    frontend_dir = Path(__file__).resolve().parent / "frontend"

app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")