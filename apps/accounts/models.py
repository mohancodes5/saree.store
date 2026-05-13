from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile'
    )
    phone = models.CharField(max_length=15, blank=True)
    referral_code = models.CharField(max_length=16, unique=True, db_index=True)
    referred_by = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='referrals'
    )
    otp_code = models.CharField(max_length=6, blank=True)
    otp_sent_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.user.get_username()
