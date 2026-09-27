from typing import TypedDict


class ToolInfo(TypedDict):
    slug: str
    name: str
    category: str
    description: str
    keywords: list[str]


TOOLS: list[ToolInfo] = [
    {
        "slug": "json",
        "name": "JSON 工具",
        "category": "数据处理",
        "description": "格式化、压缩和校验 JSON 内容。",
        "keywords": ["json", "格式化", "压缩", "校验"],
    },
    {
        "slug": "base64",
        "name": "Base64 编解码",
        "category": "编码转换",
        "description": "在 UTF-8 文本与 Base64 之间转换。",
        "keywords": ["base64", "编码", "解码", "utf-8"],
    },
    {
        "slug": "url",
        "name": "URL 编解码",
        "category": "编码转换",
        "description": "对 URL 参数值进行编码或解码。",
        "keywords": ["url", "uri", "百分号", "参数"],
    },
    {
        "slug": "timestamp",
        "name": "时间戳转换",
        "category": "时间日期",
        "description": "在 Unix 时间戳与带时区的日期时间之间转换。",
        "keywords": ["timestamp", "unix", "秒", "毫秒", "日期"],
    },
]
