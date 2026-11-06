from django import forms
from .models import PlatformSetting
from apps.crops.models import CropCategory

class PlatformSettingForm(forms.ModelForm):
    class Meta:
        model = PlatformSetting
        fields = [
            'platform_name', 'support_email', 'support_phone', 'office_address',
            'working_hours', 'emergency_helpline', 'max_upload_size_mb',
            'platform_commission_pct', 'min_contract_value', 'dispute_sla_days',
            'email_notifications_enabled', 'sms_notifications_enabled'
        ]
        widgets = {
            'platform_name': forms.TextInput(attrs={'class': 'form-input text-xs'}),
            'support_email': forms.EmailInput(attrs={'class': 'form-input text-xs'}),
            'support_phone': forms.TextInput(attrs={'class': 'form-input text-xs'}),
            'office_address': forms.Textarea(attrs={'class': 'form-input text-xs', 'rows': 2}),
            'working_hours': forms.TextInput(attrs={'class': 'form-input text-xs'}),
            'emergency_helpline': forms.TextInput(attrs={'class': 'form-input text-xs'}),
            'max_upload_size_mb': forms.NumberInput(attrs={'class': 'form-input text-xs'}),
            'platform_commission_pct': forms.NumberInput(attrs={'class': 'form-input text-xs', 'step': '0.01'}),
            'min_contract_value': forms.NumberInput(attrs={'class': 'form-input text-xs', 'step': '100'}),
            'dispute_sla_days': forms.NumberInput(attrs={'class': 'form-input text-xs'}),
            'email_notifications_enabled': forms.CheckboxInput(attrs={'class': 'form-checkbox rounded text-emerald-600'}),
            'sms_notifications_enabled': forms.CheckboxInput(attrs={'class': 'form-checkbox rounded text-emerald-600'}),
        }


class CropCategoryForm(forms.ModelForm):
    class Meta:
        model = CropCategory
        fields = ['name', 'description', 'icon', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input text-xs', 'placeholder': 'Category Name (e.g. Millets & Ancient Grains)'}),
            'description': forms.Textarea(attrs={'class': 'form-input text-xs', 'rows': 2, 'placeholder': 'Description...'}),
            'icon': forms.TextInput(attrs={'class': 'form-input text-xs', 'placeholder': 'Lucide icon name (e.g. wheat, sprout, apple)'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox rounded text-emerald-600'}),
        }


class KYCRejectForm(forms.Form):
    rejection_reason = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-input text-xs', 'rows': 3, 'placeholder': 'Provide specific reason (e.g. Document unreadable, Aadhaar name mismatch, invalid GSTIN)...'}),
        required=True
    )


class UserSuspendForm(forms.Form):
    suspension_reason = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-input text-xs', 'rows': 3, 'placeholder': 'Specify regulatory, security, or terms violation reason for account suspension...'}),
        required=True
    )

