import io
from typing import BinaryIO

import fitz
import pytesseract
from PIL import Image


# Keep OCR working images reasonably small.
# The ORIGINAL uploaded file is still preserved.
MAX_IMAGE_DIMENSION = 2200


def extract_text(file: BinaryIO, content_type: str) -> dict:
    """
    Extract text from PDF, JPG, or PNG.

    Native PDFs:
        Extract text directly using PyMuPDF.

    Scanned PDFs:
        Render pages at a controlled resolution and use Tesseract.

    JPG/PNG:
        Resize large images before OCR to reduce memory usage.
    """

    file_bytes = file.read()

    if content_type == "application/pdf":
        return _extract_from_pdf(file_bytes)

    if content_type in {"image/jpeg", "image/png"}:
        return _extract_from_image(file_bytes)

    raise ValueError(
        "Unsupported file type for text extraction."
    )


def _resize_for_ocr(image: Image.Image) -> Image.Image:
    """
    Resize large images while preserving aspect ratio.

    This reduces memory usage on small deployment instances.
    """

    image = image.convert("RGB")

    width, height = image.size

    largest_dimension = max(width, height)

    if largest_dimension <= MAX_IMAGE_DIMENSION:
        return image

    scale = MAX_IMAGE_DIMENSION / largest_dimension

    new_width = max(1, int(width * scale))
    new_height = max(1, int(height * scale))

    return image.resize(
        (new_width, new_height),
        Image.Resampling.LANCZOS,
    )


def _extract_from_pdf(file_bytes: bytes) -> dict:
    document = fitz.open(
        stream=file_bytes,
        filetype="pdf",
    )

    pages = []
    ocr_used = False

    try:
        for page_index in range(len(document)):

            page = document.load_page(page_index)

            # ------------------------------------------------
            # Try native PDF text extraction first
            # ------------------------------------------------

            text = page.get_text("text").strip()

            if text:
                pages.append({
                    "page_number": page_index + 1,
                    "text": text,
                    "ocr_used": False,
                })
                continue

            # ------------------------------------------------
            # No text layer -> OCR
            # ------------------------------------------------

            ocr_used = True

            rect = page.rect

            largest_dimension = max(
                rect.width,
                rect.height,
            )

            # Render at approximately 2200 px maximum.
            scale = min(
                2.0,
                MAX_IMAGE_DIMENSION / largest_dimension,
            )

            pixmap = page.get_pixmap(
                matrix=fitz.Matrix(
                    scale,
                    scale,
                ),
                alpha=False,
            )

            image_bytes = pixmap.tobytes("png")

            image = Image.open(
                io.BytesIO(image_bytes)
            )

            image = _resize_for_ocr(image)

            try:
                text = pytesseract.image_to_string(
                    image
                ).strip()
            finally:
                image.close()

            pages.append({
                "page_number": page_index + 1,
                "text": text,
                "ocr_used": True,
            })

            # Explicitly release the rendered image data.
            del pixmap
            del image_bytes

        full_text = "\n\n".join(
            page["text"]
            for page in pages
        )

        return {
            "text": full_text,
            "pages": pages,
            "ocr_used": ocr_used,
            "page_count": len(document),
        }

    finally:
        document.close()


def _extract_from_image(file_bytes: bytes) -> dict:
    image = Image.open(
        io.BytesIO(file_bytes)
    )

    image = _resize_for_ocr(image)

    try:
        text = pytesseract.image_to_string(
            image
        ).strip()
    finally:
        image.close()

    return {
        "text": text,
        "pages": [
            {
                "page_number": 1,
                "text": text,
                "ocr_used": True,
            }
        ],
        "ocr_used": True,
        "page_count": 1,
    }