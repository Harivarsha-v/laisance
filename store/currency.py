"""Prices in the client's currency, using a third-party exchange-rate API.

The API call has a hard time limit (CURRENCY_API_TIMEOUT). Rates are cached
for six hours; if the API is slow or down we fall back to the last good rates,
then to built-in reference rates, so prices always render.
"""

import json
import logging
import time
import urllib.parse
import urllib.request
from contextvars import ContextVar

from django.conf import settings
from django.core.cache import cache

log = logging.getLogger("laisance")

FALLBACK_RATES = {"USD": 1.0, "EUR": 0.92, "GBP": 0.79, "CHF": 0.88, "JPY": 151.0}
CACHE_KEY, CACHE_SECONDS = "fx-rates", 6 * 60 * 60
current_currency = ContextVar("current_currency", default="USD")

_last = {"source": "not fetched yet", "fetched_at": None, "latency_ms": None, "error": ""}


def _fetch():
    if not settings.CURRENCY_API_URL.startswith("https://"):
        raise ValueError("CURRENCY_API_URL must be an https:// URL")
    targets = ",".join(c for c in settings.CURRENCIES if c != "USD")
    url = f"{settings.CURRENCY_API_URL}?{urllib.parse.urlencode({'from': 'USD', 'to': targets})}"
    headers = {"User-Agent": "laisance-store/1.0", "Accept": "application/json"}
    if settings.CURRENCY_API_KEY:
        headers["Authorization"] = f"Bearer {settings.CURRENCY_API_KEY}"
    started = time.monotonic()
    request = urllib.request.Request(url, headers=headers)  # noqa: S310 - scheme checked above
    with urllib.request.urlopen(request, timeout=settings.CURRENCY_API_TIMEOUT) as r:  # noqa: S310
        data = json.load(r)
    rates = {"USD": 1.0, **{k: float(v) for k, v in data["rates"].items() if k in settings.CURRENCIES}}
    return rates, round((time.monotonic() - started) * 1000)


def get_rates():
    cached = cache.get(CACHE_KEY)
    if cached:
        return cached["rates"]
    try:
        rates, latency = _fetch()
        cache.set(CACHE_KEY, {"rates": rates}, CACHE_SECONDS)
        cache.set(CACHE_KEY + "-last-good", rates, None)
        _last.update(source="live API", fetched_at=time.time(), latency_ms=latency, error="")
        return rates
    except Exception as exc:  # timeout, DNS, bad JSON...
        last_good = cache.get(CACHE_KEY + "-last-good")
        rates = last_good or FALLBACK_RATES
        _last.update(source="last good rates" if last_good else "built-in fallback rates",
                     fetched_at=time.time(), latency_ms=None, error=f"{type(exc).__name__}: {exc}"[:160])
        log.warning("Exchange-rate API failed (%s); using %s", exc, _last["source"])
        cache.set(CACHE_KEY, {"rates": rates}, 10 * 60)  # retry the API in 10 minutes
        return rates


def status():
    get_rates()
    return {**_last, "ok": _last["source"] == "live API" or bool(cache.get(CACHE_KEY + "-last-good")),
            "timeout_s": settings.CURRENCY_API_TIMEOUT, "url": settings.CURRENCY_API_URL}


def format_price(usd, currency=None):
    currency = currency or current_currency.get()
    symbol = settings.CURRENCIES.get(currency, "$")
    amount = float(usd) * get_rates().get(currency, 1.0)
    if currency == "JPY" or amount >= 100:
        amount = round(amount, -1) if currency != "USD" else round(amount)  # boutique-style round prices
        return f"{symbol}{amount:,.0f}"
    return f"{symbol}{amount:,.2f}"
