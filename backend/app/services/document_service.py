from pathlib import Path
from typing import BinaryIO
import shutil
import logging
import time

from sqlalchemy.orm import Session

from app.repositories.document_repository import create_document
from app.services.document_validation_service import validate_document
from app.services.ocr_service import extract_text
from app.services.extraction_service import extract_structured_data
from app.services.financial_validation_service import (
    validate_document_financials,
)


logger = logging.getLogger(__name__)


# ============================================================
# SUPPORTED DOCUMENT TYPES
# ============================================================

SUPPORTED_DOCUMENT_TYPES = {
    "invoice",
    "balance_sheet",
    "profit_and_loss",
    "cash_flow_statement",
}


# ============================================================
# UPLOAD DIRECTORY
# ============================================================

# document_service.py:
#
# backend/
#   app/
#     services/
#       document_service.py
#
# parents[2] = backend/

BASE_DIR = Path(__file__).resolve().parents[2]

UPLOAD_DIR = BASE_DIR / "uploads"

UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# SAVE UPLOADED FILE
# ============================================================

def save_uploaded_file(
    file: BinaryIO,
    filename: str,
) -> Path:
    """
    Save the original uploaded document.

    The original file is preserved so that it can
    be accessed later by the frontend.
    """

    if not filename:
        raise ValueError(
            "Uploaded file has no filename."
        )

    # --------------------------------------------------------
    # Secure filename
    # --------------------------------------------------------

    safe_filename = Path(filename).name

    if not safe_filename:
        raise ValueError(
            "Invalid uploaded filename."
        )

    # --------------------------------------------------------
    # Allowed extensions
    # --------------------------------------------------------

    allowed_extensions = {
        ".pdf",
        ".jpg",
        ".jpeg",
        ".png",
    }

    extension = Path(
        safe_filename
    ).suffix.lower()

    if extension not in allowed_extensions:
        raise ValueError(
            "Only PDF, JPG and PNG documents are supported."
        )

    # --------------------------------------------------------
    # Destination
    # --------------------------------------------------------

    destination = UPLOAD_DIR / safe_filename

    # --------------------------------------------------------
    # Reset file position
    # --------------------------------------------------------

    file.seek(0)

    # --------------------------------------------------------
    # Save file
    # --------------------------------------------------------

    with open(
        destination,
        "wb",
    ) as output_file:

        shutil.copyfileobj(
            file,
            output_file,
        )

    # --------------------------------------------------------
    # Verify saved file
    # --------------------------------------------------------

    if not destination.exists():
        raise IOError(
            "Uploaded file could not be saved."
        )

    if destination.stat().st_size == 0:

        destination.unlink(
            missing_ok=True
        )

        raise IOError(
            "Uploaded file was saved as an empty file."
        )

    logger.info(
        "File saved successfully: %s (%d bytes)",
        destination.name,
        destination.stat().st_size,
    )

    return destination


# ============================================================
# PROCESS DOCUMENT
# ============================================================

def process_document(
    db: Session,
    file: BinaryIO,
    filename: str,
    content_type: str | None,
    document_type: str,
) -> dict:
    """
    Complete document-processing pipeline.

    Flow:

        Upload
            ↓
        File validation
            ↓
        Save original file
            ↓
        OCR / text extraction
            ↓
        Gemini structured extraction
            ↓
        Financial validation
            ↓
        Database persistence
            ↓
        JSON response
    """

    start_time = time.time()

    logger.info(
        "Processing started: filename=%s document_type=%s content_type=%s",
        filename,
        document_type,
        content_type,
    )

    try:

        # ====================================================
        # 1. VALIDATE DOCUMENT TYPE
        # ====================================================

        if document_type not in SUPPORTED_DOCUMENT_TYPES:

            logger.warning(
                "Unsupported document type: %s",
                document_type,
            )

            raise ValueError(
                f"Unsupported document type: {document_type}"
            )

        # ====================================================
        # 2. BASIC FILE VALIDATION
        # ====================================================

        logger.info(
            "Stage 1: validating document: %s",
            filename,
        )

        validation = validate_document(
            file=file,
            filename=filename,
            content_type=content_type,
        )

        logger.info(
            "Stage 1 complete: supported=%s readable=%s pages=%s",
            validation.get("is_supported"),
            validation.get("is_readable"),
            validation.get("page_count"),
        )

        # ====================================================
        # 3. RESET FILE POINTER
        # ====================================================

        file.seek(0)

        # ====================================================
        # 4. SAVE ORIGINAL FILE
        # ====================================================

        logger.info(
            "Stage 2: saving original file: %s",
            filename,
        )

        saved_file = save_uploaded_file(
            file=file,
            filename=filename,
        )

        logger.info(
            "Stage 2 complete: file saved to %s",
            saved_file,
        )

        # ====================================================
        # 5. RESET FILE POINTER
        # ====================================================

        file.seek(0)

        # ====================================================
        # 6. OCR / TEXT EXTRACTION
        # ====================================================

        logger.info(
            "Stage 3: starting OCR/text extraction: %s",
            filename,
        )

        ocr_result = extract_text(
            file=file,
            content_type=content_type,
        )

        logger.info(
            "Stage 3 complete: OCR finished | ocr_used=%s | pages=%s | text_length=%s",
            ocr_result.get("ocr_used"),
            ocr_result.get("page_count"),
            len(ocr_result.get("text", "")),
        )

        # ====================================================
        # 7. STRUCTURED AI EXTRACTION
        # ====================================================

        logger.info(
            "Stage 4: starting Gemini extraction: %s",
            filename,
        )

        extracted_data = extract_structured_data(
            document_type=document_type,
            ocr_result=ocr_result,
        )

        logger.info(
            "Stage 4 complete: Gemini extraction finished | fields=%s | tables=%s",
            len(extracted_data.get("fields", [])),
            len(extracted_data.get("tables", [])),
        )

        # ====================================================
        # 8. FINANCIAL VALIDATION
        # ====================================================

        logger.info(
            "Stage 5: starting financial validation: %s",
            filename,
        )

        validation_result = validate_document_financials(
            document_type=document_type,
            extracted_data=extracted_data,
        )

        logger.info(
            "Stage 5 complete: financial validation=%s",
            validation_result.get("overall_status"),
        )

        # ====================================================
        # 9. FINAL PROCESSING STATUS
        # ====================================================

        final_status = validation_result[
            "overall_status"
        ]

        # ====================================================
        # 10. SAVE RESULT TO DATABASE
        # ====================================================

        logger.info(
            "Stage 6: saving result to database: %s",
            filename,
        )

        document = create_document(
            db=db,

            document_name=filename,

            document_type=document_type,

            processing_status=final_status,

            file_type=content_type,

            is_supported=validation[
                "is_supported"
            ],

            is_readable=validation[
                "is_readable"
            ],

            page_count=validation[
                "page_count"
            ],

            extracted_data=extracted_data,

            validation_result=validation_result,

            processing_metadata={
                "ocr_used": ocr_result[
                    "ocr_used"
                ],

                "page_count": ocr_result[
                    "page_count"
                ],

                "saved_file": str(
                    saved_file
                ),
            },
        )

        logger.info(
            "Stage 6 complete: database save successful | document_id=%s",
            document.id,
        )

        # ====================================================
        # 11. PROCESSING COMPLETE
        # ====================================================

        duration = time.time() - start_time

        logger.info(
            "Processing completed successfully | filename=%s | duration=%.2fs",
            filename,
            duration,
        )

        # ====================================================
        # 12. RETURN API RESPONSE
        # ====================================================

        return {

            "document": {

                "id": str(
                    document.id
                ),

                "document_name":
                    document.document_name,

                "document_type":
                    document.document_type,

                "processing_status":
                    document.processing_status,
            },

            "validation": {

                "file_type":
                    validation[
                        "file_type"
                    ],

                "is_supported":
                    validation[
                        "is_supported"
                    ],

                "is_readable":
                    validation[
                        "is_readable"
                    ],

                "page_count":
                    validation[
                        "page_count"
                    ],
            },

            "extracted_data":
                extracted_data,

            "financial_validation":
                validation_result,

            "processing_metadata": {

                "ocr_used":
                    ocr_result[
                        "ocr_used"
                    ],

                "page_count":
                    ocr_result[
                        "page_count"
                    ],

                "saved_file":
                    str(saved_file),
            },
        }

    except Exception as exc:

        # ====================================================
        # CONTROLLED ERROR LOGGING
        # ====================================================

        duration = time.time() - start_time

        logger.exception(
            "Document processing failed | filename=%s | duration=%.2fs | error=%s",
            filename,
            duration,
            str(exc),
        )

        # Re-raise so the API route can convert the
        # exception into the appropriate HTTP response.
        raise