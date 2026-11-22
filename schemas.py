"""Validated API input and output schemas."""
from datetime import date
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class EventCreate(BaseModel):
    """Fields required when creating or replacing an event."""
    model_config = ConfigDict(str_strip_whitespace=True, json_schema_extra={"example": {"title": "Python Workshop", "description": "Learn FastAPI", "date": "2027-06-10", "location": "Conference Room", "max_capacity": 30}})
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    date: date
    location: str = Field(min_length=1, max_length=200)
    max_capacity: int = Field(gt=0, le=100000)


class EventUpdate(EventCreate):
    """Complete replacement payload for PUT."""


class EventRead(EventCreate):
    """An event returned by the API."""
    model_config = ConfigDict(from_attributes=True)
    id: int


class RegistrationCreate(BaseModel):
    """Employee information needed to register."""
    model_config = ConfigDict(str_strip_whitespace=True, json_schema_extra={"example": {"employee_name": "Ali Khan", "employee_email": "ali@example.com"}})
    employee_name: str = Field(min_length=1, max_length=200)
    employee_email: EmailStr

    @field_validator("employee_email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        """Treat email addresses as case-insensitive employee identifiers."""
        return value.lower()


class RegistrationRead(RegistrationCreate):
    """A saved registration."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    event_id: int


class Token(BaseModel):
    """Bearer access token returned by login."""
    access_token: str
    token_type: str = "bearer"
