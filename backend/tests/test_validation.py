import io

import fitz
import pytest
from PIL import Image

from app.services.document_validation_service import (
    DocumentValidationError,
    validate_document,
)


def create_test_pdf(page_count=1):
    pdf = fitz.open()

    for _ in range(page_count):
        pdf.new_page()

    pdf_bytes = pdf.tobytes()
    pdf.close()

    return pdf_bytes


def create_test_image():
    image = Image.new("RGB", (100, 100), "white")

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")

    return buffer.getvalue()


def test_valid_pdf():
    pdf_bytes = create_test_pdf(1)

    result = validate_document(
        io.BytesIO(pdf_bytes),
        "test.pdf",
        "application/pdf"
    )

    assert result["is_supported"] is True
    assert result["is_readable"] is True
    assert result["page_count"] == 1
    assert result["status"] == "PASS"


def test_pdf_page_limit():
    pdf_bytes = create_test_pdf(4)

    with pytest.raises(DocumentValidationError) as error:
        validate_document(
            io.BytesIO(pdf_bytes),
            "test.pdf",
            "application/pdf"
        )

    assert error.value.code == "PAGE_LIMIT_EXCEEDED"


def test_valid_png():
    image_bytes = create_test_image()

    result = validate_document(
        io.BytesIO(image_bytes),
        "test.png",
        "image/png"
    )

    assert result["is_supported"] is True
    assert result["is_readable"] is True
    assert result["page_count"] == 1
    assert result["status"] == "PASS"


def test_unsupported_file():
    with pytest.raises(DocumentValidationError) as error:
        validate_document(
            io.BytesIO(b"some text"),
            "test.txt",
            "text/plain"
        )

    assert error.value.code == "UNSUPPORTED_FILE_TYPE"


def test_empty_file():
    with pytest.raises(DocumentValidationError) as error:
        validate_document(
            io.BytesIO(b""),
            "empty.pdf",
            "application/pdf"
        )

    assert error.value.code == "EMPTY_FILE"


def test_corrupted_pdf():
    with pytest.raises(DocumentValidationError) as error:
        validate_document(
            io.BytesIO(b"This is not a real PDF"),
            "corrupt.pdf",
            "application/pdf"
        )

    assert error.value.code == "CORRUPTED_FILE"


def test_profit_and_loss_validation_failure():
    from app.services.financial_validation_service import (
        validate_profit_and_loss,
    )

    extracted_data = {
        "fields": [
            {
                "field_name": "total_income",
                "value": "861489858",
            },
            {
                "field_name": "total_expenditure",
                "value": "708615836",
            },
            {
                "field_name": "net_profit_for_the_year",
                "value": "999999999",
            },
        ]
    }

    result = validate_profit_and_loss(
        extracted_data
    )

    assert result["overall_status"] == "FAIL"
    assert result["checks"][0]["status"] == "FAIL"
    assert result["checks"][0]["calculated_value"] == 152874022.0
    assert result["checks"][0]["reported_value"] == 999999999.0