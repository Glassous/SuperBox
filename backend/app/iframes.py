"""Iframe 仓库目录与嵌入页渲染。

每个条目声明内容类型、原始地址、预览图、推荐尺寸和沙箱策略；嵌入页由本服务
生成可直接作为 iframe src 的完整 HTML，消费方无需自行拼接样式。
"""

from html import escape
from typing import Literal, TypedDict
from urllib.parse import parse_qsl, urlencode


MAX_QUERY_LENGTH = 100

EMBED_CACHE_CONTROL = "public, max-age=300"

MILK_FROG_IMAGE = "https://officialimages.glassous.top/other/%E5%A5%B6%E8%9B%99.png"

TAFFY_IMAGE = "https://superboxfiles.fiacloud.top/Iframe/taffy%E6%8E%A2%E5%A4%B4.png"
# 预览图与实际图片同源，仅追加 COS 缩略图参数降低列表页流量。
TAFFY_PREVIEW = f"{TAFFY_IMAGE}?imageMogr2/thumbnail/640x"

# 网页类型条目只能声明绝对地址，挂件页面由前端静态站点托管。
PENGUIN_WIDGET_URL = "https://superbox.fiacloud.top/widgets/penguin"
PENGUIN_PREVIEW = (
    "https://superboxfiles.fiacloud.top/Iframe/%E5%87%91%E4%BC%81%E9%B9%85.png"
)

IMAGE_CSP = (
    "default-src 'none'; img-src https: http: data:; "
    "style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"
)
PAGE_CSP = (
    "default-src 'none'; frame-src https: http:; script-src 'unsafe-inline'; "
    "style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"
)

# 网页条目多一层嵌入页，这里把控制消息在父页面与挂件页之间透传一次。
MESSAGE_RELAY = (
    "<script>\n"
    "  (function () {\n"
    "    var frame = document.querySelector('iframe');\n"
    "    window.addEventListener('message', function (event) {\n"
    "      if (!frame || !frame.contentWindow) return;\n"
    "      if (event.source === window.parent) {\n"
    "        frame.contentWindow.postMessage(event.data, '*');\n"
    "      } else if (event.source === frame.contentWindow) {\n"
    "        window.parent.postMessage(event.data, '*');\n"
    "      }\n"
    "    });\n"
    "  })();\n"
    "</script>"
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
    {
        "slug": "taffy",
        "name": "Taffy探头",
        "category": "图片展示",
        "description": "Taffy探头图片展示，可直接嵌入任意网页。",
        "keywords": ["taffy", "探头", "图片", "iframe"],
        "content_type": "image",
        "content_url": TAFFY_IMAGE,
        # 与奶蛙同为纯图片条目；原图较大（1328×1904），预览走同源缩略图。
        "preview_url": TAFFY_PREVIEW,
        # 推荐尺寸保持原图 83:119 的宽高比。
        "width": 415,
        "height": 595,
        "sandbox": "",
        "allow": "",
    },
    {
        "slug": "penguin",
        "name": "凑企鹅",
        "category": "3D 互动",
        "description": "基于 three.js 的凑企鹅 3D 挂件，可切换三段动作并拖拽旋转视角。",
        "keywords": ["凑企鹅", "企鹅", "3d", "three.js", "模型", "penguin", "iframe"],
        "content_type": "page",
        "content_url": PENGUIN_WIDGET_URL,
        "preview_url": PENGUIN_PREVIEW,
        "width": 800,
        "height": 800,
        # three.js 需要执行脚本，且同源加载模型文件需要保留源身份。
        "sandbox": "allow-scripts allow-same-origin",
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


def _embed_src(item: IframeItem, query: str) -> str:
    """把嵌入页的查询串透传给挂件页；对外嵌入默认收起挂件自带控件，只看模型本身。"""
    pairs = parse_qsl(query, keep_blank_values=True)
    if item["content_type"] == "page" and not any(key == "chrome" for key, _ in pairs):
        pairs.append(("chrome", "0"))
    suffix = urlencode(pairs)
    if not suffix:
        return item["content_url"]
    separator = "&" if "?" in item["content_url"] else "?"
    return f'{item["content_url"]}{separator}{suffix}'


def _iframe_attributes(item: IframeItem, src: str) -> str:
    attributes = [
        f'src="{escape(src, quote=True)}"',
        f'title="{escape(item["name"])}"',
        'loading="lazy"',
        f'sandbox="{escape(item["sandbox"], quote=True)}"',
    ]
    if item["allow"]:
        attributes.append(f'allow="{escape(item["allow"], quote=True)}"')
    return " ".join(attributes)


def render_embed(item: IframeItem, query: str = "") -> str:
    """渲染嵌入页。

    所有条目都不绘制底色：img/iframe 与 html/body 均为透明，宿主页面是什么
    底色就透出什么底色。也不声明 color-scheme，否则浏览器会按系统深浅色给
    画布补一层黑底或白底，等于强行植入背景。
    """
    title = escape(item["name"])
    relay = ""
    if item["content_type"] == "image":
        media = (
            f'<img src="{escape(item["content_url"], quote=True)}" alt="{title}">'
        )
    else:
        media = f"<iframe {_iframe_attributes(item, _embed_src(item, query))}></iframe>"
        relay = MESSAGE_RELAY + "\n"
    return (
        "<!doctype html>\n"
        '<html lang="zh-CN">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        '<meta name="robots" content="noindex">\n'
        f"<title>{title}</title>\n"
        "<style>\n"
        "html, body { height: 100%; margin: 0; background: transparent; }\n"
        "body { display: grid; place-items: center; }\n"
        "img, iframe { display: block; width: 100%; height: 100%; border: 0; "
        "object-fit: contain; background: transparent; }\n"
        "</style>\n"
        "</head>\n"
        "<body>\n"
        f"{media}\n"
        f"{relay}"
        "</body>\n"
        "</html>\n"
    )
