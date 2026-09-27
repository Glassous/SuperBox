from fastapi import APIRouter, HTTPException, Query

from app.catalog import TOOLS
from app.schemas import (
    DateTimeResult,
    ErrorResponse,
    HealthResult,
    IsoDateTimeInput,
    JsonValidationResult,
    TextInput,
    TextResult,
    ToolCatalogResult,
    ToolMetadata,
    UnixTimestampInput,
    UnixTimestampResult,
)
from app import services


router = APIRouter(
    prefix="/api/v1",
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)


@router.get("/health", response_model=HealthResult, tags=["System"])
def health() -> HealthResult:
    return HealthResult(status="ok")


@router.get("/tools", response_model=ToolCatalogResult, tags=["Catalog"])
def list_tools(q: str = Query(default="", max_length=100)) -> dict:
    query = q.strip().casefold()
    if not query:
        return {"tools": TOOLS}
    matches = [
        tool
        for tool in TOOLS
        if query in " ".join(
            [tool["name"], tool["category"], tool["description"], *tool["keywords"]]
        ).casefold()
    ]
    return {"tools": matches}


@router.get("/tools/{slug}", response_model=ToolMetadata, tags=["Catalog"])
def get_tool(slug: str) -> dict:
    tool = next((item for item in TOOLS if item["slug"] == slug), None)
    if tool is None:
        raise HTTPException(status_code=404, detail="工具不存在")
    return tool


@router.post("/json/format", response_model=TextResult, tags=["JSON"])
def json_format(body: TextInput) -> TextResult:
    return TextResult(result=services.format_json(body.text))


@router.post("/json/minify", response_model=TextResult, tags=["JSON"])
def json_minify(body: TextInput) -> TextResult:
    return TextResult(result=services.minify_json(body.text))


@router.post("/json/validate", response_model=JsonValidationResult, tags=["JSON"])
def json_validate(body: TextInput) -> JsonValidationResult:
    valid, message = services.validate_json(body.text)
    return JsonValidationResult(valid=valid, message=message)


@router.post("/base64/encode", response_model=TextResult, tags=["Base64"])
def base64_encode(body: TextInput) -> TextResult:
    return TextResult(result=services.encode_base64(body.text))


@router.post("/base64/decode", response_model=TextResult, tags=["Base64"])
def base64_decode(body: TextInput) -> TextResult:
    return TextResult(result=services.decode_base64(body.text))


@router.post("/url/encode", response_model=TextResult, tags=["URL"])
def url_encode(body: TextInput) -> TextResult:
    return TextResult(result=services.encode_url_component(body.text))


@router.post("/url/decode", response_model=TextResult, tags=["URL"])
def url_decode(body: TextInput) -> TextResult:
    return TextResult(result=services.decode_url_component(body.text))


@router.post("/timestamp/to-datetime", response_model=DateTimeResult, tags=["Timestamp"])
def to_datetime(body: UnixTimestampInput) -> DateTimeResult:
    return DateTimeResult(iso_utc=services.timestamp_to_datetime(body.value, body.unit))


@router.post("/timestamp/to-unix", response_model=UnixTimestampResult, tags=["Timestamp"])
def to_unix(body: IsoDateTimeInput) -> UnixTimestampResult:
    iso_utc, seconds, milliseconds = services.datetime_to_timestamp(body.iso_datetime)
    return UnixTimestampResult(
        iso_utc=iso_utc, seconds=seconds, milliseconds=milliseconds
    )
