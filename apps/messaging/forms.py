import os
from django import forms
from django.core.exceptions import ValidationError
from .models import Message

ALLOWED_ATTACHMENT_EXTENSIONS = ['.pdf', '.jpg', '.jpeg', '.png', '.webp', '.doc', '.docx', '.xls', '.xlsx']
MAX_ATTACHMENT_SIZE = 5 * 1024 * 1024  # 5 MB

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['content', 'attachment']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-input', 'rows': 2, 'placeholder': 'Type your message...'}),
            'attachment': forms.FileInput(attrs={'class': 'form-input'}),
        }

    def clean_attachment(self):
        attachment = self.cleaned_data.get('attachment')
        if attachment:
            # Validate size
            if attachment.size > MAX_ATTACHMENT_SIZE:
                raise ValidationError("Attachment file size cannot exceed 5 MB.")
            # Validate extension
            ext = os.path.splitext(attachment.name)[1].lower()
            if ext not in ALLOWED_ATTACHMENT_EXTENSIONS:
                raise ValidationError(f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_ATTACHMENT_EXTENSIONS)}")
        return attachment
