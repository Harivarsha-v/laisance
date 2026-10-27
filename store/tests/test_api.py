
from django.contrib.auth.models import User
from django.test import override_settings

from store.models import Product, SupportTicket

from .base import StoreTestCase


class AssistantApiTests(StoreTestCase):
    def test_answer_is_logged_with_file_fallback_when_mongo_is_absent(self):
        r = self.post_json("/api/assistant/", {"message": "how long is delivery", "page": "/"})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["kind"], "faq")
        self.assertEqual(data["stored_in"], "file")
        logged = (self.tmp_path / "chat_logs.jsonl").read_text()
        self.assertIn("how long is delivery", logged)

    @property
    def tmp_path(self):
        from django.conf import settings
        return settings.LOG_DIR

    def test_feedback_is_stored(self):
        log_id = self.post_json("/api/assistant/", {"message": "returns"}).json()["log_id"]
        r = self.post_json("/api/assistant/feedback/", {"log_id": log_id, "helpful": False})
        self.assertEqual(r.json(), {"ok": True, "stored_in": "file"})
        self.assertIn('"helpful": false', (self.tmp_path / "feedback.jsonl").read_text())

    def test_malformed_json_is_400(self):
        r = self.post_json("/api/assistant/", "{not json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["code"], "400")

    def test_empty_message_is_400(self):
        self.assertEqual(self.post_json("/api/assistant/", {"message": "  "}).status_code, 400)

    def test_ticket_email_only_from_the_same_conversation(self):
        ref = self.post_json("/api/assistant/", {"message": "do you sponsor football teams"}).json()["ticket"]
        ok = self.post_json("/api/assistant/ticket/", {"ticket": ref, "email": "client@example.com"})
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(SupportTicket.objects.get().email, "client@example.com")

        self.client.logout()
        self.client.cookies.clear()
        other = self.post_json("/api/assistant/ticket/", {"ticket": ref, "email": "attacker@example.com"})
        self.assertEqual(other.status_code, 403)
        self.assertEqual(SupportTicket.objects.get().email, "client@example.com")

    def test_invalid_email_is_400(self):
        ref = self.post_json("/api/assistant/", {"message": "speak to an advisor"}).json()["ticket"]
        self.assertEqual(self.post_json("/api/assistant/ticket/", {"ticket": ref, "email": "nope"}).status_code, 400)

    @override_settings(AI_RATE_LIMIT=3)
    def test_rate_limit_returns_429_with_retry_after(self):
        statuses = [self.post_json("/api/assistant/", {"message": "hello"}).status_code for _ in range(4)]
        self.assertEqual(statuses, [200, 200, 200, 429])
        r = self.post_json("/api/assistant/", {"message": "hello"})
        self.assertIn("Retry-After", r)
        self.assertEqual(r.json()["code"], "429")

    def test_get_is_not_allowed(self):
        self.assertEqual(self.client.get("/api/assistant/").status_code, 405)


class OrdersApiTests(StoreTestCase):
    def test_anonymous_is_401(self):
        r = self.client.get("/api/orders/")
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.json()["code"], "401")

    def test_signed_in_client_sees_their_orders(self):
        self.client.force_login(User.objects.create_user("client", password="Velvet-Coat-2026"))  # noqa: S106 - test fixture
        self.assertEqual(self.client.get("/api/orders/").json(), {"orders": []})


class CartTests(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.limited = Product.objects.filter(is_limited=True).first()
        self.regular = Product.objects.filter(is_limited=False, sizes__contains="M").first()

    def add(self, product, **data):
        payload = {"size": product.size_list[0], "color": product.color_list[0], **data}
        return self.client.post(f"/bag/add/{product.id}/", payload, HTTP_X_REQUESTED_WITH="fetch")

    def test_limited_piece_twice_is_la_470(self):
        self.assertEqual(self.add(self.limited).status_code, 200)
        r = self.add(self.limited)
        self.assertEqual(r.status_code, 470)
        self.assertEqual(r.json()["code"], "LA-470")

    def test_junk_quantity_does_not_crash(self):
        self.assertEqual(self.add(self.regular, quantity="abc").status_code, 200)
        self.assertEqual(self.add(self.regular, quantity="-5").json()["count"], 2)

    def test_invalid_size_is_rejected(self):
        self.assertEqual(self.add(self.regular, size="XXXL").status_code, 400)

    def test_checkout_creates_order_and_empties_bag(self):
        self.add(self.regular)
        r = self.client.post("/checkout/", {"full_name": "Ada Client", "email": "ada@example.com",
                                            "address": "1 Rue", "city": "Paris", "postal_code": "75001"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.client.get(r["Location"]).status_code, 200)
        self.assertEqual(self.client.get("/bag/").context["cart"].__len__(), 0)

    def test_other_visitors_cannot_see_an_order(self):
        self.add(self.regular)
        r = self.client.post("/checkout/", {"full_name": "Ada", "email": "a@example.com", "address": "1",
                                            "city": "Paris", "postal_code": "1"})
        url = r["Location"]
        self.client.cookies.clear()
        self.assertEqual(self.client.get(url).status_code, 404)


class StylistApiTests(StoreTestCase):
    def test_builds_a_look_within_budget(self):
        self.post_json("/api/stylist/", {"message": "a wedding guest look under $10,000"})
        data = self.post_json("/api/stylist/", {"message": "For her"}).json()
        self.assertTrue(data["look"]["items"])
        self.assertLessEqual(data["look"]["total"], 10000)

    def test_malformed_json_is_400(self):
        self.assertEqual(self.post_json("/api/stylist/", "{bad").status_code, 400)
