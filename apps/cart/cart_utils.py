from decimal import Decimal

from apps.orders.models import Coupon

from .models import Cart


def get_or_create_cart(request):
    user = request.user if request.user.is_authenticated else None
    session_key = request.session.session_key
    if not session_key:
        request.session.create()
        session_key = request.session.session_key

    if user:
        cart, _ = Cart.objects.get_or_create(user=user, defaults={'session_key': ''})
        orphan = Cart.objects.filter(session_key=session_key, user__isnull=True).first()
        if orphan and orphan.pk != cart.pk:
            for item in orphan.items.filter(save_for_later=False):
                ci, created = cart.items.get_or_create(
                    product=item.product,
                    color_name=item.color_name,
                    save_for_later=False,
                    defaults={'quantity': item.quantity},
                )
                if not created:
                    ci.quantity += item.quantity
                    ci.save()
            orphan.delete()
        if cart.session_key:
            cart.session_key = ''
            cart.save(update_fields=['session_key'])
        return cart

    cart, _ = Cart.objects.get_or_create(
        session_key=session_key, user__isnull=True,
        defaults={'user': None},
    )
    return cart


def cart_subtotal(cart):
    total = Decimal('0')
    for item in cart.items.filter(save_for_later=False).select_related('product'):
        p = item.product
        price = p.effective_price
        total += price * item.quantity
    return total


def apply_coupon(cart, code: str):
    code = (code or '').strip().upper()
    if not code:
        return None, 'Enter a coupon code'
    try:
        c = Coupon.objects.get(code__iexact=code)
    except Coupon.DoesNotExist:
        return None, 'Invalid coupon'
    if not c.is_valid_now():
        return None, 'Coupon expired or inactive'
    sub = cart_subtotal(cart)
    if sub < c.min_order_amount:
        return None, f'Minimum order amount ₹{c.min_order_amount} required'
    return c, ''


def compute_discount(coupon: Coupon, subtotal: Decimal) -> Decimal:
    if coupon.discount_type == Coupon.DISCOUNT_PERCENT:
        d = (subtotal * coupon.discount_value / Decimal('100')).quantize(Decimal('0.01'))
        return min(d, subtotal)
    return min(coupon.discount_value, subtotal)
