import json
import re

from store.models import Product

from .base import StoreTestCase


def ld_blocks(html):
    """Every JSON-LD object on the page (a block may hold one object or an array of them)."""
    out = []
    for raw in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
        data = json.loads(raw)
        out += data if isinstance(data, list) else [data]
    return out


class SeoTests(StoreTestCase):
    def test_robots_txt_blocks_private_surfaces_and_points_to_sitemap(self):
        body = self.client.get("/robots.txt").content.decode()
        for path in ("/admin/", "/api/", "/checkout/", "/search/"):
            self.assertIn(f"Disallow: {path}", body)
        self.assertIn("Sitemap: http://testserver/sitemap.xml", body)

    def test_sitemap_lists_every_product(self):
        xml = self.client.get("/sitemap.xml").content.decode()
        for p in Product.objects.all():
            self.assertIn(p.get_absolute_url(), xml)

    def test_product_page_has_product_and_breadcrumb_schema(self):
        p = Product.objects.get(name="Double-Face Cashmere Long Coat")
        blocks = ld_blocks(self.client.get(p.get_absolute_url()).content.decode())
        product = next(b for b in blocks if b["@type"] == "Product")
        self.assertEqual(product["offers"]["price"], "8600.00")
        self.assertEqual(product["offers"]["availability"], "https://schema.org/LimitedAvailability")
        self.assertTrue(any(b["@type"] == "BreadcrumbList" for b in blocks))

    def test_faq_schema_matches_the_page(self):
        blocks = ld_blocks(self.client.get("/help/").content.decode())
        self.assertEqual(blocks[0]["@type"], "FAQPage")
        self.assertGreaterEqual(len(blocks[0]["mainEntity"]), 10)

    def test_canonical_and_noindex(self):
        home = self.client.get("/").content.decode()
        self.assertIn('<link rel="canonical" href="http://testserver/">', home)
        self.assertIn('content="index, follow"', home)
        for url in ("/search/?q=silk", "/bag/", "/login/", "/health/"):
            with self.subTest(url=url):
                self.assertIn('content="noindex, follow"', self.client.get(url).content.decode())

    def test_collection_pages_have_unique_descriptions(self):
        women = self.client.get("/women/").content.decode()
        coats = self.client.get("/women/coats/").content.decode()
        desc = lambda h: re.search(r'<meta name="description" content="([^"]+)"', h).group(1)  # noqa: E731
        self.assertNotEqual(desc(women), desc(coats))
