import io
import re
from dataclasses import dataclass
from datetime import datetime

import pdfplumber


@dataclass
class ParsedTransaction:
    txn_date: datetime.date
    description: str
    amount: float
    txn_type: str


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    parts: list[str] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                parts.append(text)
    return "\n".join(parts)


def extract_table_rows(pdf_bytes: bytes) -> list[list[str]]:
    rows: list[list[str]] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if row and any(cell and str(cell).strip() for cell in row):
                        rows.append([str(c or "").strip() for c in row])
    return rows
