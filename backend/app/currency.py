"""Bounded, coalescing cache for Frankfurter's daily reference rates."""
import asyncio
import json
import time
from collections import OrderedDict
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP, localcontext

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
                value = Decimal(str(data["rate"]))
                rate_date = date.fromisoformat(data["date"]).isoformat()
                if not value.is_finite() or value <= 0 or value > Decimal("1e15"):
                    raise ValueError("无效汇率")
                if str(data["base"]).upper() != base or str(data["quote"]).upper() != quote:
                    raise ValueError("汇率货币对不匹配")
                entry = {"rate": format(value, "f"), "rate_date": rate_date,
                         "source": "Frankfurter", "fetched_at": datetime.now(timezone.utc).isoformat()}
                self.rates[key] = (time.monotonic(), entry)
                self.rates.move_to_end(key)
                while len(self.rates) > 256:
                    self.rates.popitem(last=False)
                return {**entry, "cached": False, "stale": False}
            except (httpx.HTTPError, ValueError, KeyError, TypeError, ArithmeticError) as exc:
                if old and time.monotonic() - old[0] <= STALE_TTL:
                    return {**old[1], "cached": True, "stale": True}
                raise ToolFailure(503, "EXCHANGE_RATE_UNAVAILABLE", "暂时无法获取汇率，且没有有效缓存") from exc
        return await self._coalesce(key, load)

    async def convert(self, body):
        # A still-valid directory is reused; a failed refresh must not prevent
        # a currency pair's permitted stale fallback.
        if self.directory and time.monotonic() - self.directory[0] <= STALE_TTL:
            directory = self.directory[1]
        else:
            try:
                directory = (await self.currencies())["currencies"]
            except ToolFailure:
                old_rate = self.rates.get((body.from_currency, body.to_currency))
                if not self.directory or not old_rate or time.monotonic() - old_rate[0] > STALE_TTL:
                    raise
                directory = self.directory[1]
        supported = {item["code"] for item in directory}
        if body.from_currency not in supported or body.to_currency not in supported:
            raise ToolInputError("不支持的货币代码，请使用货币目录中的代码")
        if body.from_currency == body.to_currency:
            entry = {"rate": "1", "rate_date": None, "source": "identity", "fetched_at": None,
                     "cached": False, "stale": False}
        else:
            entry = await self.rate(body.from_currency, body.to_currency)
        with localcontext() as context:
            context.prec = 64
            result = (Decimal(body.amount) * Decimal(entry["rate"])).quantize(
                Decimal(1).scaleb(-body.precision), rounding=ROUND_HALF_UP)
        return {"amount": body.amount, "from_currency": body.from_currency,
                "to_currency": body.to_currency, "precision": body.precision,
                "result": format(result, "f"), **entry}


service = CurrencyService()
