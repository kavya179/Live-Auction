"""
URL patterns for the auctions app.
"""

from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Home
    path('', views.home, name='home'),

    # AuctionItem (auth-based, original)
    path('auctions/', views.auction_list, name='auction_list'),
    path('auctions/<int:pk>/', views.auction_detail, name='auction_detail'),
    path('auctions/create/', views.create_auction, name='create_auction'),
    path('auctions/<int:pk>/bid/', views.place_bid, name='place_bid'),
    path('auctions/<int:pk>/watch/', views.toggle_watchlist, name='toggle_watchlist'),

    # Watchlist
    path('watchlist/', views.watchlist, name='watchlist'),

    # Auth
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='auctions/login.html'), name='login'),
    path('logout/', views.user_logout, name='logout'),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # Open Auctions (new Auction model — name-based, no login required)
    path('open-auctions/', views.auction_public_list, name='auction_public_list'),
    path('open-auctions/<int:pk>/', views.auction_public_detail, name='auction_public_detail'),
    path('open-auctions/<int:pk>/bid/', views.submit_bid, name='submit_bid'),

    # Real-Time JSON API
    path('api/auction/<int:pk>/status/', views.auction_status_api, name='auction_status_api'),
    path('open-auctions/<int:pk>/api/', views.auction_status_api, name='auction_public_api'),
]

