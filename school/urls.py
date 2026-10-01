from django.urls import path

from . import views


urlpatterns = [
    path("", views.index, name="index"),
    path("login", views.login_view, name="login"),
    path("logout", views.logout_view, name="logout"),
    path("dashboard", views.dashboard, name="dashboard"),
    path("library", views.library, name="library"),
    path("billing", views.billing, name="billing"),
    path("classes", views.classes_page, name="classes"),
    path("support", views.support_page, name="support"),
    path("contact", views.contact_page, name="contact"),
]