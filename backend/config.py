import os
from pathlib import Path
from dotenv import load_dotenv

from pathlib import Path


# Project root: /opt/render/project/src/
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Centralized PDF directory: /opt/render/project/src/pdfs
PDF_DIR = PROJECT_ROOT / "pdfs"



# Load environment variables
load_dotenv(PROJECT_ROOT / ".env", override=True)

INGEST_API_KEY = os.environ.get("INGEST_API_KEY")
GDRIVE_FOLDER_URL = os.environ.get("GDRIVE_FOLDER_URL")