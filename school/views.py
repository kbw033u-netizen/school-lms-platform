import uuid
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from . import paypal, stripe_card, zoom
from .models import Exam, Invoice, Payment, ResourceMaterial, SchoolClass, SupportTicket, User


SUPPORT_PHONE = "0721954896"


def index(request):
    return render(request, "index.html")


@require_http_methods(["GET", "POST"])
def login_view(request):
    login_role = request.GET.get("role", "").strip().lower()
    if request.path.rstrip("/").endswith("login/teacher"):
        login_role = "teacher"
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user and user.check_password(password):
            request.session.cycle_key()
            request.session["user_id"] = user.pk
            request.session["role"] = user.role
            return redirect("dashboard")
        messages.error(request, "Invalid email or password.")
        return render(request, "login.html", {"login_role": login_role}, status=401)
    return render(request, "login.html", {"login_role": login_role})


def logout_view(request):
    request.session.flush()
    return redirect("index")


def _current_user(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return User.objects.filter(pk=user_id, is_active=True).first()


def dashboard(request):
    user = _current_user(request)
    if not user:
        return redirect("login")
    context = {
        "user": user,
        "classes": SchoolClass.objects.order_by("-id")[:3],
        "resources": ResourceMaterial.objects.order_by("-id")[:3],
        "invoices": Invoice.objects.order_by("-id"),
        "total_users": User.objects.count(),
        "total_classes": SchoolClass.objects.count(),
        "total_resources": ResourceMaterial.objects.count(),
        "total_invoices": Invoice.objects.count(),
    }
    return render(request, "dashboard.html", context)


def library(request):
    return render(request, "library.html", {"resources": ResourceMaterial.objects.order_by("-id")})


def billing(request):
    user = _current_user(request)
    if not user:
        return redirect("login")
    invoices = Invoice.objects.all()
    if user.role in ("student", "parent"):
        invoices = invoices.filter(
            Q(student_name__icontains=user.first_name) | Q(student_name__icontains=user.last_name)
        )
        if not invoices.exists():
            invoices = Invoice.objects.all()
    return render(request, "billing.html", {"user": user, "invoices": invoices})


def _record_payment(invoice, amount, method, reference):
    Payment.objects.create(invoice=invoice, amount=amount, method=method, reference=reference)
    invoice.amount_paid += amount
    invoice.status = "Paid" if invoice.amount_paid >= invoice.total_amount else "Partially Paid"
    invoice.save(update_fields=["amount_paid", "status"])


def _validated_amount(request, invoice):
    try:
        amount = Decimal(request.POST.get("amount", "0")).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None
    remaining = invoice.total_amount - invoice.amount_paid
    if amount <= 0 or amount > remaining:
        return None
    return amount


@require_POST
def pay_invoice(request, invoice_id):
    user = _current_user(request)
    if not user:
        return redirect("login")
    invoice = get_object_or_404(Invoice, pk=invoice_id)
    amount = _validated_amount(request, invoice)
    if amount is None:
        messages.error(request, "Enter a valid payment amount up to the outstanding total.")
        return redirect("billing")
    method = request.POST.get("method", "mpesa")
    if method not in dict(Payment.METHOD_CHOICES):
        method = "mpesa"
    if method == "paypal":
        request.session["paypal_amount"] = str(amount)
        request.session["paypal_invoice_id"] = invoice.pk
        return redirect("paypal_start")
    if method in ("visa", "card"):
        request.session["card_amount"] = str(amount)
        request.session["card_invoice_id"] = invoice.pk
        request.session["card_method"] = method
        return redirect("card_start")
    _record_payment(invoice, amount, method, f"PAY-{uuid.uuid4().hex[:10].upper()}")
    messages.success(request, f"Payment of KES {amount} recorded for {invoice.invoice_number}.")
    return redirect("billing")


@require_http_methods(["GET"])
def paypal_start(request):
    user = _current_user(request)
    if not user:
        return redirect("login")
    invoice = get_object_or_404(Invoice, pk=request.session.get("paypal_invoice_id"))
    amount = Decimal(request.session.get("paypal_amount", "0"))
    if amount <= 0:
        messages.error(request, "No PayPal payment is in progress.")
        return redirect("billing")
    order_id, approve_url = paypal.create_order(
        amount,
        "USD",
        request.build_absolute_uri("/billing/paypal/return"),
        request.build_absolute_uri("/billing/paypal/cancel"),
        invoice.invoice_number,
    )
    if not approve_url:
        # PayPal not configured: record a local demo payment instead.
        _record_payment(invoice, amount, "paypal", f"PP-DEMO-{uuid.uuid4().hex[:10].upper()}")
        request.session.pop("paypal_amount", None)
        request.session.pop("paypal_invoice_id", None)
        messages.success(request, f"Demo PayPal payment of {amount} recorded for {invoice.invoice_number}.")
        return redirect("billing")
    request.session["paypal_order_id"] = order_id
    return redirect(approve_url)


@require_http_methods(["GET"])
def paypal_return(request):
    user = _current_user(request)
    if not user:
        return redirect("login")
    invoice = get_object_or_404(Invoice, pk=request.session.get("paypal_invoice_id"))
    amount = Decimal(request.session.get("paypal_amount", "0"))
    order_id = request.session.get("paypal_order_id", "") or request.GET.get("token", "")
    success, reference = paypal.capture_order(order_id)
    request.session.pop("paypal_amount", None)
    request.session.pop("paypal_invoice_id", None)
    request.session.pop("paypal_order_id", None)
    if success:
        _record_payment(invoice, amount, "paypal", f"PP-{reference}")
        messages.success(request, f"PayPal payment of {amount} captured for {invoice.invoice_number}.")
    else:
        messages.error(request, "PayPal payment could not be completed.")
    return redirect("billing")


@require_http_methods(["GET"])
def paypal_cancel(request):
    request.session.pop("paypal_amount", None)
    request.session.pop("paypal_invoice_id", None)
    request.session.pop("paypal_order_id", None)
    messages.error(request, "PayPal payment was cancelled.")
    return redirect("billing")


@require_http_methods(["GET"])
def card_start(request):
    user = _current_user(request)
    if not user:
        return redirect("login")
    invoice = get_object_or_404(Invoice, pk=request.session.get("card_invoice_id"))
    amount = Decimal(request.session.get("card_amount", "0"))
    method = request.session.get("card_method", "card")
    if amount <= 0:
        messages.error(request, "No card payment is in progress.")
        return redirect("billing")
    session_id, checkout_url = stripe_card.create_checkout_session(
        amount,
        "USD",
        request.build_absolute_uri("/billing/card/return"),
        request.build_absolute_uri("/billing/card/cancel"),
        invoice.invoice_number,
    )
    if not checkout_url:
        # Stripe not configured: record a local demo card payment instead.
        _record_payment(invoice, amount, method, stripe_card.demo_reference())
        for key in ("card_amount", "card_invoice_id", "card_method"):
            request.session.pop(key, None)
        messages.success(request, f"Demo card payment of {amount} recorded for {invoice.invoice_number}.")
        return redirect("billing")
    request.session["card_session_id"] = session_id
    return redirect(checkout_url)


@require_http_methods(["GET"])
def card_return(request):
    user = _current_user(request)
    if not user:
        return redirect("login")
    invoice = get_object_or_404(Invoice, pk=request.session.get("card_invoice_id"))
    amount = Decimal(request.session.get("card_amount", "0"))
    method = request.session.get("card_method", "card")
    session_id = request.session.get("card_session_id", "")
    paid, reference = stripe_card.retrieve_session(session_id)
    for key in ("card_amount", "card_invoice_id", "card_method", "card_session_id"):
        request.session.pop(key, None)
    if paid:
        _record_payment(invoice, amount, method, f"CARD-{reference}")
        messages.success(request, f"Card payment of {amount} completed for {invoice.invoice_number}.")
    else:
        messages.error(request, "Card payment could not be completed.")
    return redirect("billing")


@require_http_methods(["GET"])
def card_cancel(request):
    for key in ("card_amount", "card_invoice_id", "card_method", "card_session_id"):
        request.session.pop(key, None)
    messages.error(request, "Card payment was cancelled.")
    return redirect("billing")


def classes_page(request):
    user = _current_user(request)
    is_staff = bool(user and user.role in ("teacher", "admin"))
    return render(
        request,
        "classes.html",
        {"classes": SchoolClass.objects.order_by("id"), "is_staff": is_staff},
    )


@require_POST
def class_go_live(request, class_id):
    user = _current_user(request)
    if not user or user.role not in ("teacher", "admin"):
        return redirect("login")
    school_class = get_object_or_404(SchoolClass, pk=class_id)
    meeting = zoom.create_meeting(school_class.title, school_class.start_time)
    school_class.meeting_url = meeting["join_url"]
    school_class.zoom_start_url = meeting["start_url"]
    school_class.zoom_meeting_id = meeting["meeting_id"]
    school_class.zoom_passcode = meeting["passcode"]
    school_class.status = "Live"
    school_class.save(
        update_fields=["meeting_url", "zoom_start_url", "zoom_meeting_id", "zoom_passcode", "status"]
    )
    messages.success(request, f"{school_class.title} is now live on Zoom.")
    return redirect("classes")


@require_http_methods(["GET", "POST"])
def exams_page(request):
    user = _current_user(request)
    is_staff = bool(user and user.role in ("teacher", "admin"))
    if request.method == "POST":
        if not is_staff:
            return redirect("login")
        upload = request.FILES.get("pdf_file")
        if not upload or not upload.name.lower().endswith(".pdf"):
            messages.error(request, "Please choose a PDF file to upload.")
            return redirect("exams")
        Exam.objects.create(
            title=request.POST.get("title", "").strip() or upload.name,
            subject=request.POST.get("subject", "").strip(),
            grade_level=request.POST.get("grade_level", "").strip(),
            term=request.POST.get("term", "").strip(),
            academic_year=request.POST.get("academic_year", "").strip(),
            pdf_file=upload,
            uploaded_by=f"{user.first_name} {user.last_name}".strip() or user.email,
        )
        messages.success(request, "Exam uploaded successfully.")
        return redirect("exams")
    return render(
        request,
        "exams.html",
        {"exams": Exam.objects.order_by("-id"), "is_staff": is_staff},
    )


@require_http_methods(["GET", "POST"])
def support_page(request):
    if request.method == "POST":
        SupportTicket.objects.create(
            user_name=request.POST.get("user_name", "").strip(),
            user_email=request.POST.get("user_email", "").strip(),
            subject=request.POST.get("subject", "").strip(),
            message=request.POST.get("message", "").strip(),
        )
        return redirect("support")
    return render(request, "support.html", {"support_phone": SUPPORT_PHONE})


def contact_page(request):
    return render(
        request,
        "support.html",
        {"support_phone": SUPPORT_PHONE, "contact_only": True},
    )