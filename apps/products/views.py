from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Avg, Case, Count, DecimalField, F, Q, When
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_GET, require_POST

import json

from apps.cart.cart_utils import get_or_create_cart
from apps.reviews.forms import ReviewForm
from apps.reviews.models import Review
from apps.wishlist.models import WishlistItem

from .models import Category, HomeBanner, Product, RecentlyViewed


def _record_recent(request, product):
    user = request.user if request.user.is_authenticated else None
    key = request.session.session_key or ''
    if user:
        RecentlyViewed.objects.update_or_create(
            user=user, product=product, defaults={'session_key': ''}
        )
    elif key:
        RecentlyViewed.objects.update_or_create(
            user=None, session_key=key, product=product, defaults={}
        )


def home(request):
    banners = HomeBanner.objects.filter(is_active=True)[:6]
    featured = Product.objects.filter(is_active=True, is_featured=True)[:8]
    trending = Product.objects.filter(is_active=True, is_trending=True)[:8]
    new_arrivals = Product.objects.filter(is_active=True, is_new_arrival=True)[:8]
    best = Product.objects.filter(is_active=True, is_best_seller=True)[:8]
    categories = Category.objects.all()[:12]
    flash = Product.objects.filter(
        is_active=True, flash_sale_end__gt=timezone.now()
    ).order_by('flash_sale_end')[:6]
    return render(
        request,
        'products/home.html',
        {
            'banners': banners,
            'featured': featured,
            'trending': trending,
            'new_arrivals': new_arrivals,
            'best_sellers': best,
            'categories': categories,
            'flash_sale_products': flash,
        },
    )


def shop(request):
    eff = Case(
        When(sale_price__isnull=True, then=F('price')),
        When(sale_price__gte=F('price'), then=F('price')),
        default=F('sale_price'),
        output_field=DecimalField(max_digits=10, decimal_places=2),
    )
    qs = Product.objects.filter(is_active=True).select_related('category').annotate(
        effective_price_filter=eff,
        review_avg=Avg('reviews__rating'),
        review_count=Count('reviews', distinct=True),
    )
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(description__icontains=q)
            | Q(fabric__icontains=q)
            | Q(category__name__icontains=q)
        )
    fabric = request.GET.get('fabric')
    if fabric:
        qs = qs.filter(fabric=fabric)
    occasion = request.GET.get('occasion')
    if occasion:
        qs = qs.filter(occasion=occasion)
    color = request.GET.get('color')
    if color:
        qs = qs.filter(colors__name__icontains=color)
    cat = request.GET.get('category')
    if cat:
        qs = qs.filter(category__slug=cat)
    price_min = request.GET.get('price_min')
    price_max = request.GET.get('price_max')
    if price_min:
        qs = qs.filter(effective_price_filter__gte=price_min)
    if price_max:
        qs = qs.filter(effective_price_filter__lte=price_max)

    sort = request.GET.get('sort', '')
    if sort == 'latest':
        qs = qs.order_by('-created_at')
    elif sort == 'price_low':
        qs = qs.order_by('effective_price_filter')
    elif sort == 'price_high':
        qs = qs.order_by('-effective_price_filter')
    elif sort == 'popular':
        qs = qs.order_by('-review_count', '-review_avg')
    else:
        qs = qs.order_by('-is_featured', '-created_at')

    paginator = Paginator(qs, 12)
    page = paginator.get_page(request.GET.get('page'))
    categories = Category.objects.all()
    return render(
        request,
        'products/shop.html',
        {
            'page_obj': page,
            'categories': categories,
            'filters': request.GET,
            'product_fabric_choices': Product.FABRIC_CHOICES,
            'product_occasion_choices': Product.OCCASION_CHOICES,
        },
    )


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.select_related('category').prefetch_related('images', 'colors'),
        slug=slug,
        is_active=True,
    )
    _record_recent(request, product)
    reviews = product.reviews.filter(is_approved=True).select_related('user')[:50]
    avg = reviews.aggregate(a=Avg('rating'))['a'] or 0
    related = (
        Product.objects.filter(is_active=True, category=product.category)
        .exclude(pk=product.pk)[:8]
    )
    in_wishlist = False
    if request.user.is_authenticated:
        in_wishlist = WishlistItem.objects.filter(user=request.user, product=product).exists()
    form = ReviewForm() if request.user.is_authenticated else None
    pi = product.primary_image
    schema = {
        '@context': 'https://schema.org',
        '@type': 'Product',
        'name': product.name,
        'description': (product.meta_description or product.description)[:500],
        'image': request.build_absolute_uri(pi.image.url) if pi else '',
        'offers': {
            '@type': 'Offer',
            'priceCurrency': 'INR',
            'price': str(product.effective_price),
            'availability': 'https://schema.org/InStock'
            if product.stock > 0
            else 'https://schema.org/OutOfStock',
        },
    }
    return render(
        request,
        'products/detail.html',
        {
            'product': product,
            'reviews': reviews,
            'avg_rating': round(avg, 1),
            'related': related,
            'in_wishlist': in_wishlist,
            'review_form': form,
            'product_schema_json': mark_safe(json.dumps(schema)),
        },
    )


@login_required
@require_POST
def add_review(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    form = ReviewForm(request.POST, request.FILES)
    if form.is_valid():
        rev, created = Review.objects.get_or_create(
            product=product,
            user=request.user,
            defaults={
                'rating': form.cleaned_data['rating'],
                'title': form.cleaned_data.get('title', ''),
                'body': form.cleaned_data['body'],
            },
        )
        if not created:
            rev.rating = form.cleaned_data['rating']
            rev.title = form.cleaned_data.get('title', '')
            rev.body = form.cleaned_data['body']
            rev.save()
        for f in request.FILES.getlist('images'):
            from apps.reviews.models import ReviewImage

            ReviewImage.objects.create(review=rev, image=f)
        messages.success(request, 'Thank you for your review.')
    else:
        messages.error(request, 'Please correct the review form.')
    return redirect('products:detail', slug=slug)


def category_view(request, slug):
    cat = get_object_or_404(Category, slug=slug)
    qs = Product.objects.filter(is_active=True, category=cat).order_by('-created_at')
    paginator = Paginator(qs, 12)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'products/category.html', {'category': cat, 'page_obj': page})


@require_GET
def search_ajax(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'results': []})
    items = (
        Product.objects.filter(is_active=True)
        .filter(Q(name__icontains=q) | Q(description__icontains=q))
        .values('name', 'slug', 'price', 'sale_price')[:10]
    )
    results = []
    for p in items:
        price = p['sale_price'] or p['price']
        results.append({'name': p['name'], 'slug': p['slug'], 'price': str(price)})
    return JsonResponse({'results': results})


@login_required
def recently_viewed(request):
    qs = (
        RecentlyViewed.objects.filter(user=request.user)
        .select_related('product')
        .order_by('-viewed_at')[:24]
    )
    products = [r.product for r in qs if r.product.is_active]
    return render(request, 'products/recent.html', {'products': products})
