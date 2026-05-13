from django.urls import path

from . import views

app_name = 'adminpanel'

urlpatterns = [
    path('login/', views.StaffLoginView.as_view(), name='login'),
    path('', views.dashboard, name='dashboard'),
    path('products/', views.product_list, name='products'),
    path('products/new/', views.product_edit, name='product_new'),
    path('products/<int:pk>/', views.product_edit, name='product_edit'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('categories/', views.categories, name='categories'),
    path('orders/', views.orders_admin, name='orders'),
    path('orders/<int:pk>/status/', views.order_status, name='order_status'),
    path('orders/<int:pk>/cancel/', views.order_cancel, name='order_cancel'),
    path('customers/', views.customers, name='customers'),
    path('customers/promo/', views.promo_whatsapp, name='promo_whatsapp'),
    path('coupons/', views.coupons, name='coupons'),
    path('banners/', views.banners, name='banners'),
]
