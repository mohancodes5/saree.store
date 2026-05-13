from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.orders.models import Order

from services import whatsapp_service


@receiver(pre_save, sender=Order)
def cache_order_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_status = None
        instance._previous_payment_status = None
        return
    try:
        old = Order.objects.get(pk=instance.pk)
        instance._previous_status = old.status
        instance._previous_payment_status = old.payment_status
    except Order.DoesNotExist:
        instance._previous_status = None
        instance._previous_payment_status = None


@receiver(post_save, sender=Order)
def order_status_whatsapp(sender, instance, created, **kwargs):
    prev = getattr(instance, '_previous_status', None)
    prev_pay = getattr(instance, '_previous_payment_status', None)
    if created:
        whatsapp_service.notify_order_placed(instance)
        return
    if prev != instance.status:
        if instance.status == Order.STATUS_SHIPPED:
            whatsapp_service.notify_shipped(instance)
        elif instance.status == Order.STATUS_DELIVERED:
            whatsapp_service.notify_delivered(instance)
        elif instance.status == Order.STATUS_CANCELLED:
            whatsapp_service.notify_cancelled(instance)
    if prev_pay != instance.payment_status and instance.payment_status == 'paid':
        whatsapp_service.notify_payment_success(instance)
