from django.core.management.base import BaseCommand

from accounts import keys


class Command(BaseCommand):
    help = "Create the RSA signing key if it does not exist yet (safe to run on every start)."

    def handle(self, *args, **options):
        created = keys.ensure_key()
        self.stdout.write(f"{'created' if created else 'kept'} key {keys.signing_key().kid}")
