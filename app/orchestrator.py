
from app.retrieval import search_documents
from app.llm import generate_answer
from app.db import get_connection
from app.tools import (
    get_leave_balance,
    list_leave_requests,
    get_team_leave,
    create_leave_request,
    cancel_leave_request,
)

MIN_RELEVANCE_SCORE = 0.10

NO_ANSWER = (
    "I couldn't find enough information in the provided "
    "HR documents to answer your question."
)


def get_employee(employee_id):
    """Retrieve employee details from the original assessment database."""
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT employee_id, full_name, region, role, manager_id
            FROM employees
            WHERE employee_id = ?
            """,
            (employee_id,),
        ).fetchone()

    return dict(row) if row else None


def select_policy_documents(message, documents, region=None):
    """Filter irrelevant regional addenda and retain the latest global policy."""
    relevant = [
        doc for doc in documents
        if doc.get("score", 0) >= MIN_RELEVANCE_SCORE
    ]

    selected = []

    region_files = {
        "IN": "leave_addendum_india",
        "DE": "leave_addendum_germany",
        "US": "leave_addendum_us",
    }

    allowed_addendum = region_files.get(region)

    for doc in relevant:
        filename = doc.get("filename", "").lower()

        is_regional_addendum = any(
            name in filename for name in region_files.values()
        )

        if is_regional_addendum:
            if allowed_addendum and allowed_addendum in filename:
                selected.append(doc)
            continue

        selected.append(doc)

    global_versions = [
        doc for doc in selected
        if doc.get("filename", "").lower().startswith(
            "leave_policy_global_v"
        )
    ]

    if global_versions:
        latest = max(
            global_versions,
            key=lambda doc: (
                doc.get("effective_date") or "",
                doc.get("filename", ""),
            ),
        )

        selected = [
            doc for doc in selected
            if not doc.get("filename", "").lower().startswith(
                "leave_policy_global_v"
            )
        ]

        selected.append(latest)

    selected.sort(
        key=lambda doc: doc.get("score", 0),
        reverse=True,
    )

    return selected


def answer_hr_question(message, employee_id):
    """Answer HR questions using the employee's regional context."""
    employee = get_employee(employee_id)

    if not employee:
        return "Employee record not found."

    documents = search_documents(message)

    if not documents:
        return NO_ANSWER

    relevant = select_policy_documents(
        message,
        documents,
        employee.get("region"),
    )

    if not relevant:
        return NO_ANSWER

    context = "\n\n".join(
        (
            f"Source: {doc.get('source', 'Unknown')}\n"
            f"Effective date: {doc.get('effective_date', 'Unknown')}\n"
            f"Content:\n{doc.get('text', '')}"
        )
        for doc in relevant
    )

    answer = generate_answer(message, context)

    if not answer or not str(answer).strip():
        return NO_ANSWER

    sources = sorted({
        doc.get("source", "Unknown")
        for doc in relevant
        if doc.get("source")
    })

    answer = str(answer).strip()

    if sources:
        answer += "\n\nSources: " + ", ".join(sources)

    return answer


def route_message(message, employee_id):
    """Route messages to employee-specific tools or HR policy RAG."""
    if not message or not message.strip():
        return {
            "answer": "Please enter your question.",
            "source": "clarify",
            "needs_confirmation": False,
            "pending_action": None,
        }

    employee = get_employee(employee_id)

    if not employee:
        return {
            "answer": "Employee record not found. Please check your employee ID.",
            "source": "validation",
            "needs_confirmation": False,
            "pending_action": None,
        }

    text = message.lower().strip()

    if any(term in text for term in [
        "leave balance", "remaining leave", "available leave",
        "how many leaves", "how much leave",
    ]):
        result = get_leave_balance(employee_id)

        return {
            "answer": str(result),
            "source": "leave_tool",
            "needs_confirmation": False,
            "pending_action": None,
        }

    if any(term in text for term in [
        "my leave requests", "leave history",
        "leave status", "my leave applications",
    ]):
        result = list_leave_requests(employee_id)

        return {
            "answer": str(result),
            "source": "leave_tool",
            "needs_confirmation": False,
            "pending_action": None,
        }

    if any(term in text for term in [
        "team leave", "team members leave", "team availability",
    ]):
        if employee["role"].lower() not in ("manager", "hr"):
            return {
                "answer": "Only managers and HR can view team leave information.",
                "source": "authorization",
                "needs_confirmation": False,
                "pending_action": None,
            }

        return {
            "answer": (
                "Please provide the start and end dates "
                "for the team leave search."
            ),
            "source": "leave_tool",
            "needs_confirmation": False,
            "pending_action": {
                "action": "get_team_leave",
                "manager_id": employee_id,
            },
        }

    if any(term in text for term in [
        "apply leave", "apply for leave", "request leave",
        "book leave", "take leave",
    ]):
        return {
            "answer": (
                "I can prepare your leave request. Please provide "
                "the leave type (annual or sick), start date, "
                "end date, and reason. I will ask you to confirm "
                "before submitting it."
            ),
            "source": "leave_tool",
            "needs_confirmation": False,
            "pending_action": {
                "action": "collect_leave_details",
                "employee_id": employee_id,
            },
        }

    if any(term in text for term in [
        "cancel leave", "cancel my leave", "withdraw leave",
    ]):
        return {
            "answer": (
                "Please provide the request ID you want to cancel. "
                "I'll show the details and ask for confirmation."
            ),
            "source": "leave_tool",
            "needs_confirmation": False,
            "pending_action": {
                "action": "collect_cancellation_details",
                "employee_id": employee_id,
            },
        }

    answer = answer_hr_question(message, employee_id)

    return {
        "answer": answer,
        "source": "rag",
        "needs_confirmation": False,
        "pending_action": None,
    }


def submit_confirmed_leave(
    employee_id,
    start_date,
    end_date,
    reason=None,
    leave_type="annual",
):
    """Create a pending leave request after confirmation."""
    try:
        result = create_leave_request(
            employee_id=employee_id,
            start_date=start_date,
            end_date=end_date,
            leave_type=leave_type,
            reason=reason,
        )

        return {
            "ok": True,
            **result,
        }

    except (ValueError, Exception) as error:
        return {
            "ok": False,
            "message": str(error),
        }


def submit_confirmed_cancellation(employee_id, request_id):
    """Cancel a pending leave request after confirmation."""
    try:
        result = cancel_leave_request(
            employee_id=employee_id,
            request_id=request_id,
        )

        return {
            "ok": True,
            **result,
        }

    except Exception as error:
        return {
            "ok": False,
            "message": str(error),
        }


def get_manager_team_leave(manager_id, start_date, end_date):
    """Return leave requests for a manager's direct reports."""
    employee = get_employee(manager_id)

    if not employee:
        return {"ok": False, "message": "Employee not found."}

    if employee["role"].lower() not in ("manager", "hr"):
        return {
            "ok": False,
            "message": "Manager or HR access is required.",
        }

    try:
        return {
            "ok": True,
            **get_team_leave(manager_id, start_date, end_date),
        }
    except ValueError as error:
        return {"ok": False, "message": str(error)}
