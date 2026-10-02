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


SKILL_VERSION = "1.3.0"

SKILL_DESCRIPTION = (
    "Superbox 是由 FastAPI 提供工具能力的开发工具箱：JSON 格式化与校验、"
    "Base64 编解码、URL 参数值编解码、Unix 时间戳转换，以及图片 EXIF 读取与编辑。"
    "新增东八区当前时间、每日参考汇率转换和 PDF/DOCX/XLSX 转 Markdown/TXT。"
    "所有计算均由服务端完成。本 Skill 由官方维护，覆盖当前全部对外接口，"
    "任何 AI 平台或智能体都可以直接按本文档调用，无需认证。"
)

CONVENTIONS = [
    "当前时间固定返回 UTC+08:00；既有时间戳转换接口仍返回 UTC。汇率是每日参考值，必须保留 rate_date、source 和 stale 信息。",
    "文件转换使用 multipart/form-data：file 或 file_url 二选一，format 为 markdown（默认）或 txt；结果为 JSON，保留 result 正文供预览和复制，并通过 url 下载 UTF-8 文件，保留 2 小时。最大 5 MiB，不支持 OCR、DOC/XLS、宏或加密文件。",
    "文本工具（JSON、Base64、URL、时间戳）使用 JSON 请求与响应：请求头 "
    "`Content-Type: application/json`，字符串输入长度为 1 至 1,000,000 个字符。",
    "图片 EXIF 工具使用 `multipart/form-data`，图片来源为 `image` 文件或 `image_url` 图片链接"
    "（二选一），编辑接口返回 JSON，通过 url 下载原格式图片，文件保留 2 小时。",
    "文件输出包含 url、filename、content_type、size（字节）、expires_at（UTC ISO 8601）；到期后服务端删除，正常运行时约有一分钟清理延迟，停机或删除失败后恢复补清理。",
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
    {"status": 413, "code": "FILE_TOO_LARGE", "meaning": "图片超过 20 MiB，文档超过 5 MiB 或转换请求体超过 6 MiB"},
    {"status": 422, "code": "VALIDATION_ERROR", "meaning": "字段缺失、类型错误或超出长度限制"},
    {"status": 503, "code": "COS_UNAVAILABLE", "meaning": "COS 配置缺失、无效或无法初始化"},
    {"status": 503, "code": "COS_UPLOAD_FAILED", "meaning": "处理后的文件上传失败"},
    {"status": 503, "code": "EXIF_UNAVAILABLE", "meaning": "服务端 ExifTool 不可用"},
    {"status": 413, "code": "DOCUMENT_LIMIT_EXCEEDED", "meaning": "文档解压、页数、单元格、文本或内存超过限制"},
    {"status": 429, "code": "TOOL_BUSY", "meaning": "工具繁忙，稍后重试；文件转换同时仅处理一项"},
    {"status": 503, "code": "EXCHANGE_RATE_UNAVAILABLE", "meaning": "汇率供应商不可用且没有有效缓存"},
    {"status": 503, "code": "DOCUMENT_UNAVAILABLE", "meaning": "无法建立文件转换资源限制或处理进程不可用"},
    {"status": 504, "code": "DOCUMENT_TIMEOUT", "meaning": "文档解析超过 15 秒或 10 秒 CPU 时间"},
]

AI_GUIDANCE = [
    "直接调用 HTTP 接口完成计算，不要在客户端重写工具逻辑。",
    "校验 JSON 时读取 HTTP 200 响应中的 `valid` 字段；其余工具的无效输入返回 400，"
    "请按状态码分支处理。",
    "编辑图片前先用 `inspect` 或 `tags` 确认可写标签，再用 `edit` 提交 `changes`；"
    "`edit` 返回 JSON，使用 url 下载文件，并向用户提示 expires_at 到期时间。",
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
        "request": "路径参数 `slug` 取值：json、base64、url、timestamp、exif、time、currency、documents。",
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
    "time": [{
        "method": "GET", "path": "/time/now", "name": "获取东八区当前时间",
        "summary": "读取服务器当前时间并固定转换为 UTC+08:00，响应禁止缓存。",
        "request": "无参数。", "request_format": "none",
        "response_example": '{"date":"2026-10-02","time":"12:00:00.000","iso_datetime":"2026-10-02T12:00:00.000+08:00","timezone":"UTC+08:00","weekday":5,"unix_seconds":"1790913600","unix_milliseconds":"1790913600000"}',
    }],
    "currency": [
        {"method": "GET", "path": "/currency/currencies", "name": "货币目录",
         "summary": "获取 Frankfurter 支持的当前货币代码和名称，目录缓存 24 小时。",
         "request": "无参数。", "request_format": "none",
         "response_example": '{"currencies":[{"code":"CNY","name":"Chinese Renminbi Yuan"},{"code":"USD","name":"United States Dollar"}]}'},
        {"method": "POST", "path": "/currency/convert", "name": "汇率转换",
         "summary": "使用最新可用每日参考汇率兑换金额，并返回来源和汇率日期。",
         "request": "JSON：amount 为非负十进制字符串（最多 15 位整数、8 位小数），from_currency/to_currency 为目录中的三位代码；precision 默认 2，范围 0–8。汇率缓存 1 小时，上游失败仅允许获取时间不超过 24 小时的缓存，stale=true。同币种汇率 1，rate_date/fetched_at=null，source=identity。",
         "request_example": '{"amount":"100","from_currency":"CNY","to_currency":"USD","precision":2}',
         "response_example": '{"amount":"100","from_currency":"CNY","to_currency":"USD","precision":2,"result":"14.00","rate":"0.14","rate_date":"2026-10-02","source":"Frankfurter","fetched_at":"2026-10-02T04:00:00+00:00","cached":false,"stale":false}'},
        {"method": "POST", "path": "/currency/convert-batch", "name": "多币种汇率转换",
         "summary": "一次将一个金额兑换为最多 50 种自选货币，结果按请求顺序返回。",
         "request": "JSON：amount/from_currency/precision 与单币种一致，to_currencies 是 1–50 项不重复的货币代码数组，统一大写；重复或超限返回 422，不支持的货币返回 400。结果逐项 status=success 或 error（带 code/message）；部分成功返回 200，全部不可用返回 503 EXCHANGE_RATE_UNAVAILABLE。成功项金额和汇率为字符串，保留实际日期、来源、cached/stale。缓存规则与单币种一致。",
         "request_example": '{"amount":"100","from_currency":"CNY","to_currencies":["USD","EUR","JPY"],"precision":2}',
         "response_example": '{"amount":"100","from_currency":"CNY","precision":2,"count":3,"results":[{"status":"success","amount":"100","from_currency":"CNY","to_currency":"USD","precision":2,"result":"14.00","rate":"0.14","rate_date":"2026-10-02","source":"Frankfurter","fetched_at":"2026-10-02T04:00:00+00:00","cached":false,"stale":false},{"status":"error","to_currency":"EUR","code":"EXCHANGE_RATE_UNAVAILABLE","message":"暂时无法获取该币种的汇率，请稍后重试"},{"status":"error","to_currency":"JPY","code":"EXCHANGE_RATE_UNAVAILABLE","message":"暂时无法获取该币种的汇率，请稍后重试"}]}'},
    ],
    "documents": [{
        "method": "POST", "path": "/documents/convert", "name": "文档转 Markdown/TXT",
        "summary": "按需在受限子进程中提取 PDF、DOCX、XLSX 的文字与表格。",
        "request_format": "multipart",
        "request": "multipart：file 上传或 file_url 公开 HTTP/HTTPS 链接二选一，format=markdown（默认）或 txt。最大 5 MiB、100 页 PDF、20 个工作表及累计 50,000 单元格、500,000 输出字符。Office ZIP 最多 2,000 条目和 50 MiB 解压大小。并发 1；子进程最多 256 MiB 内存、10 秒 CPU、15 秒总解析时间。超限报错，不截断。无 OCR、不支持 DOC/XLS、宏或加密文件；公式仅返回缓存结果，缺失时输出空值并警告。返回 JSON 正文、统计、警告及 COS 文件地址 url、content_type、size、expires_at，文件保留 2 小时；通过 url 下载。",
        "request_example": 'curl -X POST "$BASE/api/v1/documents/convert" -F "file=@report.pdf" -F "format=markdown"',
        "request_language": "bash",
        "response_example": '{"result":"## 第 1 页\\n\\n示例正文","format":"markdown","filename":"report.md","source_type":"pdf","stats":{"pages":1,"worksheets":0,"cells":0,"characters":14},"warnings":[],"url":"https://superboxfiles.fiacloud.top/superbox-temp/1791007200/0123456789abcdef0123456789abcdef/report.md","content_type":"text/markdown; charset=utf-8","size":26,"expires_at":"2026-10-03T06:00:00Z"}',
    }],
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
            "summary": "上传图片或提供图片链接，获取现有 EXIF 标签及可编辑状态。",
            "request": (
                "使用 multipart/form-data，图片来源为 `image` 文件或 `image_url` 图片链接"
                "（二选一），JPEG、PNG 或 WebP，最大 20 MiB；`image_url` 必须是 "
                "http/https 公开链接，仅支持 80／443 端口，最多跟随 3 次重定向，"
                "不能指向本机或内网地址。`key` 是组名与标签名的组合，可直接用于编辑，"
                "只读标签 `writable` 为 false，`reason` 说明原因。"
            ),
            "request_format": "multipart",
            "request_example": (
                'curl -X POST "$BASE/api/v1/exif/inspect" -F "image=@photo.jpg"\n'
                'curl -X POST "$BASE/api/v1/exif/inspect" '
                '-F "image_url=https://example.com/photo.jpg"'
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
            "summary": "上传原图或提供图片链接与标签操作，返回修改后的原格式图片下载地址。",
            "request": (
                "使用 multipart/form-data：原图为 `image` 文件或 `image_url` 图片链接"
                "（二选一，链接限制同 inspect），`changes` 为 JSON 字符串，"
                "包含 1 至 100 项操作；`key` 必须来自可写标签目录，`action` 为 "
                "set 或 delete，set 必须提供非空 `value`（最多 4096 字符）。"
                "仅修改 EXIF，不重新编码图片像素；返回 JSON，通过 url 下载原格式图片，文件保留 2 小时。"
            ),
            "request_format": "multipart",
            "request_example": (
                'curl -X POST "$BASE/api/v1/exif/edit" -F "image=@photo.jpg" '
                '-F \'changes=[{"key":"IFD0:Make","action":"set","value":"Superbox"}]\' '
                "\n"
                'curl -X POST "$BASE/api/v1/exif/edit" '
                '-F "image_url=https://example.com/photo.jpg" '
                '-F \'changes=[{"key":"IFD0:Make","action":"set","value":"Superbox"}]\' '
            ),
            "request_language": "bash",
            "response_example": '{"url":"https://superboxfiles.fiacloud.top/superbox-temp/1791007200/0123456789abcdef0123456789abcdef/edited-exif.jpg","filename":"edited-exif.jpg","content_type":"image/jpeg","size":12345,"expires_at":"2026-10-03T06:00:00Z"}',
        },
    ],
}
