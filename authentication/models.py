from datetime import timedelta
import uuid

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _
from django.core.mail import send_mail
from django.contrib.auth import get_backends, get_user_model
from django.utils.encoding import force_bytes, force_text, DjangoUnicodeDecodeError
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from .managers import LoginTokenManager


class LoginToken(models.Model):
    """
    Login token model.

    """
    user = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
    )
    code = models.UUIDField(
        unique=True,
        default=uuid.uuid4,
        editable=False,
    )
    valid_until = models.DateTimeField()
    sent_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = LoginTokenManager()

    def __str__(self):
        return 'Token({}, {})'.format(self.user.email, self.code)

    def is_valid(self):
        return timezone.now() <= self.valid_until

    def is_expired(self):
        return not self.is_valid()

    @staticmethod
    def b64_encoded(email):
        return urlsafe_base64_encode(force_bytes(email)).decode()

    @staticmethod
    def b64_decoded(email_b64):
        try:
            return force_text(urlsafe_base64_decode(email_b64))
        except DjangoUnicodeDecodeError:
            return None

    def login_url(self):
        return '{}://{}{}'.format(
            'https' if settings.USE_SSL else 'http',
            settings.HOST,
            reverse(
                'verify_token',
                kwargs={
                    'pk': LoginToken.b64_encoded(self.user.primary_key),
                    'code': self.code
                }
            )
        )

    def send(self, code):
        for backend in get_backends():
            if hasattr(backend, 'send'):
                backend.send(self, code)
        self.sent_at = timezone.now()
        self.save()
