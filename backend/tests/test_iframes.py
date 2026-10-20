from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)
API = "/api/v1"
IMAGE_URL = (
    "https://officialimages.glassous.top/other/%E5%A5%B6%E8%9B%99.png"
)


def test_iframe_catalog_search_and_detail():
    catalog = client.get(f"{API}/iframes")
    assert catalog.status_code == 200
    items = catalog.json()["iframes"]
    assert [item["slug"] for item in items] == ["milk-frog"]

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

    missing = client.get(f"{API}/iframes/missing/embed")
    assert missing.status_code == 404
    assert missing.json()["code"] == "NOT_FOUND"
