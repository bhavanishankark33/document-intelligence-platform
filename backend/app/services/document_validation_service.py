import io
from typing import BinaryIO

import fitz
from PIL import Image


SUPPORTED_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
}

MAX_PDF_PAGES = 3


class DocumentValidationError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def validate_document(
    file: BinaryIO,
    filename: str,
    content_type: str | None
) -> dict:

    # Read file contents
    file_bytes = file.read()

    # Empty file check
    if not file_bytes:
        raise DocumentValidationError(
            "EMPTY_FILE",
            "The uploaded file is empty."
        )

    # File type check
    if content_type not in SUPPORTED_TYPES:
        raise DocumentValidationError(
            "UNSUPPORTED_FILE_TYPE",
            "Only PDF / JPG / PNG documents are supported."
        )

    # PDF validation
    if content_type == "application/pdf":
        return _validate_pdf(file_bytes, content_type)

    # Image validation
    return _validate_image(file_bytes, content_type)


def _validate_pdf(
    file_bytes: bytes,
    content_type: str
) -> dict:

    try:
        document = fitz.open(
            stream=file_bytes,
            filetype="pdf"
        )

        page_count = len(document)

        if page_count == 0:
            document.close()

            raise DocumentValidationError(
                "INVALID_DOCUMENT",
                "The PDF contains no pages."
            )

        if page_count > MAX_PDF_PAGES:
            document.close()

            raise DocumentValidationError(
                "PAGE_LIMIT_EXCEEDED",
                "Documents must contain no more than 3 pages."
            )

        # Try accessing every page to ensure the PDF is readable
        for page_number in range(page_count):
            document.load_page(page_number)

        document.close()

        return {
            "file_type": content_type,
            "is_supported": True,
            "is_readable": True,
            "page_count": page_count,
            "status": "PASS",
        }

    except DocumentValidationError:
        raise

    except Exception:
        raise DocumentValidationError(
            "CORRUPTED_FILE",
            "The PDF is corrupted or cannot be read."
        )


def _validate_image(
    file_bytes: bytes,
    content_type: str
) -> dict:

    try:
        image = Image.open(io.BytesIO(file_bytes))

        # Force PIL to verify the image
        image.verify()

        # Re-open because verify() invalidates the image object
        image = Image.open(io.BytesIO(file_bytes))

        width, height = image.size

        if width <= 0 or height <= 0:
            raise DocumentValidationError(
                "INVALID_DOCUMENT",
                "The image has invalid dimensions."
            )

        return {
            "file_type": content_type,
            "is_supported": True,
            "is_readable": True,
            "page_count": 1,
            "status": "PASS",
        }

    except DocumentValidationError:
        raise

    except Exception:
        raise DocumentValidationError(
            "CORRUPTED_FILE",
            "The image is corrupted or cannot be read."
        )