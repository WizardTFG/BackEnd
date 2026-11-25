from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify


class Application(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_applications'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1

            while Application.objects.filter(
                slug=slug
            ).exclude(pk=self.pk).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1

            self.slug = slug

        super().save(*args, **kwargs)


class ApplicationClinician(models.Model):
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='clinicians'
    )

    clinician = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='clinical_applications'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['application', 'clinician'],
                name='unique_application_clinician'
            )
        ]


class Form(models.Model):
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='forms'
    )

    name = models.CharField(max_length=100)
    fields = models.JSONField(default=list)

    def __str__(self):
        return self.name


class ApplicationResponse(models.Model):
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='responses'
    )

    answers = models.JSONField(default=dict)

    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f'Respuesta de {self.application.name} '
            f'- {self.submitted_at}'
        )