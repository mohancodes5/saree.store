"""Razorpay order creation and signature verification."""
import hashlib
import hmac
from decimal import Decimal
from django.conf import settings


def is_configured() -> bool:
    return bool(
        getattr(settings, 'RAZORPAY_KEY_ID', '')
        and getattr(settings, 'RAZORPAY_KEY_SECRET', '')
    )


def create_order(amount_paise: int, receipt: str, notes: dict | None = None):
    if not is_configured():
        return None, None
    import razorpay
    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )
    data = {
        'amount': amount_paise,
        'currency': 'INR',
        'receipt': receipt[:40],
        'payment_capture': 1,
    }
    if notes:
        data['notes'] = notes
    order = client.order.create(data=data)
    return order['id'], order


def verify_payment_signature(order_id: str, payment_id: str, signature: str) -> bool:
    if not is_configured():
        return False
    secret = settings.RAZORPAY_KEY_SECRET.encode()
    payload = f'{order_id}|{payment_id}'.encode()
    digest = hmac.new(secret, payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, signature or '')


def amount_to_paise(amount: Decimal) -> int:
    return int((amount * Decimal('100')).quantize(Decimal('1')))
