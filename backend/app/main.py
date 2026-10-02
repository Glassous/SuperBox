from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import router
from app.exif import ExifUnavailableError
from app.services import ToolInputError
from app.tool_errors import ToolFailure
from app.documents import DocumentAdmission
from app.file_storage import lifespan


app = FastAPI(
    title="Superbox API",
    description="工具箱的版本化 HTTP 接口。所有工具计算均在服务端完成。",
    version="1.3.0",
    lifespan=lifespan,
    openapi_url="/api/v1/openapi.json",
)

app.add_middleware(DocumentAdmission)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)


@app.exception_handler(ToolFailure)
async def tool_failure(_request: Request, exc: ToolFailure) -> JSONResponse:
    return JSONResponse(status_code=exc.status, content={"code": exc.code, "message": str(exc)},
                        headers={"Retry-After": "2"} if exc.status == 429 else None)


@app.exception_handler(ExifUnavailableError)
async def exif_unavailable(_request: Request, exc: ExifUnavailableError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"code": "EXIF_UNAVAILABLE", "message": str(exc)})


@app.exception_handler(ToolInputError)
async def tool_input_error(_request: Request, exc: ToolInputError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"code": "INVALID_INPUT", "message": str(exc)},
    )


@app.exception_handler(RequestValidationError)
async def request_validation_error(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    details = [
        {"field": ".".join(map(str, error["loc"])), "message": error["msg"]}
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "code": "VALIDATION_ERROR",
            "message": "请求参数无效",
            "details": details,
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_error(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": "NOT_FOUND" if exc.status_code == 404 else "FILE_TOO_LARGE" if exc.status_code == 413 else "VALIDATION_ERROR" if exc.status_code == 422 else "HTTP_ERROR",
            "message": str(exc.detail),
        },
    )


app.include_router(router)
