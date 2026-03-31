"""
Tests for bot commands
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch


class TestRegistrationDialog:
    """Tests for registration dialog"""

    def test_validate_name_valid(self):
        """Test valid name validation"""
        from bot.dialogs.registration import validate_name

        assert validate_name("John") is True
        assert validate_name("John Doe") is True
        assert validate_name("Ivan") is True

    def test_validate_name_invalid(self):
        """Test invalid name validation"""
        from bot.dialogs.registration import validate_name

        assert validate_name("J") is False  # Too short
        assert validate_name("123") is False  # Numbers
        assert validate_name("") is False  # Empty

    def test_validate_phone_valid(self):
        """Test valid phone validation"""
        from bot.dialogs.registration import validate_phone

        assert validate_phone("+79991234567") is True
        assert validate_phone("79991234567") is True
        assert validate_phone("+1234567890123") is True

    def test_validate_phone_invalid(self):
        """Test invalid phone validation"""
        from bot.dialogs.registration import validate_phone

        assert validate_phone("123") is False  # Too short
        assert validate_phone("") is False  # Empty
        assert validate_phone("not a phone") is False

    def test_validate_email_valid(self):
        """Test valid email validation"""
        from bot.dialogs.registration import validate_email

        assert validate_email("test@example.com") is True
        assert validate_email("user.name@domain.org") is True

    def test_validate_email_invalid(self):
        """Test invalid email validation"""
        from bot.dialogs.registration import validate_email

        assert validate_email("not an email") is False
        assert validate_email("@domain.com") is False
        assert validate_email("user@") is False


class TestKeyboards:
    """Tests for keyboard utilities"""

    def test_get_main_keyboard_buyer(self):
        """Test main keyboard for buyer"""
        from bot.keyboards import get_main_keyboard

        keyboard = get_main_keyboard("buyer")
        assert keyboard is not None
        assert len(keyboard.keyboard) > 0

    def test_get_main_keyboard_organizer(self):
        """Test main keyboard for organizer"""
        from bot.keyboards import get_main_keyboard

        keyboard = get_main_keyboard("organizer")
        assert keyboard is not None
        # Organizer should have "Create Procurement" button
        buttons = [btn.text for row in keyboard.keyboard for btn in row]
        assert "Create Procurement" in buttons

    def test_get_role_keyboard(self):
        """Test role selection keyboard"""
        from bot.keyboards import get_role_keyboard

        keyboard = get_role_keyboard()
        assert keyboard is not None
        assert len(keyboard.inline_keyboard) > 0

    def test_get_deposit_keyboard(self):
        """Test deposit amount keyboard"""
        from bot.keyboards import get_deposit_keyboard

        keyboard = get_deposit_keyboard()
        assert keyboard is not None
        # Should have predefined amounts
        callbacks = [btn.callback_data for row in keyboard.inline_keyboard for btn in row]
        assert "deposit_100" in callbacks
        assert "deposit_custom" in callbacks


class TestProcurementFormatting:
    """Tests for procurement formatting"""

    def test_get_status_emoji(self):
        """Test status emoji mapping"""
        from bot.handlers.procurement_commands import get_status_emoji

        assert get_status_emoji("active") != ""
        assert get_status_emoji("completed") != ""
        assert get_status_emoji("unknown") == ""

    def test_format_procurement_details(self):
        """Test procurement details formatting"""
        from bot.handlers.procurement_commands import format_procurement_details

        procurement = {
            "title": "Test Procurement",
            "description": "Test description",
            "organizer_name": "Test Organizer",
            "category_name": "General",
            "city": "Test City",
            "target_amount": 10000,
            "current_amount": 5000,
            "progress": 50,
            "participant_count": 5,
            "unit": "units",
            "deadline": "2025-12-31T00:00:00",
            "status": "active",
            "status_display": "Active",
            "can_join": True
        }

        result = format_procurement_details(procurement)

        assert "Test Procurement" in result
        assert "Test description" in result
        assert "50%" in result
        assert "can join" in result.lower()


class TestAPIClient:
    """Tests for API client"""

    @pytest.mark.asyncio
    async def test_check_user_exists(self):
        """Test user existence check"""
        from bot.api_client import APIClient

        client = APIClient(base_url="http://localhost:8000/api")

        with patch.object(client, '_request', new_callable=AsyncMock) as mock:
            mock.return_value = {"exists": True}

            result = await client.check_user_exists("telegram", "12345")
            assert result is True

            mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_procurements(self):
        """Test getting procurements"""
        from bot.api_client import APIClient

        client = APIClient(base_url="http://localhost:8000/api")

        with patch.object(client, '_request', new_callable=AsyncMock) as mock:
            mock.return_value = {
                "results": [
                    {"id": 1, "title": "Test 1"},
                    {"id": 2, "title": "Test 2"}
                ]
            }

            result = await client.get_procurements(status="active")
            assert len(result) == 2
            assert result[0]["title"] == "Test 1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
