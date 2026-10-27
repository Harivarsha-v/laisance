from store.ai.concierge import Concierge, find_error_code
from store.models import SupportTicket

from .base import StoreTestCase


class ErrorCodeDetectionTests(StoreTestCase):
    def test_numbers_and_descriptions_map_to_codes(self):
        cases = {"what does 429 mean": "429", "I got error 404": "404", "what is LA-470": "LA-470",
                 "the page says too many requests": "429", "it says forbidden": "403", "site is down": "503"}
        for message, code in cases.items():
            with self.subTest(message=message):
                self.assertEqual(find_error_code(message), code)

    def test_prices_are_not_error_codes(self):
        self.assertIsNone(find_error_code("is there a scarf under $500"))

    def test_unknown_code_lists_the_real_ones(self):
        reply = Concierge().reply("error 418")
        self.assertEqual(reply["kind"], "error")
        self.assertIn("LA-470", reply["html"])


class FaqAnswerTests(StoreTestCase):
    def test_paraphrased_questions_find_the_right_faq(self):
        cases = {
            "how long will shipping take": "How long does delivery take?",
            "can I send it back?": "What is your returns policy?",
            "can I pay with apple pay": "Which payment methods do you accept?",
            "Can I get my coat altered?": "Do you offer repairs or alterations?",
            "how do I wash cashmere": "How should I care for cashmere and silk?",
            "where is your shop": "Where is your boutique, and can I visit in person?",
        }
        for message, question in cases.items():
            with self.subTest(message=message):
                reply = Concierge().reply(message)
                self.assertEqual(reply["kind"], "faq")
                self.assertEqual(reply["title"], question)

    def test_answers_are_html_escaped(self):
        reply = Concierge().reply("where is your boutique")
        self.assertNotIn("l'Aisance", reply["html"])  # the apostrophe is escaped
        self.assertIn("&#x27;", reply["html"])


class TicketFallbackTests(StoreTestCase):
    def test_unanswerable_question_opens_a_ticket(self):
        reply = Concierge(page="/help/").reply("do you sponsor any football teams?")
        self.assertEqual(reply["kind"], "ticket")
        ticket = SupportTicket.objects.get()
        self.assertEqual(reply["ticket"], ticket.reference)
        self.assertEqual(ticket.page, "/help/")
        self.assertEqual(ticket.source, SupportTicket.Source.ASSISTANT)

    def test_asking_for_a_person_opens_a_ticket(self):
        self.assertEqual(Concierge().reply("I want to speak to a human")["kind"], "ticket")

    def test_styling_questions_go_to_the_stylist(self):
        reply = Concierge().reply("black dress for a party")
        self.assertEqual(reply["kind"], "stylist")
        self.assertIn("/stylist/?q=black+dress+for+a+party", reply["html"])
