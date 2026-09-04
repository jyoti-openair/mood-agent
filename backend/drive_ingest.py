import gc
import os
from pathlib import Path
from pypdf import PdfReader, PdfWriter
import cognee

def download_pdf_if_not_exists(file_url: str, output_path: str) -> str:
    """Downloads a PDF only if it doesn't already exist on disk."""
    if os.path.exists(output_path):
        print(f"Skipping download: {output_path} already exists.")
        return output_path

    print(f"Downloading file to {output_path}...")
    # Replace this line with your actual gdown / drive download call:
    # gdown.download(file_url, output_path, quiet=False)
    return output_path


async def chunk_and_ingest_pdf(file_path: str, dataset_name: str = "teachings", chunk_size: int = 10):
    """Splits a PDF into 10-page chunks and ingests them sequentially to save RAM."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    reader = PdfReader(file_path)
    total_pages = len(reader.pages)
    base_name = Path(file_path).stem

    print(f"Processing {base_name} ({total_pages} total pages in {chunk_size}-page chunks)")

    for start_page in range(0, total_pages, chunk_size):
        end_page = min(start_page + chunk_size, total_pages)
        writer = PdfWriter()

        # Extract 10-page slice
        for page_num in range(start_page, end_page):
            writer.add_page(reader.pages[page_num])

        chunk_filename = f"{base_name}_part_{start_page + 1}_to_{end_page}.pdf"
        
        # Save temporary mini-PDF
        with open(chunk_filename, "wb") as f:
            writer.write(f)

        try:
            print(f"Ingesting chunk: {chunk_filename}")
            await cognee.add(chunk_filename, dataset_name)
            await cognee.cognify(dataset_name)
        finally:
            # Clean up mini-PDF slice
            if os.path.exists(chunk_filename):
                os.remove(chunk_filename)
            
            # Force RAM cleanup
            gc.collect()

    print(f"Finished ingesting {base_name}")