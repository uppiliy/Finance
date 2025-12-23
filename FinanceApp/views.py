from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Customer, Loan, Collection
from .forms import LoanForm, CollectionForm
from django.http import JsonResponse
from django.db.models import Sum, ExpressionWrapper, DecimalField, F
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import datetime
from decimal import Decimal

def create_loan(request):
    created_loan = None

    # 🧠 Step 1: Handle normal POST request
    if request.method == 'POST':
        form = LoanForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['customer_name']
            mobile = form.cleaned_data['mobile_number']
            amount = form.cleaned_data['amount']
            repayment_type = form.cleaned_data['repayment_type']
            date_issued = form.cleaned_data['date_issued']

            # Customer check
            customer, created = Customer.objects.get_or_create(
                mobile_number=mobile,
                defaults={'name': name}
            )
            if not created and customer.name != name:
                customer.name = name
                customer.save()

            # Create loan
            loan = Loan.objects.create(
                customer=customer,
                amount=amount,
                repayment_type=repayment_type,
                date_issued=date_issued
            )

            messages.success(request, f"🎉 Loan created successfully! Loan ID: {loan.loan_code}")

            # ✅ Redirect using PRG pattern
            return redirect(f"{request.path}?loan={loan.loan_code}")
    else:
        form = LoanForm()

    # 🧠 Step 2: Handle redirected GET request with ?loan=1234
    loan_code = request.GET.get('loan')
    if loan_code:
        created_loan = get_object_or_404(Loan, loan_code=loan_code)

    return render(request, 'FinanceApp/loan_form.html', {
        'form': form,
        'created_loan': created_loan
    })


'''def check_customer(request):
    """AJAX endpoint to check if a mobile number exists."""
    mobile = request.GET.get('mobile', '').strip()
    if not mobile:
        return JsonResponse({'exists': False})

    try:
        customer = Customer.objects.get(mobile_number=mobile)
        return JsonResponse({
            'exists': True,
            'name': customer.name,
            'code': customer.customer_code
        })
    except Customer.DoesNotExist:
        return JsonResponse({'exists': False})'''

def check_customer(request):
    mobile = request.GET.get('mobile', '').strip()
    if not mobile:
        return JsonResponse({'exists': False})

    try:
        customer = Customer.objects.get(mobile_number=mobile)
        today = timezone.localdate()

        loans = (
            Loan.objects
            .filter(customer=customer, last_repayment_date__gte=today)
            .annotate(total_collected=Sum('collections__amount_collected'))
        )

        active_loans = []
        for loan in loans:
            total_collected = loan.total_collected or Decimal('0')
            remaining = loan.amount - total_collected

            if remaining > 0:  # Active loans only
                active_loans.append({
                    'loan_code': loan.loan_code,
                    'amount': float(loan.amount),
                    'repayment_type': loan.repayment_type,
                    'date_issued': loan.date_issued.strftime("%d-%b-%Y") if loan.date_issued else None,
                    'last_repayment_date': loan.last_repayment_date.strftime("%d-%b-%Y") if loan.last_repayment_date else None,
                    'total_collected': float(total_collected),
                    'remaining_balance': float(remaining),
                })

        return JsonResponse({
            'exists': True,
            'name': customer.name,
            'code': customer.customer_code,
            'active_loans': active_loans,
        })

    except Customer.DoesNotExist:
        return JsonResponse({'exists': False})
    
@csrf_exempt
def record_collection(request):
    if request.method == 'POST':
        form = CollectionForm(request.POST)
        if form.is_valid():
            loan_code = form.cleaned_data['loan_code']
            amount = form.cleaned_data['amount_collected']

            try:
                loan = Loan.objects.get(loan_code=loan_code)
            except Loan.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': f"No loan found with code {loan_code}"
                })

            # ✅ Save today's collection
            Collection.objects.create(loan=loan, amount_collected=amount)

            # ✅ Calculate updated totals
            total_collected = loan.collections.aggregate(
                total=Sum('amount_collected')
            )['total'] or 0
            remaining_balance = float(loan.amount) - float(total_collected)

            return JsonResponse({
                'success': True,
                'message': f"₹{amount} collected for Loan {loan.loan_code} \n Total Collected: ₹{total_collected}",
                'total_collected': float(total_collected),
                'remaining_balance': float(remaining_balance)
            })

        # ❌ Invalid form
        return JsonResponse({
            'success': False,
            'message': 'Invalid form data'
        })

    # 👇 For GET requests, show the normal form page
    form = CollectionForm()
    return render(request, 'FinanceApp/record_collection.html', {'form': form})


# 🔍 AJAX endpoint to fetch loan + customer info
def get_customer_details(request):
    loan_code = request.GET.get('loan_code')
    try:
        loan = Loan.objects.get(loan_code=loan_code)

        total_collected = (
            loan.collections.aggregate(total=Sum('amount_collected'))['total'] or 0
        )
        remaining_balance = float(loan.amount) - float(total_collected)

        # repayment-specific amount
        if loan.repayment_type == 'daily':
            repay_amount = float(loan.amount) / 100
        elif loan.repayment_type == 'weekly':
            repay_amount = float(loan.amount) / 14
        else:
            repay_amount = float(loan.amount) / 3

        data = {
            'found': True,
            'name': loan.customer.name,
            'mobile_number': loan.customer.mobile_number,
            'amount': float(loan.amount),
            'commission_percent': float(loan.commission_percent),
            'disbursed_amount': float(loan.disbursed_amount),
            'daily_amount': round(repay_amount, 2),
            'total_collected': float(total_collected),
            'remaining_balance': float(remaining_balance),
        }

    except Loan.DoesNotExist:
        data = {'found': False}

    return JsonResponse(data)

def daily_collection_report(request):
    selected_date = request.GET.get('date')
    if selected_date:
        date_obj = datetime.strptime(selected_date, "%Y-%m-%d").date()
    else:
        date_obj = timezone.now().date()  # gets today's local date

    collections = Collection.objects.filter(
        collection_date__date=date_obj   # ✅ match only the date part
    ).select_related('loan__customer')

    total_collected = collections.aggregate(total=Sum('amount_collected'))['total'] or 0

    return render(request, 'FinanceApp/daily_report.html', {
        'collections': collections,
        'selected_date': date_obj,
        'total_collected': total_collected
    })

from django.utils import timezone
from django.db.models import Sum

def report_view(request):
    today = timezone.localdate()
    status_filter = request.GET.get('status', 'all')  # default = all

    loans = Loan.objects.select_related('customer').annotate(
        total_collected=Sum('collections__amount_collected')
    )

    # Compute balances & status
    for loan in loans:
        loan.total_collected = loan.total_collected or 0
        loan.remaining_balance = float(loan.amount) - float(loan.total_collected)
        loan.is_overdue = (
            loan.last_repayment_date
            and loan.last_repayment_date < today
            and loan.remaining_balance > 0
        )
        loan.is_paid = loan.remaining_balance <= 0
        loan.is_active = not loan.is_paid and not loan.is_overdue

    # ✅ Apply status filter
    if status_filter == 'paid':
        loans = [l for l in loans if l.is_paid]
    elif status_filter == 'overdue':
        loans = [l for l in loans if l.is_overdue]
    elif status_filter == 'active':
        loans = [l for l in loans if l.is_active]

    # ✅ Totals (after filter)
    total_amount = sum(float(l.amount) for l in loans)
    total_commission = sum(float(l.commission_amount or 0) for l in loans)
    total_disbursed = sum(float(l.disbursed_amount or 0) for l in loans)
    total_collected = sum(float(l.total_collected) for l in loans)
    total_remaining = sum(float(l.remaining_balance) for l in loans)

    context = {
        'loans': loans,
        'generated_on': timezone.now(),
        'today': today,
        'status_filter': status_filter,
        'totals': {
            'amount': total_amount,
            'commission': total_commission,
            'disbursed': total_disbursed,
            'collected': total_collected,
            'remaining': total_remaining,
        },
    }

    return render(request, 'FinanceApp/report.html', context)

def loan_history_view(request):
    """Renders a simple page with a mobile number search box."""
    return render(request, 'FinanceApp/loan_history.html')


def get_loan_history(request):
    """AJAX endpoint: returns all loans for a given mobile number."""
    mobile = request.GET.get('mobile', '').strip()
    if not mobile:
        return JsonResponse({'error': 'No mobile number provided'}, status=400)

    try:
        customer = Customer.objects.get(mobile_number=mobile)
    except Customer.DoesNotExist:
        return JsonResponse({'exists': False, 'message': 'Customer not found'})

    loans = (
        Loan.objects.filter(customer=customer)
        .annotate(total_collected=Sum('collections__amount_collected'))
        .order_by('-date_issued')
    )

    today = timezone.localdate()
    loan_data = []
    for loan in loans:
        total_collected = float(loan.total_collected or 0)
        remaining = float(loan.amount) - total_collected
        status = 'Paid' if remaining <= 0 else 'Overdue' if loan.last_repayment_date < today else 'Active'

        loan_data.append({
            'loan_code': loan.loan_code,
            'amount': float(loan.amount),
            'repayment_type': loan.repayment_type,
            'date_issued': loan.date_issued.strftime('%d-%b-%Y'),
            'last_repayment_date': loan.last_repayment_date.strftime('%d-%b-%Y'),
            'total_collected': total_collected,
            'remaining_balance': remaining,
            'status': status,
        })

    return JsonResponse({
        'exists': True,
        'customer_name': customer.name,
        'customer_code': customer.customer_code,
        'loans': loan_data
    })

def get_loan_collections(request):
    """Return all collection entries for a given loan."""
    loan_code = request.GET.get('loan_code', '').strip()
    if not loan_code:
        return JsonResponse({'error': 'No loan code provided'}, status=400)

    try:
        loan = Loan.objects.get(loan_code=loan_code)
    except Loan.DoesNotExist:
        return JsonResponse({'error': 'Loan not found'}, status=404)

    collections = (
        Collection.objects.filter(loan=loan)
        .order_by('-collection_date')
        .values('amount_collected', 'collection_date')
    )

    collection_data = [
        {
            'amount_collected': float(c['amount_collected']),
            'collection_date': c['collection_date'].strftime('%d-%b-%Y %I:%M %p')
        }
        for c in collections
    ]

    return JsonResponse({
        'loan_code': loan.loan_code,
        'total_entries': len(collection_data),
        'collections': collection_data
    })