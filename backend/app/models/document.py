from datetime import datetime, timezone
import uuid

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    document_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )

    storage_filename: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    document_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    processing_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )

    file_type: Mapped[str] = mapped_column(
        String(100),
        nullable=True
    )

    is_supported: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )

    is_readable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )

    page_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    extracted_data: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True
    )

    validation_result: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True
    )

    processing_metadata: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )