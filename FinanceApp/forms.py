# forms.py
from django import forms
from .models import Loan, Collection, CashTransaction
from decimal import Decimal

class LoanForm(forms.ModelForm):
    customer_name = forms.CharField(max_length=100, label="Customer Name")
    mobile_number = forms.CharField(max_length=10, label="Mobile Number")

    commission_percent = forms.DecimalField(
        required=False,
        max_digits=5,
        decimal_places=2,
        label="Commission %",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.1'
        })
    )

    class Meta:
        model = Loan
        fields = ['customer_name', 'mobile_number', 'amount', 'repayment_type', 'date_issued', 'commission_percent']
        widgets = {
            'date_issued': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class CollectionForm(forms.ModelForm):
    loan_code = forms.CharField(max_length=10, label="Loan Code")

    collection_date = forms.DateField(
        required=False,
        label="Collection Date",
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    payment_mode = forms.ChoiceField(
        choices=[('cash', 'Cash'), ('upi', 'UPI / Bank')],
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Payment Mode"
    )


    class Meta:
        model = Collection
        fields = ['loan_code', 'amount_collected', 'collection_date', 'payment_mode']

from django.utils import timezone

'''class CapitalForm(forms.ModelForm):
    class Meta:
        model = CashTransaction
        fields = ['txn_date', 'amount', 'reference']
        widgets = {
            'txn_date': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'class': 'form-control'
                }
            ),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter capital amount'
            }),
            'reference': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Source / Note'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ✅ default current datetime
        self.fields['txn_date'].initial = timezone.now()

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.direction = 'credit'
        instance.txn_type = 'capital'
        if commit:
            instance.save()
        return instance

class ExpenseForm(forms.ModelForm):
    class Meta:
        model = CashTransaction
        fields = ['txn_date', 'amount', 'reference']
        widgets = {
            'txn_date': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'class': 'form-control'
                }
            ),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter expense amount'
            }),
            'reference': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Expense description'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['txn_date'].initial = timezone.now()

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.direction = 'debit'
        instance.txn_type = 'expense'
        if commit:
            instance.save()
        return instance'''

class CapitalForm(forms.ModelForm):
    class Meta:
        model = CashTransaction
        fields = ['txn_date', 'payment_mode', 'amount', 'reference']
        widgets = {
            'txn_date': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'}
            ),
            'payment_mode': forms.Select(
                attrs={'class': 'form-control'}
            ),
            'amount': forms.NumberInput(
                attrs={'class': 'form-control', 'placeholder': 'Enter capital amount'}
            ),
            'reference': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Source / Note'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['txn_date'].initial = timezone.now()
        self.fields['payment_mode'].initial = 'cash'  # ✅ default

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.direction = 'credit'
        instance.txn_type = 'capital'
        if commit:
            instance.save()
        return instance

class ExpenseForm(forms.ModelForm):
    class Meta:
        model = CashTransaction
        fields = ['txn_date', 'payment_mode', 'amount', 'reference']
        widgets = {
            'txn_date': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'}
            ),
            'payment_mode': forms.Select(
                attrs={'class': 'form-control'}
            ),
            'amount': forms.NumberInput(
                attrs={'class': 'form-control', 'placeholder': 'Enter expense amount'}
            ),
            'reference': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Expense description'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['txn_date'].initial = timezone.now()
        self.fields['payment_mode'].initial = 'cash'

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.direction = 'debit'
        instance.txn_type = 'expense'
        if commit:
            instance.save()
        return instance


