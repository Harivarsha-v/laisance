from django.contrib import admin, messages

from .ai.copywriter import write_copy
from .models import FAQ, Category, ErrorCode, Order, OrderItem, Product, SupportTicket


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slot", "sort_order"]
    list_editable = ["sort_order"]
    prepopulated_fields = {"slug": ["name"]}


@admin.action(description="✨ Rewrite description & tags with AI")
def regenerate_copy(modeladmin, request, queryset):
    for product in queryset:
        copy = write_copy(product, variant=product.pk + len(product.description))
        product.description = copy["description"]
        product.tags = ", ".join(copy["tags"])
        product.save()
    messages.success(request, f"AI rewrote copy for {queryset.count()} product(s).")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "department", "category", "price", "style", "season", "is_new", "is_featured", "is_limited"]
    list_filter = ["department", "category", "style", "season", "is_new", "is_featured"]
    list_editable = ["price", "is_new", "is_featured", "is_limited"]
    search_fields = ["name", "description", "tags", "colors"]
    actions = [regenerate_copy]
    fieldsets = [
        (None, {"fields": ["name", "slug", "department", "category", "price", "image", "swatch"]}),
        ("Details", {"fields": ["material", "colors", "sizes", "style", "season", "is_new", "is_featured", "is_limited"]}),
        ("Copy (AI fills blanks on save)", {"fields": ["description", "tags"]}),
    ]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["product", "size", "color", "quantity", "price"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "full_name", "email", "status", "created", "total"]
    list_filter = ["status"]
    list_editable = ["status"]
    inlines = [OrderItemInline]


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ["question", "topic", "sort_order", "is_published"]
    list_filter = ["topic", "is_published"]
    list_editable = ["sort_order", "is_published"]
    search_fields = ["question", "answer", "keywords"]


@admin.register(ErrorCode)
class ErrorCodeAdmin(admin.ModelAdmin):
    list_display = ["code", "http_status", "title", "sort_order"]
    list_editable = ["sort_order"]


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ["reference", "subject", "email", "source", "status", "created"]
    list_filter = ["status", "source"]
    list_editable = ["status"]
    search_fields = ["subject", "message", "email"]
    readonly_fields = ["created"]
