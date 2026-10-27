from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class Department(models.TextChoices):
    WOMEN = "women", "Women"
    MEN = "men", "Men"


class Slot(models.TextChoices):
    """Where a garment sits in an outfit. The AI stylist builds looks slot by slot."""

    TOP = "top", "Top"
    BOTTOM = "bottom", "Bottom"
    ONE_PIECE = "one_piece", "One-piece"
    OUTERWEAR = "outerwear", "Outerwear"
    SHOES = "shoes", "Shoes"
    ACCESSORY = "accessory", "Accessory"


class Style(models.TextChoices):
    CASUAL = "casual", "Casual"
    WORK = "work", "Work"
    FORMAL = "formal", "Formal"
    EVENING = "evening", "Evening"
    SPORT = "sport", "Sport"
    STREET = "street", "Street"


class Season(models.TextChoices):
    ALL = "all", "All year"
    SUMMER = "summer", "Summer"
    WINTER = "winter", "Winter"
    TRANSITIONAL = "transitional", "Spring / Autumn"


class Category(models.Model):
    name = models.CharField(max_length=60)
    slug = models.SlugField(unique=True)
    slot = models.CharField(max_length=20, choices=Slot.choices)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True, blank=True)
    department = models.CharField(max_length=10, choices=Department.choices)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    price = models.DecimalField(max_digits=8, decimal_places=2)
    description = models.TextField(blank=True, help_text="Leave blank and the AI writes one on save.")
    material = models.CharField(max_length=60, blank=True)
    colors = models.CharField(max_length=120, help_text="Comma separated, e.g. black, ecru")
    sizes = models.CharField(max_length=60, default="XS, S, M, L, XL")
    tags = models.CharField(max_length=255, blank=True, help_text="Comma separated. AI fills these if blank.")
    style = models.CharField(max_length=20, choices=Style.choices, default=Style.CASUAL)
    season = models.CharField(max_length=20, choices=Season.choices, default=Season.ALL)
    swatch = models.CharField(max_length=7, default="#d9d4cc", help_text="Hex colour for the placeholder image")
    image = models.FileField(upload_to="products/", blank=True)
    is_new = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    is_limited = models.BooleanField(default=False, help_text="Limited edition: one per client (error LA-470 if exceeded)")
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_new", "-created"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(f"{self.name}-{self.department}")
            slug, n = base, 2
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug, n = f"{base}-{n}", n + 1
            self.slug = slug
        if not self.description or not self.tags:
            from .ai.copywriter import write_copy

            copy = write_copy(self)
            self.description = self.description or copy["description"]
            self.tags = self.tags or ", ".join(copy["tags"])
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("product", args=[self.slug])

    @property
    def color_list(self):
        return [c.strip().lower() for c in self.colors.split(",") if c.strip()]

    @property
    def size_list(self):
        return [s.strip() for s in self.sizes.split(",") if s.strip()]

    @property
    def tag_list(self):
        return [t.strip().lower() for t in self.tags.split(",") if t.strip()]

    @property
    def slot(self):
        return self.category.slot


class Order(models.Model):
    class Status(models.TextChoices):
        PLACED = "placed", "Placed"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    full_name = models.CharField(max_length=120)
    email = models.EmailField()
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=80)
    postal_code = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLACED)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"Order #{self.pk}"

    @property
    def total(self):
        return sum((item.line_total for item in self.items.all()), Decimal("0"))


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    size = models.CharField(max_length=10)
    color = models.CharField(max_length=30)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=8, decimal_places=2)

    @property
    def line_total(self):
        return self.price * self.quantity


# ---- client care: the AI assistant answers from these tables ----------------

class FAQ(models.Model):
    class Topic(models.TextChoices):
        ORDERS = "orders", "Orders & payment"
        DELIVERY = "delivery", "Delivery"
        RETURNS = "returns", "Returns & exchanges"
        PIECES = "pieces", "Our pieces"
        SERVICES = "services", "Services"
        ACCOUNT = "account", "Your account"

    question = models.CharField(max_length=200)
    answer = models.TextField()
    topic = models.CharField(max_length=20, choices=Topic.choices)
    keywords = models.CharField(max_length=255, blank=True, help_text="Extra words that should match this answer")
    sort_order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["topic", "sort_order"]
        verbose_name = "FAQ"

    def __str__(self):
        return self.question


class ErrorCode(models.Model):
    code = models.CharField(max_length=12, unique=True, help_text="e.g. 404 or LA-470")
    http_status = models.PositiveIntegerField()
    title = models.CharField(max_length=80)
    meaning = models.TextField(help_text="What happened, in plain words")
    what_to_do = models.TextField()
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.code} {self.title}"


class SupportTicket(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        ANSWERED = "answered", "Answered"
        CLOSED = "closed", "Closed"

    class Source(models.TextChoices):
        ASSISTANT = "assistant", "AI assistant"
        FORM = "form", "Contact form"

    name = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True)
    subject = models.CharField(max_length=160)
    message = models.TextField()
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.ASSISTANT)
    page = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"{self.reference} {self.subject}"

    @property
    def reference(self):
        return f"LA-{self.pk:05d}" if self.pk else "LA-new"
