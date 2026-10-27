"""Client care: FAQ, error codes, contact, the AI assistant API, error pages and health check."""

import json
import logging
import platform
import time

import django
from django.conf import settings
from django.contrib import messages
from django.db import connection
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from . import currency, mongo
from .ai.concierge import STARTERS, Concierge
from .forms import ContactForm
from .middleware import RECENT, STARTED_AT, TOTALS
from .models import FAQ, ErrorCode, Order, Product, SupportTicket
from .ratelimit import rate_limited

log = logging.getLogger("laisance")
TICKETS_SESSION_KEY = "assistant_tickets"


# ---- pages -------------------------------------------------------------

def faq(request):
    order = list(FAQ.Topic.values)  # orders, delivery, returns... in the order they're declared
    topics = {}
    for f in sorted(FAQ.objects.filter(is_published=True), key=lambda f: (order.index(f.topic), f.sort_order)):
        topics.setdefault(f.get_topic_display(), []).append(f)
    ld = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": f.question, "acceptedAnswer": {"@type": "Answer", "text": f.answer}}
        for faqs in topics.values() for f in faqs]}
    return render(request, "care/faq.html", {"topics": topics, "ld": ld})


def error_codes(request):
    return render(request, "care/error_codes.html", {"codes": ErrorCode.objects.all()})


def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ticket = form.save(commit=False)
        ticket.source = SupportTicket.Source.FORM
        ticket.page = request.path
        ticket.save()
        messages.success(request, f"Thank you. Your request {ticket.reference} has been received.")
        return redirect("contact")
    return render(request, "care/contact.html", {"form": form})


@require_POST
def set_currency(request):
    code = request.POST.get("currency", "USD")
    if code in settings.CURRENCIES:
        request.session["currency"] = code
    nxt = request.POST.get("next", "/")
    return redirect(nxt if url_has_allowed_host_and_scheme(nxt, {request.get_host()}) else "/")


# ---- AI assistant API --------------------------------------------------

def _json_body(request):
    try:
        return json.loads(request.body or "{}"), None
    except json.JSONDecodeError:
        return None, JsonResponse({"error": "We couldn't read that message.", "code": "400"}, status=400)


@require_POST
@rate_limited("assistant")
def assistant_api(request):
    payload, error = _json_body(request)
    if error:
        return error
    message = str(payload.get("message", "")).strip()[:500]
    if not message:
        return JsonResponse({"error": "Please type a question first.", "code": "400"}, status=400)
    page = str(payload.get("page", ""))[:255]

    reply = Concierge(page=page).reply(message)
    if reply["ticket"]:
        request.session[TICKETS_SESSION_KEY] = [*request.session.get(TICKETS_SESSION_KEY, []), reply["ticket"]][-10:]
    if not request.session.session_key:
        request.session.save()

    log_id, store = mongo.insert("chat_logs", {
        "session": request.session.session_key, "page": page, "message": message,
        "reply": reply["html"], "kind": reply["kind"], "matched": reply["matched"],
        "confidence": reply["confidence"], "ticket": reply["ticket"],
        "user": request.user.username if request.user.is_authenticated else None,
    })
    return JsonResponse({**reply, "log_id": log_id, "stored_in": store})


@require_POST
@rate_limited("feedback")
def assistant_feedback(request):
    payload, error = _json_body(request)
    if error:
        return error
    log_id = str(payload.get("log_id", ""))[:64]
    if not log_id:
        return JsonResponse({"error": "Missing log id.", "code": "400"}, status=400)
    _, store = mongo.insert("feedback", {
        "log_id": log_id, "helpful": bool(payload.get("helpful")),
        "comment": str(payload.get("comment", ""))[:500], "session": request.session.session_key,
    })
    return JsonResponse({"ok": True, "stored_in": store})


@require_POST
@rate_limited("ticket")
def assistant_ticket(request):
    """Attach the client's email to a ticket the assistant opened in this session."""
    payload, error = _json_body(request)
    if error:
        return error
    ref = str(payload.get("ticket", ""))
    if ref not in request.session.get(TICKETS_SESSION_KEY, []):
        return JsonResponse({"error": "That request isn't linked to this conversation.", "code": "403"}, status=403)
    email = str(payload.get("email", "")).strip()[:254]
    from django.core.validators import validate_email
    from django.core.exceptions import ValidationError

    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({"error": "Please enter a valid email address.", "code": "400"}, status=400)
    SupportTicket.objects.filter(pk=int(ref.split("-")[1])).update(email=email)
    return JsonResponse({"ok": True, "message": f"Thank you. An advisor will reply to {email} about {ref}."})


def orders_api(request):
    """JSON list of the signed-in client's orders (401 when not signed in)."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Please sign in to see your orders.", "code": "401"}, status=401)
    orders = Order.objects.filter(user=request.user).prefetch_related("items__product")
    return JsonResponse({"orders": [
        {"reference": f"{o.pk:05d}", "status": o.status, "created": o.created.isoformat(), "total": float(o.total),
         "items": [i.product.name for i in o.items.all()]} for o in orders]})


# ---- health check ----------------------------------------------------------

def _health():
    checks = {}
    t = time.monotonic()
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
        checks["database"] = {"ok": True, "engine": connection.vendor, "latency_ms": round((time.monotonic() - t) * 1000, 1),
                              "products": Product.objects.count(), "faqs": FAQ.objects.count(),
                              "error_codes": ErrorCode.objects.count(), "open_tickets": SupportTicket.objects.filter(status="open").count()}
    except Exception as exc:
        checks["database"] = {"ok": False, "error": str(exc)[:160]}
    checks["mongodb"] = mongo.status()
    checks["exchange_rate_api"] = currency.status()
    recent = list(RECENT)[-50:]
    checks["requests"] = {
        "ok": True, "total_since_start": TOTALS["requests"], "server_errors": TOTALS["errors"],
        "avg_ms_last_50": round(sum(r["ms"] for r in recent) / len(recent), 1) if recent else None,
    }
    overall = "ok" if all(c["ok"] for c in checks.values()) else ("down" if not checks["database"]["ok"] else "degraded")
    return {
        "status": overall, "service": settings.BRAND_NAME, "uptime_s": round(time.time() - STARTED_AT),
        "debug": settings.DEBUG, "maintenance_mode": settings.MAINTENANCE_MODE,
        "versions": {"python": platform.python_version(), "django": django.get_version()}, "checks": checks,
    }, recent[::-1][:15]


def health(request):
    data, recent = _health()
    return render(request, "care/health.html", {"health": data, "recent": recent},
                  status=503 if data["status"] == "down" else 200)


def health_json(request):
    data, _ = _health()
    return JsonResponse(data, status=503 if data["status"] == "down" else 200, json_dumps_params={"indent": 2})


# ---- custom error pages ---------------------------------------------------

def _error_page(request, code, status, message=None):
    err = None
    try:
        err = ErrorCode.objects.filter(code=code).first()
    except Exception:  # database may be the reason we're here; still show a page
        log.exception("Could not load error code %s for the error page", code)
    ctx = {"code": code, "title": err.title if err else "Something went wrong",
           "message": message or (err.meaning if err else ""), "what_to_do": err.what_to_do if err else "",
           "assistant_prompt": f"What does error {code} mean?", "path": request.path}
    try:
        return render(request, "errors/error.html", ctx, status=status)
    except Exception:
        # last resort: a page that needs nothing (no database, no context processors)
        html = render_to_string("errors/error.html", {**ctx, "minimal": True, "BRAND_NAME": settings.BRAND_NAME})
        return HttpResponse(html, status=status)


def bad_request(request, exception=None):
    return _error_page(request, "400", 400)


def permission_denied(request, exception=None):
    return _error_page(request, "403", 403)


def csrf_failure(request, reason=""):
    return _error_page(request, "403", 403, "Your session's security token has expired, so we couldn't accept that form.")


def page_not_found(request, exception=None):
    return _error_page(request, "404", 404, "This address doesn't lead anywhere in the maison. The piece may have "
                                            "left the collection, or the link may be mistyped.")


def server_error(request):
    return _error_page(request, "500", 500)


PREVIEWABLE = {"400": 400, "401": 401, "403": 403, "404": 404, "429": 429, "500": 500, "503": 503, "LA-470": 470}


def error_preview(request, code):
    """Shows each custom error page with its real status code (linked from the error codes page)."""
    code = code.upper()
    if code not in PREVIEWABLE:
        raise Http404
    resp = _error_page(request, code, PREVIEWABLE[code])
    if code == "LA-470":
        resp.reason_phrase = "Allocation Reached"
    return resp


def assistant_starters():
    return STARTERS
