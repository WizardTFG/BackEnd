from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )

    google_sub = models.CharField(
        max_length=255,
        unique=True
    )

    imagen = models.URLField(
        blank=True,
        null=True
    )

    is_admin = models.BooleanField(default=False)

    def __str__(self):
        return self.user.email