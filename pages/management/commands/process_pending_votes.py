import requests
from decimal import Decimal
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from pages.models import VotePurchase, Vote, Candidate  # adjust import if needed


PAYSTACK_SECRET = settings.PAYSTACK_SECRET_KEY
PAYSTACK_VERIFY_URL = "https://api.paystack.co/transaction/verify/{}"


class Command(BaseCommand):
    help = "Verify pending VotePurchase payments on Paystack and convert them into votes."

    def handle(self, *args, **options):
        pending_purchases = VotePurchase.objects.filter(status=VotePurchase.Status.PENDING)

        if not pending_purchases.exists():
            self.stdout.write(self.style.SUCCESS("✅ No pending votes to process."))
            return

        self.stdout.write(f"🔎 Found {pending_purchases.count()} pending purchases...\n")

        for purchase in pending_purchases:
            reference = purchase.reference
            self.stdout.write(f"➡ Checking {reference}...")

            headers = {
                "Authorization": f"Bearer {PAYSTACK_SECRET}",
                "Content-Type": "application/json",
            }

            try:
                res = requests.get(PAYSTACK_VERIFY_URL.format(reference), headers=headers, timeout=15)
                data = res.json()
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Request error: {e}"))
                continue

            if not data.get("status") or not data.get("data"):
                self.stdout.write(self.style.ERROR(f"❌ Verification failed or no data returned"))
                continue

            tx = data["data"]
            pay_status = tx.get("status")  # "success", "failed", etc

            if pay_status != "success":
                self.stdout.write(self.style.WARNING(f"⚠ Payment not successful ({pay_status}), skipping"))
                continue

            # ✅ Success flow begins
            amount_kobo = Decimal(tx.get("amount", 0))
            amount_naira = amount_kobo / 100  # convert kobo -> NGN
            votes_awarded = int(amount_naira / 100)  # 100 NGN = 1 vote

            if votes_awarded < 1:
                self.stdout.write(self.style.WARNING("⚠ Amount too small to convert into votes, skipping"))
                continue

            # Process safely in DB transaction
            try:
                with transaction.atomic():
                    # Reload row for update lock
                    p = VotePurchase.objects.select_for_update().get(id=purchase.id)

                    if p.status == VotePurchase.Status.SUCCESS:
                        self.stdout.write(self.style.NOTICE("✓ Already credited, skipping"))
                        continue

                    # Update purchase
                    p.status = VotePurchase.Status.SUCCESS
                    p.provider_txn_id = tx.get("id")
                    p.currency = tx.get("currency", "NGN")
                    p.save()

                    # Assign votes to candidates
                    vote_rows = Vote.objects.filter(purchase=p)
                    for vote in vote_rows:
                        candidate = vote.candidate
                        candidate.vote_count = candidate.vote_count + votes_awarded
                        candidate.save(update_fields=["vote_count"])

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✔ Credited {votes_awarded} vote(s) to {vote_rows.count()} candidate(s)"
                        )
                    )

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ DB update failed: {e}"))

        self.stdout.write(self.style.SUCCESS("\n✅ Processing complete."))