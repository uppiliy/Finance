# forms.py
from django import forms
from .models import Loan, Collection

class LoanForm(forms.ModelForm):
    customer_name = forms.CharField(max_length=100, label="Customer Name")
    mobile_number = forms.CharField(max_length=10, label="Mobile Number")

    class Meta:
        model = Loan
        fields = ['customer_name', 'mobile_number', 'amount', 'repayment_type', 'date_issued']
        widgets = {
            'date_issued': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class CollectionForm(forms.ModelForm):
    loan_code = forms.CharField(max_length=10, label="Loan Code")

    class Meta:
        model = Collection
        fields = ['loan_code', 'amount_collected']
