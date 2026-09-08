import logging
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ---------------------------------------------------------
# Environment & Path Setup
# ---------------------------------------------------------
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

# Resolve ${PWD} or dynamic path variables cleanly
for key in ["COGNEE_DATA_ROOT_DIRECTORY", "COGNEE_LOG_DIR", "DATA_ROOT_DIRECTORY"]:
    val = os.environ.get(key, "")
    if "${PWD}" in val:
        os.environ[key] = val.replace("${PWD}", str(BASE_DIR))

if not os.environ.get("COGNEE_DATA_ROOT_DIRECTORY"):
    os.environ["COGNEE_DATA_ROOT_DIRECTORY"] = str((BASE_DIR / ".cognee" / "data").resolve())

# Deferred imports after ENV configuration
import cognee
from backend import cognee_service
from backend.moods import MOODS, get_mood

app = FastAPI(title="Mood Bridge")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = (
    BASE_DIR / "frontend"
    if (BASE_DIR / "frontend").exists()
    else Path(__file__).resolve().parent / "frontend"
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
# Helpers
# ---------------------------------------------------------
def _format_markdown_response(text: str) -> str:
    """Normalize AI Markdown without modifying Markdown syntax."""
    if not text:
        return ""

    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")

    # Fix bullets that Gemini sometimes puts on the same line
    cleaned = re.sub(r"([^\n])\s+(?=\*\s+)", r"\1\n\n", cleaned)

    # Remove excessive blank lines
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned.strip()


# ---------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------
@app.get("/api/moods")
def list_moods():
    return MOODS


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

        formatted_response = _format_markdown_response(data.get("response", ""))

        return ReflectResponse(
            mood_id=mood["id"],
            response=formatted_response,
            image_prompt=data.get("image_prompt", ""),
            source_excerpt_count=len(retrieval.get("raw_excerpts", [])),
        )

    except Exception as e:
        error_text = str(e).lower()

        if any(
            x in error_text
            for x in [
                "spending cap",
                "resource_exhausted",
                "rate limit",
                "quota",
                "429",
                "exceeded its monthly",
            ]
        ):
            logger.error(f"Reflection generation hit rate limit: {e}")
            raise HTTPException(
                status_code=503,
                detail="Our AI service has hit its daily usage limit. Please try again tomorrow.",
            )

        logger.error(f"Reflection generation failed: {e}", exp_info=True)
        raise HTTPException(
            status_code=500,
            detail="Something went wrong while generating your reflection. Please try again shortly.",
        )


@app.get("/mood-agent")
async def serve_mood_agent():
    mood_app_path = FRONTEND_DIR / "mood-app" / "index.html"
    if not mood_app_path.exists():
        raise HTTPException(status_code=404, detail="Mood agent template not found.")
    return FileResponse(mood_app_path)


# ---------------------------------------------------------
# Frontend Static Mounting
# ---------------------------------------------------------
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")