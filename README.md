# FinanceApp

A Django-based microfinance management application for managing customers, loans, loan collections, disbursements, fund sources, cash transactions, expenses, and financial reports.

---

## 📌 Project Overview

**FinanceApp** is a microfinance/loan management system built with:

* Python
* Django
* PostgreSQL (Production)
* SQLite (Local Development)
* Bootstrap
* JavaScript / AJAX
* Git / GitHub
* Render (Production Hosting)
* Neon PostgreSQL (Production Database)

The application is designed to manage the complete loan lifecycle:

```text
Customer
   ↓
Loan
   ↓
Loan Disbursement
   ↓
Loan Collections
   ↓
Cash / Bank Transactions
   ↓
Reports
```

---

# 🏗️ Project Structure

Typical project structure:

```text
Finance/
│
├── FinanceApp/
│   ├── migrations/
│   ├── templates/
│   │   └── FinanceApp/
│   ├── admin.py
│   ├── apps.py
│   ├── forms.py
│   ├── models.py
│   ├── urls.py
│   └── views.py
│
├── Finance/
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── manage.py
├── requirements.txt
├── db.sqlite3
└── README.md
```

---

# 👥 Customer Management

There is **no separate customer registration workflow**.

When creating a new loan:

1. Enter the customer's mobile number.
2. The system checks whether the customer already exists.
3. If the customer exists, the existing customer is used.
4. If the customer does not exist, a new customer is created automatically.

## Customer Fields

```text
customer_code
name
mobile_number
```

### Customer Code

Customer codes are automatically generated as four-digit numbers:

```text
0001
0002
0003
0004
...
```

The customer code should remain stable after creation.

---

# 💰 Loan Management

Each customer can have one or more loans.

## Loan Fields

The main `Loan` model contains:

```text
loan_code
customer
amount
repayment_type
commission_percent
commission_amount
disbursed_amount
repayment_amount
date_issued
last_repayment_date
```

---

# 🔢 Loan Codes

Loan codes are automatically generated using four digits:

```text
0001
0002
0003
0004
...
```

The application generally prefers **Loan Code** for loan-related operations instead of repeatedly entering a customer's 10-digit mobile number.

---

# 📅 Repayment Types

The application supports:

```text
Daily
Weekly
Monthly
```

## Commission Rates

Current business rules:

| Repayment Type | Commission |
| -------------- | ---------: |
| Daily          |        12% |
| Weekly         |      13.5% |
| Monthly        |        15% |

---

# 🧮 Loan Calculations

## Commission Amount

```text
commission_amount = amount × commission_percent / 100
```

## Disbursed Amount

```text
disbursed_amount = amount - commission_amount
```

---

## Repayment Amount

Current repayment calculations:

### Daily

```text
repayment_amount = amount / 100
```

### Weekly

```text
repayment_amount = amount / 14
```

### Monthly

```text
repayment_amount = amount / 4
```

---

# 📆 Last Repayment Date

The business rule currently used is:

> 100 calendar days from the day after the loan issue date.

The implementation currently uses:

```python
date_issued + timedelta(days=101)
```

This is intentional based on the current project rules.

---

# 💵 Loan Disbursement

The `LoanDisbursement` model stores a snapshot of the actual loan disbursement.

Important fields include:

```text
loan
principal_amount
commission_percent
commission_amount
disbursed_amount
collected_till_now
created_at
```

When a new loan disbursement is created, the corresponding cash transaction is recorded.

---

# 💳 Collections

The `Collection` model records customer repayments.

Important fields:

```text
loan
collection_date
amount_collected
payment_mode
```

## Payment Modes

Currently:

```text
Cash
UPI / Bank
```

A collection also creates a corresponding `CashTransaction`.

---

# 🏦 Cash Transactions

`CashTransaction` is used to maintain the financial ledger.

Important fields:

```text
payment_mode
direction
txn_type
amount
reference
created_at
txn_date
```

## Direction

```text
credit
debit
```

## Transaction Types

Current transaction types include:

```text
capital
capital_out
loan_disbursement
commission
collection
expense
```

> **Important:** Capital and FundSource are separate concepts in the project. Do not merge them or reinterpret FundSource as Capital.

---

# 💼 Fund Source

The project includes a `FundSource` model for tracking sources of funds.

Main fields:

```text
name
amount
date
notes
```

FundSource is intentionally separate from the old capital functionality.

---

# 📊 Dashboard / Reports

The application includes financial and loan reporting functionality.

Current areas include:

* Loan reports
* Daily collection report
* Loan history
* Cash dashboard
* Cash passbook
* Customer loan details
* Collection information
* Loan status
* Outstanding balance
* Total collected
* Disbursement information

---

# 🔍 Loan Lookup

The application supports looking up loans using the **Loan Code**.

The lookup can display:

```text
Customer Name
Customer Code
Loan Code
Loan Amount
Disbursed Amount
Total Amount Collected
Remaining Balance
```

The collection amount is editable.

Changing the Loan Code should **not automatically submit the collection form**.

---

# 🔄 Loan Extension

Loans can be extended.

The extension functionality:

1. Updates the relevant loan/disbursement information.
2. Creates a new `LoanDisbursement` snapshot.
3. Uses the selected extension date.
4. Keeps the historical disbursement information available.

---

# 🧠 Important Model Relationships

The main relationships are:

```text
Customer
   │
   └─── loans
          │
          ├─── collections
          │
          └─── disbursements
```

Financial transactions are recorded separately:

```text
Collection
     ↓
CashTransaction

LoanDisbursement
     ↓
CashTransaction
```

---

# ⚙️ Local Development

The project has a separate development copy used for database/migration work.

## Production Copy

```text
Desktop/Finance
```

This is the production project.

Production uses:

```text
Render
   ↓
Neon PostgreSQL
```

---

## Development Copy

```text
Documents/Copy/Finance
```

The development copy uses SQLite.

Example configuration:

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
```

This allows migrations and database changes to be tested locally without directly modifying the production Neon database.

---

# 🐍 Python Environment

The project has previously been used with different Python/Django versions.

Production has used approximately:

```text
Python 3.11.x
Django 4.2.x
```

The local development environment may differ.

Before making migration/deployment changes, always check:

```bash
python --version
python -m django --version
```

---

# 📦 Install Dependencies

Create/activate the appropriate virtual environment and install:

```bash
pip install -r requirements.txt
```

---

# 🗄️ Database Migrations

Before deploying database changes:

```bash
python manage.py makemigrations
python manage.py migrate
```

Check migration status:

```bash
python manage.py showmigrations
```

---

# 🧪 Local Database

The development copy uses:

```text
db.sqlite3
```

To inspect the database:

```bash
python manage.py shell
```

Example:

```python
from FinanceApp.models import Customer

Customer.objects.count()
```

---

# 📥 Fixtures / Data

The project has used Django fixtures for transferring development/production data.

Example:

```bash
python manage.py loaddata data.json
```

A backup fixture may contain many objects, so always verify the target database before loading production data.

---

# 🌐 Production Deployment

Production is hosted on:

```text
Render
```

The production database is:

```text
Neon PostgreSQL
```

The production database connection is configured using:

```text
DATABASE_URL
```

The production settings use `dj_database_url` to read the database URL.

Conceptually:

```python
DATABASES = {
    "default": dj_database_url.config(
        default=os.environ.get("DATABASE_URL")
    )
}
```

---

# 🚀 Render Build

The current Render build command is:

```bash
pip install -r requirements.txt
```

If database migrations are not automatically executed during deployment, migrations must be handled separately through the Render deployment configuration or shell.

**Important:** Installing Python packages does NOT create/update Django database tables.

For example:

```text
pip install -r requirements.txt
```

does not execute:

```bash
python manage.py migrate
```

---

# ⚠️ Production Migration Rule

When a model is added or changed, the production PostgreSQL database must receive the corresponding migration.

Example:

If `FundSource` is added:

```text
models.py
    ↓
makemigrations
    ↓
migration file
    ↓
migrate
    ↓
PostgreSQL table
```

Without the final migration step, Django can produce errors such as:

```text
psycopg2.errors.UndefinedTable:
relation "FinanceApp_fundsource" does not exist
```

---

# 🔀 Git Workflow

The project uses Git/GitHub.

Before making changes:

```bash
git status
```

Check the current branch:

```bash
git branch
```

Check remote status:

```bash
git fetch origin
git status
```

---

# 🛠️ Recommended Development Workflow

For database/model changes:

```text
1. Work in Documents/Copy/Finance
          ↓
2. Use SQLite
          ↓
3. Modify models
          ↓
4. makemigrations
          ↓
5. migrate
          ↓
6. Test locally
          ↓
7. git status
          ↓
8. git add
          ↓
9. git commit
          ↓
10. Transfer/merge changes to production project
          ↓
11. Push to GitHub
          ↓
12. Deploy on Render
          ↓
13. Run production migrations
          ↓
14. Verify production
```

---

# ⚠️ Important: Development vs Production

Do not confuse the two project copies.

## Development

```text
Documents/Copy/Finance
        ↓
SQLite
        ↓
Safe for migration testing
```

## Production

```text
Desktop/Finance
        ↓
GitHub
        ↓
Render
        ↓
Neon PostgreSQL
```

**Never assume that a migration applied to SQLite has also been applied to Neon PostgreSQL.**

Migration files are code.

Migration execution is database-specific.

---

# 🧹 Files That Should Generally Not Be Committed

The following should normally be excluded from Git:

```text
__pycache__/
*.pyc
.DS_Store
db.sqlite3
.env
```

A suitable `.gitignore` should be maintained.

---

# 🔐 Environment Variables

Production secrets should not be stored directly in Git.

Examples:

```text
DATABASE_URL
SECRET_KEY
```

These should be configured through the hosting environment.

Never commit production credentials to GitHub.

---

# 🐛 Troubleshooting

## Error: UndefinedTable

Example:

```text
psycopg2.errors.UndefinedTable:
relation "FinanceApp_fundsource" does not exist
```

This usually means:

```text
Django model exists
        ↓
Migration exists locally
        ↓
But migration has NOT been applied
        ↓
Production PostgreSQL table does not exist
```

Check:

```bash
python manage.py showmigrations FinanceApp
```

Then apply the missing migration to the correct production database.

---

## Error: No DATABASE_URL

If you see:

```text
No DATABASE_URL environment variable set
```

check whether the project is using production settings.

The development copy should normally use SQLite.

The production project should use the `DATABASE_URL` environment variable.

---

# 📋 Important Development Principles

### 1. Do not modify production blindly

Test database changes locally first.

### 2. Do not assume migrations are enough

A migration file being committed does not mean the production database has been migrated.

### 3. Keep business rules consistent

Loan calculations, commissions, repayment periods, and codes should not be changed casually.

### 4. Preserve historical financial data

Collections, disbursements, and transactions represent financial history and should not be deleted or recalculated without understanding the consequences.

### 5. Keep FundSource separate from Capital

FundSource is its own feature.

Do not bring the old capital concept back into FundSource unless explicitly requested.

### 6. Prefer Loan Code for loan operations

Where practical, use:

```text
Loan Code → 0001
```

instead of requiring the user to repeatedly enter:

```text
10-digit mobile number
```

---

# 📌 Current Core Models

The primary models currently include:

```text
Customer
Loan
Collection
LoanDisbursement
CashTransaction
FundSource
```

Additional models may exist as the application evolves.

---

# 🧾 Current Business Rules Summary

```text
Customer Code:
    0001, 0002, 0003...

Loan Code:
    0001, 0002, 0003...

Daily Commission:
    12%

Weekly Commission:
    13.5%

Monthly Commission:
    15%

Daily Repayment:
    Amount / 100

Weekly Repayment:
    Amount / 14

Monthly Repayment:
    Amount / 4

Disbursed Amount:
    Amount - Commission

Last Repayment Date:
    Issue Date + 101 days
```

---

# 🎯 Project Goal

FinanceApp is intended to provide a simple but complete system for managing:

```text
Customers
     ↓
Loans
     ↓
Disbursements
     ↓
Collections
     ↓
Cash / Bank Transactions
     ↓
Expenses
     ↓
Fund Sources
     ↓
Reports
```

The application should maintain accurate financial history while keeping the daily loan-management workflow fast and simple.
