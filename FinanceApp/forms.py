# forms.py
from datetime import datetime

from django import forms
from .models import Loan, Collection, CashTransaction, Expense, FundTransaction, FundSource
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
        model = Expense
        fields = [
            "description",
            "category",
            "amount",
            "payment_mode",
            "expense_date",
            "notes",
        ]

        widgets = {
            "description": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter expense description"
            }),

            "category": forms.Select(attrs={
                "class": "form-select"
            }),

            "amount": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "Enter amount",
                "step": "0.01",
                "min": "0"
            }),

            "payment_mode": forms.Select(attrs={
                "class": "form-select"
            }),

            "expense_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date"
            }),

            "notes": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Optional notes"
            }),
        }

        labels = {
            "description": "Description",
            "category": "Category",
            "amount": "Amount",
            "payment_mode": "Payment Mode",
            "expense_date": "Date",
            "notes": "Notes",
        }

    def clean_expense_date(self):
        selected_date = self.cleaned_data["expense_date"]
        current_time = timezone.localtime().time()

        return timezone.make_aware(
            datetime.combine(selected_date, current_time)
        )

class CapitalRepaymentForm(forms.ModelForm):
    class Meta:
        model = CashTransaction
        fields = ['txn_date', 'payment_mode', 'amount', 'reference']
        widgets = {
            'txn_date': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'payment_mode': forms.Select(attrs={
                'class': 'form-control'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control'
            }),
            'reference': forms.TextInput(attrs={
                'class': 'form-control'
            }),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.direction = 'debit'         # 💸 money going OUT
        instance.txn_type = 'capital_out'   # ✅ IMPORTANT
        if commit:
            instance.save()
        return instance

class FundTransactionForm(forms.ModelForm):
    fund_source_name = forms.CharField(
        label="Fund Source",
        max_length=100,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Enter fund source (e.g. Dad)"
        })
    )

    class Meta:
        model = FundTransaction
        exclude = ["fund_source"]

        widgets = {
            "transaction_type": forms.Select(attrs={
                "class": "form-control",
            }),

            "amount": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "min": "0",
                "placeholder": "Enter amount"
            }),

            "payment_mode": forms.Select(attrs={
                "class": "form-control",
            }),

            "transaction_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),

            "notes": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Optional notes"
            }),
        }

        labels = {
            "fund_source_name": "Fund Source",
            "transaction_type": "Transaction",
            "amount": "Amount",
            "payment_mode": "Payment Mode",
            "transaction_date": "Date",
            "notes": "Notes",
        }

    def clean(self):
        cleaned = super().clean()

        name = cleaned.get("fund_source_name", "").strip()

        fund = FundSource.objects.filter(name__iexact=name).first()

        txn_type = cleaned.get("transaction_type")
        amount = cleaned.get("amount")

        if fund and txn_type == "repayment":
            if amount > fund.outstanding:
                raise forms.ValidationError(
                    f"Outstanding is only ₹{fund.outstanding:,.2f}"
                )

        return cleaned
        