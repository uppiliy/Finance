from django.contrib import admin
from django import forms
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import router, transaction
from django.urls import reverse
from django.utils.html import format_html
from .models import Customer, Loan, Collection, CashTransaction, LoanDisbursement, Expense, FundTransaction
from .cash_integrity import require_cash_link, LINK_FIELDS


class SourceAdminMixin:
    cash_link = None

    def get_form(self, request, obj=None, **kwargs):
        base = super().get_form(request, obj, **kwargs)
        link = self.cash_link
        class SourceForm(base):
            def clean(self):
                cleaned = super().clean()
                if link and not self.instance._state.adding:
                    require_cash_link(self.instance, link)
                return cleaned
        return SourceForm

    def get_deleted_objects(self, objs, request):
        deleted, counts, perms, protected = super().get_deleted_objects(objs, request)
        # Cash deletion is forbidden from its own admin, but normal source cascades
        # are permitted if the user also has the ordinary cash delete permission.
        opts = CashTransaction._meta
        if request.user.has_perm('%s.delete_%s' % (opts.app_label, opts.model_name)):
            perms.discard(opts.verbose_name)
        return deleted, counts, perms, protected


@admin.register(Customer)
class CustomerAdmin(SourceAdminMixin, admin.ModelAdmin):
    list_display = ('customer_code', 'name', 'mobile_number')
    search_fields = ('name', 'mobile_number', 'customer_code')
    ordering = ('id',)
    readonly_fields = ('customer_code',)
    fieldsets = ((None, {'fields': ('customer_code', 'name', 'mobile_number')}),)


@admin.register(Loan)
class LoanAdmin(SourceAdminMixin, admin.ModelAdmin):
    def qr_preview(self, obj):
        url = reverse('loan_qr', args=[obj.loan_code])
        return format_html('<img src="{}" width="80" height="80" />', url)
    qr_preview.short_description = 'QR Code'
    list_display = ('loan_code', 'customer', 'amount', 'repayment_type', 'commission_percent',
                    'disbursed_amount', 'date_issued', 'last_repayment_date', 'qr_preview')
    search_fields = ('loan_code', 'customer__name', 'customer__mobile_number')
    list_filter = ('repayment_type', 'date_issued')
    ordering = ('-id',)
    readonly_fields = ('loan_code', 'commission_percent', 'disbursed_amount', 'last_repayment_date')
    fieldsets = (
        ('Loan Details', {'fields': ('loan_code', 'customer', 'amount', 'repayment_type',
                                     'date_issued', 'last_repayment_date')}),
        ('Calculated Fields', {'fields': ('commission_percent', 'disbursed_amount')}),
    )


@admin.register(Collection)
class CollectionAdmin(SourceAdminMixin, admin.ModelAdmin):
    cash_link = 'collection'
    list_display = ('loan', 'get_customer_name', 'amount_collected', 'collection_date')
    list_filter = ('collection_date',)
    search_fields = ('loan__loan_code', 'loan__customer__name', 'loan__customer__mobile_number')
    ordering = ('-collection_date',)
    def get_customer_name(self, obj):
        return obj.loan.customer.name
    get_customer_name.short_description = 'Customer'


def standalone_cash(obj):
    return obj.txn_type in ('capital', 'capital_out') and not any(
        getattr(obj, field) is not None for field in LINK_FIELDS
    )


class StandaloneCashForm(forms.ModelForm):
    class Meta:
        model = CashTransaction
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'txn_type' in self.fields:
            self.fields['txn_type'].choices = [
                choice for choice in CashTransaction.TYPE_CHOICES
                if choice[0] in ('capital', 'capital_out')
            ]

    def clean(self):
        cleaned = super().clean()
        expected = {'capital': 'credit', 'capital_out': 'debit'}.get(cleaned.get('txn_type'))
        if expected and cleaned.get('direction') != expected:
            raise ValidationError('Capital In must be Credit; Capital Out must be Debit.')
        return cleaned


@admin.register(CashTransaction)
class CashTransactionAdmin(admin.ModelAdmin):
    form = StandaloneCashForm
    list_display = ('id', 'created_at', 'direction', 'txn_type', 'amount', 'reference')
    list_filter = ('direction', 'txn_type', 'created_at')
    search_fields = ('reference',)
    ordering = ('-created_at',)
    raw_id_fields = ('loan_disbursement', 'collection', 'expense', 'fund_transaction')
    readonly_fields = raw_id_fields + ('source_record',)

    def source_record(self, obj):
        if obj is None:
            return 'Create collections, expenses, disbursements and fund transactions in their own sections.'
        for field in self.raw_id_fields:
            pk = getattr(obj, field + '_id')
            if pk is not None:
                model = CashTransaction._meta.get_field(field).remote_field.model
                opts = model._meta
                url = reverse('admin:%s_%s_change' % (opts.app_label, opts.model_name), args=[pk])
                return format_html('Edit the source record: <a href="{}">{} #{}</a>', url, opts.verbose_name, pk)
        return 'No source link. Non-capital entries require review before correction.'
    source_record.short_description = 'Manage transaction'

    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) and (obj is None or standalone_cash(obj))

    def has_delete_permission(self, request, obj=None):
        return super().has_delete_permission(request, obj) and (obj is None or standalone_cash(obj))

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop('delete_selected', None)
        return actions

    def save_model(self, request, obj, form, change):
        if not standalone_cash(obj):
            raise PermissionDenied('Manage this transaction through its source record.')
        if change:
            old = CashTransaction.objects.using(obj._state.db).get(pk=obj.pk)
            if not standalone_cash(old):
                raise PermissionDenied('Manage this transaction through its source record.')
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        db = router.db_for_write(CashTransaction, instance=obj)
        with transaction.atomic(using=db):
            current = CashTransaction.objects.using(db).select_for_update().get(pk=obj.pk)
            if not standalone_cash(current):
                raise PermissionDenied('Delete the source record instead.')
            super().delete_model(request, current)

    def delete_queryset(self, request, queryset):
        # Bulk cash deletion is deliberately disabled, including direct action calls.
        raise PermissionDenied('Bulk cash transaction deletion is disabled. Delete source records instead.')


@admin.register(LoanDisbursement)
class LoanDisbursementAdmin(SourceAdminMixin, admin.ModelAdmin):
    cash_link = 'loan_disbursement'
    list_display = ('loan', 'principal_amount', 'commission_percent', 'commission_amount',
                    'disbursed_amount', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('loan__loan_code', 'loan__customer__name')
    readonly_fields = ('commission_amount', 'disbursed_amount', 'created_at')
    ordering = ('-created_at',)


@admin.register(Expense)
class ExpenseAdmin(SourceAdminMixin, admin.ModelAdmin):
    cash_link = 'expense'


@admin.register(FundTransaction)
class FundTransactionAdmin(SourceAdminMixin, admin.ModelAdmin):
    cash_link = 'fund_transaction'
