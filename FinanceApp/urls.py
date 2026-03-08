from django.urls import path
from . import views
from django.shortcuts import render

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("", views.create_loan, name='create_loan'),
    path('check-customer/', views.check_customer, name='check_customer'),
    path('record-collection/', views.record_collection, name='record_collection'),
    path('get-customer-details/', views.get_customer_details, name='get_customer_details'),
    path('daily-collection-report/', views.daily_collection_report, name = 'daily_collection_report'),
    path('report/', views.report_view, name='report'),
    path('loan-history/', views.loan_history_view, name='loan_history'),
    path('get-loan-history/', views.get_loan_history, name='get_loan_history'),
    path('get-loan-collections/', views.get_loan_collections, name='get_loan_collections'),
    # in urls.py
    path("qr-test/", lambda r: render(r, "FinanceApp/qr_test.html"), name="qr_test"),


    path("cash-dashboard/", views.cash_dashboard, name="cash_dashboard"),
    path('add-capital/', views.add_capital, name='add_capital'),
    path('add-expense/', views.add_expense, name='add_expense'),
    path('cash-passbook/', views.cash_passbook, name='cash_passbook'),
    path('extend-loan/', views.extend_loan, name='extend_loan'),
    path('capital-history/', views.capital_history, name='capital_history'),
    path('expense-history/', views.expense_history, name='expense_history'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)