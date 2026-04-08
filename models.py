from __future__ import annotations

from pydantic import BaseModel, Field


class StartSessionRequest(BaseModel):
    courseCode: str = Field(min_length=2, max_length=20)
    durationMinutes: int = Field(ge=1, le=360)
    secret: str


class EndSessionRequest(BaseModel):
    secret: str


class SubmitAttendanceRequest(BaseModel):
    rollNumber: str = Field(min_length=4, max_length=15)
    token: str
    sessionId: str

