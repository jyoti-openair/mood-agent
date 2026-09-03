import shutil
from pathlib import Path
import gdown

from backend.config import PDF_DIR


def download_pdfs_from_drive(folder_url: str) -> list[str]:
    # Resolve absolute path
    target_dir = PDF_DIR.resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    tmp_dir = target_dir.parent / "_drive_tmp"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir, ignore_errors=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    # Download from Google Drive
    gdown.download_folder(
        url=folder_url,
        output=str(tmp_dir),
        quiet=False,
        use_cookies=False,
    )

    downloaded = []
    # Search recursively in temp dir for downloaded PDFs
    for pdf_path in tmp_dir.rglob("*.pdf"):
        dest = target_dir / pdf_path.name
        shutil.move(str(pdf_path), dest)
        downloaded.append(str(dest))

    # Clean up temp folder
    shutil.rmtree(tmp_dir, ignore_errors=True)

    if not downloaded:
        raise FileNotFoundError(
            f"No PDF files were downloaded into {target_dir}. Check Google Drive folder permissions."
        )

    return downloaded