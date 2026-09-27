from typing import Literal

from pydantic import BaseModel, Field


MAX_TEXT_LENGTH = 1_000_000


class TextInput(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)


class TextResult(BaseModel):
    result: str


class JsonValidationResult(BaseModel):
    valid: bool
    message: str


class UnixTimestampInput(BaseModel):
    value: str = Field(min_length=1, max_length=40)
    unit: Literal["seconds", "milliseconds"]


class IsoDateTimeInput(BaseModel):
    iso_datetime: str = Field(min_length=1, max_length=80)


class DateTimeResult(BaseModel):
    iso_utc: str


class UnixTimestampResult(BaseModel):
    iso_utc: str
    seconds: str
    milliseconds: str


class ToolMetadata(BaseModel):
    slug: str
    name: str
    category: str
    description: str
    keywords: list[str]


class ToolCatalogResult(BaseModel):
    tools: list[ToolMetadata]


class HealthResult(BaseModel):
    status: Literal["ok"]


class ErrorDetail(BaseModel):
    field: str
    message: str


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] | None = None


class ExifTag(BaseModel):
    key: str
    group: str
    name: str
    value: str
    writable: bool
    reason: str


class ExifInspectResult(BaseModel):
    format: Literal["JPEG", "PNG", "WEBP"]
    tags: list[ExifTag]


class ExifCatalogTag(BaseModel):
    key: str
    group: str
    name: str
    type: str
    writable: bool


class ExifCatalogResult(BaseModel):
    tags: list[ExifCatalogTag]


class ExifChange(BaseModel):
    key: str = Field(min_length=1, max_length=100)
    action: Literal["set", "delete"]
    value: str = Field(default="", max_length=4096)
