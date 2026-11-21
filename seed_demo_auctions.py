"""
Seed Script: Populates realistic, rich auction data for demonstration and evaluation.
Features:
  - Active auctions with diverse timing (75s for anti-sniping demo, 3m, 15m, 45m, 3h, 24h)
  - Pre-seeded bid history
  - Concurrency & anti-sniping ready
  - Closed auctions with declared single winner
  - Closed auction with zero bids (reserve held)
  - All currency in Indian Rupees (₹)
"""

import os
import django
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.utils import timezone
from auctions.models import Auction, AuctionBid


def seed():
    print("=" * 70)
    print("Seeding Live Auction Platform with Fresh Demo Data & Timers (INR ₹)...")
    print("=" * 70)
    now = timezone.now()

    demos = [
        # 1. LIVE AUCTION — ANTI-SNIPING DEMO (Ends in ~75 seconds)
        {
            'title': "🔥 Anti-Sniping Demo: 1999 Pokémon 1st Edition Charizard Holo #4 (PSA 10)",
            'description': (
                "The holy grail of modern collectibles. Authenticated Gem Mint 10 by PSA. "
                "TIMING DEMO: This auction ends in ~75 seconds. Place a bid when the timer drops below "
                "30 seconds to witness the 30-second anti-sniping extension live!"
            ),
            'starting_price': 250000.00,
            'current_price': 345000.00,
            'start_time': now - timedelta(minutes=15),
            'end_time': now + timedelta(seconds=75),
            'status': Auction.STATUS_LIVE,
            'winner_name': '',
            'bids': [
                ("Aarav Sharma", 280000.00),
                ("Vikramaditya Roy", 315000.00),
                ("Ken Goldin Collectibles", 345000.00),
            ]
        },

        # 2. LIVE AUCTION — VINTAGE MOTORCYCLE (Ends in 3 minutes)
        {
            'title': "🏍️ 1962 Royal Enfield Bullet 350 Original Cast Iron Engine (Restored)",
            'description': (
                "Flawlessly restored vintage 1962 Royal Enfield Bullet with matching original British-era "
                "frame numbers, classic heavy flywheel, and pristine chrome detailing. Comes with original RC book."
            ),
            'starting_price': 180000.00,
            'current_price': 240000.00,
            'start_time': now - timedelta(hours=1),
            'end_time': now + timedelta(minutes=3),
            'status': Auction.STATUS_LIVE,
            'winner_name': '',
            'bids': [
                ("Kabir Mehta", 195000.00),
                ("Devansh Singhania", 215000.00),
                ("Rajeshwar Rao", 240000.00),
            ]
        },

        # 3. LIVE AUCTION — CRICKET MEMORABILIA (Ends in 15 minutes)
        {
            'title': "🏏 Sachin Tendulkar 2011 ICC World Cup Match-Used Signed MRF Bat",
            'description': (
                "Iconic match-used MRF Genius bat signed by Sachin Tendulkar during the historic 2011 "
                "ICC Cricket World Cup campaign. Complete with BCCI certificate of authenticity and hologram."
            ),
            'starting_price': 500000.00,
            'current_price': 725000.00,
            'start_time': now - timedelta(hours=2),
            'end_time': now + timedelta(minutes=15),
            'status': Auction.STATUS_LIVE,
            'winner_name': '',
            'bids': [
                ("Rohan Gavaskar", 550000.00),
                ("Sunil Varma", 620000.00),
                ("Ananya Birla", 725000.00),
            ]
        },

        # 4. LIVE AUCTION — LUXURY JEWELRY (Ends in 45 minutes)
        {
            'title': "💎 Rare Kashmir Cornflower Blue Sapphire 5.2 Carat Diamond Ring",
            'description': (
                "Unheated certified Kashmir blue sapphire displaying the coveted velvety cornflower hue, "
                "flanked by trapezoid VVS1 diamonds mounted in platinum. Certified by SSEF and Gübelin."
            ),
            'starting_price': 1200000.00,
            'current_price': 1650000.00,
            'start_time': now - timedelta(hours=3),
            'end_time': now + timedelta(minutes=45),
            'status': Auction.STATUS_LIVE,
            'winner_name': '',
            'bids': [
                ("Priya Oberoi", 1350000.00),
                ("Harshavardhan Goenka", 1500000.00),
                ("Zoya Akhtar", 1650000.00),
            ]
        },

        # 5. LIVE AUCTION — VINTAGE CAR (Ends in 3 hours)
        {
            'title': "🏎️ 1965 Shelby Cobra 427 S/C Roadster (Guardsman Blue)",
            'description': (
                "Original CSX series competition roadster with aluminum body, side pipes, Halibrand "
                "knock-off wheels, and documented continuous provenance in the official SAAC Registry."
            ),
            'starting_price': 65000000.00,
            'current_price': 84000000.00,
            'start_time': now - timedelta(hours=5),
            'end_time': now + timedelta(hours=3),
            'status': Auction.STATUS_LIVE,
            'winner_name': '',
            'bids': [
                ("Peterson Heritage Fund", 70000000.00),
                ("Velocity Holdings Ltd", 78000000.00),
                ("Vijay Mallya Collection Trust", 84000000.00),
            ]
        },

        # 6. LIVE AUCTION — TECH HISTORY (Ends in 24 hours)
        {
            'title': "💻 1976 Operational Apple-1 Computer (Board #01-0025)",
            'description': (
                "Hand-assembled in Steve Jobs' garage. Original motherboard, period Sanyo monitor, "
                "Datanetics keyboard, Cassette Interface, and manual inscribed by Steve Wozniak."
            ),
            'starting_price': 28000000.00,
            'current_price': 35000000.00,
            'start_time': now - timedelta(hours=10),
            'end_time': now + timedelta(hours=24),
            'status': Auction.STATUS_LIVE,
            'winner_name': '',
            'bids': [
                ("Silicon Pioneer Fund", 31000000.00),
                ("Museum of Computing History", 35000000.00),
            ]
        },

        # 7. CLOSED AUCTION — WINNER SHOWCASE
        {
            'title': "🏆 1996 Michael Jordan NBA Finals Game 6 Championship Jersey",
            'description': (
                "Official road red Chicago Bulls jersey worn by Michael Jordan during the 1996 NBA Finals clincher. "
                "MeiGray dual photo match and letter of provenance. Auction successfully finalized."
            ),
            'starting_price': 6000000.00,
            'current_price': 18500000.00,
            'start_time': now - timedelta(days=5),
            'end_time': now - timedelta(hours=4),
            'status': Auction.STATUS_CLOSED,
            'winner_name': "David K. Harrison",
            'bids': [
                ("Chris Paulson", 9500000.00),
                ("Anthony Wright", 14000000.00),
                ("David K. Harrison", 18500000.00),
            ]
        },

        # 8. CLOSED AUCTION — NO-BIDS RESERVE SHOWCASE
        {
            'title': "🎨 1974 Monumental Brutalist Bronze Fountain Sculpture",
            'description': (
                "Architectural bronze casting from the private estate of the mid-century sculptor. "
                "Reserve price was not met before expiry; closed cleanly with zero accepted bids."
            ),
            'starting_price': 1400000.00,
            'current_price': 1400000.00,
            'start_time': now - timedelta(days=3),
            'end_time': now - timedelta(hours=8),
            'status': Auction.STATUS_CLOSED,
            'winner_name': "",
            'bids': []
        },
    ]

    for item in demos:
        bids_to_create = item.pop('bids')
        title = item.pop('title')
        auction, created = Auction.objects.update_or_create(
            title=title,
            defaults=item,
        )
        action = "Created" if created else "Updated"
        rem_sec = (auction.end_time - now).total_seconds()
        rem_str = f"{rem_sec:.0f}s remaining" if rem_sec > 0 else "Expired/Closed"
        print(f"✓ {action} [{auction.status}]: '{auction.title[:45]}' | Price: ₹{auction.current_price:,.2f} | {rem_str}")

        # Seed or refresh bids
        if created or auction.auction_bids.count() == 0:
            for bidder_name, amount in bids_to_create:
                AuctionBid.objects.create(
                    auction=auction,
                    bidder_name=bidder_name,
                    amount=amount,
                    accepted=True,
                )

    print("-" * 70)
    print(f"Total Auctions in Database: {Auction.objects.count()}")
    print(f"Total Bids in Database: {AuctionBid.objects.count()}")
    print("✓ All currencies set to Indian Rupee (₹).")
    print("=" * 70)


if __name__ == '__main__':
    seed()
