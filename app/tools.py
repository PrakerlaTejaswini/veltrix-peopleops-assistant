
import sqlite3
import uuid
from datetime import date, datetime, timedelta

from app.config import APP_TODAY
from app.db import get_connection


def _parse_date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError("Dates must use YYYY-MM-DD format.")


def _working_days(start_date, end_date, region):
    """Count weekdays excluding public holidays for the employee's region."""
    holidays = set()

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT holiday_date
            FROM public_holidays
            WHERE region = ?
              AND holiday_date BETWEEN ? AND ?
            """,
            (region, start_date.isoformat(), end_date.isoformat()),
        ).fetchall()

    holidays = {row["holiday_date"] for row in rows}

    count = 0
    current = start_date

    while current <= end_date:
        if current.weekday() < 5 and current.isoformat() not in holidays:
            count += 1
        current += timedelta(days=1)

    return count


def get_leave_balance(employee_id, leave_type=None):
    """Get an employee's available leave balance."""
    with get_connection() as conn:
        if leave_type:
            rows = conn.execute(
                """
                SELECT leave_type, balance_days
                FROM leave_balances
                WHERE employee_id = ? AND leave_type = ?
                """,
                (employee_id, leave_type.lower()),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT leave_type, balance_days
                FROM leave_balances
                WHERE employee_id = ?
                ORDER BY leave_type
                """,
                (employee_id,),
            ).fetchall()

    return {
        "employee_id": employee_id,
        "balances": [
            {
                "leave_type": row["leave_type"],
                "balance_days": row["balance_days"],
            }
            for row in rows
        ],
    }


def list_leave_requests(employee_id, status=None):
    """List leave requests belonging to one employee."""
    with get_connection() as conn:
        if status:
            rows = conn.execute(
                """
                SELECT request_id, leave_type, start_date, end_date,
                       working_days, status, created_at
                FROM leave_requests
                WHERE employee_id = ? AND LOWER(status) = ?
                ORDER BY created_at DESC
                """,
                (employee_id, status.lower()),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT request_id, leave_type, start_date, end_date,
                       working_days, status, created_at
                FROM leave_requests
                WHERE employee_id = ?
                ORDER BY created_at DESC
                """,
                (employee_id,),
            ).fetchall()

    return {
        "employee_id": employee_id,
        "requests": [dict(row) for row in rows],
    }


def get_team_leave(manager_id, start_date, end_date):
    """List leave requests for employees reporting to a manager."""
    start = _parse_date(start_date)
    end = _parse_date(end_date)

    if end < start:
        raise ValueError("End date cannot be before start date.")

    with get_connection() as conn:
        manager = conn.execute(
            """
            SELECT employee_id, role
            FROM employees
            WHERE employee_id = ?
            """,
            (manager_id,),
        ).fetchone()

        if not manager or manager["role"].lower() not in ("manager", "hr"):
            raise ValueError("Manager or HR access is required.")

        rows = conn.execute(
            """
            SELECT
                lr.request_id,
                lr.employee_id,
                e.full_name,
                lr.leave_type,
                lr.start_date,
                lr.end_date,
                lr.working_days,
                lr.status
            FROM leave_requests lr
            JOIN employees e ON e.employee_id = lr.employee_id
            WHERE e.manager_id = ?
              AND lr.start_date <= ?
              AND lr.end_date >= ?
              AND LOWER(lr.status) IN ('pending', 'approved')
            ORDER BY lr.start_date
            """,
            (manager_id, end.isoformat(), start.isoformat()),
        ).fetchall()

    return {
        "manager_id": manager_id,
        "team_leave": [dict(row) for row in rows],
    }


def create_leave_request(
    employee_id,
    start_date,
    end_date,
    leave_type="annual",
    reason=None,
):
    """
    Prepare a pending leave request.

    This function does not approve the request or deduct the balance.
    The reason parameter is accepted for compatibility but is not stored,
    because the assessment database has no reason column.
    """
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    leave_type = leave_type.lower().strip()

    if leave_type not in ("annual", "sick"):
        raise ValueError("Leave type must be annual or sick.")

    if start < APP_TODAY:
        raise ValueError("Leave cannot start in the past.")

    if end < start:
        raise ValueError("End date cannot be before start date.")

    with get_connection() as conn:
        employee = conn.execute(
            """
            SELECT employee_id, region
            FROM employees
            WHERE employee_id = ?
            """,
            (employee_id,),
        ).fetchone()

        if not employee:
            raise ValueError("Employee not found.")

        balance = conn.execute(
            """
            SELECT balance_days
            FROM leave_balances
            WHERE employee_id = ? AND leave_type = ?
            """,
            (employee_id, leave_type),
        ).fetchone()

        if not balance:
            raise ValueError("Leave balance record not found.")

        working_days = _working_days(start, end, employee["region"])

        if working_days <= 0:
            raise ValueError("The selected dates contain no working days.")

        if balance["balance_days"] < working_days:
            raise ValueError(
                f"Insufficient {leave_type} balance. "
                f"Available: {balance['balance_days']}, "
                f"requested: {working_days}."
            )

        overlap = conn.execute(
            """
            SELECT request_id
            FROM leave_requests
            WHERE employee_id = ?
              AND LOWER(status) IN ('pending', 'approved')
              AND start_date <= ?
              AND end_date >= ?
            LIMIT 1
            """,
            (employee_id, end.isoformat(), start.isoformat()),
        ).fetchone()

        if overlap:
            raise ValueError(
                "This date range overlaps an existing pending or approved request."
            )

        request_id = str(uuid.uuid4())
        created_at = datetime.now().isoformat(timespec="seconds")

        conn.execute(
            """
            INSERT INTO leave_requests (
                request_id,
                employee_id,
                leave_type,
                start_date,
                end_date,
                working_days,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request_id,
                employee_id,
                leave_type,
                start.isoformat(),
                end.isoformat(),
                working_days,
                "pending",
                created_at,
            ),
        )

    return {
        "request_id": request_id,
        "employee_id": employee_id,
        "leave_type": leave_type,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "working_days": working_days,
        "status": "pending",
        "message": "Leave request created and awaiting approval.",
    }


def cancel_leave_request(employee_id, request_id):
    """Cancel an employee's pending leave request."""
    with get_connection() as conn:
        request = conn.execute(
            """
            SELECT request_id, status, start_date
            FROM leave_requests
            WHERE request_id = ? AND employee_id = ?
            """,
            (request_id, employee_id),
        ).fetchone()

        if not request:
            raise ValueError("Leave request not found for this employee.")

        if request["status"].lower() != "pending":
            raise ValueError("Only pending leave requests can be cancelled.")

        if request["start_date"] < APP_TODAY.isoformat():
            raise ValueError("Past leave requests cannot be cancelled.")

        conn.execute(
            """
            UPDATE leave_requests
            SET status = 'cancelled'
            WHERE request_id = ? AND employee_id = ?
            """,
            (request_id, employee_id),
        )

    return {
        "request_id": request_id,
        "status": "cancelled",
        "message": "Pending leave request cancelled successfully.",
    }
