from django.urls import path
from .views import submit_paper, review_papers

urlpatterns = [
    path('submit/', submit_paper, name='submit_paper'),
    path('review/', review_papers, name='review_papers'),
]