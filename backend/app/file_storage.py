"""Temporary processed files in Tencent Cloud COS, with restart-safe expiry."""

import asyncio
import logging
import os
import re
import time
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timezone
from functools import lru_cache
from threading import Event
from urllib.parse import quote, urlsplit
from uuid import uuid4

from app.tool_errors import ToolFailure

logger = logging.getLogger(__name__)
RETENTION_SECONDS = 2 * 60 * 60
CLEANUP_INTERVAL = 60
PREFIX = "superbox-temp/"
OBJECT_KEY = re.compile(r"^superbox-temp/(\d{10})/[0-9a-f]{32}/[^/]+$")


@lru_cache(maxsize=1)
def _configuration():
    values = {name: os.environ.get(name, "").strip() for name in (
        "COS_SECRET_ID", "COS_SECRET_KEY", "COS_BUCKET", "COS_REGION", "COS_CUSTOM_DOMAIN",
    )}
    if not all(values.values()):
        raise ToolFailure(503, "COS_UNAVAILABLE", "服务器未完整配置 COS 文件存储")
    domain = values["COS_CUSTOM_DOMAIN"]
    try:
        parsed = urlsplit(domain if "://" in domain else "https://" + domain)
        port = parsed.port
    except ValueError as exc:
        raise ToolFailure(503, "COS_UNAVAILABLE", "COS 文件域名配置无效") from exc
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
            or port not in (None, 443) or parsed.path not in ("", "/") or parsed.query or parsed.fragment):
        raise ToolFailure(503, "COS_UNAVAILABLE", "COS 文件域名配置无效")
    try:
        from qcloud_cos import CosConfig, CosS3Client
        client = CosS3Client(CosConfig(
            Region=values["COS_REGION"], SecretId=values["COS_SECRET_ID"],
            SecretKey=values["COS_SECRET_KEY"], Scheme="https", Timeout=15,
        ), retry=1)
    except Exception as exc:
        raise ToolFailure(503, "COS_UNAVAILABLE", "COS 文件存储初始化失败") from exc
    return client, values["COS_BUCKET"], "https://" + parsed.netloc


def upload(data: bytes, filename: str, content_type: str) -> dict:
    client, bucket, domain = _configuration()
    name = filename.replace("\\", "/").rsplit("/", 1)[-1]
    name = re.sub(r'[\x00-\x1f\x7f"]', "_", name) or "file"
    if name in {".", ".."}:
        name = "file"
    expires = int(time.time()) + RETENTION_SECONDS
    key = f"{PREFIX}{expires}/{uuid4().hex}/{name}"
    fallback = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    try:
        client.put_object(
            Bucket=bucket, Key=key, Body=data, ContentType=content_type,
            ContentDisposition=f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quote(name, safe='')}",
            CacheControl="no-store", EnableMD5=True,
        )
    except Exception as exc:
        logger.error("COS upload failed (%s)", type(exc).__name__)
        raise ToolFailure(503, "COS_UPLOAD_FAILED", "处理后的文件上传失败，请稍后重试") from exc
    return {
        "url": f"{domain}/{quote(key, safe='/')}", "filename": name,
        "content_type": content_type, "size": len(data),
        "expires_at": datetime.fromtimestamp(expires, timezone.utc).isoformat().replace("+00:00", "Z"),
    }


async def upload_file(data: bytes, filename: str, content_type: str) -> dict:
    return await asyncio.to_thread(upload, data, filename, content_type)


def cleanup_expired(stop: Event) -> None:
    client, bucket, _domain = _configuration()
    marker = ""
    now = int(time.time())
    while not stop.is_set():
        page = client.list_objects(Bucket=bucket, Prefix=PREFIX, Marker=marker, MaxKeys=1000)
        for item in page.get("Contents", []):
            if stop.is_set():
                return
            key = item["Key"]
            match = OBJECT_KEY.fullmatch(key)
            if match is None or int(match[1]) > now:
                continue
            try:
                client.delete_object(Bucket=bucket, Key=key)
            except Exception as exc:
                logger.error("COS expiry deletion failed (%s); will retry next scan", type(exc).__name__)
        if str(page.get("IsTruncated", "false")).lower() != "true":
            return
        next_marker = page.get("NextMarker")
        if not next_marker or next_marker == marker:
            raise RuntimeError("COS listing returned an invalid pagination marker")
        marker = next_marker


async def _cleanup_loop(stop: Event) -> None:
    while True:
        try:
            await asyncio.to_thread(cleanup_expired, stop)
        except Exception as exc:
            # Avoid SDK exception text: it can contain signed request URLs.
            logger.warning("COS expiry scan unavailable (%s); will retry next scan", type(exc).__name__)
        await asyncio.sleep(CLEANUP_INTERVAL)


@asynccontextmanager
async def lifespan(_app):
    stop = Event()
    task = asyncio.create_task(_cleanup_loop(stop))
    try:
        yield
    finally:
        stop.set()
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
