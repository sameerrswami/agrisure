from django import forms
from .models import CropListing, CropImage

class CropListingForm(forms.ModelForm):
    class Meta:
        model = CropListing
        fields = [
            'category', 'title', 'variety', 'description',
            'quantity_available', 'unit', 'price_per_unit', 'minimum_acceptable_price',
            'minimum_order_quantity', 'quality_grade', 'farming_type',
            'expected_harvest_date', 'available_from', 'available_until',
            'state', 'district', 'village', 'pincode', 'latitude', 'longitude',
            'delivery_location_availability', 'delivery_conditions',
            'featured_image', 'status'
        ]
        widgets = {
            'category': forms.Select(attrs={'class': 'form-input'}),
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Organic Basmati Paddy (Pusa 1121)'}),
            'variety': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. 1121, Sona Masoori, Sharbati'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 4, 'placeholder': 'Detailed crop description, farming methods, quality highlights...'}),
            'quantity_available': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0.01', 'placeholder': '100'}),
            'unit': forms.Select(attrs={'class': 'form-input'}),
            'price_per_unit': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0.01', 'placeholder': '2800.00'}),
            'minimum_acceptable_price': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0.01', 'placeholder': '2600.00'}),
            'minimum_order_quantity': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0.01', 'placeholder': '10'}),
            'quality_grade': forms.Select(attrs={'class': 'form-input'}),
            'farming_type': forms.Select(attrs={'class': 'form-input'}),
            'expected_harvest_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'available_from': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'available_until': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'state': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'State'}),
            'district': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'District'}),
            'village': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Village/Tehsil'}),
            'pincode': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Pincode'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.000001', 'placeholder': 'e.g. 28.6139'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.000001', 'placeholder': 'e.g. 77.2090'}),
            'delivery_location_availability': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Farm Gate, Pan-India Dispatch'}),
            'delivery_conditions': forms.Textarea(attrs={'class': 'form-input', 'rows': 2, 'placeholder': 'Bagging, transport, delivery timeline...'}),
            'status': forms.Select(attrs={'class': 'form-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['minimum_order_quantity'].required = False
        self.fields['quality_grade'].required = False
        self.fields['status'].required = False

    def clean(self):
        cleaned_data = super().clean()
        price = cleaned_data.get('price_per_unit')
        min_price = cleaned_data.get('minimum_acceptable_price')
        qty = cleaned_data.get('quantity_available')
        min_qty = cleaned_data.get('minimum_order_quantity')

        if price and price <= 0:
            self.add_error('price_per_unit', 'Price must be greater than zero.')
        if min_price and price and min_price > price:
            self.add_error('minimum_acceptable_price', 'Minimum acceptable price cannot exceed the expected price.')
        if qty and qty <= 0:
            self.add_error('quantity_available', 'Quantity available must be greater than zero.')
        if min_qty and qty and min_qty > qty:
            self.add_error('minimum_order_quantity', 'Minimum order quantity cannot exceed available quantity.')
        return cleaned_data


class CropImageForm(forms.ModelForm):
    class Meta:
        model = CropImage
        fields = ['image', 'caption']
        widgets = {
            'caption': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Image caption'}),
        }
