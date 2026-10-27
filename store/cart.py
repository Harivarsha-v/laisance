from decimal import Decimal

from django.conf import settings

from .models import Product


class Cart:
    """Session-backed cart. Lines are keyed by product id + size + colour."""

    def __init__(self, request):
        self.session = request.session
        self.data = self.session.setdefault(settings.CART_SESSION_KEY, {})

    @staticmethod
    def key(product_id, size, color):
        return f"{product_id}|{size}|{color}"

    def add(self, product, size, color, quantity=1):
        k = self.key(product.id, size, color)
        line = self.data.setdefault(k, {"quantity": 0, "price": str(product.price)})
        line["quantity"] = min(line["quantity"] + quantity, 10)
        self.save()

    def set_quantity(self, k, quantity):
        if k not in self.data:
            return
        if quantity <= 0:
            del self.data[k]
        else:
            self.data[k]["quantity"] = min(quantity, 10)
        self.save()

    def remove(self, k):
        self.data.pop(k, None)
        self.save()

    def clear(self):
        self.session[settings.CART_SESSION_KEY] = {}
        self.data = self.session[settings.CART_SESSION_KEY]
        self.save()

    def save(self):
        self.session.modified = True

    def __iter__(self):
        ids = {int(k.split("|")[0]) for k in self.data}
        products = Product.objects.in_bulk(ids)
        for k, line in list(self.data.items()):
            pid, size, color = k.split("|")
            product = products.get(int(pid))
            if product is None:
                continue
            price = Decimal(line["price"])
            yield {
                "key": k,
                "product": product,
                "size": size,
                "color": color,
                "quantity": line["quantity"],
                "price": price,
                "line_total": price * line["quantity"],
            }

    def __len__(self):
        return sum(line["quantity"] for line in self.data.values())

    @property
    def total(self):
        return sum((line["line_total"] for line in self), Decimal("0"))
