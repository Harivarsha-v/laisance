from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Category, Department, Product


class StaticSitemap(Sitemap):
    changefreq, priority = "weekly", 0.6

    def items(self):
        return ["home", "stylist", "faq", "error_codes", "contact"]

    def location(self, name):
        return reverse(name)


class CollectionSitemap(Sitemap):
    changefreq, priority = "weekly", 0.8

    def items(self):
        pages = [(d, None) for d in Department.values]
        for d in Department.values:
            pages += [(d, c.slug) for c in Category.objects.filter(products__department=d).distinct()]
        return pages

    def location(self, item):
        dept, cat = item
        return reverse("shop_category", args=[dept, cat]) if cat else reverse("shop", args=[dept])


class ProductSitemap(Sitemap):
    changefreq, priority = "weekly", 0.9

    def items(self):
        return Product.objects.all()

    def lastmod(self, product):
        return product.updated


SITEMAPS = {"pages": StaticSitemap, "collections": CollectionSitemap, "products": ProductSitemap}
