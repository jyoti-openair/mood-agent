"""
Run this once (and again whenever you add new PDFs) to build the knowledge
graph:

    python scripts/ingest_pdfs.py

With a large library (dozens of PDFs) this will take a while - cognify()
calls an LLM to extract entities and relationships per chunk of text.
Leave it running; it prints progress as it goes.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import cognee_service


async def main():
    print(f"Scanning '{cognee_service.PDF_DIR}' for PDFs...")
    result = await cognee_service.ingest_pdf_library()
    print(f"\nDone. Ingested {result['files_ingested']} files into "
          f"dataset '{result['dataset']}':")
    for p in result["paths"]:
        print(f"  - {p}")


if __name__ == "__main__":
    asyncio.run(main())