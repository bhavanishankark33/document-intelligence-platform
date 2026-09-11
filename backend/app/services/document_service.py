from pathlib import Path
from typing import BinaryIO
import shutil

from sqlalchemy.orm import Session

from app.repositories.document_repository import (
    create_document,
)

from app.services.document_validation_service import (
    validate_document,
)

from app.services.ocr_service import (
    extract_text,
)

from app.services.extraction_service import (
    extract_structured_data,
)

from app.services.financial_validation_service import (
    validate_document_financials,
)


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

# document_service.py is located at:
#
# backend/
#   app/
#     services/
#       document_service.py
#
# parents[2] = backend/

BASE_DIR = Path(
    __file__
).resolve().parents[2]


UPLOAD_DIR = (
    BASE_DIR / "uploads"
)


# Make sure the directory exists.

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
    Save the original uploaded document
    into backend/uploads/.

    The original file is preserved so that
    the frontend can display it later.
    """

    if not filename:
        raise ValueError(
            "Uploaded file has no filename."
        )

    # --------------------------------------------------------
    # Security:
    # only keep the actual filename.
    #
    # Example:
    #
    # ../../secret.pdf
    #
    # becomes:
    #
    # secret.pdf
    # --------------------------------------------------------

    safe_filename = Path(
        filename
    ).name


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


    extension = (
        Path(safe_filename)
        .suffix
        .lower()
    )


    if extension not in allowed_extensions:

        raise ValueError(
            "Only PDF, JPG and PNG "
            "documents are supported."
        )


    # --------------------------------------------------------
    # Final path
    # --------------------------------------------------------

    destination = (
        UPLOAD_DIR /
        safe_filename
    )


    # --------------------------------------------------------
    # Reset file position
    # --------------------------------------------------------

    file.seek(0)


    # --------------------------------------------------------
    # Save binary file
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
    # Verify that file was actually saved
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
    Supabase persistence
        ↓
    JSON response
    """

    # ========================================================
    # 1. VALIDATE DOCUMENT TYPE
    # ========================================================

    if document_type not in SUPPORTED_DOCUMENT_TYPES:

        raise ValueError(
            f"Unsupported document type: "
            f"{document_type}"
        )


    # ========================================================
    # 2. BASIC FILE VALIDATION
    # ========================================================

    validation = validate_document(
        file=file,
        filename=filename,
        content_type=content_type,
    )


    # ========================================================
    # 3. RESET FILE POINTER
    # ========================================================

    file.seek(0)


    # ========================================================
    # 4. SAVE ORIGINAL FILE
    # ========================================================

    saved_file = save_uploaded_file(
        file=file,
        filename=filename,
    )


    # ========================================================
    # 5. RESET FILE POINTER AGAIN
    # ========================================================

    file.seek(0)


    # ========================================================
    # 6. OCR / TEXT EXTRACTION
    # ========================================================

    ocr_result = extract_text(
        file=file,
        content_type=content_type,
    )


    # ========================================================
    # 7. STRUCTURED AI EXTRACTION
    # ========================================================

    extracted_data = extract_structured_data(
        document_type=document_type,
        ocr_result=ocr_result,
    )


    # ========================================================
    # 8. DETERMINISTIC FINANCIAL VALIDATION
    # ========================================================

    validation_result = (
        validate_document_financials(
            document_type=document_type,
            extracted_data=extracted_data,
        )
    )


    # ========================================================
    # 9. FINAL PROCESSING STATUS
    # ========================================================

    final_status = (
        validation_result[
            "overall_status"
        ]
    )


    # ========================================================
    # 10. SAVE RESULT TO DATABASE
    # ========================================================

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
    )


    # ========================================================
    # 11. RETURN API RESPONSE
    # ========================================================

    return {

        "document": {

            "id":
                str(document.id),

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