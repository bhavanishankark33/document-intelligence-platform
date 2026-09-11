import io
from typing import BinaryIO

import fitz
import pytesseract
from PIL import Image


def extract_text(file: BinaryIO, content_type: str) -> dict:
    """
    Extract text from PDF, JPG, or PNG.

    Native PDFs:
        Extract text directly using PyMuPDF.

    Scanned PDFs:
        Render each page as an image and use Tesseract OCR.

    JPG/PNG:
        Use Tesseract OCR directly.
    """

    file_bytes = file.read()

    if content_type == "application/pdf":
        return _extract_from_pdf(file_bytes)

    if content_type in {"image/jpeg", "image/png"}:
        return _extract_from_image(file_bytes)

    raise ValueError(
        "Unsupported file type for text extraction."
    )


def _extract_from_pdf(file_bytes: bytes) -> dict:
    document = fitz.open(
        stream=file_bytes,
        filetype="pdf"
    )

    pages = []
    ocr_used = False

    try:
        for page_index in range(len(document)):
            page = document.load_page(page_index)

            # Try native PDF text extraction first
            text = page.get_text("text").strip()

            if text:
                pages.append({
                    "page_number": page_index + 1,
                    "text": text,
                    "ocr_used": False
                })
                continue

            # No text layer → OCR the page
            ocr_used = True

            pixmap = page.get_pixmap(
                matrix=fitz.Matrix(2, 2),
                alpha=False
            )

            image_bytes = pixmap.tobytes("png")

            image = Image.open(
                io.BytesIO(image_bytes)
            )

            text = pytesseract.image_to_string(
                image
            ).strip()

            pages.append({
                "page_number": page_index + 1,
                "text": text,
                "ocr_used": True
            })

        full_text = "\n\n".join(
            page["text"]
            for page in pages
        )

        return {
            "text": full_text,
            "pages": pages,
            "ocr_used": ocr_used,
            "page_count": len(document)
        }

    finally:
        document.close()


def _extract_from_image(file_bytes: bytes) -> dict:
    image = Image.open(
        io.BytesIO(file_bytes)
    )

    text = pytesseract.image_to_string(
        image
    ).strip()

    return {
        "text": text,
        "pages": [
            {
                "page_number": 1,
                "text": text,
                "ocr_used": True
            }
        ],
        "ocr_used": True,
        "page_count": 1
    }