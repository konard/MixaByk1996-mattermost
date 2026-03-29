"""
Configure sys.path so bot modules can be imported during tests.
"""
import sys
import os

# Add bot/ directory to path so bot code can do: from api_client import ...
bot_dir = os.path.join(os.path.dirname(__file__), '..', 'bot')
if bot_dir not in sys.path:
    sys.path.insert(0, os.path.abspath(bot_dir))
