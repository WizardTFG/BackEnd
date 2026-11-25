from django.urls import path
from . import views

urlpatterns = [
    path('clinicians/', views.search_clinicians),
    path('', views.create_application),
    path('my-applications/', views.my_applications, name='my_applications'),
    path('<slug:slug>/', views.application_by_slug, name='application_by_slug'),
    path(
        '<slug:slug>/responses/',
        views.submit_application_response,
        name='submit_application_response'
    ),
]