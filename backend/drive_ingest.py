import shutil
from pathlib import Path

import gdown
from backend.config import PDF_DIR


def download_pdfs_from_drive(folder_url: str) -> list[str]:
    # Ensure PDF_DIR is an absolute Path
    target_dir = Path(PDF_DIR).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    # Use a temp directory alongside target_dir
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
    # rglob captures PDFs inside nested subdirectories created by gdown
    for pdf_path in tmp_dir.rglob("*.pdf"):
        dest = target_dir / pdf_path.name
        shutil.move(str(pdf_path), dest)
        downloaded.append(str(dest))

    # Clean up temp folder
    shutil.rmtree(tmp_dir, ignore_errors=True)

    if not downloaded:
        raise FileNotFoundError(
            f"No PDF files were moved to {target_dir}. Check if the Drive folder contains valid .pdf files."
        )

    return downloaded