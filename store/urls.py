from django.contrib.auth import views as auth_views
from django.urls import path

from . import views, views_care

urlpatterns = [
    path("", views.home, name="home"),
    path("search/", views.search, name="search"),
    path("api/search/", views.search_suggest, name="search_suggest"),
    path("stylist/", views.stylist, name="stylist"),
    path("api/stylist/", views.stylist_api, name="stylist_api"),
    path("api/size/", views.size_api, name="size_api"),
    path("product/<slug:slug>/", views.product_detail, name="product"),
    path("bag/", views.cart_detail, name="cart"),
    path("bag/add/<int:product_id>/", views.cart_add, name="cart_add"),
    path("bag/add-look/", views.cart_add_look, name="cart_add_look"),
    path("bag/update/", views.cart_update, name="cart_update"),
    path("checkout/", views.checkout, name="checkout"),
    path("order/<int:pk>/", views.order_success, name="order_success"),
    path("account/", views.account, name="account"),
    path("signup/", views.signup, name="signup"),
    path("login/", auth_views.LoginView.as_view(), name="login"),
    # client care
    path("help/", views_care.faq, name="faq"),
    path("help/error-codes/", views_care.error_codes, name="error_codes"),
    path("help/error-codes/<str:code>/preview/", views_care.error_preview, name="error_preview"),
    path("contact/", views_care.contact, name="contact"),
    path("currency/", views_care.set_currency, name="set_currency"),
    path("api/assistant/", views_care.assistant_api, name="assistant_api"),
    path("api/assistant/feedback/", views_care.assistant_feedback, name="assistant_feedback"),
    path("api/assistant/ticket/", views_care.assistant_ticket, name="assistant_ticket"),
    path("api/orders/", views_care.orders_api, name="orders_api"),
    path("health/", views_care.health, name="health"),
    path("health.json", views_care.health_json, name="health_json"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("<str:department>/", views.shop, name="shop"),
    path("<str:department>/<slug:category_slug>/", views.shop, name="shop_category"),
]
