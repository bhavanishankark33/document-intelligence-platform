import re
from typing import Optional


# ============================================================
# VALIDATION SETTINGS
# ============================================================

TOLERANCE = 0.01


# ============================================================
# NUMBER NORMALIZATION
# ============================================================

def normalize_number(value) -> Optional[float]:
    """
    Convert OCR / Gemini financial values into numbers.

    Handles examples such as:

        1,234,567
        6,431 ,342,479
        4. 40
        0,20
        (11,476,802)
        RM 20.05

    Returns None when the value cannot be interpreted.
    """

    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    if text.lower() in {
        "none",
        "null",
        "n/a",
        "na",
        "-",
        "--",
        "---",
        "----",
    }:
        return None

    # Remove spaces.
    text = text.replace(" ", "")

    # Parentheses represent negative numbers.
    negative = (
        text.startswith("(")
        and text.endswith(")")
    )

    if negative:
        text = text[1:-1]

    # Keep only digits, comma, dot and minus.
    text = re.sub(
        r"[^0-9,.\-]",
        "",
        text,
    )

    if not text:
        return None

    # Handle comma decimals such as:
    #
    # 0,20
    # 4,40
    #
    if "," in text and "." not in text:

        parts = text.split(",")

        if (
            len(parts) == 2
            and len(parts[1]) <= 2
        ):
            text = ".".join(parts)

        else:
            text = text.replace(
                ",",
                "",
            )

    else:

        text = text.replace(
            ",",
            "",
        )

    # Handle OCR values such as:
    #
    # 4. 40
    #
    text = text.replace(
        ". ",
        ".",
    )

    try:

        number = float(text)

        if negative:
            number = -number

        return number

    except ValueError:

        return None


# ============================================================
# FIELD NAME NORMALIZATION
# ============================================================

def normalize_field_name(name: str) -> str:
    """
    Normalize field names so that different Gemini
    naming styles can be compared.

    Example:

        "Total Assets"
        "total_assets"
        "TOTAL ASSETS 2017"

    all become a comparable form.
    """

    if not name:
        return ""

    text = str(name).lower()

    text = re.sub(
        r"[^a-z0-9]+",
        "_",
        text,
    )

    text = re.sub(
        r"_+",
        "_",
        text,
    )

    return text.strip("_")


# ============================================================
# EXTRACT FIELD VALUES
# ============================================================

def get_field_values(
    extracted_data: dict,
) -> dict:
    """
    Convert extracted fields into:

        normalized_field_name -> original value
    """

    result = {}

    fields = extracted_data.get(
        "fields",
        [],
    )

    for field in fields:

        field_name = field.get(
            "field_name"
        )

        value = field.get(
            "value"
        )

        normalized_name = (
            normalize_field_name(
                field_name
            )
        )

        if normalized_name:

            result[
                normalized_name
            ] = value

    return result


# ============================================================
# FIND FIELD BY KEYWORDS
# ============================================================

def find_field_value(
    field_values: dict,
    keyword_groups: list[list[str]],
):
    """
    Find a field using keyword groups.

    Every group must match all of its keywords.

    Example:

        [
            ["total", "assets"],
            ["assets", "total"],
        ]

    allows Gemini naming variations.
    """

    # First try exact normalized names.

    for name, value in field_values.items():

        for keywords in keyword_groups:

            if all(
                keyword in name
                for keyword in keywords
            ):

                number = normalize_number(
                    value
                )

                if number is not None:

                    return (
                        value,
                        number,
                        name,
                    )

    return (
        None,
        None,
        None,
    )


# ============================================================
# TABLE VALUE EXTRACTION
# ============================================================

def find_value_in_tables(
    extracted_data: dict,
    row_keywords: list[str],
):
    """
    Search extracted tables for a financial row.

    Used as a fallback when Gemini did not create
    the required value as a standalone field.
    """

    tables = extracted_data.get(
        "tables",
        [],
    )

    for table in tables:

        headers = table.get(
            "headers",
            [],
        )

        rows = table.get(
            "rows",
            [],
        )

        for row in rows:

            row_text = " ".join(
                str(cell)
                for cell in row
                if cell is not None
            ).lower()

            normalized_row = re.sub(
                r"[^a-z0-9]+",
                " ",
                row_text,
            )

            if all(
                keyword.lower()
                in normalized_row
                for keyword in row_keywords
            ):

                # Search from right to left.
                #
                # Financial tables normally place
                # numeric values toward the right.

                for cell in reversed(row):

                    number = normalize_number(
                        cell
                    )

                    if number is not None:

                        return (
                            cell,
                            number,
                        )

    return (
        None,
        None,
    )


# ============================================================
# GENERIC VALUE FINDER
# ============================================================

def find_financial_value(
    extracted_data: dict,
    field_keywords: list[list[str]],
    table_keywords: list[str],
):
    """
    Search fields first, then tables.

    Returns:

        original_value
        normalized_number
        source
    """

    field_values = get_field_values(
        extracted_data
    )

    value, number, field_name = (
        find_field_value(
            field_values,
            field_keywords,
        )
    )

    if number is not None:

        return (
            value,
            number,
            f"field:{field_name}",
        )

    value, number = (
        find_value_in_tables(
            extracted_data,
            table_keywords,
        )
    )

    if number is not None:

        return (
            value,
            number,
            "table",
        )

    return (
        None,
        None,
        None,
    )


# ============================================================
# COMPARE VALUES
# ============================================================

def compare_values(
    calculated_value: Optional[float],
    reported_value: Optional[float],
    formula: str,
    input_values: dict,
) -> dict:
    """
    Compare calculated and reported financial values.

    Status is strictly:

        PASS
        FAIL
        NOT_APPLICABLE
    """

    if (
        calculated_value is None
        or reported_value is None
    ):

        return {

            "formula":
                formula,

            "input_values":
                input_values,

            "calculated_value":
                calculated_value,

            "reported_value":
                reported_value,

            "variance":
                None,

            "status":
                "NOT_APPLICABLE",
        }

    variance = (
        calculated_value
        - reported_value
    )

    status = (
        "PASS"
        if abs(variance) <= TOLERANCE
        else "FAIL"
    )

    return {

        "formula":
            formula,

        "input_values":
            input_values,

        "calculated_value":
            calculated_value,

        "reported_value":
            reported_value,

        "variance":
            variance,

        "status":
            status,
    }


# ============================================================
# BALANCE SHEET VALIDATION
# ============================================================

def validate_balance_sheet(
    extracted_data: dict,
) -> dict:
    """
    Balance Sheet rule:

        Total Assets
        =
        Total Capital and Liabilities
    """

    # --------------------------------------------------------
    # Find Total Assets
    # --------------------------------------------------------

    (
        assets_original,
        total_assets,
        assets_source,
    ) = find_financial_value(

        extracted_data,

        field_keywords=[
            ["total", "assets"],
            ["assets", "total"],
        ],

        table_keywords=[
            "total",
            "assets",
        ],
    )


    # --------------------------------------------------------
    # Find Total Capital and Liabilities
    # --------------------------------------------------------

    (
        liabilities_original,
        total_liabilities,
        liabilities_source,
    ) = find_financial_value(

        extracted_data,

        field_keywords=[
            [
                "total",
                "capital",
                "liabilities",
            ],

            [
                "capital",
                "liabilities",
                "total",
            ],

            [
                "total",
                "capital",
                "and",
                "liabilities",
            ],
        ],

        table_keywords=[
            "total",
        ],
    )


    # --------------------------------------------------------
    # IMPORTANT:
    #
    # Some statements don't name the first total as
    # "Total Capital and Liabilities".
    #
    # If Gemini extracted the Balance Sheet table,
    # locate the total immediately before the ASSETS
    # section when possible.
    #
    # We deliberately do not invent values.
    # --------------------------------------------------------

    if (
        total_liabilities is None
        and total_assets is not None
    ):

        field_values = get_field_values(
            extracted_data
        )

        # Look for common alternatives.

        (
            liabilities_original,
            total_liabilities,
            liabilities_source,
        ) = find_field_value(

            field_values,

            [
                [
                    "total",
                    "liabilities",
                ],

                [
                    "total",
                    "capital",
                ],

                [
                    "liabilities",
                    "total",
                ],
            ],
        )


    # --------------------------------------------------------
    # Build check
    # --------------------------------------------------------

    check = compare_values(

        calculated_value=
            total_liabilities,

        reported_value=
            total_assets,

        formula=
            "Total Assets = Total Capital and Liabilities",

        input_values={

            "total_assets":
                total_assets,

            "total_capital_and_liabilities":
                total_liabilities,

            "total_assets_source":
                assets_source,

            "total_capital_and_liabilities_source":
                liabilities_source,
        },
    )


    return {

        "document_type":
            "balance_sheet",

        "overall_status":
            check["status"],

        "checks": [
            check
        ],
    }


# ============================================================
# PROFIT AND LOSS VALIDATION
# ============================================================

def validate_profit_and_loss(
    extracted_data: dict,
) -> dict:
    """
    Profit & Loss rule:

        Total Income
        -
        Total Expenditure
        =
        Net Profit
    """

    (
        income_original,
        total_income,
        income_source,
    ) = find_financial_value(

        extracted_data,

        field_keywords=[
            ["total", "income"],
            ["total", "revenue"],
            ["revenue", "total"],
            ["income", "total"],
        ],

        table_keywords=[
            "total",
            "income",
        ],
    )


    (
        expenditure_original,
        total_expenditure,
        expenditure_source,
    ) = find_financial_value(

        extracted_data,

        field_keywords=[
            ["total", "expenditure"],
            ["total", "expenses"],
            ["total", "expense"],
            ["expenditure", "total"],
        ],

        table_keywords=[
            "total",
            "expenditure",
        ],
    )


    (
        profit_original,
        net_profit,
        profit_source,
    ) = find_financial_value(

        extracted_data,

        field_keywords=[
            [
                "net",
                "profit",
            ],

            [
                "profit",
                "for",
                "the",
                "year",
            ],

            [
                "net",
                "profit",
                "year",
            ],

            [
                "profit",
                "year",
            ],
        ],

        table_keywords=[
            "profit",
        ],
    )


    if (
        total_income is not None
        and total_expenditure is not None
    ):

        calculated_value = (
            total_income
            - total_expenditure
        )

    else:

        calculated_value = None


    check = compare_values(

        calculated_value=
            calculated_value,

        reported_value=
            net_profit,

        formula=
            "Total Income - Total Expenditure = Net Profit",

        input_values={

            "total_income":
                total_income,

            "total_expenditure":
                total_expenditure,

            "total_income_source":
                income_source,

            "total_expenditure_source":
                expenditure_source,

            "net_profit_source":
                profit_source,
        },
    )


    return {

        "document_type":
            "profit_and_loss",

        "overall_status":
            check["status"],

        "checks": [
            check
        ],
    }


# ============================================================
# CASH FLOW VALIDATION
# ============================================================

def validate_cash_flow(
    extracted_data: dict,
) -> dict:
    """
    Cash Flow rule:

        Opening Cash
        +
        Net Change in Cash
        =
        Closing Cash
    """

    (
        opening_original,
        opening_cash,
        opening_source,
    ) = find_financial_value(

        extracted_data,

        field_keywords=[
            [
                "opening",
                "cash",
            ],

            [
                "opening",
                "cash",
                "balance",
            ],

            [
                "cash",
                "opening",
            ],
        ],

        table_keywords=[
            "opening",
            "cash",
        ],
    )


    (
        change_original,
        net_change,
        change_source,
    ) = find_financial_value(

        extracted_data,

        field_keywords=[
            [
                "net",
                "increase",
                "decrease",
                "cash",
            ],

            [
                "net",
                "change",
                "cash",
            ],

            [
                "increase",
                "decrease",
                "cash",
            ],

            [
                "net",
                "cash",
            ],
        ],

        table_keywords=[
            "net",
            "cash",
        ],
    )


    (
        closing_original,
        closing_cash,
        closing_source,
    ) = find_financial_value(

        extracted_data,

        field_keywords=[
            [
                "closing",
                "cash",
            ],

            [
                "closing",
                "cash",
                "balance",
            ],

            [
                "cash",
                "closing",
            ],
        ],

        table_keywords=[
            "closing",
            "cash",
        ],
    )


    if (
        opening_cash is not None
        and net_change is not None
    ):

        calculated_value = (
            opening_cash
            + net_change
        )

    else:

        calculated_value = None


    check = compare_values(

        calculated_value=
            calculated_value,

        reported_value=
            closing_cash,

        formula=
            "Opening Cash + Net Change = Closing Cash",

        input_values={

            "opening_cash":
                opening_cash,

            "net_change":
                net_change,

            "opening_cash_source":
                opening_source,

            "net_change_source":
                change_source,

            "closing_cash_source":
                closing_source,
        },
    )


    return {

        "document_type":
            "cash_flow_statement",

        "overall_status":
            check["status"],

        "checks": [
            check
        ],
    }


# ============================================================
# MAIN VALIDATION DISPATCHER
# ============================================================

def validate_document_financials(
    document_type: str,
    extracted_data: dict,
) -> dict:
    """
    Run the appropriate deterministic financial
    validation based on document type.
    """

    if document_type == "balance_sheet":

        return validate_balance_sheet(
            extracted_data
        )


    if document_type == "profit_and_loss":

        return validate_profit_and_loss(
            extracted_data
        )


    if document_type == "cash_flow_statement":

        return validate_cash_flow(
            extracted_data
        )


    # Invoices do not have a required financial
    # statement equation in the assignment.

    return {

        "document_type":
            document_type,

        "overall_status":
            "NOT_APPLICABLE",

        "checks": [],
    }