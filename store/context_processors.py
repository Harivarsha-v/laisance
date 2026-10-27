from django.conf import settings

from .ai.concierge import STARTERS as ASSISTANT_STARTERS
from .cart import Cart
from .currency import current_currency
from .models import Category, Department


def store_context(request):
    return {
        "BRAND_NAME": settings.BRAND_NAME,
        "CURRENCY": settings.CURRENCY_SYMBOL,
        "cart_count": len(Cart(request)),
        "nav_departments": Department.choices,
        "nav_categories": Category.objects.all(),
        "currencies": list(settings.CURRENCIES),
        "currency": current_currency.get(),
        "assistant_starters": ASSISTANT_STARTERS,
    }
