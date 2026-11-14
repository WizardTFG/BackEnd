from django.urls import path
from api.views import google_login, current_user

urlpatterns = [
    path('google/', google_login),
    path('me/', current_user),
]