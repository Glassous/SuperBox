from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)
API = "/api/v1"


def test_catalog_search_and_detail():
    catalog = client.get(f"{API}/tools")
    assert catalog.status_code == 200
    assert {tool["slug"] for tool in catalog.json()["tools"]} == {
        "json", "base64", "url", "timestamp"
    }
    assert [tool["slug"] for tool in client.get(f"{API}/tools?q=编码").json()["tools"]] == [
        "base64", "url"
    ]
    assert client.get(f"{API}/tools/json").json()["name"] == "JSON 工具"
    missing = client.get(f"{API}/tools/missing")
    assert missing.status_code == 404
    assert missing.json()["code"] == "NOT_FOUND"


def test_json_operations_and_validation():
    text = '{"name":"中文","items":[1,true]}'
    formatted = client.post(f"{API}/json/format", json={"text": text})
    assert formatted.status_code == 200
    assert '\n  "name": "中文"' in formatted.json()["result"]
    minified = client.post(f"{API}/json/minify", json={"text": formatted.json()["result"]})
    assert minified.json()["result"] == text
    assert client.post(f"{API}/json/validate", json={"text": text}).json() == {
        "valid": True, "message": "JSON 格式有效"
    }
    invalid = client.post(f"{API}/json/validate", json={"text": "{"})
    assert invalid.status_code == 200
    assert invalid.json()["valid"] is False
    bad_format = client.post(f"{API}/json/format", json={"text": "{"})
    assert bad_format.status_code == 400
    assert bad_format.json()["code"] == "INVALID_INPUT"
    assert client.post(f"{API}/json/format", json={"text": "NaN"}).status_code == 400


def test_base64_utf8_and_invalid_data():
    encoded = client.post(f"{API}/base64/encode", json={"text": "你好 🌍"})
    assert encoded.status_code == 200
    decoded = client.post(f"{API}/base64/decode", json={"text": encoded.json()["result"]})
    assert decoded.json()["result"] == "你好 🌍"
    for text in ["not base64!", "/w=="]:
        response = client.post(f"{API}/base64/decode", json={"text": text})
        assert response.status_code == 400
        assert response.json()["code"] == "INVALID_INPUT"


def test_url_component_operations():
    encoded = client.post(f"{API}/url/encode", json={"text": "你好 & a+b"})
    assert encoded.json()["result"] == "%E4%BD%A0%E5%A5%BD%20%26%20a%2Bb"
    decoded = client.post(f"{API}/url/decode", json={"text": encoded.json()["result"]})
    assert decoded.json()["result"] == "你好 & a+b"
    for text in ["bad%GG", "%FF"]:
        response = client.post(f"{API}/url/decode", json={"text": text})
        assert response.status_code == 400
        assert response.json()["code"] == "INVALID_INPUT"


def test_timestamp_units_offsets_and_errors():
    assert client.post(
        f"{API}/timestamp/to-datetime", json={"value": "0", "unit": "seconds"}
    ).json()["iso_utc"] == "1970-01-01T00:00:00Z"
    assert client.post(
        f"{API}/timestamp/to-datetime", json={"value": "1001", "unit": "milliseconds"}
    ).json()["iso_utc"] == "1970-01-01T00:00:01.001000Z"
    assert client.post(
        f"{API}/timestamp/to-datetime", json={"value": "-1", "unit": "seconds"}
    ).json()["iso_utc"] == "1969-12-31T23:59:59Z"
    converted = client.post(
        f"{API}/timestamp/to-unix",
        json={"iso_datetime": "1970-01-01T08:00:01.001+08:00"},
    )
    assert converted.json() == {
        "iso_utc": "1970-01-01T00:00:01.001000Z",
        "seconds": "1.001",
        "milliseconds": "1001",
    }
    for payload in [
        {"value": "abc", "unit": "seconds"},
        {"value": "9999999999999999999", "unit": "seconds"},
    ]:
        response = client.post(f"{API}/timestamp/to-datetime", json=payload)
        assert response.status_code == 400
    naive = client.post(
        f"{API}/timestamp/to-unix", json={"iso_datetime": "2026-09-27T12:30:00"}
    )
    assert naive.status_code == 400


def test_request_validation_and_length_limit():
    empty = client.post(f"{API}/base64/encode", json={"text": ""})
    assert empty.status_code == 422
    assert empty.json()["code"] == "VALIDATION_ERROR"
    assert empty.json()["details"][0]["field"] == "body.text"
    huge = client.post(f"{API}/url/encode", json={"text": "a" * 1_000_001})
    assert huge.status_code == 422
    wrong_unit = client.post(
        f"{API}/timestamp/to-datetime", json={"value": "1", "unit": "minutes"}
    )
    assert wrong_unit.status_code == 422


def test_wildcard_cors_and_openapi():
    preflight = client.options(
        f"{API}/json/format",
        headers={
            "Origin": "https://arbitrary-client.example",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == "*"
    response = client.get(
        f"{API}/tools", headers={"Origin": "https://another-client.example"}
    )
    assert response.headers["access-control-allow-origin"] == "*"
    assert "access-control-allow-credentials" not in response.headers
    assert client.get(f"{API}/health").json() == {"status": "ok"}
    assert client.get("/docs").status_code == 200
    paths = client.get(f"{API}/openapi.json").json()["paths"]
    for path in [
        f"{API}/tools", f"{API}/json/format", f"{API}/base64/decode",
        f"{API}/url/encode", f"{API}/timestamp/to-unix",
    ]:
        assert path in paths


def test_every_tool_has_an_interface_document():
    docs = Path(__file__).resolve().parents[2] / "docs"
    for slug in ["json", "base64", "url", "timestamp"]:
        assert (docs / f"{slug}.md").is_file()
