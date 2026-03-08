from django.contrib import admin
from .models import Customer, Loan, Collection, CashTransaction, LoanDisbursement
from django.utils.html import mark_safe


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('customer_code', 'name', 'mobile_number')
    search_fields = ('name', 'mobile_number', 'customer_code')
    ordering = ('id',)
    readonly_fields = ('customer_code',)

    fieldsets = (
        (None, {
            'fields': ('customer_code', 'name', 'mobile_number')
        }),
    )

'''@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    def qr_preview(self, obj):
        if obj.qr_code:
            return mark_safe(f'<img src="{obj.qr_code.url}" width="80" height="80" />')
        return "No QR"
    qr_preview.short_description = 'QR Code'
    
    list_display = (
        'loan_code',
        'customer',
        'amount',
        'repayment_type',
        'commission_percent',
        'disbursed_amount',
        'date_issued',
        'last_repayment_date',
        'qr_preview'
    )
    search_fields = ('loan_code', 'customer__name', 'customer__mobile_number')
    list_filter = ('repayment_type', 'date_issued')
    ordering = ('-id',)
    readonly_fields = ('loan_code', 'commission_percent', 'disbursed_amount', 'last_repayment_date')

    fieldsets = (
        ('Loan Details', {
            'fields': ('loan_code', 'customer', 'amount', 'repayment_type', 'date_issued', 'last_repayment_date')
        }),
        ('Calculated Fields', {
            'fields': ('commission_percent', 'disbursed_amount'),
        }),
    )'''

from django.urls import reverse
from django.utils.html import format_html

@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):

    def qr_preview(self, obj):
        url = reverse("loan_qr", args=[obj.loan_code])
        return format_html('<img src="{}" width="80" height="80" />', url)

    qr_preview.short_description = "QR Code"

    list_display = (
        'loan_code',
        'customer',
        'amount',
        'repayment_type',
        'commission_percent',
        'disbursed_amount',
        'date_issued',
        'last_repayment_date',
        'qr_preview'
    )

    search_fields = ('loan_code', 'customer__name', 'customer__mobile_number')
    list_filter = ('repayment_type', 'date_issued')
    ordering = ('-id',)

    readonly_fields = (
        'loan_code',
        'commission_percent',
        'disbursed_amount',
        'last_repayment_date'
    )

    fieldsets = (
        ('Loan Details', {
            'fields': (
                'loan_code',
                'customer',
                'amount',
                'repayment_type',
                'date_issued',
                'last_repayment_date'
            )
        }),
        ('Calculated Fields', {
            'fields': (
                'commission_percent',
                'disbursed_amount'
            ),
        }),
    )

@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = (
        'loan', 'get_customer_name', 'amount_collected', 'collection_date'
    )
    list_filter = ('collection_date',)
    search_fields = ('loan__loan_code', 'loan__customer__name', 'loan__customer__mobile_number')
    ordering = ('-collection_date',)

    # helper to show linked customer name in admin list
    def get_customer_name(self, obj):
        return obj.loan.customer.name
    get_customer_name.short_description = 'Customer'

@admin.register(CashTransaction)
class CashTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'created_at',
        'direction',
        'txn_type',
        'amount',
        'reference',
    )

    list_filter = ('direction', 'txn_type', 'created_at')
    search_fields = ('reference',)
    ordering = ('-created_at',)

@admin.register(LoanDisbursement)
class LoanDisbursementAdmin(admin.ModelAdmin):
    list_display = (
        'loan',
        'principal_amount',
        'commission_percent',
        'commission_amount',
        'disbursed_amount',
        'created_at',
    )

    list_filter = ('created_at',)
    search_fields = ('loan__loan_code', 'loan__customer__name')

    readonly_fields = (
        'commission_amount',
        'disbursed_amount',
        'created_at',
    )

    ordering = ('-created_at',)
