from django import forms
from .models import Review

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'quality_rating', 'timeliness_rating', 'communication_rating', 'title', 'comment']
        widgets = {
            'rating': forms.Select(choices=[(i, f"{i} Stars") for i in range(5, 0, -1)], attrs={'class': 'form-input'}),
            'quality_rating': forms.Select(choices=[(i, f"{i} Stars") for i in range(5, 0, -1)], attrs={'class': 'form-input'}),
            'timeliness_rating': forms.Select(choices=[(i, f"{i} Stars") for i in range(5, 0, -1)], attrs={'class': 'form-input'}),
            'communication_rating': forms.Select(choices=[(i, f"{i} Stars") for i in range(5, 0, -1)], attrs={'class': 'form-input'}),
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Summary headline'}),
            'comment': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Share your experience working with this counterpart...'}),
        }
