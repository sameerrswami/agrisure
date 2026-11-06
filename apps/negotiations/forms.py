from django import forms
from .models import Offer

class OfferForm(forms.ModelForm):
    class Meta:
        model = Offer
        fields = ['price_per_unit', 'quantity', 'proposed_delivery_date', 'conditions', 'message']
        widgets = {
            'price_per_unit': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'placeholder': 'e.g. 2750.00'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'placeholder': 'e.g. 50'}),
            'proposed_delivery_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'conditions': forms.Textarea(attrs={'class': 'form-input', 'rows': 2, 'placeholder': 'Payment milestones, pickup location, packing...'}),
            'message': forms.Textarea(attrs={'class': 'form-input', 'rows': 2, 'placeholder': 'Note to the other party explaining this offer...'}),
        }
