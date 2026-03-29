"""
Main entry point for the GroupBuy Bot
"""
import asyncio
import json
import logging
import sys

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from handlers import user_commands, procurement_commands
from dialogs import registration
from message_processor import process_platform_message


# Configure logging
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


async def handle_message_endpoint(request: web.Request) -> web.Response:
    """HTTP endpoint for platform adapters (Mattermost, WhatsApp, etc.)"""
    try:
        message = await request.json()
        await process_platform_message(message)
        return web.json_response({'ok': True})
    except Exception as e:
        logger.error(f"Error processing platform message: {e}")
        return web.json_response({'error': str(e)}, status=500)


async def health_check(request: web.Request) -> web.Response:
    return web.json_response({'status': 'healthy'})


async def start_http_server():
    """Start HTTP server for adapter integrations"""
    app = web.Application()
    app.router.add_post('/message', handle_message_endpoint)
    app.router.add_get('/health', health_check)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', config.http_port)
    await site.start()
    logger.info(f"Bot HTTP server started on port {config.http_port}")
    return runner


async def main():
    """Main function to start the bot"""

    # Start HTTP server for platform adapters
    http_runner = await start_http_server()

    # Check for Telegram token (optional - bot can run without Telegram)
    if not config.telegram_token:
        logger.warning("TELEGRAM_TOKEN is not set - Telegram integration disabled")
        try:
            await asyncio.Event().wait()
        finally:
            await http_runner.cleanup()
        return

    # Initialize bot and dispatcher
    bot = Bot(
        token=config.telegram_token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Register routers
    dp.include_router(user_commands.router)
    dp.include_router(procurement_commands.router)
    dp.include_router(registration.router)

    logger.info("Starting GroupBuy Bot...")

    try:
        # Delete webhook and start polling
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await http_runner.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
