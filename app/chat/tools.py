from datetime import date, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import Transaction


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def get_spending_summary(db: Session, user_id: int, start_date: str, end_date: str) -> dict:
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    rows = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id, Transaction.txn_date >= start, Transaction.txn_date <= end)
        .all()
    )
    debits = sum(float(r.amount) for r in rows if r.txn_type == "DEBIT")
    credits = sum(float(r.amount) for r in rows if r.txn_type == "CREDIT")
    return {
        "period": f"{start_date} to {end_date}",
        "total_debits_inr": round(debits, 2),
        "total_credits_inr": round(credits, 2),
        "net_outflow_inr": round(debits - credits, 2),
        "transaction_count": len(rows),
    }


def get_spending_by_category(db: Session, user_id: int, start_date: str, end_date: str) -> dict:
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    rows = (
        db.query(Transaction.category, func.sum(Transaction.amount).label("total"), func.count(Transaction.id))
        .filter(
            Transaction.user_id == user_id,
            Transaction.txn_type == "DEBIT",
            Transaction.txn_date >= start,
            Transaction.txn_date <= end,
        )
        .group_by(Transaction.category)
        .all()
    )
    categories = {cat or "other": {"total_inr": round(float(total), 2), "count": count} for cat, total, count in rows}
    return {"period": f"{start_date} to {end_date}", "categories": categories}


def get_top_merchants(db: Session, user_id: int, start_date: str, end_date: str, limit: int = 10) -> dict:
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    rows = (
        db.query(Transaction.description, func.sum(Transaction.amount).label("total"), func.count(Transaction.id))
        .filter(
            Transaction.user_id == user_id,
            Transaction.txn_type == "DEBIT",
            Transaction.txn_date >= start,
            Transaction.txn_date <= end,
        )
        .group_by(Transaction.description)
        .order_by(func.sum(Transaction.amount).desc())
        .limit(limit)
        .all()
    )
    merchants = [
        {"description": desc[:80], "total_inr": round(float(total), 2), "count": count}
        for desc, total, count in rows
    ]
    return {"period": f"{start_date} to {end_date}", "merchants": merchants}


def compare_periods(
    db: Session, user_id: int, period_a_start: str, period_a_end: str, period_b_start: str, period_b_end: str
) -> dict:
    a = get_spending_summary(db, user_id, period_a_start, period_a_end)
    b = get_spending_summary(db, user_id, period_b_start, period_b_end)
    delta = a["net_outflow_inr"] - b["net_outflow_inr"]
    return {
        "period_a": a,
        "period_b": b,
        "net_outflow_change_inr": round(delta, 2),
        "direction": "increased" if delta > 0 else "decreased" if delta < 0 else "unchanged",
    }


def get_recent_transactions(db: Session, user_id: int, limit: int = 15) -> dict:
    rows = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .order_by(Transaction.txn_date.desc(), Transaction.id.desc())
        .limit(limit)
        .all()
    )
    return {
        "transactions": [
            {
                "date": r.txn_date.isoformat(),
                "amount_inr": float(r.amount),
                "type": r.txn_type,
                "description": r.description[:100],
                "category": r.category,
                "institution": r.institution,
                "source": r.source,
            }
            for r in rows
        ]
    }


def get_account_overview(db: Session, user_id: int) -> dict:
    rows = (
        db.query(
            Transaction.institution,
            Transaction.source,
            func.count(Transaction.id),
            func.min(Transaction.txn_date),
            func.max(Transaction.txn_date),
        )
        .filter(Transaction.user_id == user_id)
        .group_by(Transaction.institution, Transaction.source)
        .all()
    )
    return {
        "accounts": [
            {
                "institution": inst,
                "source": src,
                "transaction_count": count,
                "from_date": str(dmin),
                "to_date": str(dmax),
            }
            for inst, src, count, dmin, dmax in rows
        ]
    }


TOOL_DEFINITIONS = [
    {
        "name": "get_spending_summary",
        "description": "Get total debits, credits, and net outflow for a date range across all linked accounts.",
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "Start date YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "End date YYYY-MM-DD"},
            },
            "required": ["start_date", "end_date"],
        },
    },
    {
        "name": "get_spending_by_category",
        "description": "Break down debit spending by category for a date range.",
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string"},
                "end_date": {"type": "string"},
            },
            "required": ["start_date", "end_date"],
        },
    },
    {
        "name": "get_top_merchants",
        "description": "Top merchants/descriptions by total debit amount.",
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string"},
                "end_date": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["start_date", "end_date"],
        },
    },
    {
        "name": "compare_periods",
        "description": "Compare net outflow between two date ranges.",
        "parameters": {
            "type": "object",
            "properties": {
                "period_a_start": {"type": "string"},
                "period_a_end": {"type": "string"},
                "period_b_start": {"type": "string"},
                "period_b_end": {"type": "string"},
            },
            "required": ["period_a_start", "period_a_end", "period_b_start", "period_b_end"],
        },
    },
    {
        "name": "get_recent_transactions",
        "description": "Get the most recent transactions across all accounts.",
        "parameters": {
            "type": "object",
            "properties": {"limit": {"type": "integer"}},
        },
    },
    {
        "name": "get_account_overview",
        "description": "Overview of linked accounts and data sources (banks vs credit card PDF).",
        "parameters": {"type": "object", "properties": {}},
    },
]


def execute_tool(db: Session, user_id: int, name: str, args: dict) -> dict:
    if name == "get_spending_summary":
        return get_spending_summary(db, user_id, args["start_date"], args["end_date"])
    if name == "get_spending_by_category":
        return get_spending_by_category(db, user_id, args["start_date"], args["end_date"])
    if name == "get_top_merchants":
        return get_top_merchants(
            db, user_id, args["start_date"], args["end_date"], args.get("limit", 10)
        )
    if name == "compare_periods":
        return compare_periods(
            db,
            user_id,
            args["period_a_start"],
            args["period_a_end"],
            args["period_b_start"],
            args["period_b_end"],
        )
    if name == "get_recent_transactions":
        return get_recent_transactions(db, user_id, args.get("limit", 15))
    if name == "get_account_overview":
        return get_account_overview(db, user_id)
    return {"error": f"Unknown tool: {name}"}


def default_date_range() -> tuple[str, str]:
    end = date.today()
    start = end - timedelta(days=90)
    return start.isoformat(), end.isoformat()
