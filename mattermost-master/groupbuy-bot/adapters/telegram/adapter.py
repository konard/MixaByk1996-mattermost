"""
Telegram Adapter for GroupBuy Bot
Handles Telegram-specific message routing and formatting
"""
import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional

import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TelegramAdapter:
    """Adapter for Telegram messenger"""

    def __init__(self):
        self.token = os.getenv('TELEGRAM_TOKEN', '')
        self.bot_service_url = os.getenv('BOT_SERVICE_URL', 'http://bot:8001')

        if not self.token:
            raise ValueError("TELEGRAM_TOKEN is not set")

        self.bot = Bot(token=self.token)
        self.storage = MemoryStorage()
        self.dp = Dispatcher(storage=self.storage)

        # Message queue for async processing
        self.message_queue = asyncio.Queue()
        self.is_running = False

        self._register_handlers()

    def _register_handlers(self):
        """Register message handlers"""

        @self.dp.message()
        async def handle_all_messages(message: types.Message):
            """Handle all incoming messages"""
            standardized_msg = self._standardize_message(message)
            await self.message_queue.put(standardized_msg)
            logger.info(f"Message queued from user {message.from_user.id}")

        @self.dp.callback_query()
        async def handle_callback(callback_query: types.CallbackQuery):
            """Handle callback queries"""
            standardized_msg = self._standardize_callback(callback_query)
            await self.message_queue.put(standardized_msg)
            await self.bot.answer_callback_query(callback_query.id)

    def _standardize_message(self, message: types.Message) -> Dict[str, Any]:
        """Convert Telegram message to standardized format"""
        return {
            'platform': 'telegram',
            'user_id': str(message.from_user.id),
            'chat_id': str(message.chat.id),
            'text': message.text or '',
            'message_id': str(message.message_id),
            'user_info': {
                'first_name': message.from_user.first_name,
                'last_name': message.from_user.last_name or '',
                'username': message.from_user.username or '',
                'language_code': message.from_user.language_code or 'en'
            },
            'timestamp': message.date.isoformat() if message.date else datetime.now().isoformat(),
            'type': 'message'
        }

    def _standardize_callback(self, callback_query: types.CallbackQuery) -> Dict[str, Any]:
        """Convert callback query to standardized format"""
        return {
            'platform': 'telegram',
            'user_id': str(callback_query.from_user.id),
            'callback_data': callback_query.data,
            'message_id': str(callback_query.message.message_id) if callback_query.message else '',
            'user_info': {
                'first_name': callback_query.from_user.first_name,
                'last_name': callback_query.from_user.last_name or '',
                'username': callback_query.from_user.username or '',
                'language_code': callback_query.from_user.language_code or 'en'
            },
            'timestamp': datetime.now().isoformat(),
            'type': 'callback'
        }

    async def send_message(
        self,
        user_id: str,
        text: str,
        parse_mode: str = None,
        disable_web_page_preview: bool = False
    ) -> bool:
        """Send message to Telegram user"""
        try:
            await self.bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_web_page_preview
            )
            return True
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False

    async def send_message_with_keyboard(
        self,
        user_id: str,
        text: str,
        keyboard: Dict[str, Any],
        parse_mode: str = 'Markdown'
    ) -> bool:
        """Send message with keyboard"""
        try:
            # Convert standardized keyboard to Telegram format
            markup = self._convert_keyboard(keyboard)

            await self.bot.send_message(
                chat_id=user_id,
                text=text,
                reply_markup=markup,
                parse_mode=parse_mode
            )
            return True
        except Exception as e:
            logger.error(f"Error sending Telegram message with keyboard: {e}")
            return False

    def _convert_keyboard(self, keyboard: Dict[str, Any]) -> types.InlineKeyboardMarkup:
        """Convert standardized keyboard to Telegram InlineKeyboardMarkup"""
        buttons = keyboard.get('buttons', [])
        inline_keyboard = []

        for row in buttons:
            inline_row = []
            for button in row:
                inline_row.append(
                    types.InlineKeyboardButton(
                        text=button.get('text', ''),
                        callback_data=button.get('callback_data', ''),
                        url=button.get('url')
                    )
                )
            inline_keyboard.append(inline_row)

        return types.InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

    async def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a Telegram user"""
        try:
            user = await self.bot.get_chat(user_id)
            return {
                'id': str(user.id),
                'first_name': user.first_name,
                'last_name': user.last_name or '',
                'username': user.username or '',
            }
        except Exception as e:
            logger.error(f"Error getting Telegram user info: {e}")
            return None

    async def process_queue(self):
        """Process messages from queue and send to bot service"""
        while self.is_running:
            try:
                message = await asyncio.wait_for(
                    self.message_queue.get(),
                    timeout=1.0
                )
                await self._route_message(message)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing queue: {e}")

    async def _route_message(self, message: Dict[str, Any]):
        """Route message to bot service"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f'{self.bot_service_url}/message',
                    json=message
                ) as response:
                    if response.status != 200:
                        text = await response.text()
                        logger.warning(f"Bot service error: {text}")
        except Exception as e:
            logger.error(f"Error routing message: {e}")

    async def start(self):
        """Start the adapter"""
        self.is_running = True

        # Start queue processor
        asyncio.create_task(self.process_queue())

        # Start polling
        logger.info("Starting Telegram adapter...")
        await self.dp.start_polling(self.bot)

    async def stop(self):
        """Stop the adapter"""
        self.is_running = False
        await self.bot.session.close()


async def main():
    """Main entry point"""
    adapter = TelegramAdapter()

    try:
        await adapter.start()
    except KeyboardInterrupt:
        await adapter.stop()


if __name__ == '__main__':
    asyncio.run(main())
