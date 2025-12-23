from django.contrib import admin
from .models import Customer, Loan, Collection
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

@admin.register(Loan)
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