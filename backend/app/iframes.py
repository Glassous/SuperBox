"""Iframe 仓库目录与嵌入页渲染。

每个条目声明内容类型、原始地址、预览图、推荐尺寸和沙箱策略；嵌入页由本服务
生成可直接作为 iframe src 的完整 HTML，消费方无需自行拼接样式。
"""

from html import escape
from typing import Literal, TypedDict


MAX_QUERY_LENGTH = 100

EMBED_CACHE_CONTROL = "public, max-age=300"

MILK_FROG_IMAGE = "https://officialimages.glassous.top/other/%E5%A5%B6%E8%9B%99.png"

IMAGE_CSP = (
    "default-src 'none'; img-src https: http: data:; "
    "style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"
)
PAGE_CSP = (
    "default-src 'none'; frame-src https: http:; "
    "style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"
)


class IframeItem(TypedDict):
    slug: str
    name: str
    category: str
    description: str
    keywords: list[str]
    content_type: Literal["image", "page"]
    content_url: str
    preview_url: str
    width: int
    height: int
    sandbox: str
    allow: str


IFRAMES: list[IframeItem] = [
    {
        "slug": "milk-frog",
        "name": "奶蛙",
        "category": "图片展示",
        "description": "奶蛙图片展示，可直接嵌入任意网页。",
        "keywords": ["奶蛙", "图片", "milk frog", "iframe"],
        "content_type": "image",
        "content_url": MILK_FROG_IMAGE,
        # 图片条目没有独立的预览图，直接复用实际展示的图片。
        "preview_url": MILK_FROG_IMAGE,
        "width": 640,
        "height": 640,
        "sandbox": "",
        "allow": "",
    },
]


def find(slug: str) -> IframeItem | None:
    return next((item for item in IFRAMES if item["slug"] == slug), None)


def search(query: str) -> list[IframeItem]:
    text = query.strip().casefold()
    if not text:
        return IFRAMES
    return [
        item
        for item in IFRAMES
        if text
        in " ".join(
            [item["name"], item["category"], item["description"], *item["keywords"]]
        ).casefold()
    ]


def embed_path(slug: str) -> str:
    return f"/api/v1/iframes/{slug}/embed"


def embed_url(base_url: str, slug: str) -> str:
    return f"{base_url.rstrip('/')}{embed_path(slug)}"


def preview(item: IframeItem) -> str:
    """预览图：优先使用条目声明，图片条目退回复用原始图片。"""
    if item["preview_url"]:
        return item["preview_url"]
    return item["content_url"] if item["content_type"] == "image" else ""


def thumbnail(item: IframeItem) -> str:
    return preview(item)


def content_security_policy(item: IframeItem) -> str:
    return IMAGE_CSP if item["content_type"] == "image" else PAGE_CSP


def _iframe_attributes(item: IframeItem) -> str:
    attributes = [
        f'src="{escape(item["content_url"], quote=True)}"',
        f'title="{escape(item["name"])}"',
        'loading="lazy"',
        f'sandbox="{escape(item["sandbox"], quote=True)}"',
    ]
    if item["allow"]:
        attributes.append(f'allow="{escape(item["allow"], quote=True)}"')
    return " ".join(attributes)


def render_embed(item: IframeItem) -> str:
    title = escape(item["name"])
    if item["content_type"] == "image":
        media = (
            f'<img src="{escape(item["content_url"], quote=True)}" alt="{title}">'
        )
    else:
        media = f"<iframe {_iframe_attributes(item)}></iframe>"
    return (
        "<!doctype html>\n"
        '<html lang="zh-CN">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        '<meta name="robots" content="noindex">\n'
        f"<title>{title}</title>\n"
        "<style>\n"
        ":root { color-scheme: light dark; }\n"
        "html, body { height: 100%; margin: 0; }\n"
        "body { display: grid; place-items: center; background: #f6f8fc; }\n"
        "img, iframe { display: block; width: 100%; height: 100%; border: 0; "
        "object-fit: contain; }\n"
        "@media (prefers-color-scheme: dark) { body { background: #0c1020; } }\n"
        "</style>\n"
        "</head>\n"
        "<body>\n"
        f"{media}\n"
        "</body>\n"
        "</html>\n"
    )
