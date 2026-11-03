
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_unknown_employee_chat(client):
    response = client.post(
        "/chat",
        json={
            "employee_id": "INVALID_EMPLOYEE",
            "message": "What is my leave balance?"
        }
    )

    assert response.status_code in (400, 404)


def test_empty_chat_message(client):
    response = client.post(
        "/chat",
        json={
            "employee_id": "E2004",
            "message": ""
        }
    )

    assert response.status_code == 422


def test_invalid_leave_dates(client):
    response = client.post(
        "/leave/prepare",
        json={
            "employee_id": "E2004",
            "start_date": "2026-12-10",
            "end_date": "2026-12-05",
            "leave_type": "annual",
            "reason": "Personal work"
        }
    )

    assert response.status_code in (400, 422)


def test_invalid_leave_type(client):
    response = client.post(
        "/leave/prepare",
        json={
            "employee_id": "E2004",
            "start_date": "2026-12-07",
            "end_date": "2026-12-08",
            "leave_type": "unlimited",
            "reason": "Personal work"
        }
    )

    assert response.status_code == 422


def test_leave_history(client):
    response = client.get("/leave/E2004")

    assert response.status_code == 200
    assert "requests" in response.json()


def test_leave_balance_chat(client):
    response = client.post(
        "/chat",
        json={
            "employee_id": "E2004",
            "message": "What is my current annual and sick leave balance?"
        }
    )

    assert response.status_code == 200

    body = response.json()
    assert body["source"] == "leave_tool"
    assert "3.5" in body["answer"]
    assert "12.0" in body["answer"]
