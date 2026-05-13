from django.urls import path

from . import views

app_name = 'orders'

urlpatterns = [
    path('checkout/', views.checkout, name='checkout'),
    path('confirmation/<int:pk>/', views.order_confirmation, name='confirmation'),
    path('mine/', views.order_list, name='list'),
    path('<int:pk>/', views.order_detail, name='detail'),
    path('<int:pk>/invoice/', views.invoice, name='invoice'),
    path('addresses/', views.address_list, name='addresses'),
    path('addresses/save/', views.address_save, name='address_save'),
    path('addresses/<int:pk>/delete/', views.address_delete, name='address_delete'),
]
