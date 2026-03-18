from django.urls import path
from .views import generate_invoice

urlpatterns = [
    path('new/', generate_invoice, name='generate_invoice'),
]