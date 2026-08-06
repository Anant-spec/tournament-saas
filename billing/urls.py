from django.urls import path
from . import views

app_name = "billing"

urlpatterns = [
    path("pricing/", views.pricing, name="pricing"),
    path("create-order/", views.create_order, name="create_order"),
    path("verify-payment/", views.verify_payment, name="verify_payment"),
    path("webhook/razorpay/", views.razorpay_webhook, name="razorpay_webhook"),
]
