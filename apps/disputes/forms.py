from django import forms
from .models import Dispute, DisputeMessage

class DisputeFileForm(forms.ModelForm):
    class Meta:
        model = Dispute
        fields = ['category', 'title', 'description', 'evidence_file']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Moisture content exceeding contract limit in delivery'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 4, 'placeholder': 'Provide complete facts, dates, weighing slips, laboratory tests or photos...'}),
            'evidence_file': forms.FileInput(attrs={'class': 'form-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('title'):
            self.add_error('title', "A concise dispute title is required.")
        if not cleaned_data.get('description'):
            self.add_error('description', "Detailed explanation of the grievance is required.")
        return cleaned_data


class DisputeMessageForm(forms.ModelForm):
    class Meta:
        model = DisputeMessage
        fields = ['message', 'attachment']
        widgets = {
            'message': forms.Textarea(attrs={'class': 'form-input', 'rows': 2, 'placeholder': 'Type response or mediation clarification...'}),
            'attachment': forms.FileInput(attrs={'class': 'form-input'}),
        }


class DisputeResolutionForm(forms.ModelForm):
    contract_action = forms.ChoiceField(
        choices=[
            ('NO_CHANGE', 'Keep Contract Status'),
            ('RESET_ACTIVE', 'Reset Contract to Active (Fulfillment Continues)'),
            ('CANCEL_CONTRACT', 'Cancel Contract (Breach / Irreparable Failure)'),
            ('COMPLETE_CONTRACT', 'Mark Contract Completed with Resolution Settlement'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select text-xs'})
    )

    class Meta:
        model = Dispute
        fields = ['status', 'admin_response', 'resolution_details']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select text-xs'}),
            'admin_response': forms.Textarea(attrs={'class': 'form-input text-xs', 'rows': 3, 'placeholder': 'Formal summary of mediation decision issued to parties...'}),
            'resolution_details': forms.Textarea(attrs={'class': 'form-input text-xs', 'rows': 2, 'placeholder': 'Specific financial, replacement, or settlement instructions...'}),
        }
