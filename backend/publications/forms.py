from django import forms
from .models import Publication

class PublicationForm(forms.ModelForm):
    class Meta:
        model = Publication
        fields = ['title', 'abstract', 'authors', 'pdf_file']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'abstract': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'authors': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Author1, Author2...'}),
            'pdf_file': forms.FileInput(attrs={'class': 'form-control'}),
        }