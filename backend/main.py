import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

import cognee
from fastapi import BackgroundTasks, FastAPI, HTTPException
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


# ---------------------------------------------------------
# Ingest state (in-memory; resets on restart)
# ---------------------------------------------------------

_ingest_status = {"state": "idle", "detail": None}


def _require_api_key(provided_key: str | None) -> None:
    expected = os.environ.get("INGEST_API_KEY")
    if not expected:
        raise HTTPException(
            status_code=500,
            detail="INGEST_API_KEY is not configured on the server.",
        )
    if provided_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")


async def _run_ingestion(dataset_name: str) -> None:
    _ingest_status.update(state="downloading", detail=None)
    try:
        folder_url = os.environ.get("GDRIVE_FOLDER_URL")
        if not folder_url:
            raise RuntimeError("GDRIVE_FOLDER_URL is not configured on the server.")

        # Run blocking gdown I/O in thread pool
        downloaded = await run_in_threadpool(download_pdfs_from_drive, folder_url)
        _ingest_status.update(state="ingesting", detail=f"{len(downloaded)} files downloaded")

        result = await cognee_service.ingest_pdf_library(dataset_name=dataset_name)

        _ingest_status.update(state="done", detail=result)
    except Exception as e:
        _ingest_status.update(state="failed", detail=f"{type(e).__name__}: {e}")


# ---------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------

@app.get("/api/moods")
def list_moods():
    return MOODS


@app.get("/api/admin/run-ingest")
async def run_manual_ingest(secret: str = ""):
    if secret != "my-one-time-secret":
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        folder_url = os.environ.get("GDRIVE_FOLDER_URL")
        if not folder_url:
            raise HTTPException(status_code=500, detail="GDRIVE_FOLDER_URL missing")

        # 1. Download safely on threadpool to avoid event loop freezing
        downloaded = await run_in_threadpool(download_pdfs_from_drive, folder_url)

        # 2. Ingest
        result = await cognee_service.ingest_pdf_library(dataset_name="teachings")

        return {
            "status": "success",
            "files_downloaded": len(downloaded),
            "detail": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ingest/status")
def ingest_status():
    return _ingest_status


# ---------------------------------------------------------
# Cognee Knowledge Base Routes
# ---------------------------------------------------------

from cognee.modules.search.types import SearchType


def get_search_type(preferred_name: str):
    """Dynamically retrieves a valid SearchType enum member safely."""
    # 1. Try uppercase match (e.g. INSIGHTS)
    if hasattr(SearchType, preferred_name.upper()):
        return getattr(SearchType, preferred_name.upper())

    # 2. Try lowercase match (e.g. insights)
    if hasattr(SearchType, preferred_name.lower()):
        return getattr(SearchType, preferred_name.lower())

    # 3. Fall back to standard SEARCH or first available enum attribute
    for fallback in ["SEARCH", "search", "COMPLETIONS", "completions"]:
        if hasattr(SearchType, fallback):
            return getattr(SearchType, fallback)

    # 4. Fall back to the very first Enum member defined
    return list(SearchType)[0]


from typing import Optional

@app.get("/api/knowledge/search")
async def search_knowledge_base(q: Optional[str] = None):
    """Query Cognee's search engine directly via URL parameters."""
    if not q or not q.strip():
        return {
            "query": None,
            "message": "Please supply a query parameter, e.g., /api/knowledge/search?q=what is mindfulness",
            "results": []
        }

    try:
        query_type = get_search_type("INSIGHTS")
        results = await cognee.search(
            query_type=query_type,
            query_text=q,
        )
        return {
            "query": q,
            "results": results,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Knowledge base query failed: {str(e)}",
        )


@app.get("/api/knowledge/graph")
async def get_knowledge_graph():
    """Inspect knowledge graph elements stored in Cognee."""
    try:
        query_type = get_search_type("GRAPH_COMPLETIONS")

        graph_data = await cognee.search(
            query_type=query_type,
            query_text="*",
        )
        return {
            "graph": graph_data,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch graph data: {str(e)}",
        )


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
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Reflection generation failed: {str(e)}",
        )


# ---------------------------------------------------------
# Frontend Static Mounting (Must remain at the bottom)
# ---------------------------------------------------------

frontend_dir = Path(__file__).resolve().parent.parent / "frontend"

if not frontend_dir.exists():
    frontend_dir = Path(__file__).resolve().parent / "frontend"

app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")