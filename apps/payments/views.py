from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from apps.orders.models import Order
from apps.payments.models import Payment
from apps.products.models import Product

from services import razorpay_service


@login_required
@require_POST
def razorpay_verify(request):
    order_id = request.POST.get('order_id')
    payment_id = request.POST.get('razorpay_payment_id')
    signature = request.POST.get('razorpay_signature')
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    if order.payment_status == 'paid':
        return redirect('orders:confirmation', pk=order.pk)
    if not razorpay_service.verify_payment_signature(
        order.razorpay_order_id, payment_id, signature
    ):
        order.payment_status = 'failed'
        order.save(update_fields=['payment_status'])
        return redirect('orders:detail', pk=order.pk)
    with transaction.atomic():
        order.payment_status = 'paid'
        order.save(update_fields=['payment_status'])
        for line in order.items.all():
            p = Product.objects.select_for_update().get(pk=line.product_id_snap)
            p.stock = max(0, p.stock - line.quantity)
            p.save(update_fields=['stock'])
    Payment.objects.filter(order=order).update(
        razorpay_payment_id=payment_id,
        razorpay_signature=signature or '',
        status='captured',
    )
    return redirect('orders:confirmation', pk=order.pk)
