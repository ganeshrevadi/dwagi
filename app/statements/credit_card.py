import re
from datetime import datetime

from app.statements.pdf_parser import ParsedTransaction, extract_table_rows, extract_text_from_pdf

DATE_PATTERNS = [
    re.compile(r"(\d{2})[/-](\d{2})[/-](\d{4})"),
    re.compile(r"(\d{2})\s+([A-Za-z]{3})\s+(\d{4})"),
]

AMOUNT_PATTERN = re.compile(r"([\d,]+\.\d{2})")
TRAILING_MARKER = re.compile(r"\s+(Cr|Dr|CR|DR)\s*$")


def _parse_date(match: re.Match[str]) -> datetime.date | None:
    try:
        if match.lastindex == 3:
            g1, g2, g3 = match.group(1), match.group(2), match.group(3)
            if g2.isalpha():
                return datetime.strptime(f"{g1} {g2} {g3}", "%d %b %Y").date()
            return datetime(int(g3), int(g2), int(g1)).date()
    except ValueError:
        return None
    return None


def parse_credit_statement(pdf_bytes: bytes) -> list[ParsedTransaction]:
    """Parse credit card statement PDF into transactions."""
    text = extract_text_from_pdf(pdf_bytes)
    rows = extract_table_rows(pdf_bytes)
    transactions: list[ParsedTransaction] = []

    for line in text.splitlines():
        line = line.strip()
        if not line or len(line) < 10:
            continue
        if any(skip in line.lower() for skip in ("opening balance", "closing balance", "total due", "minimum due")):
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

        amounts = AMOUNT_PATTERN.findall(line)
        if not amounts:
            continue

        amount_str = amounts[-1].replace(",", "")
        amount = float(amount_str)
        description = line[: date_match.start()].strip() or line[date_match.end() :].strip()
        description = AMOUNT_PATTERN.sub("", description).strip()
        description = TRAILING_MARKER.sub("", description).strip()
        if not description:
            description = "Credit card transaction"

        desc_lower = description.lower().strip()
        txn_type = "DEBIT"
        if desc_lower in ("cr", "credit") or any(kw in desc_lower for kw in ("credit", "refund", "payment received", " paid")):
            txn_type = "CREDIT"

        transactions.append(
            ParsedTransaction(
                txn_date=txn_date,
                description=description[:500],
                amount=amount,
                txn_type=txn_type,
            )
        )

    if not transactions and rows:
        transactions = _parse_from_table_rows(rows)

    return _dedupe_transactions(transactions)


def _parse_from_table_rows(rows: list[list[str]]) -> list[ParsedTransaction]:
    results: list[ParsedTransaction] = []
    for row in rows:
        if len(row) < 3:
            continue
        row_text = " ".join(row)
        for pat in DATE_PATTERNS:
            m = pat.search(row_text)
            if not m:
                continue
            txn_date = _parse_date(m)
            if not txn_date:
                continue
            amounts = AMOUNT_PATTERN.findall(row_text)
            if not amounts:
                continue
            amount = float(amounts[-1].replace(",", ""))
            desc = row[1] if len(row) > 2 else row_text
            results.append(
                ParsedTransaction(
                    txn_date=txn_date,
                    description=desc[:500],
                    amount=amount,
                    txn_type="DEBIT",
                )
            )
            break
    return results


def _dedupe_transactions(transactions: list[ParsedTransaction]) -> list[ParsedTransaction]:
    seen: set[tuple] = set()
    unique: list[ParsedTransaction] = []
    for t in transactions:
        key = (t.txn_date, t.description[:80], t.amount, t.txn_type)
        if key not in seen:
            seen.add(key)
            unique.append(t)
    return unique
