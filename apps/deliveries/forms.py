from django import forms
from .models import Delivery

class DeliveryCreateForm(forms.ModelForm):
    class Meta:
        model = Delivery
        fields = [
            'quantity_scheduled', 'unit', 'pickup_location',
            'destination_address', 'estimated_delivery_date',
            'transporter_name', 'vehicle_number', 'driver_name',
            'driver_phone', 'delivery_notes'
        ]
        widgets = {
            'quantity_scheduled': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'unit': forms.TextInput(attrs={'class': 'form-input', 'readonly': 'readonly'}),
            'pickup_location': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Village Farm Gate / Warehouse'}),
            'destination_address': forms.Textarea(attrs={'class': 'form-input', 'rows': 2}),
            'estimated_delivery_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'transporter_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Logistics Carrier / Transporter Name'}),
            'vehicle_number': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. MH-12-AB-1234'}),
            'driver_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Driver Full Name'}),
            'driver_phone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Driver 10-digit mobile'}),
            'delivery_notes': forms.Textarea(attrs={'class': 'form-input', 'rows': 2, 'placeholder': 'Bagging, packaging, batch details...'}),
        }

    # Backward compatibility with quantity_shipped / shipping_address
    def clean(self):
        cleaned_data = super().clean()
        qty = cleaned_data.get('quantity_scheduled')
        if qty and qty <= 0:
            self.add_error('quantity_scheduled', "Scheduled quantity must be greater than zero.")
        return cleaned_data


class DeliveryDispatchForm(forms.ModelForm):
    class Meta:
        model = Delivery
        fields = [
            'transporter_name', 'vehicle_number',
            'driver_name', 'driver_phone', 'delivery_notes'
        ]
        widgets = {
            'transporter_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Transporter Agency / Vehicle Reg.'}),
            'vehicle_number': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Vehicle Registration Number'}),
            'driver_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Driver Full Name'}),
            'driver_phone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Driver Contact Number'}),
            'delivery_notes': forms.Textarea(attrs={'class': 'form-input', 'rows': 2}),
        }


class DeliveryReceiptForm(forms.ModelForm):
    class Meta:
        model = Delivery
        fields = ['quantity_delivered', 'inspection_status', 'proof_of_delivery', 'inspection_notes']
        widgets = {
            'quantity_delivered': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'placeholder': 'Actual Verified Quantity Received'}),
            'inspection_status': forms.Select(attrs={'class': 'form-select'}),
            'proof_of_delivery': forms.FileInput(attrs={'class': 'form-input'}),
            'inspection_notes': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Describe inspection results, quality check, moisture content, weighbridge receipts...'}),
        }

    def clean_quantity_delivered(self):
        qty = self.cleaned_data.get('quantity_delivered')
        if qty is None or qty < 0:
            raise forms.ValidationError("Delivered quantity cannot be negative.")
        return qty
