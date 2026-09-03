import asyncio
import sys
from pathlib import Path

# Add the project root (mood-agent/) to sys.path so `backend` is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import cognee_service

async def main():
    dataset_name = sys.argv[1] if len(sys.argv) > 1 else "teachings"

    result = await cognee_service.ingest_pdf_library(
        dataset_name=dataset_name,
    )

    print("\n========== INGEST COMPLETE ==========")
    print("Dataset:", result["dataset"])
    print("Files ingested:", result["files_ingested"])
    for p in result["paths"]:
        print(" -", p)


if __name__ == "__main__":
    asyncio.run(main())