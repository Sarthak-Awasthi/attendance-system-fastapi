from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


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


class UpsertCourseRequest(BaseModel):
    code: str = Field(min_length=2, max_length=20)
    name: str = Field(min_length=2, max_length=120)
    originalCode: str | None = Field(default=None, max_length=20)
    secret: str

    @field_validator("code")
    @classmethod
    def _normalize_code(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("name")
    @classmethod
    def _normalize_name(cls, value: str) -> str:
        return value.strip()


class DeleteCourseRequest(BaseModel):
    secret: str


class UpdateTeacherSettingsRequest(BaseModel):
    secret: str
    excelDataDir: str = Field(min_length=1, max_length=240)
    defaultSessionDurationMinutes: int = Field(ge=1, le=360)
    qrRotateIntervalSec: int = Field(ge=1, le=120)
    baseUrl: str = Field(min_length=8, max_length=200)

    @field_validator("excelDataDir")
    @classmethod
    def _normalize_excel_dir(cls, value: str) -> str:
        return value.strip()

    @field_validator("baseUrl")
    @classmethod
    def _normalize_base_url(cls, value: str) -> str:
        return value.strip().rstrip("/")


class UpdateTeacherSecretRequest(BaseModel):
    oldSecret: str = Field(min_length=1, max_length=120)
    newSecret: str = Field(min_length=4, max_length=120)
    confirmNewSecret: str = Field(min_length=4, max_length=120)

    @field_validator("oldSecret", "newSecret", "confirmNewSecret")
    @classmethod
    def _normalize_secret_fields(cls, value: str) -> str:
        return value.strip()


