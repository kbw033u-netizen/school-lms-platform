from django.contrib import messages
from django.db.models import Q
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .models import Invoice, ResourceMaterial, SchoolClass, SupportTicket, User


SUPPORT_PHONE = "0721954896"


def index(request):
    return render(request, "index.html")


@require_http_methods(["GET", "POST"])
def login_view(request):
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
        return render(request, "login.html", status=401)
    return render(request, "login.html")


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


def classes_page(request):
    return render(request, "classes.html", {"classes": SchoolClass.objects.order_by("id")})


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