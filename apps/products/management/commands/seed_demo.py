from datetime import timedelta
from decimal import Decimal
from io import BytesIO

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db.models import Count
from django.utils import timezone
from PIL import Image

from apps.orders.models import Coupon
from apps.products.models import Category, Product, ProductColor, ProductImage


def _jpeg_placeholder(filename: str, rgb: tuple[int, int, int]) -> ContentFile:
    img = Image.new('RGB', (720, 960), rgb)
    buf = BytesIO()
    img.save(buf, format='JPEG', quality=88)
    buf.seek(0)
    return ContentFile(buf.read(), name=filename)


class Command(BaseCommand):
    help = 'Seed demo categories, products, coupon, staff user, and placeholder images'

    def add_arguments(self, parser):
        parser.add_argument('--staff-password', default='admin123', help='Password for admin user')

    def handle(self, *args, **opts):
        cat, _ = Category.objects.get_or_create(
            slug='silk-classics',
            defaults={'name': 'Silk Classics', 'description': 'Handpicked silk drapes'},
        )
        cat2, _ = Category.objects.get_or_create(
            slug='everyday-cotton',
            defaults={'name': 'Everyday Cotton', 'description': 'Light & breathable'},
        )
        if not Product.objects.exists():
            p = Product.objects.create(
                category=cat,
                name='Rose Garden Banarasi Silk',
                description='Soft silk with zari border. Perfect for weddings and festive evenings.',
                fabric='banarasi',
                occasion='wedding',
                price=Decimal('8999'),
                sale_price=Decimal('6499'),
                stock=25,
                is_featured=True,
                is_trending=True,
                is_new_arrival=True,
                is_best_seller=True,
                meta_title='Rose Garden Banarasi Silk Saree',
                meta_description='Banarasi silk saree with zari border — limited offer.',
                flash_sale_end=timezone.now() + timedelta(days=2),
            )
            ProductColor.objects.create(product=p, name='Maroon')
            ProductColor.objects.create(product=p, name='Gold')
            p2 = Product.objects.create(
                category=cat2,
                name='Breeze Cotton Handloom',
                description='Minimal checks, airy cotton for daily wear.',
                fabric='cotton',
                occasion='casual',
                price=Decimal('1299'),
                stock=60,
                is_featured=True,
                is_new_arrival=True,
            )
            ProductColor.objects.create(product=p2, name='Indigo')
            self.stdout.write(self.style.SUCCESS('Created demo products.'))

        palette = [(120, 20, 60), (30, 58, 95), (45, 90, 70), (90, 40, 110)]
        n = 0
        for p in Product.objects.annotate(ic=Count('images')).filter(ic=0):
            color = palette[p.pk % len(palette)]
            ProductImage.objects.create(
                product=p,
                image=_jpeg_placeholder(f'seed-{p.pk}.jpg', color),
                alt_text=p.name,
                sort_order=0,
            )
            n += 1
        if n:
            self.stdout.write(self.style.SUCCESS(f'Added {n} placeholder product image(s).'))

        Coupon.objects.get_or_create(
            code='WELCOME10',
            defaults={
                'description': '10% off first order',
                'discount_type': Coupon.DISCOUNT_PERCENT,
                'discount_value': Decimal('10'),
                'min_order_amount': Decimal('0'),
                'valid_until': timezone.now() + timedelta(days=365),
            },
        )

        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', opts['staff_password'])
            self.stdout.write(self.style.SUCCESS('Created superuser: admin'))
        else:
            self.stdout.write('User admin already exists.')
