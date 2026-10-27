import logging
import time
from collections import deque

from django.conf import settings
from django.template.loader import render_to_string
from django.http import HttpResponse

from .currency import current_currency

log = logging.getLogger("laisance.requests")

# recent requests, kept in memory for the health page
RECENT = deque(maxlen=200)
STARTED_AT = time.time()
TOTALS = {"requests": 0, "errors": 0}


class RequestLogMiddleware:
    """Logs every request: method, path, status, duration and client IP."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started = time.monotonic()
        response = self.get_response(request)
        ms = round((time.monotonic() - started) * 1000, 1)
        path = request.path
        if not path.startswith(("/static/", "/media/", "/favicon")):
            ip = (request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
                  or request.META.get("REMOTE_ADDR", "-"))
            log.info('%s %s %s %sms ip=%s ua="%s"', request.method, path, response.status_code, ms, ip,
                     request.META.get("HTTP_USER_AGENT", "")[:60])
            TOTALS["requests"] += 1
            TOTALS["errors"] += response.status_code >= 500
            RECENT.append({"method": request.method, "path": path[:80], "status": response.status_code,
                           "ms": ms, "at": time.time()})
        response["X-Response-Time-ms"] = str(ms)
        return response


class MaintenanceModeMiddleware:
    """MAINTENANCE_MODE=true serves the 503 page (health check and admin stay up)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.MAINTENANCE_MODE and not request.path.startswith(("/health", "/admin", "/static")):
            html = render_to_string("errors/error.html", {
                "code": "503", "title": "Temporarily unavailable", "BRAND_NAME": settings.BRAND_NAME,
                "message": "The maison is briefly closed while we refresh the collection. Please return in a few minutes.",
                "minimal": True,
            })
            resp = HttpResponse(html, status=503)
            resp["Retry-After"] = "600"
            return resp
        return self.get_response(request)


class CurrencyMiddleware:
    """Makes the client's chosen currency available to price formatting."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        code = request.session.get("currency", "USD")
        token = current_currency.set(code if code in settings.CURRENCIES else "USD")
        try:
            return self.get_response(request)
        finally:
            current_currency.reset(token)
