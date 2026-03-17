from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import PublicationForm
from .models import Publication

@login_required
def submit_paper(request):
    if request.method == 'POST':
        form = PublicationForm(request.POST, request.FILES)
        if form.is_valid():
            paper = form.save(commit=False)
            paper.doctor = request.user
            paper.status = 'PENDING'
            paper.save()
            return redirect('dashboard')
    else:
        form = PublicationForm()
    return render(request, 'publications/submit_paper.html', {'form': form})

@user_passes_test(lambda u: u.is_staff)
def review_papers(request):
    pending_papers = Publication.objects.filter(status='PENDING')
    return render(request, 'publications/review_papers.html', {'papers': pending_papers})