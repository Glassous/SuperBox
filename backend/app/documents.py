import asyncio
import json
import signal
import sys
import tempfile
from pathlib import Path
from urllib.parse import unquote, urlsplit

from starlette.responses import JSONResponse

from app.services import ToolInputError
from app.tool_errors import ToolFailure
from app import file_storage

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_BODY_BYTES = 6 * 1024 * 1024
PARSE_TIMEOUT = 15


class DocumentAdmission:
    """Admit one request BEFORE buffering/parsing its multipart body."""
    def __init__(self, app):
        self.app = app
        self.busy = False

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] != "POST" or scope["path"].rstrip("/") != "/api/v1/documents/convert":
            return await self.app(scope, receive, send)
        if self.busy:
            return await JSONResponse({"code": "TOOL_BUSY", "message": "文件转换繁忙，请稍后重试"}, 429,
                                      headers={"Retry-After": "2"})(scope, receive, send)
        self.busy = True
        try:
            with tempfile.SpooledTemporaryFile(max_size=1024 * 1024) as body:
                total = 0
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    chunk = message.get("body", b"")
                    total += len(chunk)
                    if total > MAX_BODY_BYTES:
                        return await JSONResponse({"code": "FILE_TOO_LARGE", "message": "转换请求体不能超过 6 MiB"}, 413)(scope, receive, send)
                    body.write(chunk)
                    if not message.get("more_body", False):
                        break
                body.seek(0)
                delivered = False
                async def replay():
                    nonlocal delivered
                    if delivered:
                        return await receive()
                    chunk = body.read(64 * 1024)
                    delivered = body.tell() == total
                    return {"type": "http.request", "body": chunk, "more_body": not delivered}
                await self.app(scope, replay, send)
        finally:
            self.busy = False


async def run_worker(path, fmt, filename, request=None, file_url=""):
    try:
        process = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "app.document_worker", cwd=str(Path(__file__).resolve().parents[1]),
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
        )
    except OSError as exc:
        raise ToolFailure(503, "DOCUMENT_UNAVAILABLE", "无法启动文件转换进程") from exc
    deadline = asyncio.get_running_loop().time() + (10 if file_url else PARSE_TIMEOUT)
    async def communicate():
        nonlocal deadline
        process.stdin.write(json.dumps({"path": str(path), "format": fmt, "filename": filename, "file_url": file_url}).encode())
        await process.stdin.drain()
        process.stdin.close()
        first = await process.stdout.readline()
        if first == b'{"stage":"parsing"}\n':
            deadline = asyncio.get_running_loop().time() + PARSE_TIMEOUT
            first = b""
        output = first + await process.stdout.read()
        await process.wait()
        return output
    task = asyncio.create_task(communicate())
    try:
        while not task.done():
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                raise ToolFailure(504, "DOCUMENT_TIMEOUT", "文件下载超过 10 秒或解析超过 15 秒")
            await asyncio.wait({task}, timeout=min(0.1, remaining))
            if request is not None and not task.done() and await request.is_disconnected():
                raise asyncio.CancelledError()
        output = await task
        if process.returncode:
            if process.returncode in {-getattr(signal, "SIGXCPU", 24), -getattr(signal, "SIGKILL", 9)} or process.returncode == 1816:
                raise ToolFailure(504, "DOCUMENT_TIMEOUT", "文档处理超过 CPU 时间限制")
            raise ToolFailure(413, "DOCUMENT_LIMIT_EXCEEDED", "文档处理进程超过资源限制或异常退出")
        try:
            result = json.loads(output)
        except (ValueError, UnicodeDecodeError) as exc:
            raise ToolFailure(503, "DOCUMENT_UNAVAILABLE", "文件转换进程未返回有效结果") from exc
        if "error" in result:
            error = result["error"]
            raise ToolFailure(error["status"], error["code"], error["message"])
        return result
    finally:
        if process.returncode is None:
            try:
                process.kill()
            except ProcessLookupError:
                pass
        await process.wait()
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)


async def convert(file, file_url, fmt, request):
    link = file_url.strip()
    if bool(file and file.filename) == bool(link):
        raise ToolInputError("请只提供 file 文件或 file_url 文件链接中的一种")
    with tempfile.TemporaryDirectory(prefix="superbox-document-") as directory:
        path = Path(directory) / "input"
        if link:
            name = Path(unquote(urlsplit(link).path)).name or "document"
            # Signed/opaque download routes need not have a file extension.
            if Path(name).suffix.lower() not in {".pdf", ".docx", ".xlsx"}:
                name = "document"
        else:
            name = Path(file.filename.replace("\\", "/")).name
            total = 0
            with path.open("wb") as target:
                while chunk := await file.read(64 * 1024):
                    total += len(chunk)
                    if total > MAX_FILE_BYTES:
                        raise ToolFailure(413, "FILE_TOO_LARGE", "文件不能超过 5 MiB")
                    target.write(chunk)
        if not link and path.stat().st_size == 0:
            raise ToolInputError("文件不能为空")
        result = await run_worker(path, fmt, name, request, file_url=link)
        content_type = "text/markdown; charset=utf-8" if fmt == "markdown" else "text/plain; charset=utf-8"
        result.update(await file_storage.upload_file(result["result"].encode("utf-8"), result["filename"], content_type))
        return result
