from django import forms
from .models import FarmerProfile

class FarmerProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=100, required=True, widget=forms.TextInput(attrs={'class': 'form-input'}))
    last_name = forms.CharField(max_length=100, required=True, widget=forms.TextInput(attrs={'class': 'form-input'}))
    phone = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'form-input'}))

    class Meta:
        model = FarmerProfile
        fields = [
            'farm_name', 'farm_size', 'village', 'district', 'state', 'pincode',
            'farm_address', 'latitude', 'longitude', 'farming_experience_years',
            'farming_methods', 'irrigation_facilities', 'organic_certified',
            'bio', 'bank_account_number', 'bank_name', 'ifsc_code',
            'aadhar_number', 'pan_number', 'profile_image', 'verification_document'
        ]
        widgets = {
            'farm_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Green Valley Organic Farm'}),
            'farm_size': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.1', 'placeholder': 'e.g. 15.5'}),
            'village': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Village/Town'}),
            'district': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'District'}),
            'state': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'State'}),
            'pincode': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Pincode'}),
            'farm_address': forms.Textarea(attrs={'class': 'form-input', 'rows': 2, 'placeholder': 'Detailed physical address of the farm'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.000001', 'id': 'farm_lat'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.000001', 'id': 'farm_lng'}),
            'farming_experience_years': forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
            'farming_methods': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Organic, Zero Budget Natural Farming, Drip'}),
            'irrigation_facilities': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Canal, Tube Well, Solar Pump'}),
            'bio': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Brief description about your farm, heritage, and crops...'}),
            'bank_account_number': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Account Number'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Bank Name'}),
            'ifsc_code': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'IFSC Code'}),
            'aadhar_number': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '12-digit Aadhar number'}),
            'pan_number': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '10-character PAN number'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['phone'].initial = user.phone


class FarmerVerificationForm(forms.ModelForm):
    class Meta:
        model = FarmerProfile
        fields = ['verification_document']
        widgets = {
            'verification_document': forms.FileInput(attrs={'class': 'form-input'}),
        }
