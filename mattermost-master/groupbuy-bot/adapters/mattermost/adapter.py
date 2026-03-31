"""
Mattermost Adapter for GroupBuy Bot
Handles Mattermost-specific message routing via incoming/outgoing webhooks
and Mattermost Bot API.
"""
import asyncio
import json
import logging
import os
import re
from datetime import datetime
from typing import Dict, Any, Optional

import aiohttp
from aiohttp import web

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MattermostAdapter:
    """Adapter for Mattermost messenger"""

    def __init__(self):
        self.mm_url = os.getenv('MATTERMOST_URL', 'http://mattermost:8065')
        self.mm_token = os.getenv('MATTERMOST_BOT_TOKEN', '')
        self.mm_team_id = os.getenv('MATTERMOST_TEAM_ID', '')
        self.mm_channel_id = os.getenv('MATTERMOST_CHANNEL_ID', '')
        self.bot_service_url = os.getenv('BOT_SERVICE_URL', 'http://bot:8001')
        self.webhook_secret = os.getenv('MATTERMOST_WEBHOOK_SECRET', '')
        self.listen_port = int(os.getenv('MATTERMOST_ADAPTER_PORT', '8002'))

        self.app = web.Application()
        self._setup_routes()

    def _setup_routes(self):
        self.app.router.add_post('/webhook', self._handle_webhook)
        self.app.router.add_get('/health', self._health_check)

    async def _health_check(self, request: web.Request) -> web.Response:
        return web.json_response({'status': 'healthy'})

    async def _handle_webhook(self, request: web.Request) -> web.Response:
        """Handle incoming webhook from Mattermost outgoing webhook or slash command"""
        try:
            # Mattermost can send as form data or JSON
            content_type = request.content_type or ''
            if 'application/x-www-form-urlencoded' in content_type:
                data = await request.post()
                payload = dict(data)
            else:
                payload = await request.json()

            # Validate webhook token
            token = payload.get('token', '')
            if self.webhook_secret and token != self.webhook_secret:
                logger.warning("Invalid webhook token received")
                return web.json_response({'text': 'Unauthorized'}, status=403)

            # Skip bot's own messages
            if payload.get('user_name', '').endswith('-bot') or payload.get('user_name') == 'groupbuy':
                return web.json_response({})

            standardized = self._standardize_message(payload)
            await self._route_to_bot(standardized)

            return web.json_response({})

        except Exception as e:
            logger.error(f"Error handling webhook: {e}")
            return web.json_response({'text': 'Internal error'}, status=500)

    def _standardize_message(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Mattermost webhook payload to standardized format"""
        text = payload.get('text', '')

        return {
            'platform': 'mattermost',
            'user_id': payload.get('user_id', ''),
            'chat_id': payload.get('channel_id', ''),
            'text': text,
            'message_id': payload.get('post_id', ''),
            'user_info': {
                'first_name': payload.get('user_name', ''),
                'last_name': '',
                'username': payload.get('user_name', ''),
                'language_code': 'ru'
            },
            'timestamp': datetime.now().isoformat(),
            'type': 'message',
            'team_id': payload.get('team_id', ''),
            'channel_name': payload.get('channel_name', '')
        }

    async def _route_to_bot(self, message: Dict[str, Any]):
        """Send standardized message to bot service"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f'{self.bot_service_url}/message',
                    json=message,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        text = await response.text()
                        logger.warning(f"Bot service returned {response.status}: {text}")
        except Exception as e:
            logger.error(f"Error routing message to bot: {e}")

    async def send_message(
        self,
        channel_id: str,
        text: str,
        props: Optional[Dict] = None
    ) -> bool:
        """Send message to a Mattermost channel"""
        if not self.mm_token:
            logger.warning("MATTERMOST_BOT_TOKEN not set, cannot send messages")
            return False

        payload = {
            'channel_id': channel_id,
            'message': text
        }
        if props:
            payload['props'] = props

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f'{self.mm_url}/api/v4/posts',
                    json=payload,
                    headers={
                        'Authorization': f'Bearer {self.mm_token}',
                        'Content-Type': 'application/json'
                    },
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status in (200, 201):
                        return True
                    text_resp = await response.text()
                    logger.error(f"Failed to send Mattermost message: {response.status} {text_resp}")
                    return False
        except Exception as e:
            logger.error(f"Error sending Mattermost message: {e}")
            return False

    async def send_direct_message(self, user_id: str, text: str) -> bool:
        """Send a direct message to a Mattermost user"""
        if not self.mm_token:
            logger.warning("MATTERMOST_BOT_TOKEN not set")
            return False

        # First create or get DM channel
        try:
            async with aiohttp.ClientSession() as session:
                # Get bot user ID
                async with session.get(
                    f'{self.mm_url}/api/v4/users/me',
                    headers={'Authorization': f'Bearer {self.mm_token}'},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status != 200:
                        return False
                    bot_user = await resp.json()
                    bot_id = bot_user.get('id', '')

                # Create DM channel
                async with session.post(
                    f'{self.mm_url}/api/v4/channels/direct',
                    json=[bot_id, user_id],
                    headers={
                        'Authorization': f'Bearer {self.mm_token}',
                        'Content-Type': 'application/json'
                    },
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status not in (200, 201):
                        return False
                    channel = await resp.json()
                    channel_id = channel.get('id', '')

                return await self.send_message(channel_id, text)
        except Exception as e:
            logger.error(f"Error sending DM: {e}")
            return False

    async def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get Mattermost user info"""
        if not self.mm_token:
            return None

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f'{self.mm_url}/api/v4/users/{user_id}',
                    headers={'Authorization': f'Bearer {self.mm_token}'},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        user = await response.json()
                        return {
                            'id': user.get('id', ''),
                            'first_name': user.get('first_name', ''),
                            'last_name': user.get('last_name', ''),
                            'username': user.get('username', ''),
                            'email': user.get('email', '')
                        }
                    return None
        except Exception as e:
            logger.error(f"Error getting Mattermost user: {e}")
            return None

    async def start(self):
        """Start the adapter HTTP server"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.listen_port)
        await site.start()
        logger.info(f"Mattermost adapter listening on port {self.listen_port}")
        await asyncio.Event().wait()

    async def stop(self):
        pass


async def main():
    adapter = MattermostAdapter()
    try:
        await adapter.start()
    except KeyboardInterrupt:
        await adapter.stop()


if __name__ == '__main__':
    asyncio.run(main())
