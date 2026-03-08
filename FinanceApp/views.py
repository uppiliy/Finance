from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Customer, Loan, Collection, CashTransaction, LoanDisbursement
from .forms import LoanForm, CollectionForm, CapitalForm, ExpenseForm
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
            commission_percent = form.cleaned_data.get('commission_percent')
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
                commission_percent=commission_percent,
                date_issued=date_issued
            )

            # ✅ CREATE INITIAL DISBURSEMENT
            commission_percent = loan.commission_percent or Decimal("0")
            commission_amount = (amount * commission_percent) / Decimal("100")
            disbursed_amount = amount - commission_amount

            LoanDisbursement.objects.create(
                loan=loan,
                principal_amount=amount,
                commission_percent=commission_percent,
                commission_amount=commission_amount,
                disbursed_amount=disbursed_amount,
                created_at=timezone.make_aware(datetime.combine(loan.date_issued,timezone.localtime().time()))
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

# 🔍 AJAX endpoint to check customer + active loans
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
            #.annotate(total_collected=Sum('collections__amount_collected'))
        )

        active_loans = []
        for loan in loans:
            total_collected = loan.total_collected or Decimal('0')
            remaining = loan.remaining_balance

            if remaining > 0:  # Active loans only
                active_loans.append({
                    'loan_code': loan.loan_code,
                    'amount': float(loan.total_principal),
                    'repayment_type': loan.repayment_type,
                    'date_issued': loan.date_issued.strftime("%d-%b-%Y") if loan.date_issued else None,
                    'last_repayment_date': loan.last_repayment_date.strftime("%d-%b-%Y") if loan.last_repayment_date else None,
                    'total_collected': float(loan.total_collected),
                    'remaining_balance': float(loan.remaining_balance),
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
            payment_mode = form.cleaned_data['payment_mode']
            collection_date = form.cleaned_data.get('collection_date')

            try:
                loan = Loan.objects.get(loan_code=loan_code)
            except Loan.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': f"No loan found with code {loan_code}"
                })

        
            if collection_date:
                now_time = timezone.localtime().time()  # REAL current time
                collection_datetime = timezone.make_aware(
                    datetime.combine(collection_date, now_time)
                )
            else:
                collection_datetime = timezone.now()

            # ✅ SAVE COLLECTION WITH DATE
            Collection.objects.create(
                loan=loan,
                amount_collected=amount,
                payment_mode=payment_mode,
                collection_date=collection_datetime
            )

            total_collected = loan.total_collected
            remaining_balance = loan.remaining_balance

            return JsonResponse({
                'success': True,
                'message': f"₹{amount} collected for Loan {loan.loan_code}",
                'total_collected': float(total_collected),
                'remaining_balance': float(remaining_balance)
            })

        return JsonResponse({
            'success': False,
            'message': 'Invalid form data'
        })

    form = CollectionForm()
    return render(request, 'FinanceApp/record_collection.html', {'form': form})



# 🔍 AJAX endpoint to fetch loan + customer info
def get_customer_details(request):
    loan_code = request.GET.get('loan_code')
    try:
        loan = Loan.objects.get(loan_code=loan_code)

        total_collected = loan.total_collected
        remaining_balance = float(loan.remaining_balance)

        principal = loan.total_principal
        if loan.repayment_type == 'daily':
            repay_amount = principal / 100
        elif loan.repayment_type == 'weekly':
            repay_amount = principal / 14
        else:
            repay_amount = principal / 3


        data = {
            'found': True,
            'name': loan.customer.name,
            'mobile_number': loan.customer.mobile_number,
            'amount': float(loan.total_principal),
            'commission_percent': float(loan.commission_percent),
            'disbursed_amount': float(loan.total_disbursed),
            'daily_amount': float(round(repay_amount, 2)),
            'total_collected': float(loan.total_collected),
            'remaining_balance': float(loan.remaining_balance),
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
    status_filter = request.GET.get('status', 'all')

    loans = (
        Loan.objects
        .select_related('customer')
        .prefetch_related('disbursements', 'collections')
    )

    report_loans = []
    for loan in loans:
        loan.is_paid = loan.remaining_balance <= 0
        loan.is_overdue = loan.last_repayment_date and loan.last_repayment_date < today and not loan.is_paid
        loan.is_active = not loan.is_paid and not loan.is_overdue

        if status_filter == 'paid' and not loan.is_paid:
            continue
        if status_filter == 'overdue' and not loan.is_overdue:
            continue
        if status_filter == 'active' and not loan.is_active:
            continue

        report_loans.append(loan)

    totals = {
        'amount': sum(l.total_principal for l in report_loans),
        'commission': sum(l.total_commission for l in report_loans),
        'disbursed': sum(l.total_disbursed for l in report_loans),
        'collected': sum(l.total_collected for l in report_loans),
        'remaining': sum(l.remaining_balance for l in report_loans),
    }

    return render(request, 'FinanceApp/report.html', {
        'loans': report_loans,
        'totals': totals,
        'today': today,
        'generated_on': timezone.now(),
        'status_filter': status_filter,
    })


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
        #.annotate(total_collected=Sum('collections__amount_collected'))
        .order_by('-date_issued')
    )

    today = timezone.localdate()
    loan_data = []
    
    for loan in loans:
        disbursements = list(
            loan.disbursements.all().order_by('created_at')
        )

        status = 'Paid' if loan.remaining_balance <= 0 else 'Overdue' if loan.last_repayment_date < today else 'Active'
        total_collected = float(loan.total_collected or 0)
        previous_snapshot = 0
        disb_data = []

        for idx, d in enumerate(disbursements):
            snapshot = float(d.collected_till_now or 0)
            is_last = (idx == len(disbursements) - 1)

            if is_last:
                collected_display = max(total_collected - previous_snapshot, 0)
            else:
                collected_display = max(snapshot - previous_snapshot, 0)
                previous_snapshot = snapshot

            disb_data.append({
                'date': d.created_at.strftime('%d-%b-%Y'),
                'principal': float(d.principal_amount),
                'commission': float(d.commission_amount),
                'disbursed': float(d.disbursed_amount),
                'collected_till_now': collected_display,
            })

        
        loan_data.append({
            'loan_code': loan.loan_code,
            'total_principal': float(loan.total_principal),
            'repayment_type': loan.repayment_type,
            'date_issued': loan.date_issued.strftime('%d-%b-%Y'),
            'last_repayment_date': loan.last_repayment_date.strftime('%d-%b-%Y'),
            'total_collected': total_collected,
            'remaining_balance': float(loan.remaining_balance),
            'status': status,
            'disbursements': disb_data
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
            'collection_date': timezone.localtime(c['collection_date']).strftime('%d-%b-%Y %I:%M %p')
        }
        for c in collections
    ]

    return JsonResponse({
        'loan_code': loan.loan_code,
        'total_entries': len(collection_data),
        'collections': collection_data
    })

from django.db.models import Sum
from decimal import Decimal

def cash_dashboard(request):
    qs = CashTransaction.objects.all()

    # 💵 CASH
    cash_credit = qs.filter(
        direction="credit",
        payment_mode="cash"
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    cash_debit = qs.filter(
        direction="debit",
        payment_mode="cash"
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    cash_in_hand = cash_credit - cash_debit

    # 🏦 BANK / UPI
    bank_credit = qs.filter(
        direction="credit",
        payment_mode="upi"
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    bank_debit = qs.filter(
        direction="debit",
        payment_mode="upi"
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    bank_balance = bank_credit - bank_debit

    # 📊 Breakdown by txn_type + payment_mode
    breakdown = (
        qs.values("txn_type", "payment_mode")
        .annotate(total=Sum("amount"))
        .order_by("txn_type", "payment_mode")
    )

    # ➕ NEW TOTALS (DOES NOT AFFECT EXISTING)
    total_capital = qs.filter(
        txn_type="capital"
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    total_expense = qs.filter(
        txn_type="expense"
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    total_collection = qs.filter(
        txn_type="collection"
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    # 🧮 Total Balance (Cash + Bank)
    total_balance = cash_in_hand + bank_balance

    context = {
        "cash_in_hand": cash_in_hand,
        "bank_balance": bank_balance,
        "cash_credit": cash_credit,
        "cash_debit": cash_debit,
        "bank_credit": bank_credit,
        "bank_debit": bank_debit,
        "breakdown": breakdown,

        # new
        "total_capital": total_capital,
        "total_expense": total_expense,
        "total_collection": total_collection,
        "total_balance": total_balance,
    }

    return render(request, "FinanceApp/cash_dashboard.html", context)

def add_capital(request):
    if request.method == 'POST':
        form = CapitalForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "💰 Capital recorded successfully!")
            return redirect('add_capital')  # reload form empty
    else:
        form = CapitalForm()

    return render(request, 'FinanceApp/add_capital.html', {'form': form})

def add_expense(request):
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "💸 Expense recorded successfully!")
            return redirect('add_expense')  # reload empty form
    else:
        form = ExpenseForm()

    return render(request, 'FinanceApp/add_expense.html', {'form': form})

from django.db.models import Sum, F, Value
from django.db.models.functions import Coalesce
from .models import CashTransaction
from django.shortcuts import render

def cash_passbook(request):
    # Get all transactions ordered by date
    transactions = CashTransaction.objects.order_by('txn_date', 'id')

    # Running balance calculation
    balance = 0
    passbook = []
    for txn in transactions:
        if txn.direction == 'credit':
            balance += txn.amount
        else:  # debit
            balance -= txn.amount
        passbook.append({
            'date': txn.txn_date,
            'type': txn.txn_type,
            'direction': txn.direction,
            'amount': txn.amount,
            'reference': txn.reference,
            'balance': balance
        })

    # Reverse so latest transaction appears first
    passbook.reverse()

    return render(request, 'FinanceApp/cash_passbook.html', {'passbook': passbook})


'''@csrf_exempt
def extend_loan(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request'})

    try:
        loan = Loan.objects.get(loan_code=request.POST.get('loan_code'))
        principal = Decimal(request.POST.get('add_amount'))
        commission_percent = Decimal(request.POST.get('commission_percent'))
    except:
        return JsonResponse({'success': False, 'message': 'Invalid data'})

    # 🔹 STEP 1: get total collected so far
    total_collected = loan.total_collected

    # 🔹 STEP 2: update PREVIOUS disbursement
    last_disb = loan.disbursements.order_by('-created_at').first()
    if last_disb:
        last_disb.collected_till_now = total_collected
        last_disb.save(update_fields=['collected_till_now'])

    # 🔹 STEP 3: create NEW disbursement (fresh)
    LoanDisbursement.objects.create(
        loan=loan,
        principal_amount=principal,
        commission_percent=commission_percent,
        collected_till_now=0  # 👈 starts clean
    )

    return JsonResponse({
        'success': True,
        'message': f'Loan {loan.loan_code} extended by ₹{principal}'
    })'''

@csrf_exempt
def extend_loan(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request'})

    try:
        loan = Loan.objects.get(loan_code=request.POST.get('loan_code'))
        principal = Decimal(request.POST.get('add_amount'))
        commission_percent = Decimal(request.POST.get('commission_percent'))
    except:
        return JsonResponse({'success': False, 'message': 'Invalid data'})

    # 🔹 STEP 1: get total collected so far
    total_collected = loan.total_collected

    # 🔹 STEP 2: update PREVIOUS disbursement snapshot
    last_disb = loan.disbursements.order_by('-created_at').first()
    if last_disb:
        last_disb.collected_till_now = total_collected
        last_disb.save(update_fields=['collected_till_now'])

    # 🔹 STEP 3: determine extension date (OPTIONAL)
    extend_date = request.POST.get('extend_date')

    if extend_date:
        disbursed_at = timezone.make_aware(
            datetime.combine(
                datetime.strptime(extend_date, '%Y-%m-%d').date(),
                timezone.localtime().time()
            )
        )
    else:
        disbursed_at = timezone.now()

    # 🔹 STEP 4: create NEW disbursement
    LoanDisbursement.objects.create(
        loan=loan,
        principal_amount=principal,
        commission_percent=commission_percent,
        collected_till_now=0,     # 👈 starts clean
        created_at=disbursed_at   # ⭐ ONLY ADDITION
    )

    return JsonResponse({
        'success': True,
        'message': f'Loan {loan.loan_code} extended by ₹{principal}'
    })


def capital_history(request):
    capital_entries = CashTransaction.objects.filter(
        txn_type="capital"
    ).order_by('-txn_date')

    total_capital = capital_entries.aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0")

    return render(request, "FinanceApp/capital_history.html", {
        "entries": capital_entries,
        "total_capital": total_capital
    })

def expense_history(request):
    expense_entries = CashTransaction.objects.filter(
        txn_type="expense"
    ).order_by('-txn_date')

    total_expense = expense_entries.aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0")

    return render(request, "FinanceApp/expense_history.html", {
        "entries": expense_entries,
        "total_expense": total_expense
    })

import qrcode
from io import BytesIO
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from PIL import Image, ImageDraw, ImageFont

def loan_qr(request, loan_code):
    loan = get_object_or_404(Loan, loan_code=loan_code)

    qr_content = f"{loan.loan_code}"

    qr = qrcode.make(qr_content)
    qr = qr.convert("RGB")

    qr_width, qr_height = qr.size

    # text
    text = f"Loan Code: {loan.loan_code}"

    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 30)
    except:
        font = ImageFont.load_default()

    dummy = Image.new("RGB", (qr_width, 80), "white")
    draw = ImageDraw.Draw(dummy)
    text_width = draw.textlength(text, font=font)

    text_height = 40
    padding = 30
    total_height = text_height + padding + qr_height

    img = Image.new("RGB", (qr_width, total_height), "white")
    draw = ImageDraw.Draw(img)

    text_x = (qr_width - text_width) // 2
    draw.text((text_x, 10), text, fill="black", font=font)

    img.paste(qr, (0, text_height + padding // 2))

    buffer = BytesIO()
    img.save(buffer, format="PNG")

    return HttpResponse(buffer.getvalue(), content_type="image/png")