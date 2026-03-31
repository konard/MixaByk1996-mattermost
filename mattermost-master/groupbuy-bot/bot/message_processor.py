"""
Multi-platform message processor.
Handles messages from Mattermost, WhatsApp, and other adapters
in a platform-agnostic way via the Core API.
"""
import logging
from typing import Dict, Any, Optional

from api_client import api_client

logger = logging.getLogger(__name__)

# Map of command text to handler functions
COMMAND_HANDLERS: Dict[str, Any] = {}


def command(name: str):
    """Decorator to register a command handler"""
    def decorator(func):
        COMMAND_HANDLERS[name] = func
        return func
    return decorator


async def process_platform_message(message: Dict[str, Any]):
    """
    Process an incoming message from any platform adapter.

    Expected message format:
    {
        "platform": "mattermost" | "telegram" | "websocket",
        "user_id": "<platform-specific user ID>",
        "chat_id": "<channel or chat ID>",
        "text": "<message text>",
        "message_id": "<message ID>",
        "user_info": {
            "first_name": "...",
            "last_name": "...",
            "username": "...",
            "language_code": "..."
        },
        "timestamp": "ISO8601",
        "type": "message" | "callback"
    }
    """
    platform = message.get('platform', 'unknown')
    user_id = message.get('user_id', '')
    text = message.get('text', '').strip()

    if not user_id or not text:
        return

    logger.info(f"Processing {platform} message from user {user_id}: {text[:50]}")

    # Parse command
    if text.startswith('/'):
        parts = text.split(maxsplit=1)
        command_name = parts[0].lower()
        # Remove @bot_name suffix if present (common in group chats)
        command_name = command_name.split('@')[0]
        args = parts[1] if len(parts) > 1 else ''

        handler = COMMAND_HANDLERS.get(command_name)
        if handler:
            await handler(message, args)
            return

    # Auto-register user if not exists
    user = await api_client.get_user_by_platform(platform, user_id)
    if not user:
        user_info = message.get('user_info', {})
        user = await api_client.register_user({
            'platform': platform,
            'platform_user_id': user_id,
            'username': user_info.get('username', ''),
            'first_name': user_info.get('first_name', user_id),
            'last_name': user_info.get('last_name', ''),
            'language_code': user_info.get('language_code', 'ru'),
            'role': 'buyer'
        })
        if user:
            logger.info(f"Auto-registered {platform} user {user_id}")


@command('/start')
async def handle_start(message: Dict[str, Any], args: str):
    platform = message.get('platform', 'unknown')
    user_id = message.get('user_id', '')
    user_info = message.get('user_info', {})

    user = await api_client.get_user_by_platform(platform, user_id)
    if not user:
        # Register user
        user = await api_client.register_user({
            'platform': platform,
            'platform_user_id': user_id,
            'username': user_info.get('username', ''),
            'first_name': user_info.get('first_name', user_id),
            'last_name': user_info.get('last_name', ''),
            'language_code': user_info.get('language_code', 'ru'),
            'role': 'buyer'
        })
        logger.info(f"Registered new {platform} user {user_id}")
    else:
        logger.info(f"{platform} user {user_id} already registered")


@command('/help')
async def handle_help(message: Dict[str, Any], args: str):
    logger.info(f"Help requested by {message.get('platform')} user {message.get('user_id')}")


@command('/procurements')
async def handle_procurements(message: Dict[str, Any], args: str):
    procurements = await api_client.get_procurements(status='active')
    logger.info(f"Procurements requested: {len(procurements)} found")


@command('/profile')
async def handle_profile(message: Dict[str, Any], args: str):
    platform = message.get('platform', 'unknown')
    user_id = message.get('user_id', '')
    user = await api_client.get_user_by_platform(platform, user_id)
    logger.info(f"Profile requested for {platform} user {user_id}: found={user is not None}")
