from django.conf import settings
from django.db import models


class Cart(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        blank=True, null=True, related_name='carts',
    )
    session_key = models.CharField(max_length=40, blank=True, db_index=True)
    coupon_code = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['session_key']),
        ]

    def __str__(self):
        if self.user_id:
            return f'Cart user={self.user_id}'
        return f'Cart session={self.session_key[:8]}'


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    color_name = models.CharField(max_length=64, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    save_for_later = models.BooleanField(default=False)

    class Meta:
        unique_together = [('cart', 'product', 'color_name', 'save_for_later')]
