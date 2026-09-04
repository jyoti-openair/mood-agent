import os
import gdown
from pathlib import Path

def download_pdfs_from_drive(folder_url: str, output_dir: str = "./pdfs") -> list[str]:
    """
    Downloads PDFs from a Google Drive folder only if the output directory is empty.
    If PDFs are already present locally, it skips downloading and returns existing paths.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Check for existing PDFs in the target directory
    existing_pdfs = [
        os.path.join(output_dir, f) 
        for f in os.listdir(output_dir) 
        if f.lower().endswith(".pdf")
    ]
    
    # 2. Skip downloading if PDFs already exist locally
    if existing_pdfs:
        print(f"Found {len(existing_pdfs)} existing PDF(s) in '{output_dir}'. Skipping download.")
        return sorted(existing_pdfs)
        
    print(f"No existing PDFs found in '{output_dir}'. Downloading from Google Drive...")
    
    # 3. Download folder content using gdown
    gdown.download_folder(
        url=folder_url,
        output=output_dir,
        quiet=False,
        use_cookies=False
    )
    
    # 4. Gather and return newly downloaded PDF paths
    downloaded_pdfs = [
        os.path.join(output_dir, f) 
        for f in os.listdir(output_dir) 
        if f.lower().endswith(".pdf")
    ]
    
    return sorted(downloaded_pdfs)