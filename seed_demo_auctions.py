"""
Seed Script: Populates realistic, rich auction data for demonstration and evaluation.
Includes:
  - An auction ending in 90 seconds (ideal for demonstrating Anti-Sniping live!)
  - High-value active auctions ending in 15 minutes, 2 hours, 24 hours, and 3 days
  - Completed/Closed auctions with verified winners and bid logs
  - Zero-bid reserve auction
"""

import os
import django
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.utils import timezone
from auctions.models import Auction, AuctionBid


def seed():
    print("Seeding Live Auction Platform with realistic demo data...")
    now = timezone.now()

    # 1. LIVE AUCTION — ANTI-SNIPING DEMO (Ends in ~90 seconds)
    # Perfect for testing bidding in the final 30s and watching it extend!
    a_snipe, created = Auction.objects.get_or_create(
        title="🔥 1999 Pokémon 1st Edition Shadowless Charizard Holo #4 (PSA 10)",
        defaults={
            'description': (
                "The holy grail of modern collectibles. Authenticated Gem Mint 10 by PSA. "
                "Bids submitted within the final 30 seconds will trigger the 30-second anti-sniping extension."
            ),
            'starting_price': 25000.00,
            'current_price': 34500.00,
            'start_time': now - timedelta(minutes=15),
            'end_time': now + timedelta(seconds=90),  # Ends in 90s!
            'status': Auction.STATUS_LIVE,
        }
    )
    if created:
        AuctionBid.objects.create(auction=a_snipe, bidder_name="Gary Vee", amount=28000.00, accepted=True)
        AuctionBid.objects.create(auction=a_snipe, bidder_name="Logan Paul", amount=31500.00, accepted=True)
        AuctionBid.objects.create(auction=a_snipe, bidder_name="Ken Goldin", amount=34500.00, accepted=True)
        print("✓ Created: 90-second Anti-Sniping Showcase Auction")

    # 2. LIVE AUCTION — HIGH CONCURRENCY SHOWCASE (Ends in 20 minutes)
    a_car, created = Auction.objects.get_or_create(
        title="🏎️ 1965 Shelby Cobra 427 S/C Roadster (Guardsman Blue)",
        defaults={
            'description': (
                "Original CSX series competition roadster with aluminum body, side pipes, Halibrand knock-off wheels, "
                "and documented continuous provenance in the official SAAC Registry."
            ),
            'starting_price': 850000.00,
            'current_price': 1120000.00,
            'start_time': now - timedelta(hours=2),
            'end_time': now + timedelta(minutes=20),
            'status': Auction.STATUS_LIVE,
        }
    )
    if created:
        AuctionBid.objects.create(auction=a_car, bidder_name="Jay Leno Collectibles", amount=920000.00, accepted=True)
        AuctionBid.objects.create(auction=a_car, bidder_name="Peterson Heritage Trust", amount=1050000.00, accepted=True)
        AuctionBid.objects.create(auction=a_car, bidder_name="Velocity Holdings Ltd", amount=1120000.00, accepted=True)
        print("✓ Created: 20-minute Cobra Roadster Auction")

    # 3. LIVE AUCTION — LUXURY HOROLOGY (Ends in 2 hours)
    a_watch, created = Auction.objects.get_or_create(
        title="⌚ 1968 Rolex Cosmograph Daytona Ref. 6239 'Paul Newman'",
        defaults={
            'description': (
                "Highly sought-after white exotic dial with art deco font, stepped subsidiary dials, and pristine "
                "unpolished stainless steel case. Accompanied by original guarantee certificate and inner/outer presentation box."
            ),
            'starting_price': 140000.00,
            'current_price': 185000.00,
            'start_time': now - timedelta(hours=4),
            'end_time': now + timedelta(hours=2),
            'status': Auction.STATUS_LIVE,
        }
    )
    if created:
        AuctionBid.objects.create(auction=a_watch, bidder_name="Geneva Timepiece Vault", amount=155000.00, accepted=True)
        AuctionBid.objects.create(auction=a_watch, bidder_name="Sebastian Mercer", amount=170000.00, accepted=True)
        AuctionBid.objects.create(auction=a_watch, bidder_name="Aurelie Dupont", amount=185000.00, accepted=True)
        print("✓ Created: 2-hour Paul Newman Daytona Auction")

    # 4. LIVE AUCTION — TECH HISTORY (Ends in 24 hours)
    a_tech, created = Auction.objects.get_or_create(
        title="💻 1976 Operational Apple-1 Computer (Board #01-0025)",
        defaults={
            'description': (
                "Hand-assembled in Steve Jobs' garage. Original motherboard, period Sanyo monitor, Datanetics keyboard, "
                "Cassette Interface, and original operation manual inscribed by Steve Wozniak."
            ),
            'starting_price': 350000.00,
            'current_price': 420000.00,
            'start_time': now - timedelta(hours=6),
            'end_time': now + timedelta(hours=24),
            'status': Auction.STATUS_LIVE,
        }
    )
    if created:
        AuctionBid.objects.create(auction=a_tech, bidder_name="Computer History Archives", amount=380000.00, accepted=True)
        AuctionBid.objects.create(auction=a_tech, bidder_name="Silicon Pioneer Fund", amount=420000.00, accepted=True)
        print("✓ Created: 24-hour Apple-1 Computer Auction")

    # 5. CLOSED AUCTION — WINNER SHOWCASE
    a_closed1, created = Auction.objects.get_or_create(
        title="🏆 1996 Michael Jordan NBA Finals Game 6 Championship Jersey",
        defaults={
            'description': (
                "Official road red Chicago Bulls jersey worn by Michael Jordan during the 1996 NBA Finals clincher against Seattle. "
                "MeiGray dual photo match and letter of provenance."
            ),
            'starting_price': 80000.00,
            'current_price': 245000.00,
            'start_time': now - timedelta(days=5),
            'end_time': now - timedelta(hours=2),
            'status': Auction.STATUS_CLOSED,
            'winner_name': "David K. Harrison",
        }
    )
    if created:
        AuctionBid.objects.create(auction=a_closed1, bidder_name="Chris Paulson", amount=120000.00, accepted=True)
        AuctionBid.objects.create(auction=a_closed1, bidder_name="Anthony Wright", amount=195000.00, accepted=True)
        AuctionBid.objects.create(auction=a_closed1, bidder_name="David K. Harrison", amount=245000.00, accepted=True)
        print("✓ Created: Closed Auction with Declared Winner")

    # 6. CLOSED AUCTION — NO-BIDS RESERVE SHOWCASE
    a_closed2, created = Auction.objects.get_or_create(
        title="🎨 1974 Monumental Brutalist Bronze Fountain Sculpture",
        defaults={
            'description': (
                "Architectural bronze casting from the private estate of the mid-century sculptor. Reserve not met; "
                "closed with zero accepted bids."
            ),
            'starting_price': 18000.00,
            'current_price': 18000.00,
            'start_time': now - timedelta(days=3),
            'end_time': now - timedelta(hours=6),
            'status': Auction.STATUS_CLOSED,
            'winner_name': "",
        }
    )
    if created:
        print("✓ Created: Closed Auction with Zero Bids (Reserve Held)")

    print("\n🎉 Seed data populated successfully!")
    print(f"Total Auctions in Database: {Auction.objects.count()}")
    print(f"Total Bids in Database: {AuctionBid.objects.count()}")


if __name__ == '__main__':
    seed()
