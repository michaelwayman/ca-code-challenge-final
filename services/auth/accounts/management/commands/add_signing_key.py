from argparse import ArgumentParser

from django.core.management.base import BaseCommand

from accounts import keys


class Command(BaseCommand):
    help = "Generate a new RSA signing key; it signs new tokens, older keys stay in the JWKS."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--if-none", action="store_true", help="Only generate when no key exists yet."
        )

    def handle(self, *args: object, if_none: bool = False, **options: object) -> None:
        if if_none and keys.load_keys():
            self.stdout.write(f"active key {keys.active_key().kid}")
            return
        self.stdout.write(f"added key {keys.add_key()}")
