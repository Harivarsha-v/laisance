import json
import tempfile
from pathlib import Path
from unittest import mock

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings

FAKE_RATES = {"rates": {"EUR": 0.9, "GBP": 0.8, "CHF": 0.85, "JPY": 150.0}}


@override_settings(MONGODB_URI="", AI_RATE_LIMIT=20)
class StoreTestCase(TestCase):
    """Seeded catalogue + help content; external services mocked; MongoDB falls back to a temp dir."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_store", verbosity=0)
        call_command("seed_help", verbosity=0)

    def setUp(self):
        cache.clear()  # rate-limit windows and exchange-rate cache
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patcher = override_settings(LOG_DIR=Path(self.tmp.name))
        patcher.enable()
        self.addCleanup(patcher.disable)
        fx = mock.patch("store.currency._fetch", return_value=({"USD": 1.0, **FAKE_RATES["rates"]}, 12))
        self.fetch = fx.start()
        self.addCleanup(fx.stop)

    def post_json(self, url, payload, **extra):
        body = payload if isinstance(payload, str) else json.dumps(payload)
        return self.client.post(url, body, content_type="application/json", **extra)
