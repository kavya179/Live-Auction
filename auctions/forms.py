"""
Forms for the auctions app.

Forms
-----
RegisterForm    – user registration (email + username)
AuctionItemForm – create/edit an AuctionItem (auth-based)
BidForm         – place a bid on an AuctionItem (auth-based, amount only)
PlaceBidForm    – place a bid on an Auction (name-based, new backend model)
"""

from decimal import Decimal

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import AuctionItem, Bid, Auction


class RegisterForm(UserCreationForm):
    """User registration form with email field."""
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={
        'class': 'form-input',
        'placeholder': 'you@example.com'
    }))

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-input'


class AuctionItemForm(forms.ModelForm):
    """Form to create or edit an auction item."""

    class Meta:
        model = AuctionItem
        fields = ['title', 'description', 'image', 'starting_price', 'start_time', 'end_time']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Item name'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 4, 'placeholder': 'Describe your item...'}),
            'starting_price': forms.NumberInput(attrs={'class': 'form-input', 'min': '0.01', 'step': '0.01'}),
            'start_time': forms.DateTimeInput(attrs={'class': 'form-input', 'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'class': 'form-input', 'type': 'datetime-local'}),
            'image': forms.FileInput(attrs={'class': 'form-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        if start_time and end_time and end_time <= start_time:
            raise forms.ValidationError("End time must be after start time.")
        return cleaned_data


class BidForm(forms.ModelForm):
    """Form to place a bid on an AuctionItem (auth-based, amount only)."""

    class Meta:
        model = Bid
        fields = ['amount']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '0.01',
                'step': '0.01',
                'placeholder': 'Enter your bid amount'
            })
        }


class PlaceBidForm(forms.Form):
    """
    Standalone form to submit a bid on an Auction (name-based, no login needed).

    Validation
    ----------
    - bidder_name : required, stripped, non-empty
    - amount      : required, must be a positive decimal > 0
    """

    bidder_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class':       'form-input',
            'placeholder': 'Your name',
            'autocomplete': 'name',
        }),
        error_messages={
            'required': 'Please enter your name.',
            'max_length': 'Name is too long (max 150 characters).',
        },
    )

    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={
            'class':       'form-input',
            'min':         '0.01',
            'step':        '0.01',
            'placeholder': 'Your bid amount in $',
        }),
        error_messages={
            'required':   'Please enter a bid amount.',
            'invalid':    'Enter a valid number (e.g. 150.00).',
            'min_value':  'Bid must be at least $0.01.',
        },
    )

    def clean_bidder_name(self):
        name = self.cleaned_data.get('bidder_name', '').strip()
        if not name:
            raise forms.ValidationError("Bidder name cannot be blank.")
        return name

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= Decimal('0'):
            raise forms.ValidationError("Bid amount must be greater than zero.")
        return amount

