from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.cart.cart_utils import get_or_create_cart
from apps.products.models import Product

from .models import WishlistItem


@login_required
def wishlist_page(request):
    items = WishlistItem.objects.filter(user=request.user).select_related('product')
    return render(request, 'wishlist/list.html', {'items': items})


@login_required
@require_POST
def toggle(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    item, created = WishlistItem.objects.get_or_create(user=request.user, product=product)
    if not created:
        item.delete()
        return redirect(request.META.get('HTTP_REFERER', 'products:home'))
    return redirect(request.META.get('HTTP_REFERER', 'products:home'))


@login_required
@require_POST
def add(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    WishlistItem.objects.get_or_create(user=request.user, product=product)
    return redirect(request.META.get('HTTP_REFERER', 'products:home'))


@login_required
@require_POST
def to_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    WishlistItem.objects.filter(user=request.user, product=product).delete()
    cart = get_or_create_cart(request)
    ci, created = cart.items.get_or_create(
        product=product, color_name='', save_for_later=False, defaults={'quantity': 1}
    )
    if not created:
        ci.quantity += 1
        ci.save(update_fields=['quantity'])
    return redirect('cart:cart')
