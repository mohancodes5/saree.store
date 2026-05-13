from decimal import Decimal

from .cart_utils import cart_subtotal, get_or_create_cart


def cart_summary(request):
    try:
        cart = get_or_create_cart(request)
        count = sum(i.quantity for i in cart.items.filter(save_for_later=False))
        sub = cart_subtotal(cart)
    except Exception:
        count = 0
        sub = Decimal('0')
    return {'cart_count': count, 'cart_subtotal': sub}
