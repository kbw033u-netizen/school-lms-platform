from django.contrib.auth.hashers import check_password, make_password
from django.db import models


class User(models.Model):
    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("teacher", "Teacher"),
        ("student", "Student"),
        ("parent", "Parent"),
    ]

    email = models.EmailField(unique=True)
    password_hash = models.CharField(max_length=128)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    phone = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def set_password(self, raw_password):
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password_hash)

    def __str__(self):
        return self.email


class ResourceMaterial(models.Model):
    title = models.CharField(max_length=200)
    subject = models.CharField(max_length=100)
    grade_level = models.CharField(max_length=50)
    resource_type = models.CharField(max_length=50)
    term = models.CharField(max_length=50)
    academic_year = models.CharField(max_length=10)
    file_url = models.CharField(max_length=500)
    uploaded_by = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class SchoolClass(models.Model):
    title = models.CharField(max_length=200)
    teacher_name = models.CharField(max_length=150)
    subject = models.CharField(max_length=100)
    lesson_date = models.DateField(blank=True, null=True)
    start_time = models.CharField(max_length=30)
    end_time = models.CharField(max_length=30)
    room_name = models.CharField(max_length=100)
    meeting_url = models.URLField(max_length=500)
    zoom_meeting_id = models.CharField(max_length=30, blank=True)
    zoom_passcode = models.CharField(max_length=30, blank=True)
    zoom_start_url = models.URLField(max_length=1000, blank=True)
    status = models.CharField(max_length=30, default="scheduled")
    recurrence = models.CharField(max_length=50, default="One-off")

    def __str__(self):
        return self.title


class Invoice(models.Model):
    student_name = models.CharField(max_length=200)
    invoice_number = models.CharField(max_length=50, unique=True)
    term = models.CharField(max_length=50)
    due_date = models.CharField(max_length=30)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=30, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.invoice_number


class Payment(models.Model):
    METHOD_CHOICES = [
        ("mpesa", "M-Pesa"),
        ("paypal", "PayPal"),
        ("visa", "Visa"),
        ("card", "Card"),
        ("bank", "Bank Transfer"),
    ]

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default="mpesa")
    reference = models.CharField(max_length=60, unique=True)
    status = models.CharField(max_length=30, default="completed")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.reference


class Exam(models.Model):
    title = models.CharField(max_length=200)
    subject = models.CharField(max_length=100)
    grade_level = models.CharField(max_length=50)
    term = models.CharField(max_length=50)
    academic_year = models.CharField(max_length=10)
    pdf_file = models.FileField(upload_to="exams/")
    uploaded_by = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class SupportTicket(models.Model):
    user_name = models.CharField(max_length=200)
    user_email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=30, default="open")

    def __str__(self):
        return self.subject