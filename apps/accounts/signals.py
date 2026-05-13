from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import secrets
import string

from .models import UserProfile


def _gen_code():
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(8))


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if not created:
        return
    code = _gen_code()
    while UserProfile.objects.filter(referral_code=code).exists():
        code = _gen_code()
    UserProfile.objects.create(user=instance, referral_code=code)
