from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.forms import StoreAuthForm
from apps.orders.models import Coupon, Order, OrderItem, OrderStatusHistory
from apps.products.models import Category, HomeBanner, Product, ProductColor, ProductImage
from services import whatsapp_service

staff_only = user_passes_test(lambda u: u.is_authenticated and u.is_staff, login_url='adminpanel:login')


class StaffLoginView(LoginView):
    template_name = 'adminpanel/login.html'
    redirect_authenticated_user = True
    authentication_form = StoreAuthForm

    def get_success_url(self):
        return reverse_lazy('adminpanel:dashboard')

    def form_valid(self, form):
        user = form.get_user()
        if not user.is_staff:
            messages.error(self.request, 'Staff access only.')
            return redirect('adminpanel:login')
        return super().form_valid(form)


@staff_only
def dashboard(request):
    today = timezone.now().date()
    month_start = today.replace(day=1)
    orders = Order.objects.all()
    revenue = (
        orders.filter(payment_status='paid').aggregate(s=Sum('total'))['s'] or Decimal('0')
    )
    month_rev = (
        orders.filter(payment_status='paid', created_at__date__gte=month_start).aggregate(
            s=Sum('total')
        )['s']
        or Decimal('0')
    )
    best = (
        OrderItem.objects.values('product_name')
        .annotate(c=Sum('quantity'))
        .order_by('-c')[:8]
    )
    daily = (
        orders.filter(payment_status='paid', created_at__gte=timezone.now() - timedelta(days=14))
        .annotate(d=TruncDate('created_at'))
        .values('d')
        .annotate(total=Sum('total'), cnt=Count('id'))
        .order_by('d')
    )
    return render(
        request,
        'adminpanel/dashboard.html',
        {
            'orders_count': orders.count(),
            'revenue': revenue,
            'month_revenue': month_rev,
            'best': best,
            'daily': list(daily),
        },
    )


@staff_only
def product_list(request):
    q = request.GET.get('q', '')
    qs = Product.objects.select_related('category').order_by('-id')
    if q:
        qs = qs.filter(name__icontains=q)
    return render(request, 'adminpanel/products_list.html', {'products': qs[:200]})


@staff_only
def product_edit(request, pk=None):
    product = get_object_or_404(Product, pk=pk) if pk else None
    categories = Category.objects.all()
    if request.method == 'POST':
        name = request.POST.get('name', '')
        slug = request.POST.get('slug', '')
        cat_id = request.POST.get('category')
        cat = get_object_or_404(Category, pk=cat_id)
        if not product:
            product = Product(category=cat, name=name or 'Untitled', slug=slug or 'item')
        product.name = name
        if slug:
            product.slug = slug
        product.category = cat
        product.description = request.POST.get('description', '')
        product.fabric = request.POST.get('fabric', 'silk')
        product.occasion = request.POST.get('occasion', 'festive')
        product.price = Decimal(request.POST.get('price', '0') or '0')
        sp = request.POST.get('sale_price') or ''
        product.sale_price = Decimal(sp) if sp else None
        product.stock = int(request.POST.get('stock', '0') or '0')
        product.delivery_days = int(request.POST.get('delivery_days', '5') or '5')
        product.meta_title = request.POST.get('meta_title', '')
        product.meta_description = request.POST.get('meta_description', '')
        product.is_active = bool(request.POST.get('is_active'))
        product.is_featured = bool(request.POST.get('is_featured'))
        product.is_trending = bool(request.POST.get('is_trending'))
        product.is_new_arrival = bool(request.POST.get('is_new_arrival'))
        product.is_best_seller = bool(request.POST.get('is_best_seller'))
        fse = request.POST.get('flash_sale_end') or ''
        if fse:
            from django.utils.dateparse import parse_datetime
            from django.utils import timezone as dj_tz

            dt = parse_datetime(fse.replace(' ', 'T'))
            if dt and dj_tz.is_naive(dt):
                dt = dj_tz.make_aware(dt, dj_tz.get_current_timezone())
            product.flash_sale_end = dt
        else:
            product.flash_sale_end = None
        product.save()
        for f in request.FILES.getlist('images'):
            ProductImage.objects.create(product=product, image=f)
        colors = request.POST.get('colors', '')
        if colors:
            ProductColor.objects.filter(product=product).delete()
            for c in [x.strip() for x in colors.split(',') if x.strip()]:
                ProductColor.objects.create(product=product, name=c)
        messages.success(request, 'Product saved.')
        return redirect('adminpanel:product_edit', pk=product.pk)
    return render(
        request,
        'adminpanel/product_form.html',
        {
            'product': product,
            'categories': categories,
            'fabric_choices': Product.FABRIC_CHOICES,
            'occasion_choices': Product.OCCASION_CHOICES,
        },
    )


@staff_only
@require_POST
def product_delete(request, pk):
    Product.objects.filter(pk=pk).delete()
    messages.success(request, 'Deleted.')
    return redirect('adminpanel:products')


@staff_only
def categories(request):
    rows = Category.objects.all()
    if request.method == 'POST':
        Category.objects.create(
            name=request.POST.get('name', 'New'),
            description=request.POST.get('description', ''),
        )
        messages.success(request, 'Category added.')
        return redirect('adminpanel:categories')
    return render(request, 'adminpanel/categories.html', {'categories': rows})


@staff_only
def orders_admin(request):
    rows = Order.objects.select_related('user').order_by('-id')[:300]
    return render(request, 'adminpanel/orders.html', {'orders': rows, 'status_choices': Order.STATUS_CHOICES})


@staff_only
@require_POST
def order_status(request, pk):
    order = get_object_or_404(Order, pk=pk)
    st = request.POST.get('status')
    if st in dict(Order.STATUS_CHOICES):
        order.status = st
        order.save(update_fields=['status'])
        OrderStatusHistory.objects.create(order=order, status=st)
        messages.success(request, 'Status updated.')
    return redirect('adminpanel:orders')


@staff_only
@require_POST
def order_cancel(request, pk):
    order = get_object_or_404(Order, pk=pk)
    order.status = Order.STATUS_CANCELLED
    order.payment_status = 'refunded' if order.payment_status == 'paid' else order.payment_status
    order.save(update_fields=['status', 'payment_status'])
    OrderStatusHistory.objects.create(order=order, status=order.status, note='Cancelled from admin')
    messages.success(request, 'Order cancelled.')
    return redirect('adminpanel:orders')


@staff_only
def customers(request):
    users = User.objects.filter(is_staff=False).order_by('-id')[:200]
    return render(request, 'adminpanel/customers.html', {'users': users})


@staff_only
@require_POST
def promo_whatsapp(request):
    phone = request.POST.get('phone', '')
    msg = request.POST.get('message', '')
    whatsapp_service.send_promotional(phone, msg)
    messages.success(request, 'Message queued (check Twilio / logs).')
    return redirect('adminpanel:customers')


@staff_only
def coupons(request):
    rows = Coupon.objects.order_by('-id')
    if request.method == 'POST':
        Coupon.objects.create(
            code=request.POST.get('code', 'SAVE10').upper(),
            description=request.POST.get('description', ''),
            discount_type=request.POST.get('discount_type', Coupon.DISCOUNT_PERCENT),
            discount_value=Decimal(request.POST.get('discount_value', '10')),
            min_order_amount=Decimal(request.POST.get('min_order_amount', '0')),
            valid_until=timezone.now() + timedelta(days=30),
        )
        messages.success(request, 'Coupon created.')
        return redirect('adminpanel:coupons')
    return render(request, 'adminpanel/coupons.html', {'coupons': rows})


@staff_only
def banners(request):
    rows = HomeBanner.objects.all()
    if request.method == 'POST':
        img = request.FILES.get('image')
        if not img:
            messages.error(request, 'Banner image is required.')
        else:
            HomeBanner.objects.create(
                title=request.POST.get('title', 'Banner'),
                subtitle=request.POST.get('subtitle', ''),
                image=img,
                link=request.POST.get('link', ''),
            )
            messages.success(request, 'Banner added.')
        return redirect('adminpanel:banners')
    return render(request, 'adminpanel/banners.html', {'banners': rows})
