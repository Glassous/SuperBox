from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)
API = "/api/v1"
IMAGE_URL = (
    "https://officialimages.glassous.top/other/%E5%A5%B6%E8%9B%99.png"
)
PENGUIN_WIDGET_URL = "https://superbox.fiacloud.top/widgets/penguin"
PENGUIN_PREVIEW = (
    "https://superboxfiles.fiacloud.top/Iframe/%E5%87%91%E4%BC%81%E9%B9%85.png"
)
TAFFY_IMAGE = (
    "https://superboxfiles.fiacloud.top/Iframe/taffy%E6%8E%A2%E5%A4%B4.png"
)
TAFFY_PREVIEW = f"{TAFFY_IMAGE}?imageMogr2/thumbnail/640x"


def test_iframe_catalog_search_and_detail():
    catalog = client.get(f"{API}/iframes")
    assert catalog.status_code == 200
    items = catalog.json()["iframes"]
    assert [item["slug"] for item in items] == ["milk-frog", "taffy", "penguin"]

    item = items[0]
    assert item == {
        "slug": "milk-frog",
        "name": "奶蛙",
        "category": "图片展示",
        "description": "奶蛙图片展示，可直接嵌入任意网页。",
        "keywords": ["奶蛙", "图片", "milk frog", "iframe"],
        "content_type": "image",
        "content_url": IMAGE_URL,
        "preview_url": IMAGE_URL,
        "thumbnail_url": IMAGE_URL,
        "embed_path": "/api/v1/iframes/milk-frog/embed",
        "embed_url": "http://testserver/api/v1/iframes/milk-frog/embed",
        "width": 640,
        "height": 640,
        "sandbox": "",
        "allow": "",
    }
    # 图片条目的预览图与实际效果复用同一张图片。
    assert item["preview_url"] == item["content_url"]
    assert item["thumbnail_url"] == item["content_url"]
    assert [
        entry["slug"] for entry in client.get(f"{API}/iframes?q=奶蛙").json()["iframes"]
    ] == ["milk-frog"]
    assert client.get(f"{API}/iframes?q=不存在").json()["iframes"] == []
    assert client.get(f"{API}/iframes/milk-frog").json() == item

    missing = client.get(f"{API}/iframes/missing")
    assert missing.status_code == 404
    assert missing.json()["code"] == "NOT_FOUND"


def test_iframe_embed_page_is_embeddable_html():
    response = client.get(f"{API}/iframes/milk-frog/embed")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.headers["cache-control"] == "public, max-age=300"
    assert "x-frame-options" not in response.headers
    assert "img-src" in response.headers["content-security-policy"]
    assert "<title>奶蛙</title>" in response.text
    assert f'<img src="{IMAGE_URL}" alt="奶蛙">' in response.text
    assert "prefers-color-scheme: dark" in response.text
    assert '<body class="surface">' in response.text

    missing = client.get(f"{API}/iframes/missing/embed")
    assert missing.status_code == 404
    assert missing.json()["code"] == "NOT_FOUND"


def test_taffy_iframe_reuses_image_with_thumbnail_preview():
    taffy = client.get(f"{API}/iframes/taffy").json()
    assert taffy == {
        "slug": "taffy",
        "name": "Taffy探头",
        "category": "图片展示",
        "description": "Taffy探头图片展示，可直接嵌入任意网页。",
        "keywords": ["taffy", "探头", "图片", "iframe"],
        "content_type": "image",
        "content_url": TAFFY_IMAGE,
        "preview_url": TAFFY_PREVIEW,
        "thumbnail_url": TAFFY_PREVIEW,
        "embed_path": "/api/v1/iframes/taffy/embed",
        "embed_url": "http://testserver/api/v1/iframes/taffy/embed",
        "width": 415,
        "height": 595,
        "sandbox": "",
        "allow": "",
    }
    # 预览图与实际图片同源，仅追加 COS 缩略图参数。
    assert taffy["preview_url"].startswith(taffy["content_url"])
    assert taffy["thumbnail_url"] == taffy["preview_url"]

    for query in ("taffy", "探头"):
        found = client.get(f"{API}/iframes?q={query}").json()["iframes"]
        assert [entry["slug"] for entry in found] == ["taffy"]

    response = client.get(f"{API}/iframes/taffy/embed")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "<title>Taffy探头</title>" in response.text
    # 嵌入页仍展示原始大图，缩略图参数只用于目录预览。
    assert f'<img src="{TAFFY_IMAGE}" alt="Taffy探头">' in response.text
    assert "postMessage" not in response.text


def test_penguin_iframe_embeds_widget_page():
    penguin = client.get(f"{API}/iframes/penguin").json()
    assert penguin == {
        "slug": "penguin",
        "name": "凑企鹅",
        "category": "3D 互动",
        "description": "基于 three.js 的凑企鹅 3D 挂件，可切换三段动作并拖拽旋转视角。",
        "keywords": ["凑企鹅", "企鹅", "3d", "three.js", "模型", "penguin", "iframe"],
        "content_type": "page",
        "content_url": PENGUIN_WIDGET_URL,
        "preview_url": PENGUIN_PREVIEW,
        "thumbnail_url": PENGUIN_PREVIEW,
        "embed_path": "/api/v1/iframes/penguin/embed",
        "embed_url": "http://testserver/api/v1/iframes/penguin/embed",
        "width": 800,
        "height": 800,
        "sandbox": "allow-scripts allow-same-origin",
        "allow": "",
    }
    # 网页条目不再复用原始地址作为预览图，使用独立的截图。
    assert penguin["preview_url"] != penguin["content_url"]

    found = client.get(f"{API}/iframes?q=企鹅").json()["iframes"]
    assert [entry["slug"] for entry in found] == ["penguin"]

    response = client.get(f"{API}/iframes/penguin/embed")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "frame-src" in response.headers["content-security-policy"]
    assert "<title>凑企鹅</title>" in response.text
    assert (
        f'<iframe src="{PENGUIN_WIDGET_URL}?chrome=0" title="凑企鹅" loading="lazy" '
        'sandbox="allow-scripts allow-same-origin">'
    ) in response.text
    # 网页条目嵌入页保持透明，避免宿主页面出现一块底色。
    assert "<body>" in response.text
    assert 'class="surface"' not in response.text
    assert "script-src 'unsafe-inline'" in response.headers["content-security-policy"]
    assert "postMessage" in response.text


def test_penguin_embed_passes_widget_control_query():
    response = client.get(f"{API}/iframes/penguin/embed?action=2&chrome=0")
    assert response.status_code == 200
    assert (
        f'<iframe src="{PENGUIN_WIDGET_URL}?action=2&amp;chrome=0"'
        in response.text
    )

    custom = client.get(f"{API}/iframes/penguin/embed?chrome=1&action=1")
    assert (
        f'<iframe src="{PENGUIN_WIDGET_URL}?chrome=1&amp;action=1"'
        in custom.text
    )

    image = client.get(f"{API}/iframes/milk-frog/embed?action=2")
    assert image.status_code == 200
    assert f'<img src="{IMAGE_URL}" alt="奶蛙">' in image.text
    assert "postMessage" not in image.text
