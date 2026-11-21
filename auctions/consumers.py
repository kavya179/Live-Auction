"""
WebSocket consumers for real-time auction updates.
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone


class AuctionConsumer(AsyncWebsocketConsumer):
    """
    Handles WebSocket connections for a specific auction room.
    Clients join a group named 'auction_<id>' and receive
    live bid updates broadcast to that group.
    """

    async def connect(self):
        self.auction_id = self.scope['url_route']['kwargs']['auction_id']
        self.group_name = f'auction_{self.auction_id}'

        # Join the auction group
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Send a welcome confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection',
            'message': 'Connected to auction live feed.',
        }))

    async def disconnect(self, close_code):
        # Leave the auction group
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        """
        Receive a message from the WebSocket client.
        Expected payload: { "type": "bid", "amount": "150.00" }
        """
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        if data.get('type') == 'bid':
            # Broadcast the new bid to all clients in this auction group
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'bid_update',
                    'amount': data.get('amount', '0'),
                    'bidder': data.get('bidder', 'Anonymous'),
                    'timestamp': timezone.now().strftime('%H:%M:%S'),
                }
            )

    async def bid_update(self, event):
        """Send a bid update to the WebSocket client."""
        await self.send(text_data=json.dumps({
            'type': 'bid_update',
            'amount': event['amount'],
            'bidder': event['bidder'],
            'timestamp': event['timestamp'],
        }))

