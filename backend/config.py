import os
from pathlib import Path
from dotenv import load_dotenv

# Path definitions
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
PDF_DIR = BASE_DIR / "pdfs"

# Load environment variables
load_dotenv(PROJECT_ROOT / ".env", override=True)

INGEST_API_KEY = os.environ.get("INGEST_API_KEY")
GDRIVE_FOLDER_URL = os.environ.get("GDRIVE_FOLDER_URL")