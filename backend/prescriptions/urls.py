from django.urls import path
from .views import create_prescription

urlpatterns = [
    path('add/', create_prescription, name='create_prescription'),
]