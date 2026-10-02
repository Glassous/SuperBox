"""Bounded, coalescing cache for Frankfurter's daily reference rates."""
import asyncio
import json
import time
from collections import OrderedDict
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP, localcontext
from urllib.parse import urlencode

import httpx

from app.services import ToolInputError
from app.tool_errors import ToolFailure

BASE = "https://api.frankfurter.dev/v2"
RATE_TTL = 3600
STALE_TTL = 86400


class CurrencyService:
    def __init__(self):
        self.rates = OrderedDict()
        self.directory = None
        self.pending = {}

    async def _fetch(self, path: str):
        async with httpx.AsyncClient(timeout=8, follow_redirects=False) as client:
            async with client.stream("GET", BASE + path) as response:
                response.raise_for_status()
                chunks = bytearray()
                async for chunk in response.aiter_bytes():
                    chunks.extend(chunk)
                    if len(chunks) > 512 * 1024:
                        raise ValueError("汇率响应过大")
        return json.loads(chunks, parse_float=Decimal)

    async def _coalesce(self, key, factory):
        # The task survives cancellation of one caller; all waiters share it.
        task = self.pending.get(key)
        if task is None:
            if len(self.pending) >= 32:
                raise ToolFailure(429, "TOOL_BUSY", "汇率请求繁忙，请稍后重试")
            task = asyncio.create_task(factory())
            self.pending[key] = task
            def done(completed):
                if self.pending.get(key) is completed:
                    self.pending.pop(key, None)
                if not completed.cancelled():
                    completed.exception()
            task.add_done_callback(done)
        return await asyncio.shield(task)

    @staticmethod
    def _entry(data, base, quote):
        value = Decimal(str(data["rate"]))
        rate_date = date.fromisoformat(data["date"]).isoformat()
        if not value.is_finite() or value <= 0 or value > Decimal("1e15"):
            raise ValueError("无效汇率")
        if str(data["base"]).upper() != base or str(data["quote"]).upper() != quote:
            raise ValueError("汇率货币对不匹配")
        return {"rate": format(value, "f"), "rate_date": rate_date,
                "source": "Frankfurter", "fetched_at": datetime.now(timezone.utc).isoformat()}

    def _store(self, base, quote, entry):
        key = (base, quote)
        self.rates[key] = (time.monotonic(), entry)
        self.rates.move_to_end(key)
        while len(self.rates) > 256:
            self.rates.popitem(last=False)

    @staticmethod
    def _identity():
        return {"rate": "1", "rate_date": None, "source": "identity", "fetched_at": None,
                "cached": False, "stale": False}

    @staticmethod
    def _convert(body, quote, entry):
        with localcontext() as context:
            context.prec = 64
            result = (Decimal(body.amount) * Decimal(entry["rate"])).quantize(
                Decimal(1).scaleb(-body.precision), rounding=ROUND_HALF_UP)
        return {"amount": body.amount, "from_currency": body.from_currency,
                "to_currency": quote, "precision": body.precision,
                "result": format(result, "f"), **entry}

    async def currencies(self):
        if self.directory and time.monotonic() - self.directory[0] < STALE_TTL:
            return {"currencies": self.directory[1]}
        async def load():
            try:
                items = await self._fetch("/currencies")
                result = [{"code": str(item["iso_code"]).upper(), "name": str(item["name"])} for item in items]
                if not result or any(len(item["code"]) != 3 for item in result):
                    raise ValueError("无效货币目录")
                self.directory = (time.monotonic(), result)
                return {"currencies": result}
            except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
                raise ToolFailure(503, "EXCHANGE_RATE_UNAVAILABLE", "暂时无法获取货币目录") from exc
        return await self._coalesce("directory", load)

    async def rate(self, base, quote):
        key = (base, quote)
        old = self.rates.get(key)
        if old and time.monotonic() - old[0] < RATE_TTL:
            self.rates.move_to_end(key)
            return {**old[1], "cached": True, "stale": False}
        async def load():
            try:
                data = await self._fetch(f"/rate/{base.lower()}/{quote.lower()}")
                entry = self._entry(data, base, quote)
                self._store(base, quote, entry)
                return {**entry, "cached": False, "stale": False}
            except (httpx.HTTPError, ValueError, KeyError, TypeError, ArithmeticError) as exc:
                if old and time.monotonic() - old[0] <= STALE_TTL:
                    return {**old[1], "cached": True, "stale": True}
                raise ToolFailure(503, "EXCHANGE_RATE_UNAVAILABLE", "暂时无法获取汇率，且没有有效缓存") from exc
        return await self._coalesce(key, load)

    async def _directory_for(self, base, quotes):
        # A still-valid directory is reused; a failed refresh must not prevent
        # a currency pair's permitted stale fallback.
        if self.directory and time.monotonic() - self.directory[0] <= STALE_TTL:
            directory = self.directory[1]
        else:
            try:
                directory = (await self.currencies())["currencies"]
            except ToolFailure:
                has_cache = any((old := self.rates.get((base, quote))) and
                                time.monotonic() - old[0] <= STALE_TTL for quote in quotes)
                if not self.directory or not has_cache:
                    raise
                directory = self.directory[1]
        supported = {item["code"] for item in directory}
        if base not in supported or any(quote not in supported for quote in quotes):
            raise ToolInputError("不支持的货币代码，请使用货币目录中的代码")

    async def convert(self, body):
        await self._directory_for(body.from_currency, [body.to_currency])
        if body.from_currency == body.to_currency:
            entry = self._identity()
        else:
            entry = await self.rate(body.from_currency, body.to_currency)
        return self._convert(body, body.to_currency, entry)

    async def batch_rates(self, base, quotes):
        entries, missing, old = {}, [], {}
        for quote in quotes:
            if quote == base:
                entries[quote] = self._identity()
                continue
            cached = self.rates.get((base, quote))
            if cached and time.monotonic() - cached[0] < RATE_TTL:
                self.rates.move_to_end((base, quote))
                entries[quote] = {**cached[1], "cached": True, "stale": False}
            else:
                missing.append(quote)
                old[quote] = cached
        if not missing:
            return entries
        targets = tuple(sorted(missing))
        async def load():
            fresh, seen = {}, set()
            try:
                data = await self._fetch("/rates?" + urlencode({"base": base, "quotes": ",".join(targets)}))
                if not isinstance(data, list):
                    raise ValueError("无效汇率列表")
                for row in data:
                    if not isinstance(row, dict):
                        continue
                    quote = str(row.get("quote", "")).upper()
                    if quote not in targets:
                        continue
                    if quote in seen:
                        fresh.pop(quote, None)
                        continue
                    seen.add(quote)
                    try:
                        fresh[quote] = self._entry(row, base, quote)
                    except (ValueError, KeyError, TypeError, ArithmeticError):
                        continue
            except (httpx.HTTPError, ValueError, KeyError, TypeError, ArithmeticError):
                pass
            resolved = {}
            for quote in targets:
                if quote in fresh:
                    self._store(base, quote, fresh[quote])
                    resolved[quote] = {**fresh[quote], "cached": False, "stale": False}
                elif old[quote] and time.monotonic() - old[quote][0] <= STALE_TTL:
                    resolved[quote] = {**old[quote][1], "cached": True, "stale": True}
                else:
                    resolved[quote] = None
            return resolved
        entries.update(await self._coalesce(("batch", base, targets), load))
        return entries

    async def convert_batch(self, body):
        await self._directory_for(body.from_currency, body.to_currencies)
        entries = await self.batch_rates(body.from_currency, body.to_currencies)
        results = []
        for quote in body.to_currencies:
            entry = entries[quote]
            results.append({"status": "success", **self._convert(body, quote, entry)} if entry else
                           {"status": "error", "to_currency": quote, "code": "EXCHANGE_RATE_UNAVAILABLE",
                            "message": "暂时无法获取该币种的汇率，请稍后重试"})
        if not any(item["status"] == "success" for item in results):
            raise ToolFailure(503, "EXCHANGE_RATE_UNAVAILABLE", "暂时无法获取汇率，请稍后重试")
        return {"amount": body.amount, "from_currency": body.from_currency, "precision": body.precision,
                "count": len(results), "results": results}


service = CurrencyService()
