from django.urls import path

from . import views

app_name = 'cart'

urlpatterns = [
    path('', views.cart_page, name='cart'),
    path('add/', views.add_to_cart, name='add'),
    path('update/', views.update_qty, name='update'),
    path('remove/', views.remove_item, name='remove'),
    path('save-later/', views.save_for_later, name='save_later'),
    path('move-cart/', views.move_to_cart, name='move_to_cart'),
    path('coupon/', views.apply_coupon_view, name='coupon'),
    path('coupon/remove/', views.remove_coupon, name='coupon_remove'),
]
