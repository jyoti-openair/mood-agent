#!/usr/bin/env python3
import asyncio
import os
from pathlib import Path

# ============================================================
# CRITICAL: Force writable coogne data directory FIRST
# ============================================================
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent                       # mood-agent/

# Local writable location inside your project
cognee_root = project_root / ".cognee"
data_dir = cognee_root / "data"
logs_dir = cognee_root / "logs"

data_dir.mkdir(parents=True, exist_ok=True)
logs_dir.mkdir(parents=True, exist_ok=True)

# Set every possible environment variable Cognee might read
os.environ["COGNEE_DATA_ROOT_DIRECTORY"] = str(data_dir.resolve())
os.environ["DATA_ROOT_DIRECTORY"] = str(data_dir.resolve())
os.environ["COGNEE_LOG_DIR"] = str(logs_dir.resolve())
os.environ["COGNEE_ROOT_DIRECTORY"] = str(cognee_root.resolve())
os.environ["SYSTEM_ROOT_DIRECTORY"] = str(cognee_root.resolve())

print("=== Cognee Paths ===")
print(f"COGNEE_DATA_ROOT_DIRECTORY = {os.environ['COGNEE_DATA_ROOT_DIRECTORY']}")
print(f"DATA_ROOT_DIRECTORY        = {os.environ['DATA_ROOT_DIRECTORY']}")
print(f"COGNEE_LOG_DIR             = {os.environ['COGNEE_LOG_DIR']}")
print("====================\n")

# Now import cognee (after env vars are set)
import cognee

async def ingest_all_pdfs():
    # ---------- LLM Config ----------
    cognee.config.set_llm_provider("gemini")
    cognee.config.set_llm_model("gemini/gemini-3.6-flash")
    cognee.config.set_llm_api_key("AIzaSyDGfmZViRAFnAGjAA7LhN_gvF8Q9HcdoUc")
    cognee.config.set_llm_endpoint(None)

    # ---------- Embedding Config ----------
    cognee.config.set("embedding_provider", "gemini")
    cognee.config.set("embedding_model", "gemini/gemini-embedding-001")
    cognee.config.set("embedding_api_key", "AIzaSyDGfmZViRAFnAGjAA7LhN_gvF8Q9HcdoUc")
    cognee.config.set("embedding_dimensions", 768)
    cognee.config.set("embedding_endpoint", None)

    # Also try forcing the data root via config (some versions need this)
    try:
        cognee.config.set("data_root_directory", str(data_dir.resolve()))
        cognee.config.set("system_root_directory", str(cognee_root.resolve()))
    except Exception:
        pass  # older versions may not have these keys

    # ---------- Paths ----------
    pdf_dir = project_root / "pdfs"

    if not pdf_dir.exists():
        print(f"ERROR: PDF directory not found: {pdf_dir}")
        return

    pdf_files = sorted(pdf_dir.glob("*.pdf"))

    if not pdf_files:
        print(f"ERROR: No PDF files found in {pdf_dir}")
        print(f"Files present: {list(pdf_dir.iterdir())}")
        return

    print(f"Found {len(pdf_files)} PDF(s) in {pdf_dir}:")
    for f in pdf_files:
        print(f"  - {f.name}")
    print()

    # ---------- Ingest (this APPENDS to existing data) ----------
    for i, source_pdf in enumerate(pdf_files, 1):
        print(f"[{i}/{len(pdf_files)}] Processing: {source_pdf.name}")

        print("  [1/2] Adding PDF to Cognee dataset...")
        await cognee.add(str(source_pdf), dataset_name="teachings")

        print("  [2/2] Running cognify() to generate Knowledge Graph...")
        await cognee.cognify(dataset_name="teachings")
        print(f"  [SUCCESS] Knowledge graph updated for {source_pdf.name}\n")

    print(f'[DONE] All {len(pdf_files)} PDF(s) ingested into dataset "teachings"!')
    print(f"Data is stored in: {data_dir}")


if __name__ == "__main__":
    asyncio.run(ingest_all_pdfs())