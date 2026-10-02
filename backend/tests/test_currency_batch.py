import asyncio
import json
import time
from decimal import Decimal
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from fastapi.testclient import TestClient

from app import currency
from app.main import app
from app.schemas import CurrencyBatchInput, CurrencyInput
from app.tool_errors import ToolFailure

CODES = ["USD", "EUR", "JPY", "CNY"] + ["X" + chr(65 + i // 26) + chr(65 + i % 26) for i in range(50)]


def make_service():
    service = currency.CurrencyService()
    calls = []
    async def fetch(path):
        calls.append(path)
        await asyncio.sleep(0)
        if path == "/currencies":
            return [{"iso_code": code, "name": code} for code in CODES]
        params = parse_qs(urlsplit(path).query)
        return [{"base": params["base"][0], "quote": quote, "rate": Decimal("0.145"), "date": "2026-10-02"}
                for quote in reversed(params["quotes"][0].split(","))]
    service._fetch = fetch
    return service, calls


@pytest.mark.parametrize("count", [1, 50])
def test_batch_http_order_limit_and_one_upstream_call(count, monkeypatch):
    service, calls = make_service()
    monkeypatch.setattr(currency, "service", service)
    targets = (CODES[:3] + CODES[4:])[:count]
    with TestClient(app) as client:
        response = client.post("/api/v1/currency/convert-batch", json={
            "amount": "1", "from_currency": "cny", "to_currencies": [code.lower() for code in targets], "precision": 2,
        })
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["count"] == count and data["from_currency"] == "CNY"
        assert [item["to_currency"] for item in data["results"]] == targets
        assert all(item["status"] == "success" and item["result"] == "0.15" for item in data["results"])
        assert all(item["rate_date"] == "2026-10-02" and item["rate"] == "0.145" for item in data["results"])
        assert len(calls) == 2 and calls[0] == "/currencies" and calls[1].startswith("/rates?")


@pytest.mark.parametrize("updates", [
    {"to_currencies": []}, {"to_currencies": CODES[:51]}, {"to_currencies": ["USD", "usd"]},
    {"to_currencies": "USD"}, {"to_currencies": [1]}, {"to_currencies": ["US"]},
    {"amount": "NaN"}, {"amount": "-1"}, {"amount": "1e3"}, {"amount": 1},
    {"amount": "1.123456789"}, {"amount": "1000000000000000"},
    {"precision": 9}, {"precision": True}, {"precision": "2"},
])
def test_batch_validation(updates):
    with TestClient(app) as client:
        response = client.post("/api/v1/currency/convert-batch", json={
            "amount": "1", "from_currency": "CNY", "to_currencies": ["USD"], **updates,
        })
        assert response.status_code == 422 and response.json()["code"] == "VALIDATION_ERROR"


def test_unsupported_currency_is_atomic_input_error(monkeypatch):
    service, calls = make_service()
    monkeypatch.setattr(currency, "service", service)
    with TestClient(app) as client:
        for body in ({"from_currency": "CNY", "to_currencies": ["USD", "ZZZ"]},
                     {"from_currency": "ZZZ", "to_currencies": ["USD"]}):
            response = client.post("/api/v1/currency/convert-batch", json={"amount": "1", **body})
            assert response.status_code == 400 and response.json()["code"] == "INVALID_INPUT"
    assert calls == ["/currencies"]


def test_cache_coalescing_identity_rounding_and_shared_single_cache():
    async def scenario():
        service, calls = make_service()
        bodies = [CurrencyBatchInput(amount="1", from_currency="CNY", to_currencies=quotes)
                  for quotes in (["USD", "EUR"], ["EUR", "USD"]) * 5]
        data = await asyncio.gather(*(service.convert_batch(body) for body in bodies))
        assert len(calls) == 2
        assert data[0]["results"][0]["to_currency"] == "USD"
        assert data[1]["results"][0]["to_currency"] == "EUR"
        cached = await service.convert_batch(bodies[0])
        assert all(item["cached"] and not item["stale"] for item in cached["results"])
        single = await service.convert(CurrencyInput(amount="100", from_currency="CNY", to_currency="USD"))
        assert single["result"] == "14.50" and single["cached"] and len(calls) == 2
        identity = await service.convert_batch(CurrencyBatchInput(amount="999999999999999.12345678", from_currency="CNY", to_currencies=["CNY"], precision=8))
        item = identity["results"][0]
        assert item["result"] == "999999999999999.12345678" and item["rate"] == "1" and item["rate_date"] is None
        assert len(calls) == 2
        rounded = await service.convert_batch(CurrencyBatchInput(amount="10", from_currency="CNY", to_currencies=["USD"], precision=0))
        assert rounded["results"][0]["result"] == "1"
        # Cached targets are excluded from the next upstream request.
        await service.convert_batch(CurrencyBatchInput(amount="1", from_currency="CNY", to_currencies=["USD", "JPY"]))
        assert parse_qs(urlsplit(calls[-1]).query)["quotes"] == ["JPY"]
    asyncio.run(scenario())


@pytest.mark.parametrize("row_update", [{"rate": "NaN"}, {"rate": "Infinity"}, {"rate": "0"},
                                         {"rate": "-1"}, {"rate": "1e16"}, {"date": "bad"}, {"base": "USD"}])
def test_invalid_upstream_row_preserves_other_results(row_update):
    async def scenario():
        service, _ = make_service()
        await service.currencies()
        async def fetch(path):
            return [{"base": "CNY", "quote": "USD", "rate": "0.14", "date": "2026-10-02", **row_update},
                    {"base": "CNY", "quote": "EUR", "rate": "0.13", "date": "2026-10-01"}]
        service._fetch = fetch
        response = await service.convert_batch(CurrencyBatchInput(amount="1", from_currency="CNY", to_currencies=["USD", "EUR"]))
        assert [item["status"] for item in response["results"]] == ["error", "success"]
        assert ("CNY", "USD") not in service.rates
    asyncio.run(scenario())


def test_missing_rows_stale_boundary_all_failed_and_directory_fallback(monkeypatch):
    service, _ = make_service()
    async def prepare():
        await service.convert_batch(CurrencyBatchInput(amount="1", from_currency="CNY", to_currencies=["USD", "EUR"]))
        for quote, age in [("USD", 7200), ("EUR", 90000)]:
            _, entry = service.rates[("CNY", quote)]
            service.rates[("CNY", quote)] = (time.monotonic() - age, entry)
        async def empty(path): return []
        service._fetch = empty
    asyncio.run(prepare())
    monkeypatch.setattr(currency, "service", service)
    with TestClient(app) as client:
        response = client.post("/api/v1/currency/convert-batch", json={"amount": "1", "from_currency": "CNY", "to_currencies": ["USD", "EUR", "JPY"]})
        assert response.status_code == 200
        results = response.json()["results"]
        assert results[0]["cached"] and results[0]["stale"] and results[0]["rate_date"] == "2026-10-02"
        assert [item["status"] for item in results] == ["success", "error", "error"]
        response = client.post("/api/v1/currency/convert-batch", json={"amount": "1", "from_currency": "CNY", "to_currencies": ["EUR", "JPY"]})
        assert response.status_code == 503 and response.json()["code"] == "EXCHANGE_RATE_UNAVAILABLE"
        # Even after an expired directory refresh fails, usable stale rates survive.
        service.directory = (time.monotonic() - 90000, service.directory[1])
        async def offline(path): raise httpx.ConnectError("offline")
        service._fetch = offline
        response = client.post("/api/v1/currency/convert-batch", json={"amount": "1", "from_currency": "CNY", "to_currencies": ["USD", "JPY"]})
        assert response.status_code == 200 and response.json()["results"][0]["stale"]


def test_duplicate_upstream_quotes_fail_and_cache_capacity():
    async def scenario():
        service, _ = make_service()
        await service.currencies()
        async def fetch(path):
            row = {"base": "CNY", "quote": "USD", "rate": "1", "date": "2026-10-02"}
            return [row, row, {**row, "quote": "EUR"}]
        service._fetch = fetch
        result = await service.convert_batch(CurrencyBatchInput(amount="1", from_currency="CNY", to_currencies=["USD", "EUR"]))
        assert [item["status"] for item in result["results"]] == ["error", "success"]
        for i in range(300): service.rates[(str(i), "USD")] = (0, {})
        service.rates[("CNY", "EUR")] = (0, service.rates[("CNY", "EUR")][1])
        await service.convert_batch(CurrencyBatchInput(amount="1", from_currency="CNY", to_currencies=["EUR"]))
        assert len(service.rates) == 256
    asyncio.run(scenario())


def test_pending_capacity_and_cancelled_caller_does_not_cancel_shared_fetch():
    async def scenario():
        service, calls = make_service()
        await service.currencies()
        real_fetch = service._fetch
        started, release = asyncio.Event(), asyncio.Event()
        async def fetch(path):
            started.set(); await release.wait(); return await real_fetch(path)
        service._fetch = fetch
        body = CurrencyBatchInput(amount="1", from_currency="CNY", to_currencies=["USD"])
        first = asyncio.create_task(service.convert_batch(body))
        await started.wait()
        second = asyncio.create_task(service.convert_batch(body))
        await asyncio.sleep(0)
        first.cancel()
        with pytest.raises(asyncio.CancelledError): await first
        release.set()
        assert (await second)["results"][0]["result"] == "0.15"
        assert len(calls) == 2 and not service.pending
        service.pending = {i: asyncio.get_running_loop().create_future() for i in range(32)}
        with pytest.raises(ToolFailure) as cause:
            await service.batch_rates("CNY", ["JPY"])
        assert cause.value.status == 429
    asyncio.run(scenario())


def test_batch_schema_and_skill_examples_are_published():
    with TestClient(app) as client:
        paths = client.get("/api/v1/openapi.json").json()["paths"]
        assert "/api/v1/currency/convert-batch" in paths
        manifest = client.get("/api/v1/skill.json").json()
        assert manifest["version"] == "1.2.0"
        endpoint = next(item for item in manifest["endpoints"] if item["path"] == "/currency/convert-batch")
        assert isinstance(json.loads(endpoint["request_example"])["to_currencies"], list)
        assert json.loads(endpoint["response_example"])["count"] == 3
