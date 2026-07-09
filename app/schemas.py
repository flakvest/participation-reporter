from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, field_validator


VALID_MONTHS = {"JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"}
PLATOONS = {"1PLT", "2PLT"}
YES_NO = {"YES", "NO"}
ROLES = {"operator", "platoon_leader", "admin"}


class UserCreate(BaseModel):
    callsign: str
    password: str
    platoon: str

    @field_validator("callsign")
    @classmethod
    def callsign_upper(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("platoon")
    @classmethod
    def valid_platoon(cls, v: str) -> str:
        v = v.strip().upper()
        if v not in PLATOONS:
            raise ValueError(f"Platoon must be one of {PLATOONS}")
        return v


class UserOut(BaseModel):
    id: int
    callsign: str
    platoon: str
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str


class LoginRequest(BaseModel):
    callsign: str
    password: str


MONTH_ORDER = {"JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6, "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12}


def infer_year(month: str) -> int:
    now = datetime.now(timezone.utc)
    current_month_num = now.month
    reported_month_num = MONTH_ORDER.get(month.upper(), 0)
    if reported_month_num > current_month_num:
        return now.year - 1
    return now.year


class ParsedReport(BaseModel):
    platoon: str
    callsign: str
    month: str
    year: int = 2026
    equipment_ok: str
    skills_ok: str
    total_hf_hours: int
    j0g_hours: int
    gst_hours: int
    other_hf_hours: int
    total_mars_hours: int
    notes: str
    raw_strip: str


class ReportOut(BaseModel):
    id: int
    platoon: str
    callsign: str
    month: str
    year: int
    equipment_ok: str
    skills_ok: str
    total_hf_hours: int
    j0g_hours: int
    gst_hours: int
    other_hf_hours: int
    total_mars_hours: int
    notes: str
    submission_source: str
    duplicate_flag: bool
    submitted_by: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ParseResult(BaseModel):
    success: bool
    reports: list[ParsedReport]
    errors: list[str]
