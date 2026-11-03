"""
RHD Extractor Module
Extracts high-fidelity clean text from:
1. Native Digital PDFs (English & Devanagari Unicode) via pypdf
2. Scanned / Raster PDF pages via RapidOCR
3. HTML Circulars and Press releases via BeautifulSoup
"""

import os
import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

import pypdf
import pypdfium2 as pdfium
import numpy as np
from bs4 import BeautifulSoup
from rapidocr import RapidOCR

logger = logging.getLogger("rhd_extractor")

# Lazy global OCR engine instance
_OCR_ENGINE: Optional[RapidOCR] = None

def get_ocr_engine() -> RapidOCR:
    global _OCR_ENGINE
    if _OCR_ENGINE is None:
        _OCR_ENGINE = RapidOCR()
    return _OCR_ENGINE


def is_devanagari(text: str) -> bool:
    """Detects Devanagari (Hindi) Unicode range \u0900-\u097F."""
    devanagari_chars = re.findall(r'[\u0900-\u097F]', text)
    return len(devanagari_chars) > 20


def clean_text(text: str) -> str:
    """Normalizes whitespace, line breaks, and hyphenations."""
    if not text:
        return ""
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Merge hyphenated words across lines
    text = re.sub(r'(\b[a-zA-Z]+)-\n([a-zA-Z]+\b)', r'\1\2', text)
    # Collapse multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Remove redundant horizontal spaces
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()


def extract_scanned_page_with_ocr(pdf_path: str, page_index: int) -> str:
    """Renders a PDF page to high-res image and extracts text with RapidOCR."""
    try:
        pdf = pdfium.PdfDocument(pdf_path)
        page = pdf[page_index]
        # Render at 2x scale (~144-200 DPI) for accurate character recognition
        image = page.render(scale=2.0).to_pil()
        ocr = get_ocr_engine()
        output = ocr(np.array(image))
        if output and output.txts:
            return "\n".join(output.txts)
    except Exception as e:
        logger.error(f"OCR failed for {pdf_path} page {page_index + 1}: {e}")
    return ""


def extract_from_pdf(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Extracts each page from PDF using direct text parsing,
    falling back to RapidOCR if page is a scanned bitmap.
    """
    reader = pypdf.PdfReader(pdf_path)
    pages_data = []

    for i, page in enumerate(reader.pages):
        raw_text = page.extract_text() or ""
        cleaned = clean_text(raw_text)

        # If page has fewer than 25 characters, it's almost certainly a scanned raster image
        if len(cleaned) < 25:
            logger.info(f"Page {i + 1} has insufficient digital text ({len(cleaned)} chars). Triggering OCR...")
            ocr_text = extract_scanned_page_with_ocr(pdf_path, i)
            cleaned = clean_text(ocr_text)

        if not cleaned:
            continue

        lang = "hi" if is_devanagari(cleaned) else "en"
        pages_data.append({
            "page_number": i + 1,
            "text": cleaned,
            "language": lang
        })

    return pages_data


def extract_from_html(html_path: str) -> List[Dict[str, Any]]:
    """Extracts clean text from HTML files with page set to None (per Capstone spec)."""
    with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    for tag in soup(["script", "style"]):
        tag.decompose()

    text = soup.get_text(separator="\n\n")
    cleaned = clean_text(text)

    return [{
        "page_number": None,  # Capstone rule: page is null for web pages
        "text": cleaned,
        "language": "hi" if is_devanagari(cleaned) else "en"
    }]


def extract_document(file_path: str) -> List[Dict[str, Any]]:
    """Dispatcher based on extension."""
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        return extract_from_pdf(file_path)
    elif ext in [".html", ".htm"]:
        return extract_from_html(file_path)
    return []
