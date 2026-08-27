"""Remove Download rows whose expires_at is in the past.

Deletes the on-disk file first, then the DB row. Rows without an
expires_at are treated as "keep forever" and left alone.

Wire this to cron or celery-beat, e.g. daily at 03:15:

    15 3 * * *  cd /srv/app && python manage.py cleanup_expired_downloads

Idempotent -- safe to re-run.
"""
import os

from django.core.management.base import BaseCommand
from django.utils import timezone

from reporting.models import Download


class Command(BaseCommand):
    help = "Delete Download rows (and their on-disk files) whose expires_at has passed."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be deleted without touching anything.",
        )

    def handle(self, *args, **opts):
        now = timezone.now()
        qs = Download.objects.filter(expires_at__lt=now)
        total = qs.count()
        if total == 0:
            self.stdout.write("No expired downloads.")
            return

        removed_files = 0
        removed_rows = 0
        for dl in qs.iterator():
            path = dl.file_path
            if opts["dry_run"]:
                self.stdout.write(f"would delete: {dl.fingerprint} ({path})")
                continue
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                    removed_files += 1
                except OSError as exc:
                    self.stderr.write(f"could not remove {path}: {exc}")
            dl.delete()
            removed_rows += 1

        if opts["dry_run"]:
            self.stdout.write(f"dry-run: {total} rows would be deleted.")
        else:
            self.stdout.write(
                f"Deleted {removed_rows} rows and {removed_files} files."
            )
