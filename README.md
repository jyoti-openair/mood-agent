# Mood Mandala — an wisdom bridge

Pick your mood → Cognee digs through your PDF library's knowledge graph
for how he addressed exactly that (with real stories/examples) → Gemini
turns it into something written directly to you.

```
[ mandala UI ]  →  FastAPI  →  Cognee (knowledge graph over PDFs)
                                   →  Gemini (bridges mood + retrieval → response)
```

## 1. Install

```bash
cd mood-app
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Configure

```bash
cp .env.example .env
```

Edit `.env` and paste your free Gemini key (get one at
https://aistudio.google.com/apikey). It's used twice: once for the app's
"bridge" call, once as Cognee's own LLM/embedding provider for building the
graph — one key covers both, no OpenAI account needed.

## 3. Add your PDFs

Drop the whole folder (subfolders are fine) into:

```
/pdfs/
```

## 4. Build the knowledge graph

For a large library, run this as a standalone step **before** starting the
server — cognify() calls an LLM per chunk to extract entities/relationships,
so dozens of PDFs can take anywhere from tens of minutes to a few hours
depending on total page count and Gemini's free-tier rate limits.

```bash
python scripts/ingest_pdfs.py
```

Re-run it any time you add new PDFs — Cognee skips content it's already
ingested.

> Hitting Gemini free-tier rate limits during ingestion? Cognee will retry,
> but on a very large library it's worth ingesting in a few batches (move a
> subset of PDFs into `pdfs`, ingest, add the rest, ingest again).

## 5. Run the app

```bash
uvicorn backend.main:app --reload
```

Open http://127.0.0.1:8000 — that's the funky frontend, served by the same
FastAPI app.

## How it works

- **`backend/moods.py`** — the mood catalog.
- **`backend/cognee_service.py`** — runs one `GRAPH_COMPLETION` search (a
  reasoned answer) and one `CHUNKS` search (raw passages, so real stories
  survive intact) per seed query, merges and dedupes the results.
- **`backend/gemini_service.py`** — takes those results plus whatever the
  user typed about their situation, and asks Gemini to write a short,
  grounded, second-person response — explicitly instructed not to invent
  teachings beyond what was retrieved.
- **`frontend/`** — a static funky UI (mood "mandala," warm 70s-poster
  palette) that just calls `/api/moods` and `/api/reflect`. No build step.

## Extending it

- **New moods**: add entries to `MOODS` in `backend/moods.py` — the mandala
  layout in `app.js` auto-adjusts to however many you add.

## Troubleshooting

- **"No PDFs found"** — check `PDF_DIR` in `.env` matches where you put
  the files, and that they're actually `.pdf` (not `.epub`/`.txt`).
- **Cognee ingestion errors mentioning embeddings** — double check
  `EMBEDDING_API_KEY` is set (it falls back to `LLM_API_KEY` if omitted, but
  explicit is safer) and that `EMBEDDING_DIMENSIONS=3072` matches the
  `gemini-embedding-001` model.
- **Gemini rate limit errors during `/api/reflect`** — the free tier has
  requests-per-minute caps; add basic retry/backoff in `gemini_service.py`
  if you're hitting this a lot.
