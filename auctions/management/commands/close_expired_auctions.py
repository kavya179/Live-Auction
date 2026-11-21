"""
Django Management Command: close_expired_auctions
Closes and finalizes expired auctions in the database.

Features:
  - Can be run as a one-shot cron job:
      python manage.py close_expired_auctions
  - Can be run as a standing background daemon:
      python manage.py close_expired_auctions --loop --interval 5
  - Thread-safe & concurrency-safe using select_for_update() row locks.
  - Declares single winner per auction and handles no-bid auctions.
"""

import time
from django.core.management.base import BaseCommand
from django.utils import timezone
from auctions.models import Auction


class Command(BaseCommand):
    help = 'Finalize all expired auctions, declare winners, and set status to CLOSED.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--loop',
            action='store_true',
            help='Run continuously in a loop as a background daemon.',
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=5,
            help='Polling interval in seconds when running with --loop (default: 5s).',
        )

    def handle(self, *args, **options):
        is_loop = options['loop']
        interval = options['interval']

        self.stdout.write(self.style.SUCCESS(
            f"Starting auction closure engine (loop={is_loop}, interval={interval}s)..."
        ))

        while True:
            self.finalize_all_expired()
            if not is_loop:
                break
            time.sleep(interval)

    def finalize_all_expired(self):
        now = timezone.now()
        # Find all LIVE auctions whose end_time has passed
        expired_auctions = Auction.objects.filter(
            status=Auction.STATUS_LIVE,
            end_time__lt=now,
        ).values_list('pk', flat=True)

        count = len(expired_auctions)
        if count == 0:
            return

        for auction_id in expired_auctions:
            # finalize_if_expired acquires a row lock and ensures idempotency
            auction = Auction.finalize_if_expired(auction_id)
            if auction.winner_name:
                self.stdout.write(self.style.SUCCESS(
                    f"✓ Closed Auction #{auction.pk} '{auction.title}' — Winner: {auction.winner_name} (₹{auction.current_price})"
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    f"✓ Closed Auction #{auction.pk} '{auction.title}' — No bids placed (Reserve: ₹{auction.current_price})"
                ))

