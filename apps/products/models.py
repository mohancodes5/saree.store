from django.conf import settings
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, db_index=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    is_featured = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name_plural = 'Categories'

    def save(self, *args, **kwargs):
        base = self.slug or slugify(self.name)[:130] or 'category'
        slug = base
        n = 0
        qs = Category.objects.exclude(pk=self.pk) if self.pk else Category.objects.all()
        while qs.filter(slug=slug).exists():
            n += 1
            slug = f'{base[:110]}-{n}'
        self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('products:category', kwargs={'slug': self.slug})


class HomeBanner(models.Model):
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=300, blank=True)
    image = models.ImageField(upload_to='banners/')
    link = models.CharField(max_length=500, blank=True, help_text='URL path e.g. /shop/?sale=1')
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['sort_order', 'id']

    def __str__(self):
        return self.title


class Product(models.Model):
    FABRIC_CHOICES = [
        ('silk', 'Silk'),
        ('cotton', 'Cotton'),
        ('georgette', 'Georgette'),
        ('chiffon', 'Chiffon'),
        ('linen', 'Linen'),
        ('organza', 'Organza'),
        ('banarasi', 'Banarasi'),
        ('other', 'Other'),
    ]
    OCCASION_CHOICES = [
        ('wedding', 'Wedding'),
        ('party', 'Party'),
        ('festive', 'Festive'),
        ('casual', 'Casual'),
        ('office', 'Office'),
        ('traditional', 'Traditional'),
    ]

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, db_index=True)
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name='products'
    )
    description = models.TextField()
    fabric = models.CharField(max_length=32, choices=FABRIC_CHOICES, default='silk')
    occasion = models.CharField(max_length=32, choices=OCCASION_CHOICES, default='festive')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True,
        help_text='Discounted price; empty means no discount',
    )
    stock = models.PositiveIntegerField(default=0)
    delivery_days = models.PositiveSmallIntegerField(default=5)
    meta_title = models.CharField(max_length=70, blank=True)
    meta_description = models.CharField(max_length=160, blank=True)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_trending = models.BooleanField(default=False)
    is_new_arrival = models.BooleanField(default=False)
    is_best_seller = models.BooleanField(default=False)
    flash_sale_end = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        base = self.slug or slugify(self.name)[:200] or 'product'
        slug = base
        n = 0
        qs = Product.objects.exclude(pk=self.pk) if self.pk else Product.objects.all()
        while qs.filter(slug=slug).exists():
            n += 1
            slug = f'{base[:180]}-{n}'
        self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('products:detail', kwargs={'slug': self.slug})

    @property
    def effective_price(self):
        if self.sale_price is not None and self.sale_price < self.price:
            return self.sale_price
        return self.price

    @property
    def discount_percent(self):
        if self.sale_price is None or self.sale_price >= self.price:
            return 0
        off = (self.price - self.sale_price) / self.price * 100
        return int(off)

    @property
    def primary_image(self):
        return self.images.order_by('sort_order', 'id').first()


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    alt_text = models.CharField(max_length=200, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'id']


class ProductColor(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='colors')
    name = models.CharField(max_length=64)
    hex_code = models.CharField(max_length=7, blank=True)

    class Meta:
        unique_together = [('product', 'name')]

    def __str__(self):
        return f'{self.product.name} — {self.name}'


class RecentlyViewed(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        blank=True, null=True, related_name='recent_views',
    )
    session_key = models.CharField(max_length=40, blank=True, db_index=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-viewed_at']
        indexes = [
            models.Index(fields=['user', '-viewed_at']),
            models.Index(fields=['session_key', '-viewed_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'product'],
                condition=models.Q(user__isnull=False),
                name='uniq_recent_user_product',
            ),
            models.UniqueConstraint(
                fields=['session_key', 'product'],
                condition=models.Q(user__isnull=True),
                name='uniq_recent_session_product',
            ),
        ]
