from django.core.management.base import BaseCommand

from accounts.wp_import import fetch_wp_users, import_users


class Command(BaseCommand):
    help = "Create or update one auth user per wp_users row. Safe to re-run."

    def handle(self, *args, **options):
        counts = import_users(fetch_wp_users())
        self.stdout.write(f"created {counts['created']}, updated {counts['updated']}")
