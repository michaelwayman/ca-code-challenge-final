from django.core.management.base import BaseCommand

from catalog.wp_import import fetch_source, import_source

COLUMNS = ("created", "updated", "unchanged", "skipped")


class Command(BaseCommand):
    help = "Create or update brands, reviews, industries and reviewers from WP. Safe to re-run."

    def handle(self, *args, **options):
        counts = import_source(fetch_source())
        for name, c in counts.items():
            self.stdout.write(f"{name}: " + ", ".join(f"{col} {c[col]}" for col in COLUMNS))
