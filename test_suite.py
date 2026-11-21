"""
Complete Automated Verification Suite for Live Auction Platform
Tests all requested scenarios:
  1. Higher bid gets accepted.
  2. Lower bid gets rejected.
  3. Equal bid gets rejected.
  4. Bid during the final 30 seconds extends the auction by 30 seconds.
  5. Expired auction rejects new bids.
  6. Multiple simultaneous bids do not corrupt the current price.
  7. Exactly one winner is declared.
  8. Auction with no bids closes correctly.
  + Admin functionality (Create, Edit, View, Bid History, Status & Winner)
"""

import os
import threading
from datetime import timedelta
from decimal import Decimal
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from django.db import connection, transaction
from django.test import Client
from django.utils import timezone
from auctions.models import Auction, AuctionBid


def run_tests():
    print("=" * 70)
    print("LIVE AUCTION PLATFORM — COMPREHENSIVE TEST SUITE")
    print("=" * 70)

    client = Client()
    now = timezone.now()

    # -------------------------------------------------------------
    # Scenario 1: Higher bid gets accepted
    # -------------------------------------------------------------
    print("\n[Scenario 1] Higher bid gets accepted...")
    a1 = Auction.objects.create(
        title="Scenario 1 Auction",
        description="Testing higher bid acceptance",
        starting_price=100.00,
        current_price=100.00,
        start_time=now - timedelta(hours=1),
        end_time=now + timedelta(hours=2),
        status="LIVE"
    )
    r1 = client.post(f"/open-auctions/{a1.pk}/bid/", {
        "bidder_name": "Alice High",
        "amount": "150.00"
    }, follow=True)
    assert r1.status_code == 200
    a1.refresh_from_db()
    assert float(a1.current_price) == 150.00, f"Expected 150.00, got {a1.current_price}"
    assert a1.auction_bids.filter(bidder_name="Alice High", amount=150.00, accepted=True).exists()
    print("  PASS: Higher bid ($150.00) accepted, current_price updated.")

    # -------------------------------------------------------------
    # Scenario 2: Lower bid gets rejected
    # -------------------------------------------------------------
    print("\n[Scenario 2] Lower bid gets rejected...")
    r2 = client.post(f"/open-auctions/{a1.pk}/bid/", {
        "bidder_name": "Bob Low",
        "amount": "120.00"
    }, follow=True)
    assert r2.status_code == 200
    a1.refresh_from_db()
    assert float(a1.current_price) == 150.00, f"Expected 150.00, got {a1.current_price}"
    assert not a1.auction_bids.filter(bidder_name="Bob Low").exists()
    print("  PASS: Lower bid ($120.00) rejected, current_price remained $150.00.")

    # -------------------------------------------------------------
    # Scenario 3: Equal bid gets rejected
    # -------------------------------------------------------------
    print("\n[Scenario 3] Equal bid gets rejected...")
    r3 = client.post(f"/open-auctions/{a1.pk}/bid/", {
        "bidder_name": "Charlie Equal",
        "amount": "150.00"
    }, follow=True)
    assert r3.status_code == 200
    a1.refresh_from_db()
    assert float(a1.current_price) == 150.00
    assert not a1.auction_bids.filter(bidder_name="Charlie Equal").exists()
    print("  PASS: Equal bid ($150.00) rejected, current_price remained $150.00.")

    # -------------------------------------------------------------
    # Scenario 4: Bid during final 30 seconds extends auction by 30 seconds
    # -------------------------------------------------------------
    print("\n[Scenario 4] Bid during final 30 seconds extends auction by 30 seconds...")
    orig_end = timezone.now() + timedelta(seconds=20)
    a4 = Auction.objects.create(
        title="Scenario 4 Anti-Snipe",
        description="Testing 30s extension",
        starting_price=50.00,
        current_price=50.00,
        start_time=now - timedelta(hours=1),
        end_time=orig_end,
        status="LIVE"
    )
    r4 = client.post(f"/open-auctions/{a4.pk}/bid/", {
        "bidder_name": "Sniper Hunter",
        "amount": "75.00"
    }, follow=True)
    assert r4.status_code == 200
    a4.refresh_from_db()
    diff = (a4.end_time - orig_end).total_seconds()
    assert round(diff) == 30, f"Expected 30s extension, got {diff}s"
    assert float(a4.current_price) == 75.00
    print(f"  PASS: Auction extended by {diff:.1f}s (New deadline: {a4.end_time.strftime('%H:%M:%S')}).")

    # -------------------------------------------------------------
    # Scenario 5: Expired auction rejects new bids
    # -------------------------------------------------------------
    print("\n[Scenario 5] Expired auction rejects new bids...")
    a5 = Auction.objects.create(
        title="Scenario 5 Expired",
        description="Testing expired closure",
        starting_price=100.00,
        current_price=100.00,
        start_time=now - timedelta(hours=2),
        end_time=now - timedelta(seconds=10),  # expired 10s ago
        status="LIVE"
    )
    r5 = client.post(f"/open-auctions/{a5.pk}/bid/", {
        "bidder_name": "Late Bidder",
        "amount": "200.00"
    }, follow=True)
    assert r5.status_code == 200
    a5.refresh_from_db()
    assert a5.status == "CLOSED", f"Status should be CLOSED, got {a5.status}"
    assert float(a5.current_price) == 100.00, "Price should not change"
    assert not a5.auction_bids.filter(bidder_name="Late Bidder").exists()
    print("  PASS: Expired auction transitioned to CLOSED and rejected late bid.")

    # -------------------------------------------------------------
    # Scenario 6: Multiple simultaneous bids do not corrupt current price
    # -------------------------------------------------------------
    print("\n[Scenario 6] Multiple simultaneous bids do not corrupt current price...")
    a6 = Auction.objects.create(
        title="Scenario 6 Concurrency",
        description="Testing concurrent bids",
        starting_price=100.00,
        current_price=100.00,
        start_time=now - timedelta(hours=1),
        end_time=now + timedelta(hours=1),
        status="LIVE"
    )

    results = []
    def place_bid_worker(bidder, amount):
        w_client = Client()
        resp = w_client.post(f"/open-auctions/{a6.pk}/bid/", {
            "bidder_name": bidder,
            "amount": str(amount)
        })
        results.append((bidder, amount, resp.status_code))

    # Spawn concurrent threads submitting bids
    t1 = threading.Thread(target=place_bid_worker, args=("Thread-1", 120.00))
    t2 = threading.Thread(target=place_bid_worker, args=("Thread-2", 180.00))
    t3 = threading.Thread(target=place_bid_worker, args=("Thread-3", 140.00))
    t4 = threading.Thread(target=place_bid_worker, args=("Thread-4", 250.00))
    t5 = threading.Thread(target=place_bid_worker, args=("Thread-5", 210.00))

    threads = [t1, t2, t3, t4, t5]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    a6.refresh_from_db()
    # Find highest accepted bid in DB
    accepted_bids = list(a6.auction_bids.filter(accepted=True).order_by("amount"))
    highest_accepted = accepted_bids[-1] if accepted_bids else None

    assert highest_accepted is not None, "At least one bid should be accepted"
    assert a6.current_price == highest_accepted.amount, (
        f"Corruption! current_price ({a6.current_price}) != highest accepted bid ({highest_accepted.amount})"
    )
    # Check that accepted bids are strictly ascending (monotonic increase)
    for i in range(len(accepted_bids) - 1):
        assert accepted_bids[i].amount < accepted_bids[i+1].amount, "Accepted bids must be strictly ascending"

    print(f"  PASS: {len(accepted_bids)} bids accepted in strict order. Final price: ${a6.current_price} (Uncorrupted).")

    # -------------------------------------------------------------
    # Scenario 7: Exactly one winner is declared
    # -------------------------------------------------------------
    print("\n[Scenario 7] Exactly one winner is declared...")
    a7 = Auction.objects.create(
        title="Scenario 7 Single Winner",
        description="Testing single winner declaration",
        starting_price=200.00,
        current_price=450.00,
        start_time=now - timedelta(hours=3),
        end_time=now - timedelta(seconds=2),  # expired
        status="LIVE"
    )
    AuctionBid.objects.create(auction=a7, bidder_name="Bidder Alpha", amount=300.00, accepted=True)
    AuctionBid.objects.create(auction=a7, bidder_name="Bidder Beta", amount=450.00, accepted=True)
    AuctionBid.objects.create(auction=a7, bidder_name="Bidder Gamma", amount=400.00, accepted=True)

    finalized7 = Auction.finalize_if_expired(a7.pk)
    assert finalized7.status == "CLOSED"
    assert finalized7.winner_name == "Bidder Beta", f"Expected Bidder Beta, got {finalized7.winner_name}"
    assert float(finalized7.current_price) == 450.00
    print(f"  PASS: Exactly one winner declared ({finalized7.winner_name}) at ${finalized7.current_price}.")

    # -------------------------------------------------------------
    # Scenario 8: Auction with no bids closes correctly
    # -------------------------------------------------------------
    print("\n[Scenario 8] Auction with no bids closes correctly...")
    a8 = Auction.objects.create(
        title="Scenario 8 Zero Bids",
        description="Testing zero bid closure",
        starting_price=500.00,
        current_price=500.00,
        start_time=now - timedelta(hours=2),
        end_time=now - timedelta(seconds=1),  # expired
        status="LIVE"
    )
    finalized8 = Auction.finalize_if_expired(a8.pk)
    assert finalized8.status == "CLOSED"
    assert finalized8.winner_name == "", f"Expected empty winner_name, got '{finalized8.winner_name}'"
    assert float(finalized8.current_price) == 500.00
    print("  PASS: Zero-bid auction closed as CLOSED with no winner declared and reserve price preserved.")

    # -------------------------------------------------------------
    # Admin Functionality Tests
    # -------------------------------------------------------------
    print("\n" + "=" * 70)
    print("ADMIN FUNCTIONALITY VERIFICATION")
    print("=" * 70)

    admin_user, _ = User.objects.get_or_create(username='admin', is_staff=True, is_superuser=True)
    admin_user.set_password('admin123')
    admin_user.save()

    admin_client = Client()
    admin_client.login(username='admin', password='admin123')

    # 1. Admin can view all auctions
    print("\n[Admin 1] Admin can view all auctions...")
    r_adm_list = admin_client.get('/admin/auctions/auction/')
    assert r_adm_list.status_code == 200
    print("  PASS: Admin changelist loaded successfully (200 OK).")

    # 2. Admin can create auctions
    print("\n[Admin 2] Admin can create auctions...")
    adm_add_data = {
        'title': 'Admin Masterpiece Oil Painting',
        'description': '19th century oil on canvas.',
        'starting_price': '8000.00',
        'start_time_0': str(now.date()),
        'start_time_1': str(now.time())[:8],
        'end_time_0': str((now + timedelta(days=5)).date()),
        'end_time_1': str((now + timedelta(days=5)).time())[:8],
        'status': 'LIVE',
        'auction_bids-TOTAL_FORMS': '0',
        'auction_bids-INITIAL_FORMS': '0',
        'auction_bids-MIN_NUM_FORMS': '0',
        'auction_bids-MAX_NUM_FORMS': '1000',
    }
    r_adm_add = admin_client.post('/admin/auctions/auction/add/', adm_add_data, follow=True)
    assert r_adm_add.status_code == 200
    adm_auction = Auction.objects.filter(title='Admin Masterpiece Oil Painting').first()
    assert adm_auction is not None
    assert float(adm_auction.starting_price) == 8000.00
    assert float(adm_auction.current_price) == 8000.00, "current_price should initialize from starting_price"
    print(f"  PASS: Admin created Auction #{adm_auction.pk}: '{adm_auction.title}' (${adm_auction.current_price}).")

    # 3. Admin can edit auction details
    print("\n[Admin 3] Admin can edit auction details...")
    adm_edit_data = {
        'title': 'Admin Masterpiece Oil Painting (Framed & Signed)',
        'description': '19th century oil on canvas, museum frame included.',
        'starting_price': '8000.00',
        'start_time_0': str(adm_auction.start_time.date()),
        'start_time_1': str(adm_auction.start_time.time())[:8],
        'end_time_0': str(adm_auction.end_time.date()),
        'end_time_1': str(adm_auction.end_time.time())[:8],
        'status': 'LIVE',
        'auction_bids-TOTAL_FORMS': '0',
        'auction_bids-INITIAL_FORMS': '0',
        'auction_bids-MIN_NUM_FORMS': '0',
        'auction_bids-MAX_NUM_FORMS': '1000',
    }
    r_adm_edit = admin_client.post(f'/admin/auctions/auction/{adm_auction.pk}/change/', adm_edit_data, follow=True)
    assert r_adm_edit.status_code == 200
    adm_auction.refresh_from_db()
    assert adm_auction.title == 'Admin Masterpiece Oil Painting (Framed & Signed)'
    print(f"  PASS: Admin edited auction details (Title updated to: '{adm_auction.title}').")

    # 4. Admin can view bid history
    print("\n[Admin 4] Admin can view bid history...")
    AuctionBid.objects.create(auction=adm_auction, bidder_name='Museum Collector', amount=9500.00, accepted=True)
    AuctionBid.objects.create(auction=adm_auction, bidder_name='Private Gallery', amount=11000.00, accepted=True)

    # 4a: Inline on change page
    r_detail = admin_client.get(f'/admin/auctions/auction/{adm_auction.pk}/change/')
    assert r_detail.status_code == 200
    assert b'Museum Collector' in r_detail.content
    assert b'Private Gallery' in r_detail.content
    print("  PASS: Bid history verified inline on auction change page.")

    # 4b: Dedicated AuctionBid changelist
    r_all_bids = admin_client.get('/admin/auctions/auctionbid/')
    assert r_all_bids.status_code == 200
    assert b'Museum Collector' in r_all_bids.content
    assert b'Private Gallery' in r_all_bids.content
    print("  PASS: Bid history verified in dedicated AuctionBid admin list.")

    # 5. Admin can see auction status and winner
    print("\n[Admin 5] Admin can see auction status and winner...")
    adm_auction.status = 'CLOSED'
    adm_auction.winner_name = 'Private Gallery'
    adm_auction.current_price = 11000.00
    adm_auction.save()

    r_adm_status = admin_client.get('/admin/auctions/auction/')
    assert r_adm_status.status_code == 200
    assert b'Private Gallery' in r_adm_status.content
    assert b'CLOSED' in r_adm_status.content
    print("  PASS: Status 'CLOSED' and Winner 'Private Gallery' verified in admin list.")

    print("\n" + "=" * 70)
    print("🎉 ALL 8 SCENARIOS AND ALL 5 ADMIN CAPABILITIES FULLY PASSING!")
    print("=" * 70)


if __name__ == '__main__':
    run_tests()

