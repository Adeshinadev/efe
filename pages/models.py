import uuid
from decimal import Decimal
from django.conf import settings
from django.db import models
from django.db.models import F, Sum
from django.template.defaultfilters import slugify
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password

# Create your models here.
class Contact(models.Model):
    name = models.CharField(max_length=50)
    email = models.EmailField(max_length=100)
    phone = models.CharField(max_length=50)
    subject = models.CharField(max_length=50)
    message = models.TextField()

    def __str__(self):
        return self.name

class Shop(models.Model):
    name = models.CharField(max_length=50)
    image = models.ImageField(upload_to='shop_images')
    best_selling_product=models.BooleanField(default=False)

    def __str__(self):
        return self.name

class Gallery(models.Model):
    image = models.ImageField(upload_to='gallery_images')

    def __str__(self):
        return self.image.name

# class Category(models.Model):
#     name=models.CharField(max_length=500)
#
#     def __str__(self):
#         return self.name


class Nominated_Brand(models.Model):
    name=models.CharField(max_length=100)
    nominated=models.IntegerField(default=1)
    category = models.CharField(max_length=500)
    def __str__(self):
        return self.name+','+self.category+','+ str(self.nominated)


class Nomination_visiblility(models.Model):
    visibility=models.BooleanField(default=False)

    def __str__(self):
        return str(self.visibility)



class Vote_visiblility(models.Model):
    visibility=models.BooleanField(default=False)

    def __str__(self):
        return str(self.visibility)




class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        abstract = True


# --- Core: Events, Categories, Candidates -----------------------------

class Event(TimeStampedModel):
    """
    A public voting event, e.g. "Christmas Vote".
    URL: /events/<slug>/
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=220, unique=True, db_index=True, blank=True)
    description = models.TextField(blank=True)
    banner_image = models.ImageField(upload_to="events/banners/", blank=True, null=True)

    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    is_published = models.BooleanField(default=False)

    # Payments
    currency = models.CharField(max_length=10, default="NGN")
    vote_unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("100.00"))

    # Optional ownership (who created the event)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="owned_events"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    @property
    def is_live(self) -> bool:
        now = timezone.now()
        return self.is_published and self.start_at <= now <= self.end_at

    @property
    def total_votes(self):
        return Vote.objects.filter(purchase__event=self, purchase__status=VotePurchase.Status.SUCCESS) \
                           .aggregate(total=Sum("quantity"))["total"] or 0


class Category(TimeStampedModel):
    """
    Category within an event, e.g. 'Best Costume'.
    URL: /events/<event-slug>/<category-slug>/
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="categories",
        null=True
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=240, db_index=True, blank=True)
    class Meta:
        unique_together = [("event", "slug")]
        ordering = ["name"]

    def __str__(self):
        return f"{self.event.title} • {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Candidate(TimeStampedModel):
    """
    Candidate in a category. Belongs to exactly one category (and therefore one event).
    URL: /events/<event-slug>/<category-slug>/<candidate-slug>/
    """
    password_hash = models.CharField(max_length=128, blank=True)  # NEW
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="candidates")
    name = models.CharField(max_length=300)
    slug = models.SlugField(max_length=340, db_index=True, blank=True)
    email = models.EmailField(max_length=120, blank=True)
    phone_number = models.CharField(max_length=50, blank=True)
    year = models.CharField(max_length=20, blank=True)
    secret_code = models.CharField(max_length=100, unique=True, editable=False)  # now enforced unique
    photo = models.ImageField(upload_to="candidates/photos/", blank=True, null=True)

    vote_count = models.PositiveIntegerField(default=0, db_index=True)

    def set_password(self, raw_password: str):
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password(raw_password, self.password_hash)
    class Meta:
        unique_together = [("category", "slug")]
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.category.name})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if not self.secret_code:
            # Ensure it's unique by looping until we find a non-existing one
            code = str(uuid.uuid4())
            while Candidate.objects.filter(secret_code=code).exists():
                code = str(uuid.uuid4())
            self.secret_code = code
        super().save(*args, **kwargs)

    @property
    def event(self):
        return self.category.event


# --- Voting & Payments -----------------------------------------------

class Voter(TimeStampedModel):
    """
    Optional: store payer identity even without account (guest checkout).
    If you have users, you may also link to AUTH_USER_MODEL.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="voter_profiles"
    )
    name = models.CharField(max_length=180, blank=True)
    email = models.EmailField(max_length=180, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    country = models.CharField(max_length=2, blank=True)  # ISO alpha-2

    def __str__(self):
        return self.name or self.email or str(self.id)


class VotePurchase(TimeStampedModel):
    """
    One payment intent/charge that can carry votes for one candidate.
    If you want to allow splitting a single payment across multiple candidates,
    move candidate to the child 'Vote' rows (already done below).
    """
    class Gateway(models.TextChoices):
        FLUTTERWAVE = "flutterwave", "Flutterwave"
        PAYSTACK = "paystack", "Paystack"
        STRIPE = "stripe", "Stripe"
        MANUAL = "manual", "Manual"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        CANCELED = "canceled", "Canceled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.PROTECT, related_name="purchases")
    voter = models.ForeignKey(Voter, on_delete=models.SET_NULL, null=True, blank=True, related_name="purchases")

    # Payment meta
    gateway = models.CharField(max_length=20, choices=Gateway.choices, default=Gateway.PAYSTACK)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    currency = models.CharField(max_length=10, default="NGN")
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    # Gateway refs
    reference = models.CharField(max_length=120, unique=True, db_index=True)     # your generated ref
    provider_txn_id = models.CharField(max_length=180, blank=True)               # gateway's txn id
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.reference} • {self.status}"

    @property
    def total_votes(self):
        return self.votes.aggregate(total=Sum("quantity"))["total"] or 0


class Vote(TimeStampedModel):
    """
    The atomic vote allocation (after successful payment).
    Kept separate so a single purchase can split votes across multiple candidates.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    purchase = models.ForeignKey(VotePurchase, on_delete=models.CASCADE, related_name="votes")
    candidate = models.ForeignKey(Candidate, on_delete=models.PROTECT, related_name="votes")
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        indexes = [
            models.Index(fields=["candidate"]),
            models.Index(fields=["purchase", "candidate"]),
        ]

    def __str__(self):
        return f"{self.quantity} vote(s) → {self.candidate.name}"


class PaymentWebhookEvent(TimeStampedModel):
    """
    Store the raw payload from payment gateway webhooks for audit/replay.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gateway = models.CharField(max_length=20, choices=VotePurchase.Gateway.choices)
    event_type = models.CharField(max_length=120, db_index=True)
    reference = models.CharField(max_length=120, db_index=True)      # should match VotePurchase.reference
    received_at = models.DateTimeField(auto_now_add=True)
    payload = models.JSONField()

    processed = models.BooleanField(default=False, db_index=True)
    processed_at = models.DateTimeField(null=True, blank=True)


class HomeSlider(models.Model):
    image = models.ImageField(upload_to="banners/")
    alt_text = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]
        verbose_name = "Home Slider"
        verbose_name_plural = "Home Sliders"

    def __str__(self):
        return self.alt_text or f"Slider {self.pk}"

class SiteConfig(models.Model):
    vote_url = models.URLField(blank=True, help_text="Leave blank to hide the Vote button.")

    class Meta:
        verbose_name = "Site Config"
        verbose_name_plural = "Site Config"

    def __str__(self):
        return "Site Configuration (single record)"

    def save(self, *args, **kwargs):
        # Always force single record (pk=1)
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        # Get or create the one and only instance
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj