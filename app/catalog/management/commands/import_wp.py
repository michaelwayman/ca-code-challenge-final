from django.core.management.base import BaseCommand

from catalog.wp_import import import_source
from catalog.wp_source import fetch_source

COLUMNS = ("created", "updated", "unchanged", "deleted", "skipped")


class Command(BaseCommand):
    help = "Create or update brands, reviews, industries and reviewers from WP. Safe to re-run."

    def handle(self, *args, **options):
        counts = import_source(fetch_source())
        for name, c in counts.items():
            self.stdout.write(f"{name}: " + ", ".join(f"{col} {c[col]}" for col in COLUMNS))
