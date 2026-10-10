from .cash_integrity import atomic_cash_save
from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone
from datetime import time, timedelta
from decimal import Decimal
from django.db.models import Sum
from datetime import datetime


import qrcode
from io import BytesIO
from django.core.files import File


ind_num_validator = RegexValidator(
    regex=r'[6-9]\d{9}$',
    message="Enter a valid 10-digit mobile number"
)

class Customer(models.Model):
    customer_code = models.CharField(max_length=10, unique=True, editable=False)
    name = models.CharField(max_length=100)
    mobile_number = models.CharField(
        max_length=10,
        unique=True,
        validators=[ind_num_validator],
        help_text="10 digit mobile number"
    )

    def save(self, *args, **kwargs):
        if not self.customer_code:
            last_customer = Customer.objects.order_by('-customer_code').first()
            if last_customer and last_customer.customer_code.isdigit():
                next_number = int(last_customer.customer_code) + 1
            else:
                next_number = 1
            self.customer_code = f"{next_number:04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.customer_code} - {self.name}"

class Loan(models.Model):
    REPAYMENT_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]

    def local_date():
    # returns current date in the active timezone (e.g. Asia/Kolkata)
        return timezone.localdate()

    loan_code = models.CharField(max_length=10, unique=True, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='loans')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    repayment_type = models.CharField(max_length=10, choices=REPAYMENT_CHOICES, default='daily')
    commission_percent = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    disbursed_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    repayment_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    date_issued = models.DateField(default=local_date)
    last_repayment_date = models.DateField(blank=True, null=True)

    #qr_code = models.ImageField(upload_to='loan_qrcodes/', blank=True, null=True)  # ✅ new field


    def save(self, *args, **kwargs):
        is_new = self.pk is None  # ✅ detect first creation

        # 🔢 Loan Code
        if not self.loan_code:
            last_loan = Loan.objects.order_by('-loan_code').first()
            if last_loan and last_loan.loan_code.isdigit():
                next_number = int(last_loan.loan_code) + 1
            else:
                next_number = 1
            self.loan_code = f"{next_number:04d}"

        # 💰 Commission %
        if self.commission_percent is None:
            if self.repayment_type == 'daily':
                self.commission_percent = Decimal('12.0')
            elif self.repayment_type == 'weekly':
                self.commission_percent = Decimal('13.5')
            elif self.repayment_type == 'monthly':
                self.commission_percent = Decimal('15.0')
            else:
                self.commission_percent = Decimal('0')

        # 💸 Amount calculations
        self.commission_amount = (self.amount * self.commission_percent) / Decimal('100')
        self.disbursed_amount = self.amount - self.commission_amount

        # 📆 Repayment amount
        if self.repayment_type == 'daily':
            self.repayment_amount = self.amount / 100
        elif self.repayment_type == 'weekly':
            self.repayment_amount = self.amount / 14
        elif self.repayment_type == 'monthly':
            self.repayment_amount = self.amount / 4

        # 📅 Last repayment date
        if self.date_issued:
            self.last_repayment_date = self.date_issued + timedelta(days=101)

        super().save(*args, **kwargs)  # 🚨 MUST SAVE FIRST


    from django.utils.functional import cached_property

    @cached_property
    def total_collected(self):
        return sum(
            (c.amount_collected or Decimal('0'))
            for c in self.collections.all()
    )

    @cached_property
    def total_principal(self):
        return sum(
            (d.principal_amount or Decimal('0'))
            for d in self.disbursements.all()
    )

    @cached_property
    def total_commission(self):
        return sum(
            (d.commission_amount or Decimal('0'))
            for d in self.disbursements.all()
        )
    @cached_property
    def total_disbursed(self):
        return sum(
            (d.disbursed_amount or Decimal('0'))
            for d in self.disbursements.all()
        )
    @cached_property
    def remaining_balance(self):
        return self.total_principal - self.total_collected

    def __str__(self):
        return f"Loan {self.loan_code} - {self.customer.name}"
from django.db import models
from django.utils import timezone

class Collection(models.Model):
    PAYMENT_MODES = [
        ('cash', 'Cash'),
        ('upi', 'UPI / Bank'),
    ]

    loan = models.ForeignKey(
        'Loan',
        on_delete=models.CASCADE,
        related_name='collections'
    )
    collection_date = models.DateTimeField(default=timezone.now)
    amount_collected = models.DecimalField(max_digits=10, decimal_places=2)

    payment_mode = models.CharField(
        max_length=10,
        choices=PAYMENT_MODES,
        default='cash'
    )

    @atomic_cash_save("collection")
    def save(self, *args, **kwargs):

        super().save(*args, **kwargs)

        # Read persisted values so update_fields and database rounding stay consistent.
        db = self._state.db
        source = type(self).objects.using(db).get(pk=self.pk)
        cash_txn = CashTransaction.objects.using(db).filter(collection_id=self.pk).first()
        if cash_txn is None:
            cash_txn = CashTransaction(collection=self)

        cash_txn.amount = source.amount_collected
        cash_txn.direction = CashTransaction.CREDIT
        cash_txn.txn_type = "collection"
        cash_txn.payment_mode = source.payment_mode
        cash_txn.reference = f"Loan {source.loan.loan_code} - {source.loan.customer.name}"
        cash_txn.txn_date = source.collection_date

        cash_txn.save(using=db)


    def __str__(self):
        return f"{self.loan.loan_code} - ₹{self.amount_collected}"


class CashTransaction(models.Model):
    CREDIT = 'credit'
    DEBIT = 'debit'

    DIRECTION_CHOICES = [
        (CREDIT, 'Credit'),
        (DEBIT, 'Debit'),
    ]

    TYPE_CHOICES = [
        ('capital', 'Capital In'),
        ('capital_out', 'Capital Out'),
        ('fund_in', 'Fund Received'),
        ('fund_repayment', 'Fund Repaid'),
        ('loan_disbursement', 'Loan Disbursement'),
        ('commission', 'Commission'),
        ('collection', 'Collection'),
        ('expense', 'Expense'),
    ]

    PAYMENT_MODES = [
        ('cash', 'Cash'),
        ('upi', 'UPI / Bank'),
    ]

    payment_mode = models.CharField(
        max_length=10,
        choices=PAYMENT_MODES,
        default='cash'
    )


    direction = models.CharField(
        max_length=6,
        choices=DIRECTION_CHOICES,
        default=CREDIT
    )

    txn_type = models.CharField(
        max_length=30,
        choices=TYPE_CHOICES,
        default='capital'
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reference = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # ✅ USER SELECTABLE DATE (default = now)
    txn_date = models.DateTimeField(default=timezone.now)

    loan_disbursement = models.OneToOneField(
        "LoanDisbursement",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="cash_transaction",
    )

    collection = models.OneToOneField(
        "Collection",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="cash_transaction",
    )

    expense = models.OneToOneField(
        "Expense",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="cash_transaction",
    )

    fund_transaction = models.OneToOneField(
        "FundTransaction",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="cash_transaction",
    )


    def __str__(self):
        sign = "+" if self.direction == "credit" else "-"
        return f"{sign}₹{self.amount} ({self.txn_type})"


class LoanDisbursement(models.Model):
    loan = models.ForeignKey(
        Loan,
        on_delete=models.CASCADE,
        related_name='disbursements'
    )

    principal_amount = models.DecimalField(max_digits=10, decimal_places=2)
    commission_percent = models.DecimalField(max_digits=5, decimal_places=2)
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2)
    disbursed_amount = models.DecimalField(max_digits=10, decimal_places=2)

    # 🔥 SNAPSHOT FIELD
    collected_till_now = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    # 🔥 BUSINESS DATE (editable / backdatable / future-proof)
    created_at = models.DateTimeField(default=timezone.now)

    @atomic_cash_save("loan_disbursement")
    def save(self, *args, **kwargs):

        # Commission calculation
        self.commission_amount = (
            self.principal_amount * self.commission_percent / Decimal("100")
        )

        self.disbursed_amount = (
            self.principal_amount - self.commission_amount
        )

        super().save(*args, **kwargs)

        # Read persisted values so update_fields and database rounding stay consistent.
        db = self._state.db
        source = type(self).objects.using(db).get(pk=self.pk)
        cash_txn = CashTransaction.objects.using(db).filter(loan_disbursement_id=self.pk).first()
        if cash_txn is None:
            cash_txn = CashTransaction(loan_disbursement=self)

        cash_txn.amount = source.disbursed_amount
        cash_txn.direction = CashTransaction.DEBIT
        cash_txn.txn_type = "loan_disbursement"
        cash_txn.reference = f"Loan {source.loan.loan_code} - {source.loan.customer.name}"
        cash_txn.txn_date = source.created_at

        cash_txn.save(using=db)


class Expense(models.Model):
    PAYMENT_MODES = [
        ('cash', 'Cash'),
        ('upi', 'UPI / Bank'),
    ]

    CATEGORY_CHOICES = [
        ('fuel', 'Fuel'),
        ('salary', 'Salary'),
        ('rent', 'Rent'),
        ('office', 'Office'),
        ('travel', 'Travel'),
        ('other', 'Other'),
    ]

    description = models.CharField(max_length=200)

    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        default='other'
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    payment_mode = models.CharField(
        max_length=10,
        choices=PAYMENT_MODES,
        default='cash'
    )

    expense_date = models.DateTimeField(
        default=timezone.now
    )

    notes = models.TextField(
        blank=True,
        null=True
    )

    @atomic_cash_save("expense")
    def save(self, *args, **kwargs):

        super().save(*args, **kwargs)

        # Read persisted values so update_fields and database rounding stay consistent.
        db = self._state.db
        source = type(self).objects.using(db).get(pk=self.pk)
        cash_txn = CashTransaction.objects.using(db).filter(expense_id=self.pk).first()
        if cash_txn is None:
            cash_txn = CashTransaction(expense=self)

        cash_txn.amount = source.amount
        cash_txn.direction = CashTransaction.DEBIT
        cash_txn.txn_type = "expense"
        cash_txn.payment_mode = source.payment_mode
        cash_txn.reference = source.description
        cash_txn.txn_date = source.expense_date

        cash_txn.save(using=db)


    def __str__(self):
        return f"{self.description} - ₹{self.amount}"

class FundSource(models.Model):
    name = models.CharField(max_length=100, unique=True)
    notes = models.TextField(blank=True, null=True)

    @property
    def total_received(self):
        return self.transactions.filter(
            transaction_type="received"
        ).aggregate(
            total=models.Sum("amount")
        )["total"] or Decimal("0")


    @property
    def total_repaid(self):
        return self.transactions.filter(
            transaction_type="repayment"
        ).aggregate(
            total=models.Sum("amount")
        )["total"] or Decimal("0")


    @property
    def outstanding(self):
        return self.total_received - self.total_repaid

    def __str__(self):
        return f"{self.name} (Outstanding ₹{self.outstanding:,.2f})"

class FundTransaction(models.Model):
    RECEIVED = "received"
    REPAYMENT = "repayment"

    TRANSACTION_CHOICES = [
        (RECEIVED, "Money Received"),
        (REPAYMENT, "Money Repaid"),
    ]

    PAYMENT_MODES = [
        ("cash", "Cash"),
        ("upi", "UPI / Bank"),
    ]

    fund_source = models.ForeignKey(
        FundSource,
        on_delete=models.CASCADE,
        related_name="transactions"
    )

    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_CHOICES
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    payment_mode = models.CharField(
        max_length=10,
        choices=PAYMENT_MODES,
        default="cash"
    )

    transaction_date = models.DateTimeField(
        default=timezone.now
    )

    notes = models.TextField(
        blank=True,
        null=True
    )

    @atomic_cash_save("fund_transaction")
    def save(self, *args, **kwargs):

        super().save(*args, **kwargs)

        # Read persisted values so update_fields and database rounding stay consistent.
        db = self._state.db
        source = type(self).objects.using(db).get(pk=self.pk)
        cash_txn = CashTransaction.objects.using(db).filter(fund_transaction_id=self.pk).first()
        if cash_txn is None:
            cash_txn = CashTransaction(fund_transaction=self)

        cash_txn.amount = source.amount
        cash_txn.payment_mode = source.payment_mode
        cash_txn.reference = source.fund_source.name
        cash_txn.txn_date = source.transaction_date

        if source.transaction_type == source.RECEIVED:
            cash_txn.direction = CashTransaction.CREDIT
            cash_txn.txn_type = "fund_in"

        else:
            cash_txn.direction = CashTransaction.DEBIT
            cash_txn.txn_type = "fund_repayment"

        cash_txn.save(using=db)


    def __str__(self):
        return f"{self.fund_source.name} - {self.get_transaction_type_display()} ₹{self.amount}"