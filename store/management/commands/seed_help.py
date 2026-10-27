from django.core.management.base import BaseCommand

from store.models import FAQ, ErrorCode

FAQS = [
    ("orders", "How do I place an order?",
     "Choose your size and colour on the piece's page and add it to your bag, then proceed to checkout. You may check out as a guest or sign in to keep a record of your orders in your account.",
     "buy purchase checkout order place"),
    ("orders", "Which payment methods do you accept?",
     "We accept all major credit cards, Apple Pay and bank transfer for orders above $20,000. Payment is taken only once your pieces leave our atelier. (This is a student project, so no payment is actually taken.)",
     "pay payment card credit visa amex apple transfer"),
    ("orders", "Can I change or cancel my order?",
     "Orders can be changed or cancelled within two hours of being placed. After that they are already being prepared in the atelier. Ask the assistant to open a request and client care will help.",
     "change cancel modify amend order mistake"),
    ("delivery", "How long does delivery take?",
     "Express delivery is complimentary on every order. Pieces arrive within 2 to 3 working days in Europe and the United States, and within 5 working days elsewhere, presented in our signature box.",
     "delivery shipping how long arrive days time express when"),
    ("delivery", "Do you ship internationally?",
     "Yes, we deliver to more than 60 countries. Duties and taxes are included in the price shown at checkout, so there is nothing more to pay on arrival.",
     "international abroad country countries worldwide customs duties tax"),
    ("delivery", "How can I track my order?",
     "Once your order leaves the atelier you will receive an email with a tracking link. Signed-in clients can also follow every order from the Account page.",
     "track tracking where is my order status"),
    ("returns", "What is your returns policy?",
     "You may return any piece within 30 days, unworn and with its tags, and we will collect it from your door free of charge. Limited-edition pieces may be exchanged but not refunded.",
     "return returns refund money back policy send back"),
    ("returns", "How do I exchange a size?",
     "Request an exchange through the assistant or your account and we will send the new size as soon as the original is collected. Exchanges are always complimentary.",
     "exchange swap size wrong size too big too small fit"),
    ("pieces", "How do I find my size?",
     "Each piece's page has a size advisor: enter your height, weight and preferred fit, and our AI will suggest a size and select it for you. Our pieces are cut generously for ease of movement.",
     "size sizing fit measurements guide chart small large"),
    ("pieces", "How should I care for cashmere and silk?",
     "We recommend professional cleaning by a specialist. Store knitwear folded, never hung, in the cotton dust bag provided, and let silk rest between wears. Every piece includes complimentary aftercare.",
     "care wash clean cashmere silk wool dry clean store pilling"),
    ("pieces", "What does limited edition mean?",
     "Some pieces are made in very small numbers in a single atelier. To keep them available to as many clients as possible, each is allocated one per client. Adding a second triggers error LA-470.",
     "limited edition allocation one per client exclusive rare LA-470"),
    ("services", "Do you offer repairs or alterations?",
     "Yes. Alterations are complimentary within 60 days of purchase, and we repair any of our pieces for life, from re-knitting cashmere to resoling shoes. Ask the assistant to open a request.",
     "repair repairs repaired alter altered altering alteration alterations tailor tailored hem hemmed shorten shortened take in resole fix mend"),
    ("services", "Can I book a private styling appointment?",
     "Our AI stylist is available at any hour on the Stylist page. For an appointment in one of our salons, ask the assistant and a client advisor will contact you.",
     "appointment private styling stylist salon book personal shopper"),
    ("services", "Where is your boutique, and can I visit in person?",
     "Our salon is at 12 rue de l'Aisance in Paris, open Tuesday to Saturday by appointment. We also hold private previews in London, New York and Tokyo each season; ask the assistant to request an invitation.",
     "boutique boutiques store stores shop shops salon location located address where visit paris london new york tokyo in person"),
    ("account", "Do I need an account to order?",
     "No, you may check out as a guest. An account lets you see your order history and speeds up future orders. You can create one from the Sign in page.",
     "account register sign up login guest password"),
]

ERRORS = [
    ("400", 400, "Bad request", "The request we received was incomplete or malformed, for example a form submitted with missing information or a message the assistant could not read.",
     "Go back, check the details you entered and try again. If it keeps happening, refresh the page."),
    ("401", 401, "Sign-in required", "This page or action belongs to a client account, and you are not signed in.",
     "Sign in, or create an account, then try again. Guest checkout does not need an account."),
    ("403", 403, "Access refused", "You are signed in, or your session is valid, but this action is not permitted. It also appears when a form's security token has expired.",
     "Refresh the page to get a new security token and try again. Staff-only areas cannot be opened by clients."),
    ("404", 404, "Page not found", "The address does not lead to a page. The piece may have left the collection, or the link may be mistyped.",
     "Check the address, return to the collection, or ask the assistant to help you find what you were looking for."),
    ("429", 429, "Too many requests", "Our systems received a lot of requests from you in a short time, so we paused briefly to protect the service. This most often happens when chatting very quickly with the stylist or assistant.",
     "Wait about a minute, then continue. Nothing you did has been lost."),
    ("500", 500, "Something went wrong on our side", "An unexpected error happened on our servers. It is not caused by anything you did, and our team is alerted automatically.",
     "Try again in a moment. If it persists, ask the assistant to open a support ticket and we will follow up."),
    ("503", 503, "Temporarily unavailable", "The maison is briefly closed for maintenance, or a service we rely on is not responding.",
     "Please return in a few minutes. Your bag is kept safely in the meantime."),
    ("LA-470", 470, "Allocation reached", "Specific to L’Aisance: limited-edition pieces are allocated one per client, and this piece is already in your bag or was ordered recently.",
     "Choose a different size or colour of another piece, or ask the assistant about a client allocation request."),
]


class Command(BaseCommand):
    help = "Load the FAQs and error codes the AI assistant answers from."

    def handle(self, *args, **opts):
        FAQ.objects.exclude(question__in=[q for _, q, _, _ in FAQS]).delete()  # drop renamed/removed questions
        for i, (topic, q, a, kw) in enumerate(FAQS):
            FAQ.objects.update_or_create(question=q, defaults={"answer": a, "topic": topic, "keywords": kw, "sort_order": i})
        for i, (code, status, title, meaning, todo) in enumerate(ERRORS):
            ErrorCode.objects.update_or_create(code=code, defaults={
                "http_status": status, "title": title, "meaning": meaning, "what_to_do": todo, "sort_order": i})
        self.stdout.write(self.style.SUCCESS(f"{FAQ.objects.count()} FAQs, {ErrorCode.objects.count()} error codes."))
