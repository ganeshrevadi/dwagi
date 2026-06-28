import logging
from datetime import date, timedelta

from google import genai
from google.genai import types
from sqlalchemy.orm import Session

from app.chat.tools import TOOL_DEFINITIONS, default_date_range, execute_tool
from app.config import get_settings
from app.db.models import ChatMessage, Transaction

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a personal spending assistant for an Indian user.
You analyze transactions from bank accounts (via Account Aggregator)
and credit card statements (from PDF uploads).

Use the provided tools to query real transaction data. Never invent amounts.
Format currency as ₹ with Indian numbering (e.g. ₹1,23,456.78).
Today's date is {today}.
Default to last 90 days when the user doesn't specify a period.
Be concise and helpful. If no transactions exist, tell the user to /connect banks or upload a credit card PDF.
"""


def _gemini_tools() -> list[types.Tool]:
    declarations = []
    for tool in TOOL_DEFINITIONS:
        declarations.append(
            types.FunctionDeclaration(
                name=tool["name"],
                description=tool["description"],
                parameters=tool["parameters"],
            )
        )
    return [types.Tool(function_declarations=declarations)]


def _load_history(db: Session, user_id: int, limit: int = 10) -> list[types.Content]:
    rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == user_id)
        .order_by(ChatMessage.id.desc())
        .limit(limit)
        .all()
    )
    contents: list[types.Content] = []
    for row in reversed(rows):
        role = "user" if row.role == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part(text=row.content)]))
    return contents


async def chat_with_agent(db: Session, user_id: int, user_message: str) -> str:
    settings = get_settings()
    if not settings.gemini_configured:
        txn_count = db.query(Transaction).filter(Transaction.user_id == user_id).count()
        if txn_count == 0:
            return (
                "Gemini API is not configured yet. Add GEMINI_API_KEY to enable spending analysis.\n\n"
                "Meanwhile:\n"
                "• /connect — link bank accounts\n"
                "• Send a PDF — import credit card statement"
            )
        return "GEMINI_API_KEY is not set. Add it to enable AI spending analysis."

    client = genai.Client(api_key=settings.gemini_api_key)
    history = _load_history(db, user_id)
    today = date.today().isoformat()

    contents = [
        types.Content(
            role="user",
            parts=[types.Part(text=SYSTEM_PROMPT.format(today=today))],
        ),
        *history,
        types.Content(role="user", parts=[types.Part(text=user_message)]),
    ]

    config = types.GenerateContentConfig(
        tools=_gemini_tools(),
        temperature=0.2,
    )

    for _ in range(5):
        try:
            response = client.models.generate_content(
                model=settings.llm_model,
                contents=contents,
                config=config,
            )
        except Exception as e:
            err = str(e)
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                return "Gemini API rate limit reached (20 free requests/day). Try again later or upgrade at ai.google.dev."
            logger.exception("Gemini API error")
            return f"Sorry, I hit an error: {err[:200]}"

        if not response.candidates:
            return "I couldn't generate a response. Please try again."

        candidate = response.candidates[0]
        parts = candidate.content.parts if candidate.content else []

        tool_calls = [p for p in parts if p.function_call]
        if not tool_calls:
            text = response.text or "I don't have enough data to answer that."
            _save_messages(db, user_id, user_message, text)
            return text

        contents.append(candidate.content)
        tool_response_parts = []
        for part in tool_calls:
            fc = part.function_call
            name = fc.name
            args = dict(fc.args) if fc.args else {}
            _fill_default_dates(name, args)
            result = execute_tool(db, user_id, name, args)
            tool_response_parts.append(
                types.Part(
                    function_response=types.FunctionResponse(
                        name=name,
                        response=result,
                    )
                )
            )
        contents.append(types.Content(role="user", parts=tool_response_parts))

    return "I need more steps to answer that. Please try a simpler question."


def _fill_default_dates(tool_name: str, args: dict) -> None:
    if tool_name in ("get_spending_summary", "get_spending_by_category", "get_top_merchants"):
        if "start_date" not in args or "end_date" not in args:
            start, end = default_date_range()
            args.setdefault("start_date", start)
            args.setdefault("end_date", end)
    if tool_name == "compare_periods":
        today = date.today()
        if "period_a_start" not in args:
            args["period_a_start"] = (today.replace(day=1)).isoformat()
            args["period_a_end"] = today.isoformat()
        if "period_b_start" not in args:
            prev_month_end = today.replace(day=1) - timedelta(days=1)
            args["period_b_start"] = prev_month_end.replace(day=1).isoformat()
            args["period_b_end"] = prev_month_end.isoformat()


def _save_messages(db: Session, user_id: int, user_msg: str, assistant_msg: str) -> None:
    db.add(ChatMessage(user_id=user_id, role="user", content=user_msg))
    db.add(ChatMessage(user_id=user_id, role="assistant", content=assistant_msg))
    db.commit()
