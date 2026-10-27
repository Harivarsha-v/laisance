from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Order, SupportTicket


class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["full_name", "email", "address", "city", "postal_code"]
        widgets = {
            "full_name": forms.TextInput(attrs={"autocomplete": "name", "placeholder": " "}),
            "email": forms.EmailInput(attrs={"autocomplete": "email", "placeholder": " "}),
            "address": forms.TextInput(attrs={"autocomplete": "street-address", "placeholder": " "}),
            "city": forms.TextInput(attrs={"autocomplete": "address-level2", "placeholder": " "}),
            "postal_code": forms.TextInput(attrs={"autocomplete": "postal-code", "placeholder": " "}),
        }


class SignupForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ["username", "email"]


class ContactForm(forms.ModelForm):
    class Meta:
        model = SupportTicket
        fields = ["name", "email", "subject", "message"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": " ", "autocomplete": "name"}),
            "email": forms.EmailInput(attrs={"placeholder": " ", "autocomplete": "email", "required": True}),
            "subject": forms.TextInput(attrs={"placeholder": " "}),
            "message": forms.Textarea(attrs={"placeholder": " ", "rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True
