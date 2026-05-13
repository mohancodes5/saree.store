from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View

from .forms import SignupForm, StoreAuthForm


class SignupView(View):
    template_name = 'accounts/signup.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('products:home')
        return render(request, self.template_name, {'form': SignupForm()})

    def post(self, request):
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created. Welcome!')
            return redirect('products:home')
        return render(request, self.template_name, {'form': form})


class StoreLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True
    authentication_form = StoreAuthForm


class StoreLogoutView(LogoutView):
    next_page = reverse_lazy('products:home')


class StorePasswordResetView(PasswordResetView):
    template_name = 'accounts/password_reset_form.html'
    email_template_name = 'accounts/email/password_reset_email.txt'
    subject_template_name = 'accounts/email/password_reset_subject.txt'
    success_url = reverse_lazy('accounts:password_reset_done')


class StorePasswordResetDoneView(PasswordResetDoneView):
    template_name = 'accounts/password_reset_done.html'


class StorePasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'accounts/password_reset_confirm.html'
    success_url = reverse_lazy('accounts:password_reset_complete')


class StorePasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'accounts/password_reset_complete.html'


def verify_otp_optional(request):
    """Optional OTP: demo stores code on profile; in DEBUG shows in message."""
    from django.conf import settings
    import random

    if not request.user.is_authenticated:
        return redirect('accounts:login')
    if request.method == 'POST':
        code = request.POST.get('code', '')
        profile = request.user.profile
        if profile.otp_code and profile.otp_code == code.strip():
            messages.success(request, 'Phone verified.')
            profile.otp_code = ''
            profile.save(update_fields=['otp_code'])
            return redirect('products:home')
        messages.error(request, 'Invalid code.')
        return render(request, 'accounts/otp_verify.html', {})
    profile = request.user.profile
    profile.otp_code = f'{random.randint(100000, 999999)}'
    profile.save(update_fields=['otp_code'])
    if settings.DEBUG:
        messages.info(request, f'Demo OTP (optional): {profile.otp_code}')
    return render(request, 'accounts/otp_verify.html', {})
