
from typing import Optional, Dict, Any, Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=3000)
    employee_id: str = Field(min_length=1)


class ChatResponse(BaseModel):
    answer: str
    source: str = "assistant"
    needs_confirmation: bool = False
    pending_action: Optional[Dict[str, Any]] = None


class LeaveRequest(BaseModel):
    employee_id: str = Field(min_length=1)
    start_date: str = Field(
        description="Leave start date in YYYY-MM-DD format"
    )
    end_date: str = Field(
        description="Leave end date in YYYY-MM-DD format"
    )
    leave_type: Literal["annual", "sick"] = "annual"
    reason: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=500
    )


class LeaveConfirmationRequest(BaseModel):
    employee_id: str = Field(min_length=1)
    confirmation_token: str = Field(min_length=1)


class LeaveCancellationRequest(BaseModel):
    employee_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    confirmation_token: str = Field(min_length=1)
