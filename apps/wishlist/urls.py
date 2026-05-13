from django.urls import path

from . import views

app_name = 'wishlist'

urlpatterns = [
    path('', views.wishlist_page, name='list'),
    path('toggle/<int:product_id>/', views.toggle, name='toggle'),
    path('add/<int:product_id>/', views.add, name='add'),
    path('to-cart/<int:product_id>/', views.to_cart, name='to_cart'),
]
