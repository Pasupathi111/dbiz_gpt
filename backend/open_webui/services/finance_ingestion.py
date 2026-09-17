"""Parsers that turn uploaded UBS custody Excel files and LGI PDF statements
into bond record rows for the Bond Copilot finance module.

Each parser returns a list of raw dicts shaped like::

    {
        "bond_id": str,
        "isin": str | None,
        "description": str | None,
        ... other BondRecordForm fields ...,
        "_raw_data": dict,            # original row/line, for BondSourceRecord.raw_data
        "_sheet_name": str | None,    # Excel only
        "_row_number": int | None,    # Excel only
        "_page_number": int | None,   # PDF only
        "_cell_references": dict | None,
        "_confidence": float,         # 0..1, based on how many fields were matched
    }
"""

import logging
import re
from datetime import datetime
from io import BytesIO
from typing import Any, Optional

import openpyxl
from pypdf import PdfReader

log = logging.getLogger(__name__)

# BondRecordForm fields we attempt to populate from a source file, and the
# header/label aliases (lowercased) that identify each one in real-world
# custodian exports.
FIELD_ALIASES: dict[str, list[str]] = {
    "isin": ["isin", "isin code", "security id", "identifier"],
    "bond_id": ["bond id", "security number", "valor"],
    "description": ["description", "security name", "security description", "name"],
    "issuer": ["issuer", "issuer name"],
    "currency": ["currency", "ccy"],
    "face_value": ["face value", "nominal", "nominal amount", "par value", "face amount"],
    "book_value": ["book value", "cost value", "amortized cost", "book value (ccy)"],
    "market_value": ["market value", "market value (ccy)", "fair value", "value"],
    "coupon_rate": ["coupon", "coupon rate", "coupon %", "interest rate"],
    "accrued_interest": ["accrued interest", "accrued int", "accrued int."],
    "maturity_date": ["maturity date", "maturity"],
    "purchase_date": ["purchase date", "trade date", "acquisition date"],
    "settlement_date": ["settlement date", "value date"],
    "quantity": ["quantity", "units", "nominal quantity", "holdings"],
}

NUMERIC_FIELDS = {
    "face_value", "book_value", "market_value", "coupon_rate",
    "accrued_interest", "quantity",
}
DATE_FIELDS = {"maturity_date", "purchase_date", "settlement_date"}

ISIN_RE = re.compile(r"\b[A-Z]{2}[A-Z0-9]{9}\d\b")
NUMBER_RE = re.compile(r"-?\d+(?:[,\']\d{3})*(?:\.\d+)?")


def _normalize_header(value: Any) -> str:
    return str(value).strip().lower() if value is not None else ""


def _to_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).replace(",", "").replace("'", "").replace("%", "").strip()
    try:
        return float(text)
    except ValueError:
        return None


def _to_date_str(value: Any) -> Optional[str]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%m/%d/%Y", "%d-%b-%Y", "%d-%b-%y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return text or None


def _map_header_row(values: list[Any]) -> dict[str, int]:
    """Return {field_name: column_index} for a candidate header row."""
    header_map: dict[str, int] = {}
    for col_index, raw in enumerate(values):
        header = _normalize_header(raw)
        if not header:
            continue
        for field, aliases in FIELD_ALIASES.items():
            if field in header_map:
                continue
            if header in aliases or any(header == a or header.startswith(a) for a in aliases):
                header_map[field] = col_index
                break
    return header_map


def parse_ubs_excel(contents: bytes) -> list[dict[str, Any]]:
    """Parse a UBS custody-statement style workbook into bond record rows."""
    workbook = openpyxl.load_workbook(BytesIO(contents), data_only=True, read_only=True)
    records: list[dict[str, Any]] = []

    for sheet in workbook.worksheets:
        header_map: dict[str, int] = {}
        header_row_values: list[str] = []

        for row in sheet.iter_rows(values_only=False):
            values = [cell.value for cell in row]
            if all(v is None for v in values):
                continue

            if not header_map:
                candidate = _map_header_row(values)
                # A real header row must at least identify the ISIN or
                # description column, otherwise keep scanning.
                if "isin" in candidate or "description" in candidate:
                    header_map = candidate
                    header_row_values = [_normalize_header(v) for v in values]
                continue

            record: dict[str, Any] = {}
            raw_data: dict[str, Any] = {}
            cell_references: dict[str, str] = {}
            for field, col_index in header_map.items():
                if col_index >= len(values):
                    continue
                cell = row[col_index]
                value = values[col_index]
                header_label = (
                    header_row_values[col_index] if col_index < len(header_row_values) else field
                )
                raw_data[header_label] = value
                cell_references[field] = cell.coordinate
                if field in NUMERIC_FIELDS:
                    record[field] = _to_float(value)
                elif field in DATE_FIELDS:
                    record[field] = _to_date_str(value)
                else:
                    record[field] = str(value).strip() if value is not None else None

            isin = record.get("isin")
            description = record.get("description")
            if not isin and not description:
                continue

            record["bond_id"] = record.get("bond_id") or isin or description
            record["_raw_data"] = raw_data
            record["_sheet_name"] = sheet.title
            matched_fields = sum(1 for f in header_map if record.get(f) not in (None, ""))
            record["_row_number"] = row[0].row
            record["_cell_references"] = cell_references
            record["_page_number"] = None
            record["_confidence"] = round(matched_fields / max(len(header_map), 1), 2)
            records.append(record)

    return records


def _guess_description(line: str, isin: str) -> Optional[str]:
    before = line.split(isin)[0].strip(" -:\t")
    return before or None


def parse_lgi_pdf(contents: bytes) -> list[dict[str, Any]]:
    """Best-effort parser for LGI PDF holding statements.

    LGI statements are tabular text laid out one bond per line. We locate
    each line that contains an ISIN and pull the surrounding numeric tokens
    as quantity / value fields, keeping the raw line and page number for
    provenance so a reviewer can validate/correct via the UI.
    """
    reader = PdfReader(BytesIO(contents))
    records: list[dict[str, Any]] = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        for line in text.splitlines():
            match = ISIN_RE.search(line)
            if not match:
                continue
            isin = match.group(0)
            numbers = [_to_float(n) for n in NUMBER_RE.findall(line.replace(isin, " "))]
            numbers = [n for n in numbers if n is not None]

            record: dict[str, Any] = {
                "isin": isin,
                "bond_id": isin,
                "description": _guess_description(line, isin),
                "issuer": None,
                "currency": None,
                "quantity": numbers[0] if len(numbers) >= 1 else None,
                "face_value": numbers[1] if len(numbers) >= 4 else None,
                "book_value": numbers[-2] if len(numbers) >= 2 else None,
                "market_value": numbers[-1] if numbers else None,
                "coupon_rate": None,
                "accrued_interest": None,
                "maturity_date": None,
                "purchase_date": None,
                "settlement_date": None,
                "_raw_data": {"line": line.strip()},
                "_sheet_name": None,
                "_row_number": None,
                "_page_number": page_number,
                "_cell_references": None,
            }
            field_keys = [k for k in record if not k.startswith("_")]
            matched_fields = sum(1 for k in field_keys if record.get(k) not in (None, ""))
            record["_confidence"] = round(matched_fields / len(field_keys), 2)
            records.append(record)

    return records


def parse_document(document_type: str, contents: bytes) -> list[dict[str, Any]]:
    if document_type == "UBS_EXCEL":
        return parse_ubs_excel(contents)
    if document_type == "LGI_PDF":
        return parse_lgi_pdf(contents)
    raise ValueError(f"Unsupported document_type for extraction: {document_type}")
