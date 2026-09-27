import base64
import binascii
import json
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from urllib.parse import quote, unquote


EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
INVALID_PERCENT_ESCAPE = re.compile(r"%(?![0-9A-Fa-f]{2})")
INTEGER = re.compile(r"^[+-]?\d+$")


class ToolInputError(ValueError):
    pass


def _reject_non_json_constant(value: str) -> None:
    raise ValueError(f"{value} 不是有效的 JSON 值")


def parse_json(text: str):
    try:
        return json.loads(text, parse_constant=_reject_non_json_constant)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ToolInputError(f"JSON 无效：{exc}") from exc


def format_json(text: str) -> str:
    return json.dumps(parse_json(text), ensure_ascii=False, allow_nan=False, indent=2)


def minify_json(text: str) -> str:
    return json.dumps(
        parse_json(text), ensure_ascii=False, allow_nan=False, separators=(",", ":")
    )


def validate_json(text: str) -> tuple[bool, str]:
    try:
        parse_json(text)
    except ToolInputError as exc:
        return False, str(exc)
    return True, "JSON 格式有效"


def encode_base64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def decode_base64(text: str) -> str:
    try:
        decoded = base64.b64decode(text, validate=True)
        return decoded.decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
        raise ToolInputError("Base64 无效，或解码结果不是 UTF-8 文本") from exc


def encode_url_component(text: str) -> str:
    return quote(text, safe="-_.!~*'()")


def decode_url_component(text: str) -> str:
    if INVALID_PERCENT_ESCAPE.search(text):
        raise ToolInputError("URL 编码包含无效的百分号转义")
    try:
        return unquote(text, encoding="utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ToolInputError("URL 编码不是有效的 UTF-8 文本") from exc


def _iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def timestamp_to_datetime(value: str, unit: str) -> str:
    if not INTEGER.fullmatch(value.strip()):
        raise ToolInputError("时间戳必须是整数")
    try:
        amount = int(value)
        delta = timedelta(seconds=amount) if unit == "seconds" else timedelta(milliseconds=amount)
        return _iso_utc(EPOCH + delta)
    except (OverflowError, ValueError) as exc:
        raise ToolInputError("时间戳超出支持的日期范围") from exc


def _decimal_string(value: Decimal) -> str:
    return format(value.normalize(), "f")


def datetime_to_timestamp(value: str) -> tuple[str, str, str]:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ToolInputError("请输入有效的 ISO 8601 日期时间") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ToolInputError("日期时间必须包含时区偏移或 Z")
    utc_value = parsed.astimezone(timezone.utc)
    delta = utc_value - EPOCH
    total_microseconds = (
        (delta.days * 86_400 + delta.seconds) * 1_000_000 + delta.microseconds
    )
    seconds = _decimal_string(Decimal(total_microseconds) / Decimal(1_000_000))
    milliseconds = _decimal_string(Decimal(total_microseconds) / Decimal(1_000))
    return _iso_utc(utc_value), seconds, milliseconds
