import re
from datetime import datetime

from app.statements.pdf_parser import ParsedTransaction, extract_table_rows, extract_text_from_pdf

DATE_PATTERNS = [
    re.compile(r"(\d{2})[-/](\d{2})[-/](\d{4})"),
    re.compile(r"(\d{2})\s+([A-Za-z]{3})\s+(\d{4})"),
    re.compile(r"(\d{2})[-]([A-Za-z]{3})[-](\d{4})"),
]

AMOUNT_RE = re.compile(r"([\d,]+\.\d{2})")
HEADER_RE = re.compile(
    r"(date|txn|dt|posting|value\s*date|transaction\s*date)", re.I
)
DEBIT_HEADER_RE = re.compile(
    r"(debit|dr\b|withdrawal|withdrawn|amount\s*-)", re.I
)
CREDIT_HEADER_RE = re.compile(
    r"(credit|cr\b|deposit)", re.I
)
BALANCE_HEADER_RE = re.compile(r"(balance|bal\b)", re.I)


def _parse_date(match: re.Match[str]) -> datetime.date | None:
    try:
        g1, g2, g3 = match.group(1), match.group(2), match.group(3)
        if g2.isalpha():
            return datetime.strptime(f"{g1} {g2} {g3}", "%d %b %Y").date()
        return datetime(int(g3), int(g2), int(g1)).date()
    except ValueError:
        return None


def _is_date_column(cells: list[str], col_idx: int) -> bool:
    for row in cells:
        for pat in DATE_PATTERNS:
            m = pat.search(row)
            if m:
                try:
                    return True
                except ValueError:
                    continue
    return False


def _detect_table_schema(header: list[str], sample_rows: list[list[str]]) -> dict:
    schema = {"date": -1, "debit": -1, "credit": -1, "balance": -1, "desc": []}
    for i, h in enumerate(header):
        hl = h.lower().strip()
        if HEADER_RE.search(hl):
            schema["date"] = i
        elif BALANCE_HEADER_RE.search(hl):
            schema["balance"] = i
        elif DEBIT_HEADER_RE.search(hl):
            schema["debit"] = i
        elif CREDIT_HEADER_RE.search(hl):
            schema["credit"] = i

    if schema["date"] == -1:
        for i in range(min(3, len(header))):
            if not sample_rows:
                break
            col_vals = [r[i] for r in sample_rows if i < len(r)]
            if _is_date_column(col_vals, i):
                schema["date"] = i
                break

    if schema["debit"] == -1 or schema["credit"] == -1:
        amount_cols = []
        for i in range(len(header)):
            if schema["date"] == i or schema["balance"] == i:
                continue
            if i in schema.get("desc", []):
                continue
            if sample_rows:
                col_vals = [r[i] for r in sample_rows if i < len(r)]
                amount_count = sum(1 for v in col_vals if AMOUNT_RE.search(v))
                if amount_count > len(col_vals) * 0.3:
                    amount_cols.append(i)

        if schema["debit"] == -1 and len(amount_cols) > 0:
            schema["debit"] = amount_cols[0]
        if schema["credit"] == -1 and len(amount_cols) > 1:
            schema["credit"] = amount_cols[1]

    for i in range(len(header)):
        if i not in (schema["date"], schema["debit"], schema["credit"], schema["balance"], -1):
            schema["desc"].append(i)

    return schema


def _parse_table_row(
    row: list[str], schema: dict
) -> ParsedTransaction | None:
    if schema["date"] >= len(row):
        return None
    date_val = row[schema["date"]]
    txn_date = None
    for pat in DATE_PATTERNS:
        m = pat.search(date_val)
        if m:
            txn_date = _parse_date(m)
            if txn_date:
                break
    if not txn_date:
        return None

    debit_str = ""
    credit_str = ""
    if schema["debit"] >= 0 and schema["debit"] < len(row):
        debit_str = row[schema["debit"]]
    if schema["credit"] >= 0 and schema["credit"] < len(row):
        credit_str = row[schema["credit"]]

    amount = 0.0
    txn_type = "DEBIT"
    d_match = AMOUNT_RE.search(debit_str.replace(",", ""))
    c_match = AMOUNT_RE.search(credit_str.replace(",", ""))
    if d_match and c_match:
        d_amt = float(d_match.group(1).replace(",", ""))
        c_amt = float(c_match.group(1).replace(",", ""))
        if d_amt > 0 and c_amt > 0:
            amount = d_amt if d_amt >= c_amt else c_amt
        elif d_amt > 0:
            amount = d_amt
        else:
            amount = c_amt
            txn_type = "CREDIT"
    elif d_match:
        amount = float(d_match.group(1).replace(",", ""))
    elif c_match:
        amount = float(c_match.group(1).replace(",", ""))
        txn_type = "CREDIT"
    else:
        return None

    if amount == 0.0:
        return None

    desc_parts = []
    for ci in schema.get("desc", []):
        if ci < len(row) and row[ci].strip():
            desc_parts.append(row[ci].strip())
    description = " ".join(desc_parts) if desc_parts else "Bank transaction"

    return ParsedTransaction(
        txn_date=txn_date,
        description=description[:500],
        amount=abs(amount),
        txn_type=txn_type,
    )


def _parse_from_tables(rows: list[list[str]]) -> list[ParsedTransaction]:
    if len(rows) < 2:
        return []

    header = rows[0]
    data_rows = rows[1:]

    filtered = []
    for r in data_rows:
        cleaned = [c.strip() for c in r if c is not None]
        if cleaned and any(c for c in cleaned):
            if not any(
                kw in " ".join(cleaned).lower()
                for kw in ("opening balance", "closing balance", "total ", "page ", "statement")
            ):
                filtered.append(cleaned)

    if not filtered:
        return []

    schema = _detect_table_schema(header, filtered[:10])

    transactions = []
    for row in filtered:
        txn = _parse_table_row(row, schema)
        if txn:
            transactions.append(txn)
    return transactions


def _parse_from_text(text: str) -> list[ParsedTransaction]:
    transactions = []
    for line in text.splitlines():
        line = line.strip()
        if not line or len(line) < 15:
            continue
        if any(
            kw in line.lower()
            for kw in (
                "opening balance", "closing balance", "total ", "page ", "statement",
                "minimum due", "credit limit", "outstanding",
            )
        ):
            continue

        date_match = None
        for pat in DATE_PATTERNS:
            date_match = pat.search(line)
            if date_match:
                break
        if not date_match:
            continue

        txn_date = _parse_date(date_match)
        if not txn_date:
            continue

        amounts = AMOUNT_RE.findall(line)
        if not amounts:
            continue

        amount_str = amounts[-1].replace(",", "")
        amount = float(amount_str)
        if amount == 0.0:
            continue

        description = (
            line[: date_match.start()].strip()
            or line[date_match.end() :].strip()
        )
        description = AMOUNT_RE.sub("", description).strip()
        description = re.sub(r"\s+", " ", description).strip()
        if not description:
            description = "Bank transaction"

        txn_type = "DEBIT"
        if any(
            cr in line.lower()
            for cr in (" cr ", "credit", "refund", "deposit", "payment received")
        ):
            txn_type = "CREDIT"
        if "dr " in line.lower() or "debit" in line.lower():
            txn_type = "DEBIT"

        transactions.append(
            ParsedTransaction(
                txn_date=txn_date,
                description=description[:500],
                amount=abs(amount),
                txn_type=txn_type,
            )
        )

    return transactions


def _dedupe(transactions: list[ParsedTransaction]) -> list[ParsedTransaction]:
    seen: set[tuple] = set()
    unique = []
    for t in transactions:
        key = (t.txn_date, t.description[:80], t.amount, t.txn_type)
        if key not in seen:
            seen.add(key)
            unique.append(t)
    return unique


def parse_bank_statement(pdf_bytes: bytes) -> list[ParsedTransaction]:
    text = extract_text_from_pdf(pdf_bytes)
    rows = extract_table_rows(pdf_bytes)

    if rows and len(rows) > 1:
        transactions = _parse_from_tables(rows)
        if transactions:
            return _dedupe(transactions)

    transactions = _parse_from_text(text)
    return _dedupe(transactions)
