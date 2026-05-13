from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('signup/', views.SignupView.as_view(), name='signup'),
    path('login/', views.StoreLoginView.as_view(), name='login'),
    path('logout/', views.StoreLogoutView.as_view(), name='logout'),
    path('password-reset/', views.StorePasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', views.StorePasswordResetDoneView.as_view(), name='password_reset_done'),
    path(
        'reset/<uidb64>/<token>/',
        views.StorePasswordResetConfirmView.as_view(),
        name='password_reset_confirm',
    ),
    path(
        'reset/done/',
        views.StorePasswordResetCompleteView.as_view(),
        name='password_reset_complete',
    ),
    path('verify-otp/', views.verify_otp_optional, name='otp_verify'),
]
