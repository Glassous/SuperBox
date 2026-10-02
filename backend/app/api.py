import json
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response
from pydantic import TypeAdapter, ValidationError

from app.catalog import TOOLS
from app.skill import build_skill_manifest, build_skill_markdown
from app.schemas import (
    DateTimeResult,
    ErrorResponse,
    ExifCatalogResult,
    ExifChange,
    ExifInspectResult,
    FileResult,
    HealthResult,
    IsoDateTimeInput,
    JsonValidationResult,
    TextInput,
    TextResult,
    ToolCatalogResult,
    ToolMetadata,
    UnixTimestampInput,
    UnixTimestampResult,
    CurrentTimeResult, CurrencyInput, CurrencyCatalogResult, CurrencyResult, DocumentResult,
    CurrencyBatchInput, CurrencyBatchResult,
)
from app import exif, image_source, services, current_time, currency, documents, file_storage


router = APIRouter(
    prefix="/api/v1",
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)


@router.get("/time/now", response_model=CurrentTimeResult, tags=["Time"])
def current_datetime(response: Response) -> dict:
    response.headers["Cache-Control"] = "no-store"
    return current_time.now()


@router.get("/currency/currencies", response_model=CurrencyCatalogResult, tags=["Currency"],
            responses={503: {"model": ErrorResponse}, 429: {"model": ErrorResponse}})
async def supported_currencies() -> dict:
    return await currency.service.currencies()


@router.post("/currency/convert", response_model=CurrencyResult, tags=["Currency"],
             responses={503: {"model": ErrorResponse}, 429: {"model": ErrorResponse}})
async def convert_currency(body: CurrencyInput) -> dict:
    return await currency.service.convert(body)


@router.post("/currency/convert-batch", response_model=CurrencyBatchResult, tags=["Currency"],
             responses={503: {"model": ErrorResponse}, 429: {"model": ErrorResponse}})
async def convert_currencies(body: CurrencyBatchInput) -> dict:
    return await currency.service.convert_batch(body)


@router.post("/documents/convert", response_model=DocumentResult, tags=["Documents"],
             responses={413: {"model": ErrorResponse}, 429: {"model": ErrorResponse},
                        503: {"model": ErrorResponse}, 504: {"model": ErrorResponse}})
async def convert_document(
    request: Request,
    file: UploadFile | None = File(default=None),
    file_url: str = Form(default="", max_length=2048),
    format: Literal["markdown", "txt"] = Form(default="markdown"),
) -> dict:
    return await documents.convert(file, file_url, format, request)


@router.get("/health", response_model=HealthResult, tags=["System"])
def health() -> HealthResult:
    return HealthResult(status="ok")


@router.get("/skill", responses={200: {"content": {"text/markdown": {}}}}, tags=["System"])
def get_skill(request: Request) -> Response:
    return Response(
        content=build_skill_markdown(str(request.base_url)),
        media_type="text/markdown; charset=utf-8",
    )


@router.get(
    "/skill.json",
    responses={200: {"content": {"application/json": {}}}},
    tags=["System"],
)
def get_skill_manifest(request: Request) -> dict:
    return build_skill_manifest(str(request.base_url))


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


def _request_bytes(image: UploadFile | None, image_url: str) -> bytes:
    link = image_url.strip()
    if image is not None and image.filename:
        if link:
            raise services.ToolInputError("请只提供图片文件或图片链接中的一种")
        return _image_bytes(image)
    if not link:
        raise services.ToolInputError("请选择图片文件或填写图片链接")
    try:
        return image_source.fetch_image(link, exif.MAX_IMAGE_BYTES)
    except image_source.ImageTooLargeError as exc:
        raise HTTPException(status_code=413, detail="图片不能超过 20 MB") from exc


@router.post("/exif/inspect", response_model=ExifInspectResult, tags=["EXIF"])
def exif_inspect(
    image: UploadFile | None = File(default=None),
    image_url: str = Form(default="", max_length=image_source.MAX_URL_LENGTH),
) -> dict:
    return exif.inspect(_request_bytes(image, image_url))


@router.get("/exif/tags", response_model=ExifCatalogResult, tags=["EXIF"])
def exif_tags(q: str = Query(default="", max_length=100)) -> dict:
    return {"tags": exif.available_tags(q)}


@router.post("/exif/edit", response_model=FileResult, tags=["EXIF"],
             responses={413: {"model": ErrorResponse}, 503: {"model": ErrorResponse}})
def exif_edit(
    changes: str = Form(...),
    image: UploadFile | None = File(default=None),
    image_url: str = Form(default="", max_length=image_source.MAX_URL_LENGTH),
) -> dict:
    try:
        parsed = TypeAdapter(list[ExifChange]).validate_python(json.loads(changes))
    except (ValueError, ValidationError) as exc:
        raise HTTPException(status_code=422, detail="changes 必须是有效的 EXIF 操作数组") from exc
    output, mime_type, suffix = exif.edit(
        _request_bytes(image, image_url), [item.model_dump() for item in parsed]
    )
    return file_storage.upload(output, f"edited-exif{suffix}", mime_type)
