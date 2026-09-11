from sqlalchemy.orm import Session

from app.models.document import Document


def create_document(
    db: Session,
    document_name: str,
    document_type: str,
    processing_status: str,
    storage_filename: str | None = None,
    file_type: str | None = None,
    is_supported: bool = False,
    is_readable: bool = False,
    page_count: int | None = None,
    extracted_data: dict | None = None,
    validation_result: dict | None = None,
    processing_metadata: dict | None = None,
    error_message: str | None = None,
) -> Document:

    document = Document(
        document_name=document_name,
        document_type=document_type,
        storage_filename=storage_filename,
        processing_status=processing_status,
        file_type=file_type,
        is_supported=is_supported,
        is_readable=is_readable,
        page_count=page_count,
        extracted_data=extracted_data,
        validation_result=validation_result,
        processing_metadata=processing_metadata,
        error_message=error_message,
    )

    db.add(document)

    db.commit()

    db.refresh(document)

    return document


def get_document_by_name(
    db: Session,
    document_name: str,
) -> Document | None:

    return (
        db.query(Document)
        .filter(
            Document.document_name == document_name
        )
        .order_by(
            Document.created_at.desc()
        )
        .first()
    )


def get_all_documents(
    db: Session,
) -> list[Document]:

    return (
        db.query(Document)
        .order_by(
            Document.created_at.desc()
        )
        .all()
    )