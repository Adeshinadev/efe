from django.contrib import admin
from .models import *

from django.contrib import admin, messages
from django.db.models import Sum, Q
from django.utils import timezone
from django import forms
from django.http import HttpResponseRedirect
from django.urls import reverse
from .models import (
    Event,
    Category,
    Candidate,
    Voter,
    VotePurchase,
    Vote,
    PaymentWebhookEvent,
)

# Register your models here.
admin.site.register(Contact)
admin.site.register(Shop)
admin.site.register(Gallery)
# admin.site.register(Nominee)
# admin.site.register(Nominated_Brand)
# admin.site.register(Nomination_visiblility)
# admin.site.register(Vote_visiblility)


# admin.py
import uuid
from decimal import Decimal



# ---------------------------
# Inline configs
# ---------------------------

class CategoryInline(admin.TabularInline):
    model = Category
    fk_name = "event"
    extra = 0
    # The `event` FK is provided by the parent EventAdmin automatically; exclude it from the inline form
    fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    show_change_link = True


class CandidateInline(admin.TabularInline):
    model = Candidate
    extra = 0
    autocomplete_fields = ["category"]
    fields = ("name", "slug", "photo", "vote_count")
    readonly_fields = ("vote_count",)
    prepopulated_fields = {"slug": ("name",)}
    show_change_link = True


class VoteInline(admin.TabularInline):
    model = Vote
    extra = 0
    autocomplete_fields = ["candidate"]
    fields = ("candidate", "quantity", "created_at")
    readonly_fields = ("created_at",)


# ---------------------------
# Actions
# ---------------------------

@admin.action(description="Publish selected events")
def publish_events(modeladmin, request, queryset):
    updated = queryset.update(is_published=True)
    messages.success(request, f"{updated} event(s) published.")


@admin.action(description="Unpublish selected events")
def unpublish_events(modeladmin, request, queryset):
    updated = queryset.update(is_published=False)
    messages.success(request, f"{updated} event(s) unpublished.")


@admin.action(description="Mark selected purchases as SUCCESS (paid now)")
def mark_purchases_success(modeladmin, request, queryset):
    updated = queryset.update(status=VotePurchase.Status.SUCCESS, paid_at=timezone.now())
    messages.success(request, f"{updated} purchase(s) marked as SUCCESS.")


@admin.action(description="Recalculate vote_count for selected candidates")
def recalc_candidate_vote_counts(modeladmin, request, queryset):
    # Recompute from Vote table per candidate
    affected = 0
    for candidate in queryset:
        total = Vote.objects.filter(
            candidate=candidate,
            purchase__status=VotePurchase.Status.SUCCESS
        ).aggregate(total=Sum("quantity"))["total"] or 0
        if candidate.vote_count != total:
            candidate.vote_count = total
            candidate.save(update_fields=["vote_count", "updated_at"])
            affected += 1
    messages.success(request, f"Recalculated vote_count for {affected} candidate(s).")


# ---------------------------
# Model admins
# ---------------------------

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "title", "slug", "is_published", "is_live", "start_at", "end_at", "total_votes_display", "created_at",
    )
    list_filter = ("is_published", ("start_at", admin.DateFieldListFilter), ("end_at", admin.DateFieldListFilter))
    search_fields = ("title", "slug", "description")
    date_hierarchy = "start_at"
    readonly_fields = ("created_at", "updated_at", "id", "total_votes_display", "is_live_display")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [CategoryInline]
    actions = [publish_events, unpublish_events]

    fieldsets = (
        (None, {
            "fields": ("title", "slug", "description", "banner_image")
        }),
        ("Schedule & Visibility", {
            "fields": ("is_published", "start_at", "end_at", "is_live_display")
        }),
        ("Payments", {
            "fields": ("currency", "vote_unit_price")
        }),
        ("Ownership", {
            "fields": ("owner",)
        }),
        ("System", {
            "classes": ("collapse",),
            "fields": ("id", "created_at", "updated_at", "total_votes_display"),
        }),
    )

    @admin.display(description="Total votes", ordering=False)
    def total_votes_display(self, obj):
        return obj.total_votes

    @admin.display(description="Is live now?", boolean=True)
    def is_live_display(self, obj):
        return obj.is_live


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "event", "slug", "created_at")
    list_filter = ("event",)
    search_fields = ("name", "slug", "event__title")
    autocomplete_fields = ("event",)
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at", "id")
    inlines = [CandidateInline]

    fieldsets = (
        (None, {
            "fields": ("event", "name", "slug")
        }),
        ("System", {
            "classes": ("collapse",),
            "fields": ("id", "created_at", "updated_at"),
        }),
    )


class CandidateAdminForm(forms.ModelForm):
    # write-only password field
    new_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="Set or reset candidate portal password. Leave blank to keep current."
    )
    confirm_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        label="Confirm password"
    )

    class Meta:
        model = Candidate
        fields = ("name", "email", "phone_number", "year", "category", "photo", "new_password", "confirm_password")

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("new_password") or ""
        p2 = cleaned.get("confirm_password") or ""
        if p1 or p2:
            if p1 != p2:
                raise forms.ValidationError("Passwords do not match.")
            if len(p1) < 6:
                raise forms.ValidationError("Password must be at least 6 characters.")
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        p1 = self.cleaned_data.get("new_password")
        if p1:
            obj.set_password(p1)
        if commit:
            obj.save()
        return obj

@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    form = CandidateAdminForm
    list_display = ("name", "category", "email", "vote_count")
    list_filter = ("category__event", "category")
    search_fields = ("name", "email", "category__name", "category__event__title")


    @admin.display(description="Event")
    def event_title(self, obj):
        try:
            return obj.category.event.title
        except Exception:
            return "—"


@admin.register(Voter)
class VoterAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "phone", "country", "user", "created_at")
    search_fields = ("name", "email", "phone", "user__username", "user__email")
    list_filter = ("country",)
    readonly_fields = ("created_at", "updated_at", "id")
    autocomplete_fields = ("user",)


@admin.register(VotePurchase)
class VotePurchaseAdmin(admin.ModelAdmin):
    list_display = (
        "reference", "event", "voter", "gateway", "status", "currency", "amount", "total_votes_display", "paid_at", "created_at"
    )
    list_filter = ("status", "gateway", "currency", ("paid_at", admin.DateFieldListFilter), "event")
    search_fields = ("reference", "provider_txn_id", "voter__name", "voter__email", "event__title")
    autocomplete_fields = ("event", "voter")
    readonly_fields = ("created_at", "updated_at", "id", "total_votes_display")
    inlines = [VoteInline]
    actions = [mark_purchases_success]

    fieldsets = (
        (None, {
            "fields": ("event", "voter")
        }),
        ("Payment", {
            "fields": ("gateway", "status", "currency", "amount", "reference", "provider_txn_id", "ip_address", "paid_at")
        }),
        ("Votes", {
            "fields": ("total_votes_display",)
        }),
        ("System", {
            "classes": ("collapse",),
            "fields": ("id", "created_at", "updated_at"),
        }),
    )

    @admin.display(description="Total votes", ordering=False)
    def total_votes_display(self, obj):
        return obj.total_votes


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ("candidate", "purchase", "quantity", "created_at")
    list_filter = ("candidate__category__event", "candidate__category",)
    search_fields = ("candidate__name", "purchase__reference")
    autocomplete_fields = ("purchase", "candidate")
    readonly_fields = ("created_at", "updated_at", "id")

    fieldsets = (
        (None, {
            "fields": ("purchase", "candidate", "quantity")
        }),
        ("System", {
            "classes": ("collapse",),
            "fields": ("id", "created_at", "updated_at"),
        }),
    )


@admin.register(PaymentWebhookEvent)
class PaymentWebhookEventAdmin(admin.ModelAdmin):
    list_display = ("gateway", "event_type", "reference", "processed", "received_at")
    list_filter = ("gateway", "processed", "event_type", ("received_at", admin.DateFieldListFilter))
    search_fields = ("gateway", "event_type", "reference")
    readonly_fields = ("id", "created_at", "updated_at", "received_at", "payload")

    fieldsets = (
        (None, {
            "fields": ("gateway", "event_type", "reference", "processed")
        }),
        ("Payload", {
            "fields": ("payload",)
        }),
        ("System", {
            "classes": ("collapse",),
            "fields": ("id", "received_at", "created_at", "updated_at"),
        }),
    )


@admin.register(HomeSlider)
class HomeSliderAdmin(admin.ModelAdmin):
    list_display = ("alt_text", "order", "is_active")
    list_editable = ("order", "is_active")
    ordering = ("order",)

@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
    list_display = ("vote_url",)

    def has_add_permission(self, request):
        # Prevent adding a second config
        return not SiteConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # Prevent deleting the config
        return False

    def changelist_view(self, request, extra_context=None):
        # When you click “Site Config”, go straight to the edit form
        obj = SiteConfig.get_solo()
        return HttpResponseRedirect(
            reverse(f"admin:{obj._meta.app_label}_{obj._meta.model_name}_change", args=[obj.pk])
        )