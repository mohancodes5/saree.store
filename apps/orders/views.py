from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.cart.cart_utils import apply_coupon, cart_subtotal, compute_discount, get_or_create_cart
from apps.cart.models import CartItem
from apps.orders.models import Address, Coupon, Order, OrderItem, OrderStatusHistory
from apps.payments.models import Payment

from services import razorpay_service


def _shipping_for(subtotal: Decimal) -> Decimal:
    if subtotal >= Decimal('999'):
        return Decimal('0')
    return Decimal('49')


@login_required
def checkout(request):
    cart = get_or_create_cart(request)
    items = list(cart.items.filter(save_for_later=False).select_related('product'))
    if not items:
        messages.warning(request, 'Your bag is empty.')
        return redirect('cart:cart')

    addresses = Address.objects.filter(user=request.user)
    subtotal = cart_subtotal(cart)
    coupon = None
    coupon_discount = Decimal('0')
    if cart.coupon_code:
        c, _ = apply_coupon(cart, cart.coupon_code)
        if c:
            coupon = c
            coupon_discount = compute_discount(c, subtotal)

    profile = request.user.profile
    referral_discount = Decimal('0')
    if profile.referred_by_id and not Order.objects.filter(user=request.user).exists():
        referral_discount = (
            subtotal * Decimal(settings.REFERRAL_DISCOUNT_PERCENT) / Decimal('100')
        ).quantize(Decimal('0.01'))

    ship = _shipping_for(subtotal - coupon_discount - referral_discount)
    total = subtotal - coupon_discount - referral_discount + ship

    if request.method == 'POST':
        addr_id = request.POST.get('address_id')
        addr = get_object_or_404(Address, pk=addr_id, user=request.user)
        pay_method = request.POST.get('payment_method', Order.PAY_COD)
        if pay_method not in (Order.PAY_RAZORPAY, Order.PAY_UPI, Order.PAY_COD):
            pay_method = Order.PAY_COD
        if pay_method == Order.PAY_UPI:
            pay_method = Order.PAY_RAZORPAY
        if pay_method == Order.PAY_RAZORPAY and not razorpay_service.is_configured():
            pay_method = Order.PAY_COD

        try:
            with transaction.atomic():
                order = Order.objects.create(
                    user=request.user,
                    order_number='TMP',
                    email=request.user.email or '',
                    phone=addr.phone,
                    status=Order.STATUS_ORDERED,
                    payment_method=pay_method,
                    payment_status='pending',
                    address_snapshot={
                        'full_name': addr.full_name,
                        'phone': addr.phone,
                        'line1': addr.line1,
                        'line2': addr.line2,
                        'city': addr.city,
                        'state': addr.state,
                        'pincode': addr.pincode,
                    },
                    coupon=coupon,
                    coupon_discount=coupon_discount,
                    referral_discount=referral_discount,
                    subtotal=subtotal,
                    shipping=ship,
                    total=total,
                )
                order.order_number = f'SR{timezone.now().year % 100}{order.pk:05d}'
                order.save(update_fields=['order_number'])
                OrderStatusHistory.objects.create(order=order, status=order.status)

                if coupon:
                    coupon.times_used += 1
                    coupon.save(update_fields=['times_used'])

                for ci in items:
                    p = ci.product
                    unit = p.effective_price
                    OrderItem.objects.create(
                        order=order,
                        product_id_snap=p.id,
                        product_name=p.name,
                        product_slug=p.slug,
                        unit_price=unit,
                        color_name=ci.color_name,
                        quantity=ci.quantity,
                    )

                is_prepaid = pay_method == Order.PAY_RAZORPAY and razorpay_service.is_configured()
                if not is_prepaid:
                    for ci in items:
                        p = ci.product
                        p.stock = max(0, p.stock - ci.quantity)
                        p.save(update_fields=['stock'])
                    order.payment_method = Order.PAY_COD
                    order.save(update_fields=['payment_method'])

                if is_prepaid:
                    paise = razorpay_service.amount_to_paise(total)
                    oid, raw = razorpay_service.create_order(
                        paise, order.order_number, {'order_id': str(order.pk)}
                    )
                    if not oid:
                        raise RuntimeError('razorpay')
                    order.razorpay_order_id = oid
                    order.save(update_fields=['razorpay_order_id'])
                    Payment.objects.create(
                        order=order,
                        razorpay_order_id=oid,
                        amount_paise=paise,
                        status='created',
                        raw_response=raw or {},
                    )

                CartItem.objects.filter(pk__in=[i.pk for i in items]).delete()
                cart.coupon_code = ''
                cart.save(update_fields=['coupon_code'])
        except RuntimeError:
            messages.error(request, 'Payment gateway error. Please try COD or try again.')
            return redirect('cart:cart')

        if pay_method == Order.PAY_RAZORPAY and razorpay_service.is_configured() and order.razorpay_order_id:
            paise = razorpay_service.amount_to_paise(total)
            return render(
                request,
                'orders/razorpay_pay.html',
                {
                    'order': order,
                    'razorpay_key': settings.RAZORPAY_KEY_ID,
                    'amount_paise': paise,
                },
            )

        messages.success(request, 'Order placed.')
        return redirect('orders:confirmation', pk=order.pk)

    return render(
        request,
        'orders/checkout.html',
        {
            'addresses': addresses,
            'items': items,
            'subtotal': subtotal,
            'coupon': coupon,
            'coupon_discount': coupon_discount,
            'referral_discount': referral_discount,
            'shipping': ship,
            'total': total,
            'razorpay_ready': razorpay_service.is_configured(),
        },
    )


@login_required
def order_confirmation(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    return render(request, 'orders/confirmation.html', {'order': order})


@login_required
def order_list(request):
    orders = Order.objects.filter(user=request.user)[:50]
    return render(request, 'orders/list.html', {'orders': orders})


@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    return render(request, 'orders/detail.html', {'order': order})


@login_required
def invoice(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    return render(request, 'orders/invoice.html', {'order': order})


@login_required
def address_list(request):
    rows = Address.objects.filter(user=request.user)
    return render(request, 'orders/addresses.html', {'addresses': rows})


@login_required
@require_POST
def address_save(request):
    pk = request.POST.get('id')
    data = {
        'full_name': request.POST.get('full_name', ''),
        'phone': request.POST.get('phone', ''),
        'line1': request.POST.get('line1', ''),
        'line2': request.POST.get('line2', ''),
        'city': request.POST.get('city', ''),
        'state': request.POST.get('state', ''),
        'pincode': request.POST.get('pincode', ''),
    }
    if pk:
        addr = get_object_or_404(Address, pk=pk, user=request.user)
        for k, v in data.items():
            setattr(addr, k, v)
        addr.save()
    else:
        Address.objects.create(user=request.user, **data)
    messages.success(request, 'Address saved.')
    return redirect('orders:addresses')


@login_required
@require_POST
def address_delete(request, pk):
    Address.objects.filter(pk=pk, user=request.user).delete()
    return redirect('orders:addresses')
