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
    {
        "slug": "exif",
        "name": "EXIF 编辑",
        "category": "图片处理",
        "description": "查看、编辑图片 EXIF 标签并下载原格式图片。",
        "keywords": ["exif", "图片", "元数据", "照片", "gps"],
    },
]

TOOLS.extend([
    {"slug": "time", "name": "当前时间", "category": "时间日期",
     "description": "获取当前日期和时间，自动转换为东八区。", "keywords": ["当前", "时间", "日期", "东八区", "now"]},
    {"slug": "currency", "name": "汇率转换", "category": "数据处理",
     "description": "使用每日参考汇率，将金额兑换为一种或多种货币。", "keywords": ["汇率", "货币", "人民币", "美元", "多币种", "计算器", "currency"]},
    {"slug": "documents", "name": "文件转换", "category": "文件处理",
     "description": "将 PDF、DOCX、XLSX 的文字和表格转换为 Markdown 或 TXT。", "keywords": ["pdf", "word", "docx", "excel", "xlsx", "markdown", "txt", "文件"]},
])
