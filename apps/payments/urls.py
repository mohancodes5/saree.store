from django.urls import path

from . import views

app_name = 'payments'

urlpatterns = [
    path('razorpay/verify/', views.razorpay_verify, name='razorpay_verify'),
]
