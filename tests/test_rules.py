
import pytest
from datetime import date

from app.tools import (
    _parse_date,
    get_leave_balance,
    list_leave_requests,
    get_team_leave,
)


def test_parse_valid_date():
    result = _parse_date("2026-12-07")
    assert result == date(2026, 12, 7)


def test_parse_invalid_date():
    with pytest.raises(ValueError):
        _parse_date("07-12-2026")


def test_get_annual_and_sick_balances():
    result = get_leave_balance("E2004")

    balances = {
        item["leave_type"]: item["balance_days"]
        for item in result["balances"]
    }

    assert balances["annual"] == 3.5
    assert balances["sick"] == 12.0


def test_get_leave_history():
    result = list_leave_requests("E2004")

    assert result["employee_id"] == "E2004"
    assert len(result["requests"]) >= 1


def test_invalid_manager_cannot_view_team_leave():
    with pytest.raises(ValueError):
        get_team_leave(
            "E2004",
            "2026-12-01",
            "2026-12-31"
        )


def test_invalid_team_leave_date_range():
    with pytest.raises(ValueError):
        get_team_leave(
            "E2001",
            "2026-12-31",
            "2026-12-01"
        )
