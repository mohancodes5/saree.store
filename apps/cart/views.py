from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.products.models import Product

from .cart_utils import apply_coupon, cart_subtotal, compute_discount, get_or_create_cart
from .models import CartItem


def cart_page(request):
    cart = get_or_create_cart(request)
    items = cart.items.filter(save_for_later=False).select_related('product')
    saved = cart.items.filter(save_for_later=True).select_related('product')
    subtotal = cart_subtotal(cart)
    discount = Decimal('0')
    coupon = None
    if cart.coupon_code:
        c, err = apply_coupon(cart, cart.coupon_code)
        if c:
            coupon = c
            discount = compute_discount(c, subtotal)
    total = subtotal - discount
    return render(
        request,
        'cart/cart.html',
        {
            'cart': cart,
            'items': items,
            'saved_items': saved,
            'subtotal': subtotal,
            'discount': discount,
            'total': total,
            'coupon': coupon,
        },
    )


@require_POST
def add_to_cart(request):
    cart = get_or_create_cart(request)
    pid = request.POST.get('product_id')
    qty = max(1, int(request.POST.get('quantity', 1)))
    color = (request.POST.get('color') or '').strip()
    product = get_object_or_404(Product, pk=pid, is_active=True)
    if product.stock < qty:
        messages.error(request, 'Not enough stock.')
        return redirect(request.META.get('HTTP_REFERER', 'products:shop'))
    item, created = cart.items.get_or_create(
        product=product,
        color_name=color,
        save_for_later=False,
        defaults={'quantity': qty},
    )
    if not created:
        item.quantity = min(product.stock, item.quantity + qty)
        item.save(update_fields=['quantity'])
    messages.success(request, 'Added to bag')
    return redirect(request.META.get('HTTP_REFERER', 'cart:cart'))


@require_POST
def update_qty(request):
    cart = get_or_create_cart(request)
    item_id = request.POST.get('item_id')
    qty = max(1, int(request.POST.get('quantity', 1)))
    item = get_object_or_404(CartItem, pk=item_id, cart=cart, save_for_later=False)
    if qty > item.product.stock:
        qty = item.product.stock
    item.quantity = qty
    item.save(update_fields=['quantity'])
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'subtotal': str(cart_subtotal(cart))})
    return redirect('cart:cart')


@require_POST
def remove_item(request):
    cart = get_or_create_cart(request)
    item_id = request.POST.get('item_id')
    CartItem.objects.filter(pk=item_id, cart=cart).delete()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'ok': True})
    return redirect('cart:cart')


@require_POST
def save_for_later(request):
    cart = get_or_create_cart(request)
    item_id = request.POST.get('item_id')
    item = get_object_or_404(CartItem, pk=item_id, cart=cart, save_for_later=False)
    item.save_for_later = True
    item.save(update_fields=['save_for_later'])
    return redirect('cart:cart')


@require_POST
def move_to_cart(request):
    cart = get_or_create_cart(request)
    item_id = request.POST.get('item_id')
    item = get_object_or_404(CartItem, pk=item_id, cart=cart, save_for_later=True)
    dup = cart.items.filter(
        product=item.product, color_name=item.color_name, save_for_later=False
    ).first()
    if dup:
        dup.quantity += item.quantity
        dup.save(update_fields=['quantity'])
        item.delete()
    else:
        item.save_for_later = False
        item.save(update_fields=['save_for_later'])
    return redirect('cart:cart')


@require_POST
def apply_coupon_view(request):
    cart = get_or_create_cart(request)
    code = request.POST.get('code', '')
    c, err = apply_coupon(cart, code)
    if not c:
        messages.error(request, err)
    else:
        cart.coupon_code = c.code
        cart.save(update_fields=['coupon_code'])
        messages.success(request, 'Coupon applied')
    return redirect('cart:cart')


@require_POST
def remove_coupon(request):
    cart = get_or_create_cart(request)
    cart.coupon_code = ''
    cart.save(update_fields=['coupon_code'])
    return redirect('cart:cart')
