from django.shortcuts import redirect, render, get_object_or_404
from .models import Candidate, Category, Contact, Gallery, Nominated_Brand, Nomination_visiblility, Shop, \
    Vote_visiblility, Event, Vote, VotePurchase, Voter, HomeSlider, SiteConfig
from django.contrib import messages
from django.core.paginator import Paginator
from datetime import date
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
import requests
import json
import uuid
import hashlib
from decimal import Decimal, InvalidOperation
import hmac
from django.conf import settings
from django.db import transaction
from django.db.models import Sum, F
from django.http import JsonResponse, HttpResponseBadRequest,HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt
todays_date = date.today()

def _tally_purchase_votes(purchase: VotePurchase):
    """
    Idempotently add this purchase's votes to each candidate's denormalized vote_count.
    Assumes provisional Vote rows were created at init and should be counted only once,
    when the purchase moves to SUCCESS.
    """
    # Aggregate total votes per candidate within this purchase
    rows = (
        purchase.votes
                .values("candidate")
                .annotate(total=Sum("quantity"))
    )
    for row in rows:
        Candidate.objects.filter(pk=row["candidate"]).update(
            vote_count=F("vote_count") + row["total"]
        )





# Create your views here.
def home(request):
    shop = Shop.objects.filter(best_selling_product=True)
    sliders = HomeSlider.objects.filter(is_active=True).order_by("order")
    return render(request, "home.html", {"shop": shop, "sliders": sliders})
def contact(request):
    if request.method=='POST':
        name=request.POST['name']
        email=request.POST['email']
        phone=request.POST['phone']
        subject=request.POST['subject']
        message=request.POST['message']
        contact=Contact(name=name, email=email, phone=phone, subject=subject, message=message)
        contact.save()
        return render(request, 'thankyou.html')
    return render(request, 'contact.html')

def about(request):
    return render(request, 'about.html')


def shop(request):
    search_query = request.GET.get('q', '')
    if search_query:
        shop_items = Shop.objects.filter(name__icontains=search_query)
    else:
        shop_items = Shop.objects.all()

    paginator = Paginator(shop_items, 9)  # 9 items per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'shop.html', {'shop': page_obj, 'search_query': search_query})

def gallery(request):
    images=Gallery.objects.all()
    return render(request, 'gallery.html', {'images':images})

def coming_soon(request):
    return render(request, 'coming-soon.html')

def swfw_portal(request):
    config = SiteConfig.get_solo()
    vote_link = config.vote_url if config.vote_url else None
    return render(request, "vote.html", {"vote_link": vote_link})

def dashboard(request):
    if request.user.is_authenticated and request.user.is_staff:
        nomination_status=Nomination_visiblility.objects.all().first()
        election_status=Vote_visiblility.objects.all().first()
        categories=Category.objects.all()
        return render(request, 'dahsboard2.html',{'nomination_status':nomination_status,'election_status':election_status,'categories':categories})
    else:
        return redirect('login')


def login(request):
    if request.method=='POST':
        username=request.POST['username']
        password=request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_staff:
            auth_login(request, user)
            return redirect('dashboard')

        else:
            messages.info(request,'incorrect credentials')
            return render(request, 'login.html')
    return render(request, 'login.html')

def modify_nomination_status(request,id):
    if id==1:
        Nomination_visiblility.objects.all().delete()
        Nomination_visiblility_save=Nomination_visiblility(visibility=True)
        Nomination_visiblility_save.save()
        messages.info(request, f'Nomination page is now available for {todays_date.year}')
        return redirect('dashboard')
    else:
        Nomination_visiblility.objects.all().delete()
        Nomination_visiblility_save=Nomination_visiblility(visibility=False)
        Nomination_visiblility_save.save()
        messages.info(request, f'Nomination page has been closed for {todays_date.year}')
        return redirect('dashboard')


def election_status(request,id):
    if id==1:
        Vote_visiblility.objects.all().delete()
        Vote_visiblility_save=Vote_visiblility(visibility=True)
        Nomination_visiblility.objects.all().delete()
        Nomination_visiblility_save=Nomination_visiblility(visibility=False)
        Nomination_visiblility_save.save()
        Vote_visiblility_save.save()
        messages.info(request, f'Voting page is now available for {todays_date.year}')
        return redirect('dashboard')
    else:
        Vote_visiblility.objects.all().delete()
        Vote_visiblility_save=Vote_visiblility(visibility=False)
        Vote_visiblility_save.save()
        messages.info(request, f'Voting page has been closed for {todays_date.year}')
        return redirect('dashboard')





def nomination_result(request):
    category_id=request.POST['category_id']
    category=Category.objects.get(pk=category_id)
    print(category)
    nominated_brands=Nominated_Brand.objects.filter(category=category.name)
    print(nominated_brands)
    return render(request,'nomination_result.html',{'nominated_brands':nominated_brands})

def choose_category(request):
    if request.method=="POST":
        if Vote_visiblility.objects.all().first().visibility:
            category=Category.objects.filter(pk=request.POST['category']).first()
            candidates=Candidate.objects.filter(category=category)
            return render(request,'candidates.html',{'candidates':candidates,'category':category})

        else:
            return redirect('coming_soon')

    else:
        if Vote_visiblility.objects.all().first().visibility:
            categories=Category.objects.all()
            return render(request, 'choose_category.html',{'categories':categories})
        else:
            return redirect('coming_soon')

def vote_page(request,id):
    if request.method=="POST":
        pass
    candidate=Candidate.objects.get(pk=id)
    return render(request,'vote_page.html',{'candidate':candidate})


def event_detail(request, slug):
    # Only show if published; 404 otherwise
    event = get_object_or_404(Event, slug=slug, is_published=True)

    now = timezone.now()
    has_started = event.start_at <= now
    has_ended = now > event.end_at
    is_active = event.is_live  # already checks published + within window

    # Build a lightweight structure for modal (categories + candidates)
    categories_payload = []
    qs = (
        event.categories
        .select_related("event")
        .prefetch_related("candidates")
        .all()
    )
    for cat in qs:
        categories_payload.append({
            "id": str(cat.id),
            "name": cat.name,
            "slug": cat.slug,
            "candidates": [
                {
                    "id": str(c.id),
                    "name": c.name,
                    "slug": c.slug,
                    "photo": (c.photo.url if getattr(c, "photo", None) else ""),
                } for c in cat.candidates.all()
            ]
        })

    # IMPORTANT: serialize to JSON so the template gets valid JavaScript, not Python reprs
    categories_json = json.dumps(categories_payload)

    context = {
        "event": event,
        "has_started": has_started,
        "has_ended": has_ended,
        "is_active": is_active,
        "categories_payload": categories_payload,  # for <option>s
        "categories_json": json.dumps(categories_payload),  # for JS
    }
    return render(request, "events/detail.html", context)

def _client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")

def _unique_reference(prefix="EVT"):
    # Short, unique, Paystack-safe reference
    base = uuid.uuid4().hex[:12].upper()
    return f"{prefix}_{base}"

@require_POST
@csrf_exempt  # remove this if you include the CSRF token in your fetch()
def vote_checkout_init(request, slug):
    """
    Initialize a Paystack payment for casting votes.
    Body: JSON {
      "category_id": "...", "candidate_id": "...",
      "votes": 10,
      "email": "user@example.com", "name": "Jane", "phone": "+234..."
    }
    """
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON")

    category_id = str(payload.get("category_id") or "").strip()
    candidate_id = str(payload.get("candidate_id") or "").strip()
    votes_raw = payload.get("votes")
    email = (payload.get("email") or "").strip()
    name = (payload.get("name") or "").strip()
    phone = (payload.get("phone") or "").strip()

    # Basic validation
    if not category_id or not candidate_id:
        return JsonResponse({"ok": False, "error": "Category and candidate are required."}, status=400)
    try:
        votes = int(votes_raw)
        if votes < 1:
            raise ValueError
    except Exception:
        return JsonResponse({"ok": False, "error": "Votes must be an integer >= 1."}, status=400)

    # Event must be published and live
    event = get_object_or_404(Event, slug=slug, is_published=True)
    now = timezone.now()
    if not (event.start_at <= now <= event.end_at):
        return JsonResponse({"ok": False, "error": "Voting is not active for this event."}, status=400)

    # Category & candidate must belong to this event
    category = get_object_or_404(Category, id=category_id, event=event)
    candidate = get_object_or_404(Candidate, id=candidate_id, category=category)

    # Server-side amount calculation (authoritative)
    try:
        unit = Decimal(event.vote_unit_price)
        amount = (unit * votes).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError):
        return JsonResponse({"ok": False, "error": "Cannot compute amount."}, status=400)

    # Create/attach a voter profile (guest-friendly)
    voter = None
    if email or name or phone:
        voter = Voter.objects.create(
            name=name[:180],
            email=email[:180],
            phone=phone[:50],
        )

    # Create purchase + provisional vote (safe: counts only when status=success)
    with transaction.atomic():
        ref = _unique_reference(prefix="VOTE")
        purchase = VotePurchase.objects.create(
            event=event,
            voter=voter,
            gateway=VotePurchase.Gateway.PAYSTACK,
            status=VotePurchase.Status.PENDING,
            currency=event.currency,
            amount=amount,
            reference=ref,
            ip_address=_client_ip(request),
        )

        # Provisional vote row; will only be tallied after success
        Vote.objects.create(
            purchase=purchase,
            candidate=candidate,
            quantity=votes,
        )

    # Payload for Paystack checkout (amount must be in *kobo*)
    amount_kobo = int((amount * 100).to_integral_value())

    # Minimal email requirement for Paystack – fallback if none
    checkout_email = email or "guest@noemail.local"

    resp = {
        "ok": True,
        "reference": purchase.reference,
        "amount": str(amount),          # human-readable
        "amount_kobo": amount_kobo,     # Paystack expects this
        "currency": event.currency,
        "email": checkout_email,
        "public_key": settings.PAYSTACK_PUBLIC_KEY,
        # Pass context along in Paystack metadata for later verification
        "metadata": {
            "event_id": str(event.id),
            "event_slug": event.slug,
            "category_id": str(category.id),
            "candidate_id": str(candidate.id),
            "votes": votes,
            "purchase_id": str(purchase.id),
        },
    }
    return JsonResponse(resp, status=201)



@require_POST
def paystack_verify(request):
    """
    Verify Paystack payment after checkout.
    Expected payload: { "reference": "VOTE_XXXXXXX" }
    """
    import json
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)

    reference = data.get("reference")
    if not reference:
        return JsonResponse({"ok": False, "error": "Missing reference"}, status=400)

    secret_key = getattr(settings, "PAYSTACK_SECRET_KEY", None)
    if not secret_key:
        return JsonResponse({"ok": False, "error": "Missing Paystack secret key"}, status=500)

    url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers = {"Authorization": f"Bearer {secret_key}"}
    r = requests.get(url, headers=headers)

    if r.status_code != 200:
        return JsonResponse({"ok": False, "error": "Failed to verify with Paystack"}, status=r.status_code)

    resp = r.json()
    if not resp.get("status"):
        return JsonResponse({"ok": False, "error": resp.get("message", "Verification failed")}, status=400)

    data = resp.get("data", {})
    status = data.get("status")
    amount_paid = data.get("amount") / 100  # Paystack returns kobo

    try:
        with transaction.atomic():
            vp = VotePurchase.objects.select_for_update().get(reference=reference)
            was_success = (vp.status == VotePurchase.Status.SUCCESS)

            if status == "success":
                if vp.status == VotePurchase.Status.PENDING:
                    vp.status = VotePurchase.Status.SUCCESS
                    vp.paid_at = timezone.now()
                    vp.provider_txn_id = str(data.get("id"))
                    vp.save(update_fields=["status", "paid_at", "provider_txn_id"])
                    # Tally once on first transition to SUCCESS
                    _tally_purchase_votes(vp)
                # Idempotent OK
                return JsonResponse({"ok": True, "verified": True, "amount": amount_paid})
            else:
                if not was_success:
                    vp.status = VotePurchase.Status.FAILED
                    vp.save(update_fields=["status"])
                return JsonResponse({"ok": True, "verified": False, "message": status})
    except VotePurchase.DoesNotExist:
        return JsonResponse({"ok": False, "error": "No matching VotePurchase"}, status=404)


WEBHOOK_DEBUG_URL = "https://webhook.site/3dac193d-92b9-4c67-b6ff-9f7987ec45f2"
WEBHOOK_TIMEOUT = 5  # seconds


@csrf_exempt
@require_POST
def paystack_webhook(request):
    tally_executed = False  # ✅ prevent undefined errors later

    # 1) Signature check
    signature = request.headers.get("x-paystack-signature") or request.META.get("HTTP_X_PAYSTACK_SIGNATURE")
    if not signature:
        return HttpResponse("Missing signature", status=401)

    secret = settings.PAYSTACK_SECRET_KEY
    raw = request.body
    computed = hmac.new(secret.encode(), raw, hashlib.sha512).hexdigest()
    if not hmac.compare_digest(computed, signature):
        return HttpResponse("Invalid signature", status=401)

    # 2) Parse JSON safely
    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception:
        try:
            requests.post(WEBHOOK_DEBUG_URL, json={
                "stage": "bad_json",
                "raw": raw.decode("utf-8", errors="replace")[:4000],
                "headers": {k: v for k, v in request.headers.items() if k.lower() not in ["authorization", "cookie"]},
                "timestamp": timezone.now().isoformat()
            }, timeout=WEBHOOK_TIMEOUT)
        except:
            pass
        return HttpResponse("Bad JSON", status=400)

    # 3) Debug: log received payload
    try:
        requests.post(WEBHOOK_DEBUG_URL, json={
            "stage": "received",
            "event": payload.get("event"),
            "incoming_payload": payload,
            "headers": {k: v for k, v in request.headers.items() if k.lower() not in ["authorization", "cookie"]},
            "timestamp": timezone.now().isoformat()
        }, timeout=WEBHOOK_TIMEOUT)
    except:
        pass

    # 4) Only allow charge.success
    if payload.get("event") != "charge.success":
        try:
            requests.post(WEBHOOK_DEBUG_URL, json={
                "stage": "ignored_event",
                "event": payload.get("event"),
                "timestamp": timezone.now().isoformat()
            }, timeout=WEBHOOK_TIMEOUT)
        except:
            pass
        return JsonResponse({"ok": True, "ignored": payload.get("event")})

    data = payload.get("data") or {}
    reference = data.get("reference")
    if not reference:
        try:
            requests.post(WEBHOOK_DEBUG_URL, json={
                "stage": "missing_reference",
                "incoming_payload": payload,
                "timestamp": timezone.now().isoformat()
            }, timeout=WEBHOOK_TIMEOUT)
        except:
            pass
        return HttpResponse("No reference", status=400)

    # 5) DB lookup + update (must be inside transaction for select_for_update)
    try:
        with transaction.atomic():
            purchase = VotePurchase.objects.select_for_update().get(reference=reference)

            before = {
                "reference": purchase.reference,
                "status": purchase.status,
                "amount": str(purchase.amount),
                "currency": purchase.currency,
                "votes": getattr(purchase, "votes", None),
                "candidate_id": str(getattr(purchase, "candidate_id", None)),
                "paid_at": str(purchase.paid_at) if purchase.paid_at else None,
            }

            # 6) Idempotency: already successful
            if purchase.status == VotePurchase.Status.SUCCESS:
                try:
                    requests.post(WEBHOOK_DEBUG_URL, json={
                        "stage": "idempotent_already_success",
                        "reference": reference,
                        "before": before,
                        "timestamp": timezone.now().isoformat()
                    }, timeout=WEBHOOK_TIMEOUT)
                except:
                    pass
                return JsonResponse({"ok": True, "idempotent": True})

            # 7) Validate amount & currency
            try:
                ps_amount_kobo = int(data.get("amount") or 0)
            except:
                ps_amount_kobo = 0

            ps_currency = (data.get("currency") or "").upper()
            expected_kobo = int(Decimal(purchase.amount) * 100)

            if ps_amount_kobo != expected_kobo:
                try:
                    requests.post(WEBHOOK_DEBUG_URL, json={
                        "stage": "amount_mismatch",
                        "reference": reference,
                        "ps_amount_kobo": ps_amount_kobo,
                        "expected_kobo": expected_kobo,
                        "incoming_payload": payload,
                        "before": before,
                        "timestamp": timezone.now().isoformat()
                    }, timeout=WEBHOOK_TIMEOUT)
                except:
                    pass
                return HttpResponse("Amount mismatch", status=400)

            if purchase.currency.upper() != ps_currency:
                try:
                    requests.post(WEBHOOK_DEBUG_URL, json={
                        "stage": "currency_mismatch",
                        "reference": reference,
                        "ps_currency": ps_currency,
                        "expected_currency": purchase.currency,
                        "incoming_payload": payload,
                        "before": before,
                        "timestamp": timezone.now().isoformat()
                    }, timeout=WEBHOOK_TIMEOUT)
                except:
                    pass
                return HttpResponse("Currency mismatch", status=400)

            # 8) Mark success
            purchase.status = VotePurchase.Status.SUCCESS
            purchase.paid_at = timezone.now()
            purchase.provider_txn_id = str(data.get("id") or "")
            purchase.save(update_fields=["status", "paid_at", "provider_txn_id"])

            # 9) Tally votes
            _tally_purchase_votes(purchase)
            tally_executed = True

            after = {
                "reference": purchase.reference,
                "status": purchase.status,
                "amount": str(purchase.amount),
                "currency": purchase.currency,
                "votes": getattr(purchase, "votes", None),
                "candidate_id": str(getattr(purchase, "candidate_id", None)),
                "paid_at": str(purchase.paid_at) if purchase.paid_at else None,
            }

    except VotePurchase.DoesNotExist:
        try:
            requests.post(WEBHOOK_DEBUG_URL, json={
                "stage": "purchase_missing",
                "reference": reference,
                "incoming_payload": payload,
                "timestamp": timezone.now().isoformat()
            }, timeout=WEBHOOK_TIMEOUT)
        except:
            pass
        return JsonResponse({"ok": True, "missing": True})

    except Exception as exc:
        try:
            requests.post(WEBHOOK_DEBUG_URL, json={
                "stage": "processing_error",
                "reference": reference,
                "error": str(exc),
                "timestamp": timezone.now().isoformat()
            }, timeout=WEBHOOK_TIMEOUT)
        except:
            pass
        return HttpResponse("Internal error", status=500)

    # 10) Final success debug log
    try:
        requests.post(WEBHOOK_DEBUG_URL, json={
            "stage": "processed",
            "reference": reference,
            "before": before,
            "after": after,
            "tally_executed": bool(tally_executed),
            "incoming_payload": payload,
            "timestamp": timezone.now().isoformat()
        }, timeout=WEBHOOK_TIMEOUT)
    except:
        pass

    return JsonResponse({"ok": True, "verified": True, "reference": reference})


SESSION_KEY = "candidate_portal"  # will store {"event_id": "...", "email": "..."}

def _event_scoped_session_ok(request, event):
    data = request.session.get(SESSION_KEY) or {}
    return str(data.get("event_id")) == str(event.id) and (data.get("email") or "")

def _require_portal_session(view_func):
    def wrapper(request, event_slug, *args, **kwargs):
        event = get_object_or_404(Event, slug=event_slug, is_published=True)
        if not _event_scoped_session_ok(request, event):
            messages.warning(request, "Please sign in to view your results.")
            return redirect("candidate_login", event_slug=event.slug)
        request._portal_event = event  # attach for downstream access
        return view_func(request, event_slug, *args, **kwargs)
    return wrapper

@require_http_methods(["GET", "POST"])
def candidate_login(request, event_slug):
    event = get_object_or_404(Event, slug=event_slug, is_published=True)

    if request.method == "GET":
        return render(request, "events/candidate_login.html", {"event": event})

    # POST
    email = (request.POST.get("email") or "").strip().lower()
    password = (request.POST.get("password") or "")

    # Find matching candidates for this event by email
    qs = Candidate.objects.filter(
        email__iexact=email,
        category__event=event
    )

    if not qs.exists():
        messages.error(request, "Invalid credentials.")  # generic
        return render(request, "events/candidate_login.html", {"event": event, "email": email})

    # Check password against any of the records in this event (same email might have multiple candidates)
    if not any(c.check_password(password) for c in qs):
        messages.error(request, "Invalid credentials.")  # generic
        return render(request, "events/candidate_login.html", {"event": event, "email": email})

    # OK -> store session (scoped to event)
    request.session[SESSION_KEY] = {"event_id": str(event.id), "email": email, "ts": timezone.now().isoformat()}
    request.session.modified = True
    return redirect("candidate_results", event_slug=event.slug)

@_require_portal_session
def candidate_results(request, event_slug):
    event = request._portal_event
    email = request.session.get(SESSION_KEY, {}).get("email")

    # All candidates within this event for this email
    candidates = Candidate.objects.filter(
        email__iexact=email, category__event=event
    ).select_related("category", "category__event")

    # For each candidate, total successful votes
    stats = []
    for c in candidates:
        total = (
            Vote.objects.filter(
                candidate=c,
                purchase__status=VotePurchase.Status.SUCCESS
            ).aggregate(total=Sum("quantity"))["total"] or 0
        )
        stats.append({"candidate": c, "total_votes": total})

    context = {
        "event": event,
        "email": email,
        "rows": stats,
    }
    return render(request, "events/candidate_results.html", context)

@require_http_methods(["POST"])
def candidate_logout(request, event_slug):
    # Clear only our portal session info (don’t clobber user auth session etc.)
    if SESSION_KEY in request.session:
        del request.session[SESSION_KEY]
        request.session.modified = True
    messages.success(request, "You’ve been signed out.")
    return redirect("candidate_login", event_slug=event_slug)

