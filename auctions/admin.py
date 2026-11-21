"""
Django Admin configuration for the auctions app.
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import AuctionItem, Bid, WatchList, Auction, AuctionBid

# ---------------------------------------------------------------------------
# Original model admins
# ---------------------------------------------------------------------------

@admin.register(AuctionItem)
class AuctionItemAdmin(admin.ModelAdmin):
    list_display  = ['title', 'seller', 'starting_price', 'current_price', 'status', 'start_time', 'end_time']
    list_filter   = ['status']
    search_fields = ['title', 'seller__username']
    readonly_fields = ['created_at']


@admin.register(Bid)
class OriginalBidAdmin(admin.ModelAdmin):
    list_display  = ['item', 'bidder', 'amount', 'timestamp']
    list_filter   = ['timestamp']
    search_fields = ['item__title', 'bidder__username']


@admin.register(WatchList)
class WatchListAdmin(admin.ModelAdmin):
    list_display = ['user', 'item', 'added_at']


# ---------------------------------------------------------------------------
# New model admins — Auction & Bid
# ---------------------------------------------------------------------------

class AuctionBidInline(admin.TabularInline):
    """Show bids directly inside the Auction change page."""
    model          = AuctionBid
    extra          = 0
    readonly_fields = ['bidder_name', 'amount', 'accepted', 'created_at']
    can_delete     = False
    ordering       = ['-amount']
    show_change_link = True


@admin.register(Auction)
class AuctionAdmin(admin.ModelAdmin):
    list_display   = [
        'title', 'status_badge', 'starting_price', 'current_price',
        'winner_name', 'start_time', 'end_time', 'bid_count', 'created_at',
    ]
    list_filter    = ['status', 'created_at']
    search_fields  = ['title', 'description', 'winner_name']
    ordering       = ['-created_at']
    inlines        = [AuctionBidInline]

    fieldsets = [
        ('Auction Details', {
            'fields': ('title', 'description', 'starting_price', 'current_price'),
        }),
        ('Schedule', {
            'fields': ('start_time', 'end_time'),
        }),
        ('Status & Result', {
            'fields': ('status', 'winner_name', 'created_at'),
        }),
    ]

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            # On creation: created_at, current_price, and winner_name are readonly
            return ['created_at', 'winner_name', 'current_price']
        # On editing: created_at, current_price, and winner_name are protected
        return ['created_at', 'current_price', 'winner_name']

    def save_model(self, request, obj, form, change):
        if not change and not obj.current_price:
            obj.current_price = obj.starting_price
        super().save_model(request, obj, form, change)

    @admin.display(description='Status')
    def status_badge(self, obj):
        colour = '#22c55e' if obj.status == 'LIVE' else '#6b7280'
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:0.75rem;font-weight:600;">{}</span>',
            colour, obj.status,
        )

    @admin.display(description='Total Bids')
    def bid_count(self, obj):
        return obj.auction_bids.count()


@admin.register(AuctionBid)
class AuctionBidAdmin(admin.ModelAdmin):
    list_display   = ['auction', 'bidder_name', 'amount', 'accepted_badge', 'created_at']
    list_filter    = ['accepted', 'created_at']
    search_fields  = ['auction__title', 'bidder_name']
    readonly_fields = ['auction', 'bidder_name', 'amount', 'accepted', 'created_at']
    ordering       = ['-created_at']

    @admin.display(description='Accepted')
    def accepted_badge(self, obj):
        if obj.accepted:
            return format_html('<span style="color:#22c55e;font-weight:bold">{}</span>', '✓ Yes')
        return format_html('<span style="color:#ef4444">{}</span>', '✗ No')

