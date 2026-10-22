from django import forms
from finance.models import FundTransfer # Ensure this points to your exact model

class FundTransferForm(forms.ModelForm):
    class Meta:
        model = FundTransfer
        fields = ['amount', 'transfer_date', 'classification', 'transaction_reference']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'transfer_date': forms.DateInput(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500', 'type': 'date'}),
            'classification': forms.Select(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white'}),
            'transaction_reference': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500', 'placeholder': 'e.g., IndusInd UTR number'}),
        }