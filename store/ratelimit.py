"""Tiny fixed-window rate limiter for the AI endpoints (returns HTTP 429)."""

import functools
import time

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse


def client_ip(request):
    return (request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
            or request.META.get("REMOTE_ADDR", "unknown"))


def rate_limited(scope, per_minute=None, html=False, methods=None):
    """429 after `per_minute` requests per IP. html=True renders the 429 page instead of JSON;
    methods=("POST",) limits only those methods (e.g. sign-in attempts, not page views)."""
    def decorator(view):
        @functools.wraps(view)
        def wrapper(request, *args, **kwargs):
            if methods and request.method not in methods:
                return view(request, *args, **kwargs)
            limit = per_minute or settings.AI_RATE_LIMIT
            window = int(time.time() // 60)
            key = f"rl:{scope}:{client_ip(request)}:{window}"
            count = cache.get_or_set(key, 0, 61)
            if count >= limit:
                if html:
                    from .views_care import _error_page

                    resp = _error_page(request, "429", 429)
                    resp["Retry-After"] = str(60 - int(time.time()) % 60)
                    return resp
                resp = JsonResponse({
                    "error": "You're sending messages a little quickly. Please wait a minute and try again.",
                    "code": "429",
                }, status=429)
                resp["Retry-After"] = str(60 - int(time.time()) % 60)
                return resp
            cache.incr(key)
            return view(request, *args, **kwargs)
        return wrapper
    return decorator
