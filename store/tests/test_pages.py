from unittest import mock

from django.test import override_settings

from store import currency
from store.models import FAQ, ErrorCode, Product

from .base import StoreTestCase


class SeedDataTests(StoreTestCase):
    def test_assessment_minimums(self):
        self.assertGreaterEqual(FAQ.objects.count(), 10)
        codes = set(ErrorCode.objects.values_list("code", flat=True))
        self.assertTrue({"400", "401", "403", "404", "429", "500", "503", "LA-470"} <= codes)

    def test_every_product_has_ai_copy(self):
        self.assertFalse(Product.objects.filter(description="").exists())


class PageTests(StoreTestCase):
    PAGES = ["/", "/women/", "/men/coats/", "/stylist/", "/search/?q=cashmere", "/bag/", "/help/",
             "/help/error-codes/", "/contact/", "/health/", "/login/", "/signup/"]

    def test_pages_render_with_the_assistant_widget(self):
        for url in self.PAGES + [Product.objects.first().get_absolute_url()]:
            with self.subTest(url=url):
                r = self.client.get(url)
                self.assertEqual(r.status_code, 200)
                self.assertContains(r, "data-concierge")

    def test_faq_page_lists_every_faq(self):
        r = self.client.get("/help/")
        for q in FAQ.objects.values_list("question", flat=True):
            self.assertContains(r, q, html=False)

    def test_security_headers(self):
        r = self.client.get("/")
        self.assertIn("script-src 'self'", r["Content-Security-Policy"])
        self.assertEqual(r["X-Frame-Options"], "DENY")
        self.assertIn("X-Response-Time-ms", r)


@override_settings(DEBUG=False)
class ErrorPageTests(StoreTestCase):
    def test_custom_404_offers_the_assistant(self):
        r = self.client.get("/this/does/not/exist/")
        self.assertEqual(r.status_code, 404)
        self.assertContains(r, "Ask the assistant", status_code=404)
        self.assertContains(r, "What does error 404 mean?", status_code=404)

    def test_custom_500_on_a_crash(self):
        client = self.client_class(raise_request_exception=False)
        with mock.patch("store.views.render", side_effect=RuntimeError("boom")):
            r = client.get("/")
        self.assertEqual(r.status_code, 500)
        self.assertContains(r, "Ask the assistant", status_code=500)

    def test_every_error_page_previews_with_its_status(self):
        for code, status in {"400": 400, "401": 401, "403": 403, "404": 404, "429": 429,
                             "500": 500, "503": 503, "LA-470": 470}.items():
            with self.subTest(code=code):
                self.assertEqual(self.client.get(f"/help/error-codes/{code}/preview/").status_code, status)

    @override_settings(MAINTENANCE_MODE=True)
    def test_maintenance_mode_is_503_but_health_stays_up(self):
        r = self.client.get("/women/")
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r["Retry-After"], "600")
        self.assertEqual(self.client.get("/health.json").status_code, 200)


class HealthAndCurrencyTests(StoreTestCase):
    def test_health_reports_each_dependency(self):
        data = self.client.get("/health.json").json()
        self.assertTrue(data["checks"]["database"]["ok"])
        self.assertEqual(data["checks"]["mongodb"]["store"], "file fallback")
        self.assertEqual(data["checks"]["exchange_rate_api"]["source"], "live API")
        self.assertEqual(data["status"], "degraded")  # mongo not configured in tests

    def test_prices_convert_with_live_rates(self):
        self.assertEqual(currency.format_price(1000, "EUR"), "€900")

    def test_api_timeout_falls_back_to_reference_rates(self):
        self.fetch.side_effect = TimeoutError("timed out")
        self.assertEqual(currency.format_price(1000, "EUR"), "€920")  # built-in rate 0.92
        self.assertEqual(currency.status()["source"], "built-in fallback rates")

    def test_currency_switch_changes_displayed_prices(self):
        self.client.post("/currency/", {"currency": "GBP", "next": "/women/"})
        self.assertContains(self.client.get("/women/"), "£")

    def test_currency_switch_rejects_offsite_redirects(self):
        r = self.client.post("/currency/", {"currency": "EUR", "next": "https://evil.example/"})
        self.assertEqual(r["Location"], "/")
