from datetime import datetime
from decimal import Decimal

from django import forms
from django.utils import timezone
from .models import (
    Loan, Collection, CashTransaction, Expense, FundTransaction,
    FundSource, ind_num_validator,
)


class PositiveAmountMixin:
    """Server-side amount validation; HTML min alone is not validation."""
    def clean(self):
        cleaned = super().clean()
        for name in ('amount', 'amount_collected'):
            amount = cleaned.get(name)
            if amount is not None and amount <= 0:
                self.add_error(name, 'Enter an amount greater than zero.')
        return cleaned


class LoanForm(PositiveAmountMixin, forms.ModelForm):
    customer_name = forms.CharField(max_length=100, label='Customer Name')
    mobile_number = forms.CharField(
        min_length=10, max_length=10, validators=[ind_num_validator], label='Mobile Number'
    )
    commission_percent = forms.DecimalField(
        required=False, max_digits=5, decimal_places=2,
        min_value=Decimal('0'), max_value=Decimal('100'), label='Commission %',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
    )

    class Meta:
        model = Loan
        fields = ['customer_name', 'mobile_number', 'amount', 'repayment_type', 'date_issued', 'commission_percent']
        widgets = {'date_issued': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class CollectionForm(PositiveAmountMixin, forms.ModelForm):
    loan_code = forms.CharField(max_length=10, label='Loan Code')
    collection_date = forms.DateField(
        required=False, label='Collection Date', widget=forms.DateInput(attrs={'type': 'date'})
    )
    payment_mode = forms.ChoiceField(
        choices=[('cash', 'Cash'), ('upi', 'UPI / Bank')],
        widget=forms.Select(attrs={'class': 'form-control'}), label='Payment Mode',
    )

    class Meta:
        model = Collection
        fields = ['loan_code', 'amount_collected', 'collection_date', 'payment_mode']


    def clean_collection_date(self):
        selected_date = self.cleaned_data.get('collection_date')
        if selected_date is None:
            return None
        return timezone.make_aware(datetime.combine(selected_date, timezone.localtime().time()))


class LoanExtensionForm(forms.Form):
    loan_code = forms.CharField(max_length=10)
    add_amount = forms.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'))
    commission_percent = forms.DecimalField(
        max_digits=5, decimal_places=2, min_value=Decimal('0'), max_value=Decimal('100')
    )
    extend_date = forms.DateField(required=False, input_formats=['%Y-%m-%d'])


class CapitalForm(PositiveAmountMixin, forms.ModelForm):
    class Meta:
        model = CashTransaction
        fields = ['txn_date', 'payment_mode', 'amount', 'reference']
        widgets = {
            'txn_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'payment_mode': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter capital amount'}),
            'reference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Source / Note'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['txn_date'].initial = timezone.now()
        self.fields['payment_mode'].initial = 'cash'

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.direction = 'credit'
        instance.txn_type = 'capital'
        if commit:
            instance.save()
        return instance


class ExpenseForm(PositiveAmountMixin, forms.ModelForm):
    # CashTransaction.reference is limited to 100 characters; retain full notes separately.
    description = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter expense description'}),
    )
    expense_date = forms.DateField(
        label='Date', initial=timezone.localdate,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

    class Meta:
        model = Expense
        fields = ['description', 'category', 'amount', 'payment_mode', 'expense_date', 'notes']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter amount', 'step': '0.01', 'min': '0.01'}),
            'payment_mode': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional notes'}),
        }
        labels = {'description': 'Description', 'category': 'Category', 'amount': 'Amount',
                  'payment_mode': 'Payment Mode', 'expense_date': 'Date', 'notes': 'Notes'}

    def clean_expense_date(self):
        selected_date = self.cleaned_data['expense_date']
        return timezone.make_aware(datetime.combine(selected_date, timezone.localtime().time()))


class CapitalRepaymentForm(PositiveAmountMixin, forms.ModelForm):
    class Meta:
        model = CashTransaction
        fields = ['txn_date', 'payment_mode', 'amount', 'reference']
        widgets = {
            'txn_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'payment_mode': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'reference': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.direction = 'debit'
        instance.txn_type = 'capital_out'
        if commit:
            instance.save()
        return instance


class FundTransactionForm(PositiveAmountMixin, forms.ModelForm):
    fund_source_name = forms.CharField(
        label='Fund Source', max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter fund source (e.g. Dad)'}),
    )
    transaction_date = forms.DateField(
        label='Date', initial=timezone.localdate,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

    class Meta:
        model = FundTransaction
        exclude = ['fund_source']
        widgets = {
            'transaction_type': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01', 'placeholder': 'Enter amount'}),
            'payment_mode': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional notes'}),
        }
        labels = {'fund_source_name': 'Fund Source', 'transaction_type': 'Transaction',
                  'amount': 'Amount', 'payment_mode': 'Payment Mode', 'transaction_date': 'Date', 'notes': 'Notes'}

    def clean_transaction_date(self):
        # Preserve the model's existing business-date-at-midnight convention.
        return timezone.make_aware(datetime.combine(self.cleaned_data['transaction_date'], datetime.min.time()))

    def clean(self):
        cleaned = super().clean()
        name = cleaned.get('fund_source_name', '').strip()
        amount = cleaned.get('amount')
        if cleaned.get('transaction_type') == 'repayment' and name:
            fund = FundSource.objects.filter(name__iexact=name).first()
            if fund is None:
                self.add_error('fund_source_name', 'Select an existing fund source for repayment.')
            elif amount is not None and amount > fund.outstanding:
                self.add_error('amount', f'Outstanding is only ₹{fund.outstanding:,.2f}')
        return cleaned
