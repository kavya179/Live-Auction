"""
Database models for the auctions app.

Contains two model groups:
  1. AuctionItem / Bid / WatchList  — original user-auth-based models
  2. Auction / Bid (new)            — name-based bidding models required
                                      by the backend specification
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


# ---------------------------------------------------------------------------
# Original models (kept intact — used by all existing views and templates)
# ---------------------------------------------------------------------------

class AuctionItem(models.Model):
    """Represents an item listed for auction (auth-based)."""

    STATUS_CHOICES = [
        ('upcoming', 'Upcoming'),
        ('live', 'Live'),
        ('ended', 'Ended'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    image = models.ImageField(upload_to='auction_images/', blank=True, null=True)
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='items_listed')
    starting_price = models.DecimalField(max_digits=10, decimal_places=2)
    current_price = models.DecimalField(max_digits=10, decimal_places=2)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='upcoming')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def is_live(self):
        now = timezone.now()
        return self.start_time <= now <= self.end_time

    def update_status(self):
        now = timezone.now()
        if now < self.start_time:
            self.status = 'upcoming'
        elif self.start_time <= now <= self.end_time:
            self.status = 'live'
        else:
            self.status = 'ended'
        self.save()


class Bid(models.Model):
    """
    Original bid model — kept exactly as first migrated.
    Linked to AuctionItem and Django's User model.
    """

    item      = models.ForeignKey(AuctionItem, on_delete=models.CASCADE, related_name='bids')
    bidder    = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bids_placed')
    amount    = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-amount']

    def __str__(self):
        return f"{self.bidder.username} bid ${self.amount} on {self.item.title}"


class WatchList(models.Model):
    """Tracks items a user is watching."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='watchlist')
    item = models.ForeignKey(AuctionItem, on_delete=models.CASCADE, related_name='watchers')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'item')

    def __str__(self):
        return f"{self.user.username} watching {self.item.title}"


# ---------------------------------------------------------------------------
# New backend models — Auction + Bid (name-based, no auth dependency)
# ---------------------------------------------------------------------------

class Auction(models.Model):
    """
    Core auction model.

    Status lifecycle:
      LIVE   → auction is open for bids (now is between start_time and end_time)
      CLOSED → auction has ended (time expired or manually closed)

    winner_name is set automatically when the auction closes and at least
    one accepted bid exists.
    """

    STATUS_LIVE   = 'LIVE'
    STATUS_CLOSED = 'CLOSED'

    STATUS_CHOICES = [
        (STATUS_LIVE,   'Live'),
        (STATUS_CLOSED, 'Closed'),
    ]

    title          = models.CharField(max_length=200)
    description    = models.TextField()
    starting_price = models.DecimalField(max_digits=10, decimal_places=2)
    current_price  = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    start_time     = models.DateTimeField()
    end_time       = models.DateTimeField()
    status         = models.CharField(
                         max_length=6,
                         choices=STATUS_CHOICES,
                         default=STATUS_LIVE,
                     )
    winner_name    = models.CharField(
                         max_length=150,
                         blank=True,
                         default='',
                         help_text='Populated automatically when the auction closes.',
                     )
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name        = 'Auction'
        verbose_name_plural = 'Auctions'

    def save(self, *args, **kwargs):
        # Auto-initialize current_price from starting_price on creation if not set
        if self.current_price is None and self.starting_price is not None:
            self.current_price = self.starting_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.status}] {self.title}"

    # ------------------------------------------------------------------
    # Computed properties
    # ------------------------------------------------------------------

    @property
    def is_live(self) -> bool:
        """True when the auction is currently accepting bids."""
        now = timezone.now()
        return self.status == self.STATUS_LIVE and self.start_time <= now <= self.end_time

    @property
    def is_expired(self) -> bool:
        """True when the wall-clock time has passed the end_time."""
        return timezone.now() > self.end_time

    # ------------------------------------------------------------------
    # Business logic & Concurrency-Safe Finalization
    # ------------------------------------------------------------------

    @classmethod
    def finalize_if_expired(cls, auction_id) -> 'Auction':
        """
        Thread-safe and concurrency-safe method to finalize an expired auction.
        Uses select_for_update() row locking to guarantee:
          1. Prevents duplicate finalization.
          2. Rejects all new bids once closed.
          3. Deterministically selects exactly one winner (highest bid, tie-broken by earliest submission).
          4. Handles auctions without any bids cleanly (leaves reserve, winner_name empty).
        """
        from django.db import transaction
        with transaction.atomic():
            locked_auction = cls.objects.select_for_update().get(pk=auction_id)

            # Prevent duplicate finalization
            if locked_auction.status == cls.STATUS_CLOSED:
                return locked_auction

            now = timezone.now()
            if now > locked_auction.end_time:
                locked_auction.status = cls.STATUS_CLOSED

                # Find highest accepted bid. Deterministic tie-breaking ensures exactly one winner.
                highest_bid = (
                    locked_auction.auction_bids
                    .filter(accepted=True)
                    .order_by('-amount', 'created_at', 'id')
                    .first()
                )

                if highest_bid:
                    locked_auction.winner_name = highest_bid.bidder_name
                    locked_auction.current_price = highest_bid.amount
                else:
                    # Clean handling for auctions with zero bids
                    locked_auction.winner_name = ""

                locked_auction.save(update_fields=['status', 'winner_name', 'current_price'])

            return locked_auction

    def refresh_status(self) -> None:
        """
        Sync the status field with current wall-clock time.
        If expired, safely finalizes and reloads state.
        """
        if self.status == self.STATUS_CLOSED:
            return

        now = timezone.now()
        if now > self.end_time:
            self.finalize_if_expired(self.pk)
            self.refresh_from_db(fields=['status', 'winner_name', 'current_price'])
        elif now < self.start_time:
            # Not started yet
            pass
        else:
            if self.status != self.STATUS_LIVE:
                self.status = self.STATUS_LIVE
                self.save(update_fields=['status'])


class AuctionBid(models.Model):
    """
    A bid placed on an Auction (new backend model).

    Fields
    ------
    auction      – the Auction being bid on
    bidder_name  – free-text name (no login required)
    amount       – the bid value in dollars
    accepted     – True when the bid was the highest valid bid at submit time
    created_at   – timestamp of submission
    """

    auction     = models.ForeignKey(
                      Auction,
                      on_delete=models.CASCADE,
                      related_name='auction_bids',
                  )
    bidder_name = models.CharField(max_length=150)
    amount      = models.DecimalField(max_digits=10, decimal_places=2)
    accepted    = models.BooleanField(
                      default=False,
                      help_text='True when this bid was accepted as the new highest bid.',
                  )
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-amount', '-created_at']
        verbose_name        = 'Auction Bid'
        verbose_name_plural = 'Auction Bids'

    def __str__(self):
        status = '✓' if self.accepted else '✗'
        return f"[{status}] {self.bidder_name} → ${self.amount} on '{self.auction.title}'"

