
import secrets
import time
from threading import Lock

from fastapi import FastAPI, HTTPException

from app.db import init_db, get_connection
from app.schemas import (
    ChatRequest,
    ChatResponse,
    LeaveRequest,
    LeaveConfirmationRequest,
    LeaveCancellationRequest,
)
from app.retrieval import build_index
from app.orchestrator import (
    route_message,
    submit_confirmed_leave,
    submit_confirmed_cancellation,
)
from app.tools import list_leave_requests


app = FastAPI(
    title="Veltrix PeopleOps Assistant",
    description="AI assistant for HR policies and leave management",
    version="2.0.0",
)

# Temporary in-memory confirmation store.
# Pending actions expire after five minutes.
pending_confirmations = {}
confirmation_lock = Lock()
CONFIRMATION_TTL = 300


def get_employee(employee_id):
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


def create_confirmation(employee_id, action):
    token = secrets.token_urlsafe(32)

    with confirmation_lock:
        now = time.time()

        expired = [
            key for key, value in pending_confirmations.items()
            if now - value["created_at"] > CONFIRMATION_TTL
        ]

        for key in expired:
            pending_confirmations.pop(key, None)

        pending_confirmations[token] = {
            "employee_id": employee_id,
            "action": action,
            "created_at": now,
        }

    return token


def consume_confirmation(token, employee_id, expected_action):
    with confirmation_lock:
        item = pending_confirmations.pop(token, None)

    if not item:
        raise HTTPException(
            status_code=400,
            detail="Invalid, expired, or already-used confirmation token.",
        )

    if time.time() - item["created_at"] > CONFIRMATION_TTL:
        raise HTTPException(
            status_code=400,
            detail="Confirmation token has expired. Please start again.",
        )

    if item["employee_id"] != employee_id:
        raise HTTPException(
            status_code=403,
            detail="This confirmation belongs to another employee.",
        )

    if item["action"]["type"] != expected_action:
        raise HTTPException(
            status_code=400,
            detail="Confirmation action does not match.",
        )

    return item["action"]


@app.on_event("startup")
def startup():
    init_db()


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    employee = get_employee(request.employee_id)

    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found.")

    result = route_message(request.message, request.employee_id)

    action = result.get("pending_action")

    if action and action.get("action") == "collect_leave_details":
        return ChatResponse(**result)

    if action and action.get("action") == "collect_cancellation_details":
        return ChatResponse(**result)

    return ChatResponse(**result)


@app.post("/ingest")
def ingest_documents():
    try:
        number_of_chunks = build_index()

        return {
            "message": "Documents indexed successfully",
            "chunks": number_of_chunks,
        }

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Document ingestion failed.",
        )


@app.post("/leave/prepare")
def prepare_leave(request: LeaveRequest):
    employee = get_employee(request.employee_id)

    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found.")

    try:
        # Validate and calculate the request without inserting it.
        from app.tools import (
            _parse_date,
            _working_days,
            get_leave_balance,
        )

        start = _parse_date(request.start_date)
        end = _parse_date(request.end_date)

        if start < __import__("app.config", fromlist=["APP_TODAY"]).APP_TODAY:
            raise ValueError("Leave cannot start in the past.")

        if end < start:
            raise ValueError("End date cannot be before start date.")

        working_days = _working_days(
            start,
            end,
            employee["region"] if "region" in employee else None,
        )

        balance = get_leave_balance(
            request.employee_id,
            request.leave_type,
        )

        if not balance["balances"]:
            raise ValueError("Leave balance record not found.")

        available = balance["balances"][0]["balance_days"]

        if working_days <= 0:
            raise ValueError("No working days in the selected date range.")

        if available < working_days:
            raise ValueError("Insufficient leave balance.")

        action = {
            "type": "create_leave",
            "employee_id": request.employee_id,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "leave_type": request.leave_type,
            "reason": request.reason,
        }

        token = create_confirmation(request.employee_id, action)

        return {
            "message": "Review your leave request and confirm within five minutes.",
            "request_preview": {
                "start_date": request.start_date,
                "end_date": request.end_date,
                "leave_type": request.leave_type,
                "working_days": working_days,
                "available_balance": available,
                "reason": request.reason,
            },
            "confirmation_token": token,
            "needs_confirmation": True,
        }

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.post("/leave/confirm")
def confirm_leave(request: LeaveConfirmationRequest):
    action = consume_confirmation(
        request.confirmation_token,
        request.employee_id,
        "create_leave",
    )

    result = submit_confirmed_leave(
        employee_id=action["employee_id"],
        start_date=action["start_date"],
        end_date=action["end_date"],
        reason=action["reason"],
        leave_type=action["leave_type"],
    )

    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@app.post("/leave/cancel/prepare")
def prepare_cancellation(request: LeaveCancellationRequest):
    employee = get_employee(request.employee_id)

    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found.")

    with get_connection() as conn:
        leave = conn.execute(
            """
            SELECT request_id, leave_type, start_date, end_date,
                   working_days, status
            FROM leave_requests
            WHERE request_id = ? AND employee_id = ?
            """,
            (request.request_id, request.employee_id),
        ).fetchone()

    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found.")

    if leave["status"].lower() != "pending":
        raise HTTPException(
            status_code=400,
            detail="Only pending leave requests can be cancelled.",
        )

    action = {
        "type": "cancel_leave",
        "employee_id": request.employee_id,
        "request_id": request.request_id,
    }

    token = create_confirmation(request.employee_id, action)

    return {
        "message": "Review the cancellation and confirm within five minutes.",
        "request_preview": dict(leave),
        "confirmation_token": token,
        "needs_confirmation": True,
    }


@app.post("/leave/cancel/confirm")
def confirm_cancellation(request: LeaveConfirmationRequest):
    action = consume_confirmation(
        request.confirmation_token,
        request.employee_id,
        "cancel_leave",
    )

    result = submit_confirmed_cancellation(
        employee_id=action["employee_id"],
        request_id=action["request_id"],
    )

    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@app.get("/leave/{employee_id}")
def get_leave(employee_id: str):
    employee = get_employee(employee_id)

    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found.")

    return list_leave_requests(employee_id)
