import json
from typing import Optional

from google import genai
from google.genai import types
from pydantic import BaseModel

from app.core.config import settings


# ============================================================
# GEMINI CLIENT
# ============================================================

client = genai.Client(
    api_key=settings.GEMINI_API_KEY
)


# ============================================================
# CUSTOM GEMINI ERRORS
# ============================================================

class GeminiQuotaError(Exception):
    """
    Raised when the Gemini API quota/rate limit
    has been exceeded.
    """

    def __init__(
        self,
        message: str,
    ):
        self.message = message
        super().__init__(message)


class GeminiServiceError(Exception):
    """
    Raised when Gemini is unavailable for another
    service-level reason.
    """

    def __init__(
        self,
        message: str,
    ):
        self.message = message
        super().__init__(message)


# ============================================================
# STRUCTURED OUTPUT MODELS
# ============================================================

class ExtractedField(BaseModel):
    field_name: str
    value: Optional[str] = None
    evidence: Optional[str] = None
    page_number: Optional[int] = None


class ExtractedTable(BaseModel):
    table_name: str
    headers: list[str]
    rows: list[list[Optional[str]]]
    page_number: Optional[int] = None


class ExtractionResult(BaseModel):
    document_type: str
    fields: list[ExtractedField]
    tables: list[ExtractedTable]


# ============================================================
# DOCUMENT PROMPTS
# ============================================================

DOCUMENT_PROMPTS = {

    "invoice": """
Extract all meaningful visible information from this invoice.

Look for:
- invoice number
- invoice date
- seller/vendor
- buyer/customer
- address
- tax/GST number
- currency
- line items
- quantities
- unit prices
- line totals
- subtotal
- tax
- total
- payment information
- any other meaningful visible information

Extract every meaningful field that is actually visible.
""",

    "balance_sheet": """
Extract all meaningful visible information from this balance sheet.

Look for:
- reporting date
- comparative date
- company name
- unit of measurement
- capital
- reserves
- minority interest
- deposits
- borrowings
- liabilities
- assets
- cash
- balances with banks
- investments
- advances
- fixed assets
- other assets
- total assets
- total capital and liabilities
- contingent liabilities
- bills for collection
- all other visible financial line items

Extract every meaningful financial line item that is actually visible.
""",

    "profit_and_loss": """
Extract all meaningful visible information from this profit and loss statement.

Look for:
- company name
- reporting period
- currency or unit
- interest earned
- other income
- total income
- interest expended
- operating expenses
- provisions
- total expenditure
- net profit
- consolidated profit
- earnings per share
- taxes
- exceptional items
- all other meaningful visible financial line items

Extract every meaningful financial line item that is actually visible.
""",

    "cash_flow_statement": """
Extract all meaningful visible information from this cash flow statement.

Look for:
- company name
- reporting period
- currency or unit
- cash flow from operating activities
- cash flow from investing activities
- cash flow from financing activities
- net increase/decrease in cash
- opening cash balance
- closing cash balance
- all other meaningful visible financial line items

Extract every meaningful financial line item that is actually visible.
""",
}


# ============================================================
# STRUCTURED EXTRACTION
# ============================================================

def extract_structured_data(
    document_type: str,
    ocr_result: dict,
) -> dict:
    """
    Send OCR text to Gemini and return structured
    financial document data.
    """

    # --------------------------------------------------------
    # Validate document type
    # --------------------------------------------------------

    if document_type not in DOCUMENT_PROMPTS:

        raise ValueError(
            f"Unsupported document type: "
            f"{document_type}"
        )


    # --------------------------------------------------------
    # Build extraction prompt
    # --------------------------------------------------------

    prompt = f"""
You are a financial document extraction system.

Document type:
{document_type}

Task:
{DOCUMENT_PROMPTS[document_type]}

IMPORTANT RULES:

1. Extract only information supported by the OCR.
2. NEVER invent information.
3. NEVER calculate financial values.
4. NEVER infer missing values.
5. If a value cannot be read reliably, use null.
6. Preserve the meaning of the source document.
7. Include supporting OCR evidence for every field.
8. Include the page number where the evidence appears.
9. Extract all meaningful visible information.
10. Extract tables when the document contains tabular information.
11. Do not put explanations outside the requested JSON structure.
12. Keep the original meaning of financial values.
13. Do not change a reported number unless the OCR clearly
    contains formatting noise that can be safely normalized.

===== OCR TEXT =====

{ocr_result["text"]}

===== PAGE-WISE OCR =====

{json.dumps(
    ocr_result["pages"],
    ensure_ascii=False
)}

===== END DOCUMENT =====
"""


    # --------------------------------------------------------
    # Call Gemini
    # --------------------------------------------------------

    try:

        response = client.models.generate_content(

            model="gemini-3.6-flash",

            contents=prompt,

            config=types.GenerateContentConfig(

                response_mime_type="application/json",

                response_schema=ExtractionResult,

                temperature=0,
            ),
        )


    except Exception as exc:

        error_text = str(exc)

        # ----------------------------------------------------
        # Detect quota/rate-limit errors
        # ----------------------------------------------------

        quota_indicators = [
            "429",
            "RESOURCE_EXHAUSTED",
            "quota",
            "rate limit",
            "rate_limit",
            "free_tier",
            "exceeded your current quota",
        ]

        if any(
            indicator.lower()
            in error_text.lower()
            for indicator in quota_indicators
        ):

            raise GeminiQuotaError(
                "Gemini API quota has been exhausted. "
                "Please wait for the quota to reset or "
                "check your Gemini API billing and limits."
            ) from exc


        # ----------------------------------------------------
        # Other Gemini service errors
        # ----------------------------------------------------

        raise GeminiServiceError(
            "Gemini AI service is temporarily "
            "unavailable. Please try again later."
        ) from exc


    # --------------------------------------------------------
    # Validate response
    # --------------------------------------------------------

    if not response.text:

        raise GeminiServiceError(
            "Gemini returned an empty response."
        )


    # --------------------------------------------------------
    # Parse structured JSON
    # --------------------------------------------------------

    try:

        result = (
            ExtractionResult
            .model_validate_json(
                response.text
            )
        )

    except Exception as exc:

        raise GeminiServiceError(
            "Gemini returned an invalid "
            "structured response."
        ) from exc


    # --------------------------------------------------------
    # Return dictionary
    # --------------------------------------------------------

    return result.model_dump()