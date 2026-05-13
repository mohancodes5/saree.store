from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import UserProfile


class StoreAuthForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.setdefault('class', 'w-full rounded-xl border border-stone-200 px-3 py-2')


class SignupForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=15, required=False)
    referral_code = forms.CharField(max_length=16, required=False, label='Referral code (optional)')

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ('username', 'email', 'phone', 'referral_code', 'password1', 'password2'):
            if name in self.fields:
                self.fields[name].widget.attrs.setdefault(
                    'class', 'w-full rounded-xl border border-stone-200 px-3 py-2'
                )

    def clean_referral_code(self):
        code = (self.cleaned_data.get('referral_code') or '').strip().upper()
        if not code:
            return ''
        if not UserProfile.objects.filter(referral_code__iexact=code).exists():
            raise forms.ValidationError('Invalid referral code')
        return code

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            phone = self.cleaned_data.get('phone') or ''
            ref = self.cleaned_data.get('referral_code') or ''
            if hasattr(user, 'profile'):
                user.profile.phone = phone
                if ref:
                    ref_profile = UserProfile.objects.get(referral_code__iexact=ref)
                    user.profile.referred_by = ref_profile
                    user.profile.save(update_fields=['phone', 'referred_by'])
                else:
                    user.profile.save(update_fields=['phone'])
        return user
