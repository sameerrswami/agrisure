from django import forms
from .models import BuyerProfile

class BuyerProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=100, required=True, widget=forms.TextInput(attrs={'class': 'form-input'}))
    last_name = forms.CharField(max_length=100, required=True, widget=forms.TextInput(attrs={'class': 'form-input'}))
    phone = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'form-input'}))

    class Meta:
        model = BuyerProfile
        fields = [
            'company_name', 'contact_person', 'business_type', 'gstin', 'pan_number',
            'business_address', 'city', 'district', 'state', 'pincode',
            'latitude', 'longitude', 'delivery_address', 'website', 'bio',
            'annual_procurement_budget', 'preferred_crops', 'preferred_locations',
            'required_quantities', 'company_logo', 'verification_document'
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'AgriFoods Corp Ltd.'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Procurement Head'}),
            'business_type': forms.Select(attrs={'class': 'form-input'}),
            'gstin': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '22AAAAA0000A1Z5'}),
            'pan_number': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'AAAAA0000A'}),
            'business_address': forms.Textarea(attrs={'class': 'form-input', 'rows': 2, 'placeholder': 'Corporate / registered office address'}),
            'city': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'City'}),
            'district': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'District'}),
            'state': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'State'}),
            'pincode': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Pincode'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.000001', 'id': 'buyer_lat'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.000001', 'id': 'buyer_lng'}),
            'delivery_address': forms.Textarea(attrs={'class': 'form-input', 'rows': 2, 'placeholder': 'Primary warehouse / factory receiving address'}),
            'website': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://example.com'}),
            'bio': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'About your company and procurement volumes...'}),
            'annual_procurement_budget': forms.NumberInput(attrs={'class': 'form-input', 'step': '1000', 'placeholder': '5000000'}),
            'preferred_crops': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Basmati Rice, Wheat, Soybean, Mustard'}),
            'preferred_locations': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Punjab, Haryana, Madhya Pradesh, Rajasthan'}),
            'required_quantities': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. 500 Quintals / month'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['phone'].initial = user.phone


class BuyerVerificationForm(forms.ModelForm):
    class Meta:
        model = BuyerProfile
        fields = ['verification_document']
        widgets = {
            'verification_document': forms.FileInput(attrs={'class': 'form-input'}),
        }
