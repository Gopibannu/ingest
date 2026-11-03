"""
RHD Ingestion Pipeline Runner
Processes all PDFs and HTML documents in the `documents/` directory,
extracts English and Hindi text, generates semantic chunks,
and saves `final_chunks.json` for teammate 2 (ChromaDB insertion).
"""

import os
import sys
import json
import logging
from pathlib import Path

# Add current folder to sys.path so standalone execution works
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

try:
    from .extractor import extract_document
    from .chunker import build_chunks
except ImportError:
    from extractor import extract_document
    from chunker import build_chunks

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("rhd_ingestion")


def find_documents_dir() -> Path:
    """Finds documents directory whether run inside parent project or standalone cloned repo."""
    candidates = [
        CURRENT_DIR.parent / "documents",
        CURRENT_DIR / "documents",
        CURRENT_DIR.parent / "data",
        CURRENT_DIR / "data",
    ]
    for c in candidates:
        if c.exists() and any(c.glob("*.*")):
            return c
    # Fallback default
    return CURRENT_DIR.parent / "documents"


def run():
    documents_dir = find_documents_dir()
    output_dir = CURRENT_DIR / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "final_chunks.json"

    logger.info(f"Scanning documents in: {documents_dir}")
    doc_paths = sorted(list(documents_dir.glob("*.*")))

    total_chunks = []
    hindi_count = 0
    english_count = 0

    for path in doc_paths:
        if path.suffix.lower() not in [".pdf", ".html", ".htm"]:
            continue

        filename = path.name
        logger.info(f"Processing: {filename}")

        pages_data = extract_document(str(path))
        if not pages_data:
            logger.warning(f"No text extracted from {filename} (might be scanned raster image).")
            continue

        file_chunks = build_chunks(pages_data, source_filename=filename, chunk_size=650, chunk_overlap=120)

        for ch in file_chunks:
            if ch["metadata"]["language"] == "hi":
                hindi_count += 1
            else:
                english_count += 1

        total_chunks.extend(file_chunks)
        logger.info(f"  -> Generated {len(file_chunks)} chunks from {filename}")

    # Save to final JSON
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(total_chunks, f, ensure_ascii=False, indent=2)

    logger.info("=" * 50)
    logger.info(f"SUCCESS: Ingestion complete!")
    logger.info(f"Total Chunks Generated: {len(total_chunks)}")
    logger.info(f"  - English Chunks: {english_count}")
    logger.info(f"  - Hindi Chunks:   {hindi_count}")
    logger.info(f"Saved final chunks to: {output_file}")
    logger.info("=" * 50)


if __name__ == "__main__":
    run()
