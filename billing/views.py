import hmac
import hashlib
import json
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from datetime import timedelta

from .models import Plan, Subscription


def _razorpay_client():
    import razorpay
    return razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )


def _get_org(user):
    """Return the first org the user owns, or None."""
    return user.owned_organizations.first()


@login_required
def pricing(request):
    """Plan selection page — shows all plans."""
    plans = Plan.objects.all().order_by("price_monthly")
    org = _get_org(request.user)
    current_sub = getattr(org, "subscription", None) if org else None
    return render(request, "billing/pricing.html", {
        "plans": plans,
        "current_sub": current_sub,
        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
    })


@login_required
@require_POST
def create_order(request):
    """
    POST { "plan_id": "<uuid>" }
    Creates a Razorpay order and returns { order_id, amount, currency, key_id }.
    """
    try:
        body = json.loads(request.body)
        plan_id = body["plan_id"]
    except (KeyError, json.JSONDecodeError):
        return JsonResponse({"error": "plan_id required"}, status=400)

    plan = get_object_or_404(Plan, id=plan_id)

    if plan.price_monthly == 0:
        return JsonResponse({"error": "Free plan does not require payment"}, status=400)

    org = _get_org(request.user)
    if not org:
        return JsonResponse({"error": "You must create an organisation before upgrading."}, status=400)

    amount_paise = int(plan.price_monthly * 100)

    # Razorpay receipt max 40 chars; UUID is 36 so use last 32 chars of plan id
    receipt = f"p_{str(plan.id).replace('-', '')[:32]}"

    client = _razorpay_client()
    order = client.order.create({
        "amount": amount_paise,
        "currency": "INR",
        "receipt": receipt,
        "notes": {
            "plan_name": plan.name,
            "user_id": str(request.user.id),
            "org_id": str(org.id),
        },
    })

    return JsonResponse({
        "order_id": order["id"],
        "amount": amount_paise,
        "currency": "INR",
        "key_id": settings.RAZORPAY_KEY_ID,
        "plan_id": str(plan.id),
        "plan_name": plan.get_name_display(),
    })


@login_required
@require_POST
def verify_payment(request):
    """
    POST { razorpay_order_id, razorpay_payment_id, razorpay_signature, plan_id }
    Verifies the HMAC signature and activates the subscription.
    """
    try:
        body = json.loads(request.body)
        order_id = body["razorpay_order_id"]
        payment_id = body["razorpay_payment_id"]
        signature = body["razorpay_signature"]
        plan_id = body["plan_id"]
    except (KeyError, json.JSONDecodeError):
        return JsonResponse({"error": "Missing required fields"}, status=400)

    expected = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(),
        f"{order_id}|{payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        return JsonResponse({"error": "Invalid payment signature"}, status=400)

    plan = get_object_or_404(Plan, id=plan_id)
    org = _get_org(request.user)
    if not org:
        return JsonResponse({"error": "No organisation found."}, status=400)

    sub, _ = Subscription.objects.get_or_create(organization=org, defaults={"plan": plan})
    sub.plan = plan
    sub.status = "active"
    sub.expires_at = timezone.now() + timedelta(days=30)
    sub.save()

    return JsonResponse({"status": "ok", "plan": plan.get_name_display()})


@csrf_exempt
@require_POST
def razorpay_webhook(request):
    webhook_secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", None)
    if webhook_secret:
        received_sig = request.headers.get("X-Razorpay-Signature", "")
        expected = hmac.new(
            webhook_secret.encode(),
            request.body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, received_sig):
            return HttpResponse(status=400)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    event = payload.get("event")
    if event == "payment.captured":
        pass  # verify_payment already handles activation; add email/analytics here

    return HttpResponse(status=200)
