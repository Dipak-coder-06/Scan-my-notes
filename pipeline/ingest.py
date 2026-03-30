"""
pipeline/ingest.py
------------------
Handles PDF → OCR → structured word objects with (x, y) coordinates and page numbers.
Uses Google Cloud Vision API for high-accuracy handwriting recognition.
"""
import os
import io
from pathlib import Path
from typing import List, Dict, Any

import fitz  # PyMuPDF
from google.cloud import vision
from dotenv import load_dotenv

load_dotenv()


def _get_vision_client() -> vision.ImageAnnotatorClient:
    """Initialize and return Google Vision client with clear credential validation."""
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")

    # Catch the common mistake of leaving the placeholder value
    placeholder_values = {"", "path/to/your/service-account-key.json", "path/to/your-key.json"}
    if creds_path in placeholder_values:
        raise RuntimeError(
            "Google Cloud credentials are not configured.\n"
            "→ In the Streamlit sidebar, open '🔑 Google Vision Credentials' "
            "and upload your service account JSON key file."
        )

    if creds_path and Path(creds_path).exists():
        return vision.ImageAnnotatorClient.from_service_account_file(creds_path)

    if creds_path and not Path(creds_path).exists():
        raise RuntimeError(
            f"GCP credentials file not found at: {creds_path}\n"
            "→ Upload your service account JSON key in the '🔑 Google Vision Credentials' sidebar panel."
        )

    # Falls back to Application Default Credentials (gcloud auth login)
    return vision.ImageAnnotatorClient()


def _ocr_page(client: vision.ImageAnnotatorClient, page_image_bytes: bytes, page_num: int) -> List[Dict[str, Any]]:
    """
    Run Google Vision document_text_detection on a single page image.
    Returns a list of word-level objects with text, page, bounding box.
    """
    image = vision.Image(content=page_image_bytes)
    response = client.document_text_detection(image=image)

    words = []
    if response.error.message:
        raise RuntimeError(f"OCR error on page {page_num}: {response.error.message}")

    for page in response.full_text_annotation.pages:
        for block in page.blocks:
            for paragraph in block.paragraphs:
                for word in paragraph.words:
                    word_text = "".join([
                        symbol.text for symbol in word.symbols
                    ])
                    vertices = word.bounding_box.vertices
                    # Normalize bounding box: (x, y, width, height) in pixels
                    xs = [v.x for v in vertices]
                    ys = [v.y for v in vertices]
                    bbox = {
                        "x": min(xs),
                        "y": min(ys),
                        "w": max(xs) - min(xs),
                        "h": max(ys) - min(ys),
                    }
                    words.append({
                        "text": word_text,
                        "page": page_num,
                        "bbox": bbox,
                        "confidence": word.confidence,
                    })
    return words


def _pdf_page_to_image(pdf_path: str, page_idx: int, dpi: int = 200) -> bytes:
    """Render a PDF page to a PNG image (bytes) at the specified DPI."""
    doc = fitz.open(pdf_path)
    page = doc[page_idx]
    matrix = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=matrix, colorspace=fitz.csRGB)
    doc.close()
    return pix.tobytes("png")


def ingest_pdf(pdf_path: str, progress_callback=None) -> List[Dict[str, Any]]:
    """
    Main ingestion function.

    Args:
        pdf_path: Path to the handwritten PDF file.
        progress_callback: Optional callable(current, total) for progress updates.

    Returns:
        List of word objects: [{text, page, bbox, confidence}, ...]
    """
    client = _get_vision_client()
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    doc.close()

    all_words: List[Dict[str, Any]] = []

    for page_idx in range(total_pages):
        page_num = page_idx + 1  # 1-indexed
        img_bytes = _pdf_page_to_image(pdf_path, page_idx)
        page_words = _ocr_page(client, img_bytes, page_num)
        all_words.extend(page_words)

        if progress_callback:
            progress_callback(page_idx + 1, total_pages)

    return all_words
