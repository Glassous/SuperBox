"""Download remote images for the EXIF tool with SSRF safeguards."""

from __future__ import annotations

import http.client
import ipaddress
import socket
import ssl
from urllib.parse import SplitResult, urljoin, urlsplit

from app.services import ToolInputError


MAX_URL_LENGTH = 2048
MAX_REDIRECTS = 3
FETCH_TIMEOUT = 10.0
CHUNK_BYTES = 64 * 1024
STANDARD_PORTS = {"http": 80, "https": 443}
REDIRECT_STATUSES = {301, 302, 303, 307, 308}
SHARED_ADDRESS_SPACE = ipaddress.ip_network("100.64.0.0/10")
USER_AGENT = "Superbox/1.0"


class ImageTooLargeError(ToolInputError):
    pass


def fetch_image(url: str, max_bytes: int) -> bytes:
    """Download one image over http(s), following at most MAX_REDIRECTS hops."""
    target = url.strip()
    for _ in range(MAX_REDIRECTS + 1):
        parts = _parse(target)
        status, location, data = _download(parts, max_bytes)
        if status in REDIRECT_STATUSES:
            if not location:
                raise ToolInputError("图片链接重定向缺少目标地址")
            target = urljoin(target, location)
            continue
        if status != 200:
            raise ToolInputError(f"图片链接返回 HTTP {status}")
        return data
    raise ToolInputError("图片链接重定向次数过多")


def _parse(url: str) -> SplitResult:
    if not url or len(url) > MAX_URL_LENGTH:
        raise ToolInputError("图片链接不能为空且不能超过 2048 字符")
    parts = urlsplit(url)
    if parts.scheme not in STANDARD_PORTS:
        raise ToolInputError("图片链接必须以 http:// 或 https:// 开头")
    if parts.username or parts.password:
        raise ToolInputError("图片链接不能包含用户名或密码")
    if not parts.hostname:
        raise ToolInputError("图片链接缺少主机名")
    if _port(parts) not in STANDARD_PORTS.values():
        raise ToolInputError("图片链接只支持 80 或 443 端口")
    return parts


def _port(parts: SplitResult) -> int:
    try:
        return parts.port or STANDARD_PORTS[parts.scheme]
    except ValueError as exc:
        raise ToolInputError("图片链接的端口无效") from exc


def _path(parts: SplitResult) -> str:
    path = parts.path or "/"
    return f"{path}?{parts.query}" if parts.query else path


def _resolve(host: str, port: int) -> list[str]:
    try:
        records = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise ToolInputError("无法解析图片链接的主机名") from exc
    addresses: list[str] = []
    for record in records:
        address = public_address(record[4][0])
        if address not in addresses:
            addresses.append(address)
    if not addresses:
        raise ToolInputError("无法解析图片链接的主机名")
    return addresses


def public_address(value: str) -> str:
    """Return a globally routable address, rejecting private and internal ranges."""
    try:
        address = ipaddress.ip_address(value)
    except ValueError as exc:
        raise ToolInputError("图片链接的主机地址无效") from exc
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        address = address.ipv4_mapped
    blocked = (
        not address.is_global
        or address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
        or (isinstance(address, ipaddress.IPv4Address) and address in SHARED_ADDRESS_SPACE)
    )
    if blocked:
        raise ToolInputError("图片链接指向的地址不允许访问")
    return str(address)


def _connect(parts: SplitResult, port: int, address: str) -> http.client.HTTPConnection:
    host = parts.hostname or ""
    raw = socket.create_connection((address, port), FETCH_TIMEOUT)
    if parts.scheme == "https":
        context = ssl.create_default_context()
        connection = http.client.HTTPSConnection(host, port, timeout=FETCH_TIMEOUT, context=context)
        connection.sock = context.wrap_socket(raw, server_hostname=host)
    else:
        connection = http.client.HTTPConnection(host, port, timeout=FETCH_TIMEOUT)
        connection.sock = raw
    return connection


def _read_body(response: http.client.HTTPResponse, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = response.read(CHUNK_BYTES)
        if not chunk:
            return b"".join(chunks)
        total += len(chunk)
        if total > max_bytes:
            raise ImageTooLargeError("图片不能超过 20 MB")
        chunks.append(chunk)


def _download(parts: SplitResult, max_bytes: int) -> tuple[int, str, bytes]:
    host = parts.hostname or ""
    port = _port(parts)
    addresses = _resolve(host, port)
    last_error: Exception | None = None
    for address in addresses:
        try:
            connection = _connect(parts, port, address)
        except OSError as exc:
            last_error = exc
            continue
        try:
            connection.request(
                "GET", _path(parts),
                headers={"User-Agent": USER_AGENT, "Accept": "image/*,*/*;q=0.8"},
            )
            response = connection.getresponse()
            if response.status in REDIRECT_STATUSES:
                return response.status, response.getheader("Location") or "", b""
            if response.status != 200:
                return response.status, "", b""
            return response.status, "", _read_body(response, max_bytes)
        except (OSError, http.client.HTTPException) as exc:
            last_error = exc
        finally:
            connection.close()
    raise ToolInputError("无法下载图片链接") from last_error
