from typing import NotRequired, TypedDict


class Endpoint(TypedDict):
    method: str
    path: str
    name: str
    summary: str
    request: str
    response_example: str
    request_format: NotRequired[str]
    request_example: NotRequired[str]
    request_language: NotRequired[str]
    response_language: NotRequired[str]
    response_label: NotRequired[str]


class ErrorContractEntry(TypedDict):
    status: int
    code: str
    meaning: str


SKILL_VERSION = "1.0.0"

SKILL_DESCRIPTION = (
    "Superbox 是由 FastAPI 提供工具能力的开发工具箱：JSON 格式化与校验、"
    "Base64 编解码、URL 参数值编解码、Unix 时间戳转换，以及图片 EXIF 读取与编辑。"
    "所有计算均由服务端完成。本 Skill 由官方维护，覆盖当前全部对外接口，"
    "任何 AI 平台或智能体都可以直接按本文档调用，无需认证。"
)

CONVENTIONS = [
    "文本工具（JSON、Base64、URL、时间戳）使用 JSON 请求与响应：请求头 "
    "`Content-Type: application/json`，字符串输入长度为 1 至 1,000,000 个字符。",
    "图片 EXIF 工具使用 `multipart/form-data` 上传，编辑接口返回二进制图片，需按文件保存。",
    "时间戳值通过字符串传输，避免不同客户端对大整数或小数的精度差异。",
    "当前接口无需认证；CORS 允许所有来源，但不支持携带浏览器凭据的跨域请求。",
]

ERROR_EXAMPLES = [
    '{"code":"INVALID_INPUT","message":"时间戳必须是整数"}',
    '{"code":"VALIDATION_ERROR","message":"请求参数无效",'
    '"details":[{"field":"body.text","message":"String should have at least 1 character"}]}',
]

ERROR_CONTRACT: list[ErrorContractEntry] = [
    {
        "status": 400,
        "code": "INVALID_INPUT",
        "meaning": "内容无法完成对应操作，例如 JSON 语法错误、无效 Base64、时间戳非整数或超出支持范围",
    },
    {"status": 404, "code": "NOT_FOUND", "meaning": "未知接口或工具"},
    {"status": 413, "code": "FILE_TOO_LARGE", "meaning": "图片超过 20 MiB"},
    {"status": 422, "code": "VALIDATION_ERROR", "meaning": "字段缺失、类型错误或超出长度限制"},
    {"status": 503, "code": "EXIF_UNAVAILABLE", "meaning": "服务端 ExifTool 不可用"},
]

AI_GUIDANCE = [
    "直接调用 HTTP 接口完成计算，不要在客户端重写工具逻辑。",
    "校验 JSON 时读取 HTTP 200 响应中的 `valid` 字段；其余工具的无效输入返回 400，"
    "请按状态码分支处理。",
    "编辑图片前先用 `inspect` 或 `tags` 确认可写标签，再用 `edit` 提交 `changes`；"
    "`edit` 返回二进制图片，需保存为文件。",
    "失败时依据 HTTP 状态与 `code` 处理，不要解析中文提示文本。",
    "需要程序化描述时读取 OpenAPI 定义，或调用工具目录接口动态发现能力。",
]

PUBLIC_ENDPOINTS: list[Endpoint] = [
    {
        "method": "GET",
        "path": "/health",
        "name": "健康检查",
        "summary": "返回服务状态，用于探活与连通性检查。",
        "request": "无请求参数。",
        "request_format": "none",
        "response_example": '{"status":"ok"}',
    },
    {
        "method": "GET",
        "path": "/tools",
        "name": "工具目录",
        "summary": "返回全部工具的元数据，包含 slug、名称、分类、描述和关键词。",
        "request": "可选查询参数 `q`，最多 100 字符，在名称、分类、描述和关键词中搜索。",
        "request_format": "query",
        "request_example": "GET $BASE/api/v1/tools?q=编码",
        "request_language": "http",
        "response_example": (
            '{"tools":[{"slug":"base64","name":"Base64 编解码","category":"编码转换",'
            '"description":"在 UTF-8 文本与 Base64 之间转换。",'
            '"keywords":["base64","编码","解码","utf-8"]}]}'
        ),
    },
    {
        "method": "GET",
        "path": "/tools/{slug}",
        "name": "工具详情",
        "summary": "按 slug 返回单个工具的元数据；未知 slug 返回 404。",
        "request": "路径参数 `slug` 取值：json、base64、url、timestamp、exif。",
        "request_format": "path",
        "request_example": "GET $BASE/api/v1/tools/json",
        "request_language": "http",
        "response_example": (
            '{"slug":"json","name":"JSON 工具","category":"数据处理",'
            '"description":"格式化、压缩和校验 JSON 内容。",'
            '"keywords":["json","格式化","压缩","校验"]}'
        ),
    },
    {
        "method": "GET",
        "path": "/openapi.json",
        "name": "OpenAPI 定义",
        "summary": "机器可读的 OpenAPI 3 定义，供客户端代码生成器与 AI 工具读取。",
        "request": "无请求参数；paths 中包含本文档列出的全部接口。",
        "request_format": "none",
        "response_example": "OpenAPI 3 JSON 文档。",
        "response_language": "text",
    },
]


TOOL_ENDPOINTS: dict[str, list[Endpoint]] = {
    "json": [
        {
            "method": "POST",
            "path": "/json/format",
            "name": "格式化 JSON",
            "summary": "使用两个空格缩进格式化 JSON，并保留非 ASCII 字符。",
            "request": (
                "使用 JSON 请求体，`text` 为 1 至 1,000,000 字符的标准 JSON 文本，"
                "顶层对象、数组和标量均可，`NaN` 与 `Infinity` 无效。"
            ),
            "request_example": r'{"text":"{\"name\":\"中文\"}"}',
            "response_example": r'{"result":"{\n  \"name\": \"中文\"\n}"}',
        },
        {
            "method": "POST",
            "path": "/json/minify",
            "name": "压缩 JSON",
            "summary": "移除 JSON 中不必要的空白。",
            "request": "使用与格式化接口相同的 JSON 请求体。",
            "request_example": r'{"text":"{ \"a\": 1 }"}',
            "response_example": r'{"result":"{\"a\":1}"}',
        },
        {
            "method": "POST",
            "path": "/json/validate",
            "name": "校验 JSON",
            "summary": "检查 JSON 语法并返回校验结果。",
            "request": (
                "使用与格式化接口相同的 JSON 请求体；语法无效时仍返回 HTTP 200，"
                "响应中 `valid` 为 false。"
            ),
            "request_example": r'{"text":"{"}',
            "response_example": (
                r'{"valid":false,"message":"JSON 无效：Expecting property name '
                r'enclosed in double quotes: line 1 column 2 (char 1)"}'
            ),
            "response_label": "响应示例",
        },
    ],
    "base64": [
        {
            "method": "POST",
            "path": "/base64/encode",
            "name": "Base64 编码",
            "summary": "将 UTF-8 文本编码为标准 Base64。",
            "request": (
                "使用 JSON 请求体，`text` 为 1 至 1,000,000 字符的 UTF-8 文本；"
                "操作对象是文本，不处理任意二进制文件。"
            ),
            "request_example": r'{"text":"你好"}',
            "response_example": r'{"result":"5L2g5aW9"}',
        },
        {
            "method": "POST",
            "path": "/base64/decode",
            "name": "Base64 解码",
            "summary": "将标准 Base64 解码为 UTF-8 文本。",
            "request": (
                "使用 JSON 请求体，严格 Base64 校验，不接受多余空白；"
                "解码结果必须是有效 UTF-8，否则返回 400 INVALID_INPUT。"
            ),
            "request_example": r'{"text":"5L2g5aW9"}',
            "response_example": r'{"result":"你好"}',
        },
    ],
    "url": [
        {
            "method": "POST",
            "path": "/url/encode",
            "name": "URL 参数编码",
            "summary": "对单个 URL 参数值做 UTF-8 百分号编码，语义接近 encodeURIComponent。",
            "request": "使用 JSON 请求体，`text` 为参数值；只处理单个参数值，不解析完整网址。",
            "request_example": r'{"text":"你好 & a+b"}',
            "response_example": r'{"result":"%E4%BD%A0%E5%A5%BD%20%26%20a%2Bb"}',
        },
        {
            "method": "POST",
            "path": "/url/decode",
            "name": "URL 参数解码",
            "summary": "将百分号编码还原为 UTF-8 文本。",
            "request": (
                "使用 JSON 请求体；加号保持为 +，不转换为空格；无效百分号转义或无效 UTF-8 "
                "返回 400 INVALID_INPUT。"
            ),
            "request_example": r'{"text":"%E4%BD%A0%E5%A5%BD%20%26%20a%2Bb"}',
            "response_example": r'{"result":"你好 & a+b"}',
        },
    ],
    "timestamp": [
        {
            "method": "POST",
            "path": "/timestamp/to-datetime",
            "name": "时间戳转日期",
            "summary": "把整数 Unix 时间戳转换为 UTC 日期时间，输出以 Z 结尾。",
            "request": (
                "使用 JSON 请求体，`value` 为最长 40 字符的十进制整数时间戳，"
                "`unit` 必须是 seconds 或 milliseconds；允许负值。"
            ),
            "request_example": r'{"value":"1001","unit":"milliseconds"}',
            "response_example": r'{"iso_utc":"1970-01-01T00:00:01.001000Z"}',
        },
        {
            "method": "POST",
            "path": "/timestamp/to-unix",
            "name": "日期转时间戳",
            "summary": "把带时区的 ISO 8601 日期时间转换为 Unix 时间戳。",
            "request": (
                "使用 JSON 请求体，`iso_datetime` 最长 80 字符，必须包含 Z 或明确时区偏移，"
                "不接受无时区日期；返回的 `seconds`、`milliseconds` 是十进制字符串，"
                "可含小数以保留微秒精度。"
            ),
            "request_example": r'{"iso_datetime":"1970-01-01T08:00:01.001+08:00"}',
            "response_example": (
                r'{"iso_utc":"1970-01-01T00:00:01.001000Z",'
                r'"seconds":"1.001","milliseconds":"1001"}'
            ),
        },
    ],
    "exif": [
        {
            "method": "POST",
            "path": "/exif/inspect",
            "name": "读取 EXIF",
            "summary": "上传图片并获取现有 EXIF 标签及可编辑状态。",
            "request": (
                "使用 multipart/form-data，字段 `image` 为 JPEG、PNG 或 WebP 文件，"
                "最大 20 MiB；`key` 是组名与标签名的组合，可直接用于编辑，"
                "只读标签 `writable` 为 false，`reason` 说明原因。"
            ),
            "request_format": "multipart",
            "request_example": (
                'curl -X POST "$BASE/api/v1/exif/inspect" -F "image=@photo.jpg"'
            ),
            "request_language": "bash",
            "response_example": (
                '{"format":"JPEG","tags":[{"key":"IFD0:Make","group":"IFD0",'
                '"name":"Make","value":"Canon","writable":true,"reason":""}]}'
            ),
        },
        {
            "method": "GET",
            "path": "/exif/tags",
            "name": "搜索可写标签",
            "summary": "搜索当前 ExifTool 版本支持的安全可写 EXIF 标签。",
            "request": "可选查询参数 `q`，最多 100 字符；最多返回 100 项。",
            "request_format": "query",
            "request_example": "GET $BASE/api/v1/exif/tags?q=DateTimeOriginal",
            "request_language": "http",
            "response_example": (
                '{"tags":[{"key":"ExifIFD:DateTimeOriginal","group":"ExifIFD",'
                '"name":"DateTimeOriginal","type":"string","writable":true}]}'
            ),
        },
        {
            "method": "POST",
            "path": "/exif/edit",
            "name": "编辑并下载",
            "summary": "上传原图与标签操作，返回修改后的原格式图片。",
            "request": (
                "使用 multipart/form-data：`image` 为原图，`changes` 为 JSON 字符串，"
                "包含 1 至 100 项操作；`key` 必须来自可写标签目录，`action` 为 "
                "set 或 delete，set 必须提供非空 `value`（最多 4096 字符）。"
                "仅修改 EXIF，不重新编码图片像素，结果作为文件下载。"
            ),
            "request_format": "multipart",
            "request_example": (
                'curl -X POST "$BASE/api/v1/exif/edit" -F "image=@photo.jpg" '
                '-F \'changes=[{"key":"IFD0:Make","action":"set","value":"Superbox"}]\' '
                "-o edited-exif.jpg"
            ),
            "request_language": "bash",
            "response_example": (
                "二进制图片，Content-Type 为 image/jpeg、image/png 或 image/webp，"
                'Content-Disposition 带有下载文件名如 edited-exif.jpg。'
            ),
            "response_language": "text",
        },
    ],
}
