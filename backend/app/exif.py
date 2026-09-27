"""Transient EXIF inspection and editing through the installed ExifTool."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from functools import lru_cache
from pathlib import Path

from app.services import ToolInputError


MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_CHANGES = 100
MAX_VALUE_LENGTH = 4096
FORMATS = {
    "JPEG": (".jpg", "image/jpeg"),
    "PNG": (".png", "image/png"),
    "WEBP": (".webp", "image/webp"),
}
SAFE_GROUPS = {"IFD0", "ExifIFD", "GPS", "InteropIFD"}
BLOCKED_FLAGS = {"Unsafe", "Protected", "Permanent", "Binary", "Unknown", "Mandatory"}
BLOCKED_TYPES = ("binary", "undef", "struct")
BLOCKED_KEYS = {"IFD0:Orientation"}
TEXT_UNDEF_TAGS = {"ExifIFD:UserComment"}
TAG_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")


class ExifUnavailableError(RuntimeError):
    pass


def _run(*args: str, timeout: int = 15) -> subprocess.CompletedProcess[str]:
    executable = os.environ.get("EXIFTOOL_PATH", "exiftool")
    if not shutil.which(executable):
        raise ExifUnavailableError("服务器未安装 ExifTool")
    try:
        environment = os.environ.copy()
        environment["LC_ALL"] = "C"
        return subprocess.run(
            [executable, *args], capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout, check=False, env=environment,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ExifUnavailableError("ExifTool 处理失败或超时") from exc


def detect_format(data: bytes) -> str:
    if data.startswith(b"\xff\xd8\xff"):
        return "JPEG"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "WEBP"
    raise ToolInputError("仅支持 JPEG、PNG 和 WebP 图片")


def validate_file(path: Path, expected: str) -> None:
    result = _run("-s3", "-FileType", "--", str(path))
    detected = result.stdout.strip().upper()
    if result.returncode != 0 or detected not in ({"WEBP", "EXTENDED WEBP"} if expected == "WEBP" else {expected}):
        raise ToolInputError("图片内容无效或文件格式不匹配")


@lru_cache(maxsize=1)
def tag_catalog() -> dict[str, dict[str, str | bool]]:
    result = _run("-s", "-f", "-listx", "-EXIF:All", timeout=30)
    if result.returncode != 0:
        raise ExifUnavailableError("无法读取 ExifTool 标签目录")
    try:
        root = ET.fromstring(result.stdout)
    except ET.ParseError as exc:
        raise ExifUnavailableError("ExifTool 标签目录无效") from exc
    catalog: dict[str, dict[str, str | bool]] = {}
    for table in root.iter():
        if table.tag.rsplit("}", 1)[-1] != "table" or table.get("g0") != "EXIF":
            continue
        for tag in table:
            if tag.tag.rsplit("}", 1)[-1] != "tag":
                continue
            group = tag.get("g1", table.get("g1", ""))
            if group not in SAFE_GROUPS:
                continue
            name = tag.get("name", "")
            if not TAG_NAME.fullmatch(name):
                continue
            flags = set(tag.get("flags", "").split(","))
            value_type = tag.get("type", "")
            writable = (
                tag.get("writable") == "true"
                and not flags.intersection(BLOCKED_FLAGS)
                and (f"{group}:{name}" in TEXT_UNDEF_TAGS or not any(item in value_type.casefold() for item in BLOCKED_TYPES))
                and f"{group}:{name}" not in BLOCKED_KEYS
            )
            key = f"{group}:{name}"
            candidate: dict[str, str | bool] = {
                "key": key, "group": group, "name": name,
                "type": value_type, "writable": writable,
            }
            if key not in catalog or (writable and not catalog[key]["writable"]):
                catalog[key] = candidate
    if not catalog:
        raise ExifUnavailableError("ExifTool 未返回可用的 EXIF 标签目录")
    return catalog


def _metadata(path: Path) -> list[dict[str, str | bool]]:
    result = _run("-j", "-a", "-G0:1", "-s", "-n", "-EXIF:All", "--", str(path))
    if result.returncode != 0:
        raise ToolInputError("无法读取图片 EXIF 信息")
    try:
        payload = json.loads(result.stdout)[0]
    except (ValueError, IndexError, TypeError) as exc:
        raise ToolInputError("图片 EXIF 信息无效") from exc
    catalog = tag_catalog()
    tags: list[dict[str, str | bool]] = []
    for raw_key, raw_value in payload.items():
        if not raw_key.startswith("EXIF:"):
            continue
        parts = raw_key.split(":", 2)
        if len(parts) != 3:
            continue
        _, group, name = parts
        key = f"{group}:{name}"
        definition = catalog.get(key)
        scalar = isinstance(raw_value, (str, int, float)) and not isinstance(raw_value, bool)
        writable = bool(definition and definition["writable"] and scalar)
        tags.append({
            "key": key, "group": group, "name": name,
            "value": str(raw_value) if scalar else json.dumps(raw_value, ensure_ascii=False),
            "writable": writable,
            "reason": "" if writable else "该标签为只读、受限或包含二进制／结构性内容",
        })
    return sorted(tags, key=lambda item: (str(item["group"]), str(item["name"])))


def inspect(data: bytes) -> dict[str, object]:
    file_format = detect_format(data)
    with tempfile.TemporaryDirectory(prefix="superbox-exif-") as folder:
        path = Path(folder) / ("image" + FORMATS[file_format][0])
        path.write_bytes(data)
        validate_file(path, file_format)
        return {"format": file_format, "tags": _metadata(path)}


def available_tags(query: str = "") -> list[dict[str, str | bool]]:
    needle = query.strip().casefold()
    entries = (tag for tag in tag_catalog().values() if tag["writable"])
    return sorted(
        (tag for tag in entries if needle in str(tag["key"]).casefold()),
        key=lambda tag: str(tag["key"]),
    )[:100]


def edit(data: bytes, changes: list[dict[str, str]]) -> tuple[bytes, str, str]:
    file_format = detect_format(data)
    if not changes or len(changes) > MAX_CHANGES:
        raise ToolInputError("请提交 1 至 100 项 EXIF 修改")
    catalog = tag_catalog()
    arguments: list[str] = []
    seen: set[str] = set()
    for change in changes:
        key = change["key"]
        action = change["action"]
        value = change.get("value", "")
        if key in seen or key not in catalog or not catalog[key]["writable"]:
            raise ToolInputError(f"标签不可编辑或重复：{key}")
        if action not in {"set", "delete"} or (action == "set" and (not value or len(value) > MAX_VALUE_LENGTH)):
            raise ToolInputError(f"标签操作或值无效：{key}")
        seen.add(key)
        arguments.append(f"-{key}={value if action == 'set' else ''}")
    with tempfile.TemporaryDirectory(prefix="superbox-exif-") as folder:
        suffix, mime_type = FORMATS[file_format]
        source = Path(folder) / ("source" + suffix)
        target = Path(folder) / ("edited" + suffix)
        source.write_bytes(data)
        validate_file(source, file_format)
        shutil.copyfile(source, target)
        result = _run("-overwrite_original", "-n", *arguments, "--", str(target), timeout=30)
        if result.returncode != 0 or "error" in result.stderr.casefold() or "warning" in result.stderr.casefold():
            message = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "EXIF 写入失败"
            raise ToolInputError(message[:300])
        validate_file(target, file_format)
        updated = {str(tag["key"]): tag for tag in _metadata(target)}
        for change in changes:
            key = change["key"]
            if change["action"] == "set" and key not in updated:
                raise ToolInputError(f"标签写入后未找到：{key}")
            if change["action"] == "delete" and key in updated:
                raise ToolInputError(f"标签删除后仍存在：{key}")
        return target.read_bytes(), mime_type, suffix
