import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend import cognee_service
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
# API Endpoints
# ---------------------------------------------------------

@app.get("/api/moods")
def list_moods():
    return MOODS


@app.post("/api/ingest")
async def ingest():
    try:
        result = await cognee_service.ingest_pdf_library()
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/reflect", response_model=ReflectResponse)
async def reflect(req: ReflectRequest):
    mood = get_mood(req.mood_id)
    if not mood:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown mood_id '{req.mood_id}'",
        )

    try:
        # 1. Query Cognee graph for real excerpts matching the mood.
        #    query_teaching is async -> must be awaited.
        retrieval = await cognee_service.query_teaching(mood)

        # 2. Synthesize teachings + generate the image prompt.
        #    generate_teaching_and_prompt is a regular (sync) function
        #    -> call it directly, no await.
        data = cognee_service.generate_teaching_and_prompt(
            mood_label=mood["label"],
            user_context=req.context,
            raw_excerpts=retrieval.get("raw_excerpts", []),
            graph_answers=retrieval.get("graph_answers", []),
        )

        # 3. Attempt image generation (also sync).
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
    # Fallback if frontend is at root relative to main.py
    frontend_dir = Path(__file__).resolve().parent / "frontend"

app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
