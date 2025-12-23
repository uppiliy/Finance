from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

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

    qr_code = models.ImageField(upload_to='loan_qrcodes/', blank=True, null=True)  # ✅ new field


    def save(self, *args, **kwargs):
        # Generate Loan Code (sequential, not tied to ID)
        if not self.loan_code:
            last_loan = Loan.objects.order_by('-loan_code').first()
            if last_loan and last_loan.loan_code.isdigit():
                next_number = int(last_loan.loan_code) + 1
            else:
                next_number = 1
            self.loan_code = f"{next_number:04d}"

        # Commission by repayment type
        if self.repayment_type == 'daily':
            self.commission_percent = Decimal('12.0')
        elif self.repayment_type == 'weekly':
            self.commission_percent = Decimal('13.5')
        elif self.repayment_type == 'monthly':
            self.commission_percent = Decimal('15.0')

        # Commission + Disbursed Amount
        if self.amount:
            self.commission_amount = (self.amount * self.commission_percent) / Decimal('100')
            self.disbursed_amount = self.amount - self.commission_amount

            # Repayment logic
            if self.repayment_type == 'daily':
                self.repayment_amount = self.amount / 100
            elif self.repayment_type == 'weekly':
                self.repayment_amount = self.amount / 14
            elif self.repayment_type == 'monthly':
                self.repayment_amount = self.amount / 4

        # 🔥 Set Last Repayment Date = date_issued + 100 days (starting tomorrow)
        if self.date_issued:
            self.last_repayment_date = self.date_issued + timedelta(days=101)

        super().save(*args, **kwargs)

         # ✅ Generate QR Code only if not already created
        if not self.qr_code:
            self.generate_qr_code()

    def generate_qr_code(self):
        """Generates and saves a unique QR code for this loan."""
        '''qr_content = self.loan_code

        qr = qrcode.make(qr_content)
        buffer = BytesIO()
        qr.save(buffer, format='PNG')
        file_name = f"loan_{self.loan_code}.png"
        self.qr_code.save(file_name, File(buffer), save=False)
        super().save(update_fields=['qr_code'])'''

        """Generates a QR code with big readable loan_code text above it."""
        import qrcode
        from PIL import Image, ImageDraw, ImageFont
        from io import BytesIO
        from django.core.files import File
        import os

        # QR CONTENT (loan code only)
        qr_content = f"{self.loan_code}"

        # Generate QR
        qr = qrcode.make(qr_content)
        qr = qr.convert("RGB")  # ensure RGB

        qr_width, qr_height = qr.size

        # -------- BIG FONT LOADING --------
        # Try to load a big TTF font (more readable)
        try:
            # macOS default font path
            font_path = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
            font = ImageFont.truetype(font_path, 30)  # 40px font size
        except:
            # fallback (still bigger than default)
            font = ImageFont.load_default()

        text = f"Loan Code: {self.loan_code}"

        # Calculate text size
        dummy_img = Image.new("RGB", (qr_width, 80), "white")
        dummy_draw = ImageDraw.Draw(dummy_img)
        text_width = dummy_draw.textlength(text, font=font)
        text_height = 40  # Approx for 40px font

        padding = 30

        # New image height = text + padding + QR
        total_height = text_height + padding + qr_height

        # Create final image
        combined = Image.new("RGB", (qr_width, total_height), "white")
        draw = ImageDraw.Draw(combined)

        # Center text
        text_x = (qr_width - text_width) // 2
        text_y = 10

        draw.text((text_x, text_y), text, fill="black", font=font)

        # Paste QR below text
        qr_y = text_height + padding // 2
        combined.paste(qr, (0, qr_y))

        # Save final image
        buffer = BytesIO()
        combined.save(buffer, format="PNG")
        file_name = f"loan_{self.loan_code}.png"

        self.qr_code.save(file_name, File(buffer), save=False)
        super().save(update_fields=["qr_code"])
            
        def __str__(self):
            return f"Loan {self.loan_code} - {self.customer.name}"
    
from django.db import models
from django.utils import timezone

class Collection(models.Model):    
    loan = models.ForeignKey('Loan', on_delete=models.CASCADE, related_name='collections')
    collection_date = models.DateTimeField(default=timezone.now)
    amount_collected = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.loan.loan_code} - {self.collection_date} - ₹{self.amount_collected}"

