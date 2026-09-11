from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)

from fastapi.responses import FileResponse

from sqlalchemy.orm import Session

from app.core.database import get_db

from app.repositories.document_repository import (
    get_all_documents,
    get_document_by_name,
)

from app.services.document_service import (
    process_document,
)

from app.services.document_validation_service import (
    DocumentValidationError,
)

from app.services.extraction_service import (
    GeminiQuotaError,
    GeminiServiceError,
)


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/api/v1/documents",
    tags=["Documents"],
)


# ============================================================
# POST /api/v1/documents/process
# ============================================================

@router.post("/process")
def process_document_endpoint(
    file: UploadFile = File(...),
    document_type: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Upload and process a financial document.

    Flow:

    Upload
        ↓
    File validation
        ↓
    Save original file
        ↓
    OCR
        ↓
    Gemini extraction
        ↓
    Financial validation
        ↓
    Supabase persistence
        ↓
    JSON response
    """

    try:

        # ----------------------------------------------------
        # Validate filename
        # ----------------------------------------------------

        if not file.filename:

            raise HTTPException(
                status_code=400,
                detail={
                    "code": "INVALID_FILENAME",
                    "message": (
                        "Uploaded file has no filename."
                    ),
                },
            )

        # ----------------------------------------------------
        # Process document
        # ----------------------------------------------------

        result = process_document(
            db=db,
            file=file.file,
            filename=file.filename,
            content_type=file.content_type,
            document_type=document_type,
        )

        return result

    # ========================================================
    # FILE VALIDATION ERROR
    # ========================================================

    except DocumentValidationError as exc:

        raise HTTPException(
            status_code=400,
            detail={
                "code": exc.code,
                "message": exc.message,
            },
        )

    # ========================================================
    # INVALID REQUEST
    # ========================================================

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_REQUEST",
                "message": str(exc),
            },
        )

    # ========================================================
    # GEMINI QUOTA ERROR
    # ========================================================

    except GeminiQuotaError as exc:

        print(
            "Gemini quota error:",
            exc.message,
        )

        raise HTTPException(
            status_code=429,
            detail={
                "code": "AI_QUOTA_EXCEEDED",
                "message": exc.message,
            },
        )

    # ========================================================
    # GEMINI SERVICE ERROR
    # ========================================================

    except GeminiServiceError as exc:

        print(
            "Gemini service error:",
            exc.message,
        )

        raise HTTPException(
            status_code=503,
            detail={
                "code": "AI_SERVICE_UNAVAILABLE",
                "message": exc.message,
            },
        )

    # ========================================================
    # HTTP EXCEPTION
    # ========================================================

    except HTTPException:

        raise

    # ========================================================
    # UNEXPECTED ERROR
    # ========================================================

    except Exception as exc:

        print(
            "Document processing error:",
            exc,
        )

        raise HTTPException(
            status_code=500,
            detail={
                "code": "PROCESSING_ERROR",
                "message": (
                    "An unexpected error occurred "
                    "while processing the document."
                ),
            },
        )


# ============================================================
# GET /api/v1/documents
# ============================================================

@router.get("")
def list_documents(
    db: Session = Depends(get_db),
):
    """
    Return all processed documents.
    """

    documents = get_all_documents(db)

    return {
        "count": len(documents),
        "documents": [
            {
                "id": str(document.id),
                "document_name": document.document_name,
                "document_type": document.document_type,
                "processing_status": document.processing_status,
                "file_type": document.file_type,
                "is_supported": document.is_supported,
                "is_readable": document.is_readable,
                "page_count": document.page_count,
                "ocr_used": (
                    document.processing_metadata.get("ocr_used")
                    if document.processing_metadata
                    else None
                ),
                "created_at": document.created_at,
            }
            for document in documents
        ],
    }


# ============================================================
# GET /api/v1/documents/{document_name}/file
# ============================================================

@router.get("/{document_name}/file")
def get_document_file(
    document_name: str,
    db: Session = Depends(get_db),
):
    """
    Return the original uploaded document.

    PDF:
        Opens inside browser PDF viewer.

    JPG/JPEG/PNG:
        Displays directly inside browser.

    content_disposition_type="inline"
    prevents automatic downloading.
    """

    # --------------------------------------------------------
    # Find database record
    # --------------------------------------------------------

    document = get_document_by_name(
        db,
        document_name,
    )

    if document is None:

        raise HTTPException(
            status_code=404,
            detail={
                "code": "DOCUMENT_NOT_FOUND",
                "message": "Document not found.",
            },
        )

    # --------------------------------------------------------
    # Upload directory
    # --------------------------------------------------------

    upload_directory = (
        Path(__file__)
        .resolve()
        .parents[3]
        / "uploads"
    )

    upload_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # Safe filename
    # --------------------------------------------------------

    safe_filename = Path(
        document.document_name
    ).name

    if not safe_filename:

        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_FILE_PATH",
                "message": "Invalid document path.",
            },
        )

    requested_path = (
        upload_directory
        / safe_filename
    )

    # --------------------------------------------------------
    # Security check
    # --------------------------------------------------------

    try:

        upload_directory_resolved = (
            upload_directory.resolve()
        )

        file_path = (
            requested_path.resolve()
        )

        file_path.relative_to(
            upload_directory_resolved
        )

    except ValueError:

        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_FILE_PATH",
                "message": "Invalid document path.",
            },
        )

    # --------------------------------------------------------
    # Check original file
    # --------------------------------------------------------

    if not file_path.exists():

        raise HTTPException(
            status_code=404,
            detail={
                "code": "FILE_NOT_FOUND",
                "message": (
                    "The original uploaded file "
                    "is not available."
                ),
            },
        )

    if not file_path.is_file():

        raise HTTPException(
            status_code=404,
            detail={
                "code": "FILE_NOT_FOUND",
                "message": (
                    "The requested document "
                    "file is not available."
                ),
            },
        )

    # --------------------------------------------------------
    # Determine MIME type
    # --------------------------------------------------------

    media_type = (
        document.file_type
    )

    if not media_type:

        suffix = (
            file_path
            .suffix
            .lower()
        )

        if suffix == ".pdf":

            media_type = (
                "application/pdf"
            )

        elif suffix in {
            ".jpg",
            ".jpeg",
        }:

            media_type = (
                "image/jpeg"
            )

        elif suffix == ".png":

            media_type = (
                "image/png"
            )

        else:

            media_type = (
                "application/octet-stream"
            )

    # --------------------------------------------------------
    # Return original file INLINE
    # --------------------------------------------------------

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=document.document_name,
        content_disposition_type="inline",
    )


# ============================================================
# GET /api/v1/documents/{document_name}
# ============================================================

@router.get("/{document_name}")
def get_document(
    document_name: str,
    db: Session = Depends(get_db),
):
    """
    Return a single processed document.

    Includes:

    - metadata
    - extracted fields
    - extracted tables
    - financial validation
    - processing metadata
    - error message
    """

    document = get_document_by_name(
        db,
        document_name,
    )

    if document is None:

        raise HTTPException(
            status_code=404,
            detail={
                "code": "DOCUMENT_NOT_FOUND",
                "message": "Document not found.",
            },
        )

    return {
        "document": {
            "id": str(document.id),
            "document_name": document.document_name,
            "document_type": document.document_type,
            "processing_status": document.processing_status,
            "file_type": document.file_type,
            "is_supported": document.is_supported,
            "is_readable": document.is_readable,
            "page_count": document.page_count,
            "created_at": document.created_at,
            "updated_at": document.updated_at,
        },
        "extracted_data": document.extracted_data,
        "financial_validation": document.validation_result,
        "processing_metadata": document.processing_metadata,
        "error_message": document.error_message,
    }