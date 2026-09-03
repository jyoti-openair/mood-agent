import shutil
from pathlib import Path

import gdown
from backend.config import PDF_DIR  # <--- MUST import from config


def download_pdfs_from_drive(folder_url: str, pdf_dir: Path = PDF_DIR) -> list[str]:
    pdf_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = pdf_dir.parent / "_drive_tmp"

    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)

    gdown.download_folder(
        url=folder_url,
        output=str(tmp_dir),
        quiet=False,
        use_cookies=False,
    )

    downloaded = []
    for path in tmp_dir.rglob("*.pdf"):
        dest = pdf_dir / path.name
        shutil.move(str(path), dest)
        downloaded.append(str(dest))

    shutil.rmtree(tmp_dir, ignore_errors=True)

    if not downloaded:
        raise FileNotFoundError(
            "No PDF files found in the Drive folder. Check that the "
            "folder is shared as 'Anyone with the link' and actually "
            "contains .pdf files."
        )

    return downloaded