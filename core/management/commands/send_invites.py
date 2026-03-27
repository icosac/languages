from __future__ import annotations

from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from core.invitations import issue_invite
from core.mailjet import build_invite_url, send_invite_email


class Command(BaseCommand):
    help = "Create and send invitation emails via Mailjet"

    def add_arguments(self, parser):
        parser.add_argument(
            "--emails",
            type=str,
            default="",
            help="Comma-separated email list.",
        )
        parser.add_argument(
            "--file",
            type=str,
            default="",
            help="Path to file with one email per line.",
        )
        parser.add_argument(
            "--invited-by",
            type=str,
            default="",
            help="Username of inviter (optional).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Create no records and send no emails.",
        )

    def handle(self, *args, **options):
        emails = set()
        if options["emails"]:
            emails.update(
                email.strip().lower()
                for email in options["emails"].split(",")
                if email.strip()
            )
        if options["file"]:
            file_path = Path(options["file"])
            if not file_path.exists():
                raise CommandError(f"File does not exist: {file_path}")
            emails.update(
                line.strip().lower()
                for line in file_path.read_text().splitlines()
                if line.strip()
            )

        if not emails:
            raise CommandError("Provide at least one email using --emails or --file.")

        inviter = None
        if options["invited_by"]:
            inviter = get_user_model().objects.filter(
                username=options["invited_by"].strip()
            ).first()
            if inviter is None:
                raise CommandError("--invited-by user not found.")

        for email in sorted(emails):
            if options["dry_run"]:
                self.stdout.write(self.style.WARNING(f"[dry-run] would invite {email}"))
                continue

            invite, raw_token = issue_invite(email=email, invited_by=inviter)
            invite_url = build_invite_url(raw_token)
            try:
                send_invite_email(recipient_email=email, invite_url=invite_url)
            except Exception as exc:
                self.stderr.write(self.style.ERROR(f"failed {email}: {exc}"))
                continue

            self.stdout.write(self.style.SUCCESS(f"sent {email} (invite id={invite.id})"))
