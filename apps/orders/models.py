from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone


class Coupon(models.Model):
    DISCOUNT_PERCENT = 'percent'
    DISCOUNT_FIXED = 'fixed'
    TYPE_CHOICES = [(DISCOUNT_PERCENT, 'Percent'), (DISCOUNT_FIXED, 'Fixed amount')]

    code = models.CharField(max_length=40, unique=True, db_index=True)
    description = models.CharField(max_length=200, blank=True)
    discount_type = models.CharField(max_length=16, choices=TYPE_CHOICES, default=DISCOUNT_PERCENT)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'))
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    usage_limit = models.PositiveIntegerField(blank=True, null=True)
    times_used = models.PositiveIntegerField(default=0)

    def is_valid_now(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if now < self.valid_from or now > self.valid_until:
            return False
        if self.usage_limit is not None and self.times_used >= self.usage_limit:
            return False
        return True

    def __str__(self):
        return self.code


class Address(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='addresses'
    )
    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=15)
    line1 = models.CharField(max_length=200)
    line2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=80)
    state = models.CharField(max_length=80)
    pincode = models.CharField(max_length=10)
    is_default = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'Addresses'
        ordering = ['-is_default', '-id']

    def __str__(self):
        return f'{self.full_name}, {self.city}'


class Order(models.Model):
    STATUS_ORDERED = 'ordered'
    STATUS_PACKED = 'packed'
    STATUS_SHIPPED = 'shipped'
    STATUS_OUT = 'out_for_delivery'
    STATUS_DELIVERED = 'delivered'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_ORDERED, 'Ordered'),
        (STATUS_PACKED, 'Packed'),
        (STATUS_SHIPPED, 'Shipped'),
        (STATUS_OUT, 'Out for delivery'),
        (STATUS_DELIVERED, 'Delivered'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    PAY_RAZORPAY = 'razorpay'
    PAY_UPI = 'upi'
    PAY_COD = 'cod'
    PAY_CHOICES = [
        (PAY_RAZORPAY, 'Razorpay'),
        (PAY_UPI, 'UPI (Razorpay)'),
        (PAY_COD, 'Cash on Delivery'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='orders',
    )
    order_number = models.CharField(max_length=32, unique=True, db_index=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=15)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=STATUS_ORDERED)
    payment_method = models.CharField(max_length=20, choices=PAY_CHOICES, default=PAY_COD)
    payment_status = models.CharField(
        max_length=20, default='pending',
        help_text='pending, paid, failed, refunded',
    )

    address_snapshot = models.JSONField(default=dict)

    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    coupon_discount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'))
    referral_discount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'))
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    shipping = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'))
    total = models.DecimalField(max_digits=12, decimal_places=2)

    razorpay_order_id = models.CharField(max_length=64, blank=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.order_number


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product_id_snap = models.PositiveIntegerField()
    product_name = models.CharField(max_length=200)
    product_slug = models.SlugField(max_length=220)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    color_name = models.CharField(max_length=64, blank=True)
    quantity = models.PositiveIntegerField(default=1)

    @property
    def line_total(self):
        return self.unit_price * self.quantity


class OrderStatusHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    status = models.CharField(max_length=32)
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    @property
    def status_label(self):
        return dict(Order.STATUS_CHOICES).get(self.status, self.status.replace('_', ' ').title())
