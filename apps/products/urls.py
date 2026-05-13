from django.urls import path

from . import views

app_name = 'products'

urlpatterns = [
    path('', views.home, name='home'),
    path('shop/', views.shop, name='shop'),
    path('category/<slug:slug>/', views.category_view, name='category'),
    path('saree/<slug:slug>/', views.product_detail, name='detail'),
    path('saree/<slug:slug>/review/', views.add_review, name='add_review'),
    path('search-ajax/', views.search_ajax, name='search_ajax'),
    path('recent/', views.recently_viewed, name='recent'),
]
