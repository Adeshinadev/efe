from django.core.management.base import BaseCommand
from django.db.models import Max
from pages.models import Event, Category, Candidate  # update path as needed


class Command(BaseCommand):
    help = "Print a numbered list of all categories and their winners."

    def handle(self, *args, **options):
        events = Event.objects.all().order_by("title")

        if not events.exists():
            self.stdout.write("No events found.")
            return

        for event in events:
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS(f"=== EVENT: {event.title} ===\n"))

            categories = event.categories.all().order_by("name")

            if not categories.exists():
                self.stdout.write("No categories for this event.\n")
                continue

            for idx, category in enumerate(categories, start=1):
                candidates = category.candidates.all()

                # No candidates
                if not candidates.exists():
                    self.stdout.write(f"{idx}. {category.name} – No candidates")
                    continue

                # Determine highest votes
                max_votes = candidates.aggregate(Max("vote_count"))["vote_count__max"]

                # No votes
                if not max_votes or max_votes == 0:
                    self.stdout.write(f"{idx}. {category.name} – No votes cast")
                    continue

                # Possible tie
                winners = candidates.filter(vote_count=max_votes)

                if winners.count() == 1:
                    winner = winners.first()
                    self.stdout.write(
                        f"{idx}. {category.name} – {winner.name} ({winner.vote_count} votes)"
                    )
                else:
                    # Tie
                    names = ", ".join([w.name for w in winners])
                    self.stdout.write(
                        f"{idx}. {category.name} – TIE between: {names} ({max_votes} votes each)"
                    )
