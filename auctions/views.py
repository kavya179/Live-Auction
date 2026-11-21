"""
Views for the auctions app.

Bidding logic (place_bid) uses:
  - django.db.transaction.atomic()  → all-or-nothing DB write
  - select_for_update()             → row-level lock (advisory on SQLite,
                                      real lock on PostgreSQL)
  - Explicit validation rules:
      1. Auction must be LIVE (status check + time check)
      2. bid amount > current_price
      3. Auction must not be expired at commit time
"""

from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import AuctionItemForm, BidForm, PlaceBidForm, RegisterForm
from .models import Auction, AuctionBid, AuctionItem, Bid, WatchList


def home(request):
    """Homepage - shows live auctions and available auctions."""
    # Update statuses for AuctionItem
    for item in AuctionItem.objects.all():
        item.update_status()

    # Update statuses for Auction
    for auction in Auction.objects.all():
        auction.refresh_status()

    live_auctions = AuctionItem.objects.filter(status='live')[:6]
    upcoming_auctions = AuctionItem.objects.filter(status='upcoming')[:6]
    available_auctions = Auction.objects.all().order_by('-status', '-created_at')[:12]

    return render(request, 'auctions/home.html', {
        'live_auctions': live_auctions,
        'upcoming_auctions': upcoming_auctions,
        'available_auctions': available_auctions,
    })


def auction_list(request):
    """List all auction items with optional filtering."""
    status_filter = request.GET.get('status', 'all')

    # Update statuses
    for item in AuctionItem.objects.all():
        item.update_status()

    items = AuctionItem.objects.all()
    if status_filter in ['live', 'upcoming', 'ended']:
        items = items.filter(status=status_filter)

    return render(request, 'auctions/auction_list.html', {
        'items': items,
        'status_filter': status_filter,
    })


def auction_detail(request, pk):
    """Detail page for a single auction item."""
    item = get_object_or_404(AuctionItem, pk=pk)
    item.update_status()

    bids = item.bids.all().order_by('-amount')[:10]
    bid_form = BidForm()

    is_watching = False
    if request.user.is_authenticated:
        is_watching = WatchList.objects.filter(user=request.user, item=item).exists()

    return render(request, 'auctions/auction_detail.html', {
        'item': item,
        'bids': bids,
        'bid_form': bid_form,
        'is_watching': is_watching,
    })


@login_required
def place_bid(request, pk):
    """
    Handle bid placement on an AuctionItem (auth-based, original flow).

    Bidding rules enforced:
      1. Auction must be in 'live' status.
      2. Bid amount must exceed current_price.
      3. Seller cannot bid on their own item.
      4. Bid + price update executed in a single atomic transaction with
         select_for_update() row-locking so concurrent bids are serialised.
    """
    item = get_object_or_404(AuctionItem, pk=pk)
    item.update_status()          # Rule 1 — sync status from wall-clock time

    if item.status != 'live':
        messages.error(request, "This auction is not currently live.")
        return redirect('auction_detail', pk=pk)

    if request.method != 'POST':
        return redirect('auction_detail', pk=pk)

    form = BidForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Invalid bid — please enter a valid positive number.")
        return redirect('auction_detail', pk=pk)

    bid_amount = form.cleaned_data['amount']

    # Rule 3
    if request.user == item.seller:
        messages.error(request, "You cannot bid on your own item.")
        return redirect('auction_detail', pk=pk)

    try:
        with transaction.atomic():
            # Lock this specific row so no other request can read/write it
            # until we commit.  On PostgreSQL this is a real SELECT … FOR UPDATE;
            # on SQLite it serialises via the write lock.
            locked_item = (
                AuctionItem.objects
                .select_for_update()
                .get(pk=pk)
            )
            locked_item.update_status()      # re-check inside the lock

            # Rule 1 (re-checked inside lock — race-condition safe)
            if locked_item.status != 'live':
                messages.error(request, "This auction closed just before your bid was processed.")
                return redirect('auction_detail', pk=pk)

            # Rule 3 — auction expired mid-request
            if locked_item.is_live() is False:
                messages.error(request, "Bidding has ended for this auction.")
                return redirect('auction_detail', pk=pk)

            # Rule 2 — amount must beat current price
            if bid_amount <= locked_item.current_price:
                messages.error(
                    request,
                    f"Your bid (${bid_amount}) must exceed the current price "
                    f"(${locked_item.current_price})."
                )
                return redirect('auction_detail', pk=pk)

            # All rules passed — persist bid and update price atomically
            Bid.objects.create(
                item=locked_item,
                bidder=request.user,
                amount=bid_amount,
            )
            locked_item.current_price = bid_amount
            locked_item.save(update_fields=['current_price'])

    except Exception as exc:
        messages.error(request, f"Could not process bid: {exc}")
        return redirect('auction_detail', pk=pk)

    messages.success(request, f"🎉 Bid of ${bid_amount} placed successfully!")
    return redirect('auction_detail', pk=pk)


# ---------------------------------------------------------------------------
# New Auction / Bid views (name-based, no auth required)
# ---------------------------------------------------------------------------

def auction_public_list(request):
    """
    Public list of all Auction objects with live-status refresh.
    Accessible at /open-auctions/
    """
    for a in Auction.objects.filter(status=Auction.STATUS_LIVE):
        a.refresh_status()

    status_filter = request.GET.get('status', 'all')
    auctions = Auction.objects.all().order_by('-status', '-created_at')
    if status_filter in ('LIVE', 'CLOSED'):
        auctions = auctions.filter(status=status_filter)

    return render(request, 'auctions/open_auction_list.html', {
        'auctions': auctions,
        'status_filter': status_filter,
    })


def auction_public_detail(request, pk):
    """
    Public detail + bid submission for an Auction.
    Accessible at /open-auctions/<pk>/
    """
    auction = get_object_or_404(Auction, pk=pk)
    auction.refresh_status()

    bids     = auction.auction_bids.order_by('-amount', '-created_at')[:15]
    bid_form = PlaceBidForm()

    return render(request, 'auctions/open_auction_detail.html', {
        'auction':   auction,
        'bids':      bids,
        'bid_form':  bid_form,
    })


@require_POST
def submit_bid(request, pk):
    """
    POST-only view: serialize bids with row-locking and atomic transactions.

    Technical Guarantees:
      1. Concurrency: select_for_update() row-locking serializes all bids for this auction.
      2. Fresh State: validates against the latest committed current_price inside the lock.
      3. Closure & Winner: rejects bids if auction expired/closed, finalized automatically.
      4. Anti-Sniping: if a valid bid arrives in the final 30 seconds, extends end_time by 30 seconds.
    """
    form = PlaceBidForm(request.POST)

    if not form.is_valid():
        error_text = ' | '.join(
            f"{field}: {', '.join(errs)}"
            for field, errs in form.errors.items()
        )
        messages.error(request, f"Invalid input — {error_text}")
        return redirect('auction_public_detail', pk=pk)

    bidder_name = form.cleaned_data['bidder_name'].strip()
    bid_amount  = form.cleaned_data['amount']

    if not bidder_name:
        messages.error(request, "Bidder name cannot be blank.")
        return redirect('auction_public_detail', pk=pk)

    sniping_extended = False

    try:
        with transaction.atomic():
            # ----------------------------------------------------------------
            # 1. Row-Level Pessimistic Lock (PostgreSQL: SELECT ... FOR UPDATE)
            # Blocks concurrent requests until this transaction commits.
            # ----------------------------------------------------------------
            auction = (
                Auction.objects
                .select_for_update()
                .get(pk=pk)
            )

            now = timezone.now()

            # 2. Check if expired or closed. If so, finalize and reject bid.
            if auction.status == Auction.STATUS_CLOSED or now > auction.end_time:
                Auction.finalize_if_expired(auction.pk)
                messages.error(request, "This auction is CLOSED. No more bids can be accepted.")
                return redirect('auction_public_detail', pk=pk)

            # 3. Validate against the latest committed current_price inside the lock
            if bid_amount <= auction.current_price:
                messages.error(
                    request,
                    f"Your bid (${bid_amount}) must be greater than the latest current price "
                    f"(${auction.current_price}). Another bidder may have placed a bid just before you."
                )
                return redirect('auction_public_detail', pk=pk)

            # 4. Anti-Sniping Logic:
            # If a valid bid arrives during the final 30 seconds, extend end_time by exactly 30 seconds.
            remaining_seconds = (auction.end_time - now).total_seconds()
            fields_to_update = ['current_price']

            if 0 < remaining_seconds <= 30:
                auction.end_time = auction.end_time + timedelta(seconds=30)
                fields_to_update.append('end_time')
                sniping_extended = True

            # 5. Persist bid and update price atomically in the same database transaction
            AuctionBid.objects.create(
                auction=auction,
                bidder_name=bidder_name,
                amount=bid_amount,
                accepted=True,
            )
            auction.current_price = bid_amount
            auction.save(update_fields=fields_to_update)

    except Auction.DoesNotExist:
        messages.error(request, "Auction not found.")
        return redirect('auction_public_list')
    except Exception as exc:
        messages.error(request, f"Could not process bid: {exc}")
        return redirect('auction_public_detail', pk=pk)

    if sniping_extended:
        messages.success(
            request,
            f"✅ Bid of ${bid_amount} accepted! ⏱️ Anti-sniping: auction extended by 30 seconds."
        )
    else:
        messages.success(
            request,
            f"✅ Bid of ${bid_amount} accepted for '{auction.title}'!"
        )
    return redirect('auction_public_detail', pk=pk)


@login_required
def create_auction(request):
    """Create a new auction listing."""
    if request.method == 'POST':
        form = AuctionItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.seller = request.user
            item.current_price = item.starting_price
            item.save()
            item.update_status()
            messages.success(request, "Auction created successfully!")
            return redirect('auction_detail', pk=item.pk)
    else:
        form = AuctionItemForm()

    return render(request, 'auctions/create_auction.html', {'form': form})


@login_required
def toggle_watchlist(request, pk):
    """Add or remove an item from the user's watchlist."""
    item = get_object_or_404(AuctionItem, pk=pk)
    watch, created = WatchList.objects.get_or_create(user=request.user, item=item)

    if not created:
        watch.delete()
        messages.info(request, f"Removed '{item.title}' from your watchlist.")
    else:
        messages.success(request, f"Added '{item.title}' to your watchlist.")

    return redirect('auction_detail', pk=pk)


@login_required
def watchlist(request):
    """Show the current user's watchlist."""
    watched_items = WatchList.objects.filter(user=request.user).select_related('item')
    return render(request, 'auctions/watchlist.html', {'watched_items': watched_items})


@login_required
def dashboard(request):
    """User dashboard — shows their listings and bids."""
    my_listings = AuctionItem.objects.filter(seller=request.user)
    my_bids = Bid.objects.filter(bidder=request.user).select_related('item').order_by('-timestamp')
    return render(request, 'auctions/dashboard.html', {
        'my_listings': my_listings,
        'my_bids': my_bids,
    })


def register(request):
    """User registration."""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome, {user.username}! Account created successfully.")
            return redirect('home')
    else:
        form = RegisterForm()

    return render(request, 'auctions/register.html', {'form': form})


def user_logout(request):
    """
    Log out the user on GET or POST request, display message, and redirect to home.
    Resolves Django 5.0+ HTTP 405 Method Not Allowed error when clicking logout links.
    """
    logout(request)
    messages.info(request, "You have been successfully logged out.")
    return redirect('home')


# ---------------------------------------------------------------------------
# Live Status JSON API Endpoints
# ---------------------------------------------------------------------------

def auction_status_api(request, pk):
    """
    JSON API endpoint returning real-time auction state:
      - current_price
      - status ('LIVE' / 'CLOSED')
      - remaining_time (human-readable string)
      - remaining_seconds (integer)
      - end_time (ISO 8601 string)
      - total_accepted_bids (integer)
      - winner_name (string)
      - recent_bids (list of recent bids)
    """
    # Concurrency-safe automatic finalization check on every poll
    auction = Auction.finalize_if_expired(pk)

    now = timezone.now()
    diff = auction.end_time - now
    total_seconds = int(diff.total_seconds())

    if total_seconds > 0:
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        mins = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        parts.append(f"{hours:02d}h {mins:02d}m {secs:02d}s")
        remaining_time = " ".join(parts)
    else:
        total_seconds = 0
        remaining_time = "Auction Closed"

    accepted_bids_count = auction.auction_bids.filter(accepted=True).count()

    recent_bids_data = [
        {
            'bidder_name': b.bidder_name,
            'amount': f"{b.amount:.2f}",
            'accepted': b.accepted,
            'created_at': b.created_at.strftime('%H:%M:%S'),
        }
        for b in auction.auction_bids.order_by('-amount', '-created_at')[:12]
    ]

    return JsonResponse({
        'id': auction.pk,
        'title': auction.title,
        'current_price': f"{auction.current_price:.2f}",
        'status': auction.status,
        'remaining_time': remaining_time,
        'remaining_seconds': total_seconds,
        'end_time': auction.end_time.isoformat(),
        'total_accepted_bids': accepted_bids_count,
        'winner_name': auction.winner_name or '',
        'recent_bids': recent_bids_data,
    })


