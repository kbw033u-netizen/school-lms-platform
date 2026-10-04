from getpass import getpass

from django.core.management.base import BaseCommand, CommandError

from school.models import User


class Command(BaseCommand):
    help = "Create the first administrator for a deployed school portal."

    def handle(self, *args, **options):
        email = input("Admin email: ").strip()
        if not email or User.objects.filter(email__iexact=email).exists():
            raise CommandError("Enter an email address that is not already registered.")

        first_name = input("First name: ").strip()
        last_name = input("Last name: ").strip()
        password = getpass("Password (at least 12 characters): ")
        confirmation = getpass("Confirm password: ")
        if len(password) < 12 or password != confirmation:
            raise CommandError("Passwords must match and contain at least 12 characters.")

        admin = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            role="admin",
        )
        admin.set_password(password)
        admin.save()
        self.stdout.write(self.style.SUCCESS(f"Administrator {email} created."))