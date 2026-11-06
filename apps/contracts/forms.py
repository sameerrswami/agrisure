from django import forms
from .models import Contract

class ContractRequestForm(forms.ModelForm):
    buyer_message = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Introduce your company, procurement requirements, and expectations...'}),
        required=False
    )

    class Meta:
        model = Contract
        fields = [
            'quantity', 'price_per_unit', 'advance_payment_percentage',
            'delivery_date', 'delivery_address', 'required_quality_grade',
            'quality_specifications', 'payment_terms', 'terms_and_conditions',
            'additional_conditions', 'penalty_clause', 'buyer_message'
        ]
        widgets = {
            'quantity': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'id': 'req_quantity'}),
            'price_per_unit': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'id': 'req_price'}),
            'advance_payment_percentage': forms.NumberInput(attrs={'class': 'form-input', 'step': '1', 'min': '0', 'max': '100', 'placeholder': '20'}),
            'delivery_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'delivery_address': forms.Textarea(attrs={'class': 'form-input', 'rows': 2, 'placeholder': 'Warehouse or receiving facility physical address'}),
            'required_quality_grade': forms.Select(attrs={'class': 'form-input'}),
            'quality_specifications': forms.Textarea(attrs={'class': 'form-input', 'rows': 2, 'placeholder': 'Required moisture content (<12%), grain size, purity, packaging requirements...'}),
            'payment_terms': forms.Textarea(attrs={'class': 'form-input', 'rows': 2, 'placeholder': 'e.g. 20% advance upon contract signing in escrow, 80% balance upon delivery inspection'}),
            'terms_and_conditions': forms.Textarea(attrs={'class': 'form-input', 'rows': 2, 'placeholder': 'Weighment at delivery point, quality testing protocols...'}),
            'additional_conditions': forms.Textarea(attrs={'class': 'form-input', 'rows': 2, 'placeholder': 'Specific packaging materials, transport arrangements, harvest timelines...'}),
            'penalty_clause': forms.Textarea(attrs={'class': 'form-input', 'rows': 2, 'placeholder': 'Liquidated damages or settlement adjustments for delayed delivery...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'required_quality_grade' in self.fields:
            self.fields['required_quality_grade'].required = False

    def clean(self):
        cleaned_data = super().clean()
        qty = cleaned_data.get('quantity')
        price = cleaned_data.get('price_per_unit')
        advance_pct = cleaned_data.get('advance_payment_percentage')

        if qty and qty <= 0:
            self.add_error('quantity', 'Requested quantity must be greater than zero.')
        if price and price <= 0:
            self.add_error('price_per_unit', 'Proposed price must be greater than zero.')
        if advance_pct is not None and (advance_pct < 0 or advance_pct > 100):
            self.add_error('advance_payment_percentage', 'Advance percentage must be between 0% and 100%.')
        return cleaned_data


class ContractAmendmentForm(forms.ModelForm):
    amendment_reason = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-input', 'rows': 2, 'placeholder': 'Explain why this contract amendment is requested (e.g. Weather adjustment, volume expansion)...'}),
        required=True
    )

    class Meta:
        model = Contract
        fields = [
            'quantity', 'price_per_unit', 'delivery_date', 'delivery_address',
            'required_quality_grade', 'quality_specifications', 'payment_terms',
            'additional_conditions'
        ]
        widgets = {
            'quantity': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'price_per_unit': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'delivery_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'delivery_address': forms.Textarea(attrs={'class': 'form-input', 'rows': 2}),
            'required_quality_grade': forms.Select(attrs={'class': 'form-input'}),
            'quality_specifications': forms.Textarea(attrs={'class': 'form-input', 'rows': 2}),
            'payment_terms': forms.Textarea(attrs={'class': 'form-input', 'rows': 2}),
            'additional_conditions': forms.Textarea(attrs={'class': 'form-input', 'rows': 2}),
        }
