from django.urls import path

from . import views


urlpatterns = [
    path("", views.index, name="index"),
    path("login", views.login_view, name="login"),
    path("logout", views.logout_view, name="logout"),
    path("dashboard", views.dashboard, name="dashboard"),
    path("library", views.library, name="library"),
    path("exams", views.exams_page, name="exams"),
    path("billing", views.billing, name="billing"),
    path("billing/pay/<int:invoice_id>", views.pay_invoice, name="pay_invoice"),
    path("classes", views.classes_page, name="classes"),
    path("classes/<int:class_id>/go-live", views.class_go_live, name="class_go_live"),
    path("support", views.support_page, name="support"),
    path("contact", views.contact_page, name="contact"),
]