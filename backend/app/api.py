import json
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import TypeAdapter, ValidationError

from app.catalog import TOOLS
from app.schemas import (
    DateTimeResult,
    ErrorResponse,
    ExifCatalogResult,
    ExifChange,
    ExifInspectResult,
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
from app import exif, services


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


def _image_bytes(image: UploadFile) -> bytes:
    data = image.file.read(exif.MAX_IMAGE_BYTES + 1)
    if len(data) > exif.MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="图片不能超过 20 MB")
    if not data:
        raise services.ToolInputError("请选择图片文件")
    expected = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".webp": "WEBP"}.get(
        Path(image.filename or "").suffix.lower()
    )
    if expected is None or exif.detect_format(data) != expected:
        raise services.ToolInputError("文件名与图片实际格式不匹配")
    return data


@router.post("/exif/inspect", response_model=ExifInspectResult, tags=["EXIF"])
def exif_inspect(image: UploadFile = File(...)) -> dict:
    return exif.inspect(_image_bytes(image))


@router.get("/exif/tags", response_model=ExifCatalogResult, tags=["EXIF"])
def exif_tags(q: str = Query(default="", max_length=100)) -> dict:
    return {"tags": exif.available_tags(q)}


@router.post("/exif/edit", tags=["EXIF"], responses={200: {"content": {"image/jpeg": {}, "image/png": {}, "image/webp": {}}}})
def exif_edit(image: UploadFile = File(...), changes: str = Form(...)) -> Response:
    try:
        parsed = TypeAdapter(list[ExifChange]).validate_python(json.loads(changes))
    except (ValueError, ValidationError) as exc:
        raise HTTPException(status_code=422, detail="changes 必须是有效的 EXIF 操作数组") from exc
    output, mime_type, suffix = exif.edit(_image_bytes(image), [item.model_dump() for item in parsed])
    return Response(
        content=output, media_type=mime_type,
        headers={"Content-Disposition": f'attachment; filename="edited-exif{suffix}"'},
    )
