"""
Registration dialog for new users
"""
import re
from typing import Dict, Any, Optional

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from api_client import api_client
from keyboards import get_role_keyboard, get_main_keyboard


class RegistrationStates(StatesGroup):
    """Registration dialog states"""
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_email = State()
    waiting_for_role = State()


router = Router()


def validate_name(name: str) -> bool:
    """Validate name format (allows Russian, Latin, spaces, hyphens)"""
    return bool(re.match(r'^[\u0400-\u04FF a-zA-Z\-]{2,50}$', name.strip()))


def validate_phone(phone: str) -> bool:
    """Validate phone format"""
    return bool(re.match(r'^\+?[1-9]\d{10,14}$', phone))


def validate_email(email: str) -> bool:
    """Validate email format"""
    return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email))


@router.message(RegistrationStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    """Process name input"""
    name = message.text.strip()

    if not validate_name(name):
        await message.answer(
            "Please enter a valid name (letters only, 2-50 characters)."
        )
        return

    await state.update_data(name=name)
    await state.set_state(RegistrationStates.waiting_for_phone)
    await message.answer(
        f"Great, {name}!\n\n"
        "Now please enter your phone number (e.g., +79991234567):"
    )


@router.message(RegistrationStates.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    """Process phone input"""
    phone = message.text.strip()

    if not validate_phone(phone):
        await message.answer(
            "Please enter a valid phone number (e.g., +79991234567)."
        )
        return

    if not phone.startswith('+'):
        phone = '+' + phone

    await state.update_data(phone=phone)
    await state.set_state(RegistrationStates.waiting_for_email)
    await message.answer(
        "Thank you! Now please enter your email address:"
    )


@router.message(RegistrationStates.waiting_for_email)
async def process_email(message: Message, state: FSMContext):
    """Process email input"""
    email = message.text.strip().lower()

    if not validate_email(email):
        await message.answer(
            "Please enter a valid email address."
        )
        return

    await state.update_data(email=email)
    await state.set_state(RegistrationStates.waiting_for_role)
    await message.answer(
        "Almost done! Please select your role:",
        reply_markup=get_role_keyboard()
    )


@router.callback_query(F.data.startswith("role_"), RegistrationStates.waiting_for_role)
async def process_role(callback: CallbackQuery, state: FSMContext):
    """Process role selection"""
    role = callback.data.split("_")[1]

    data = await state.get_data()

    # Register user via API
    user_data = {
        "platform": "telegram",
        "platform_user_id": str(callback.from_user.id),
        "username": callback.from_user.username or "",
        "first_name": data.get("name", callback.from_user.first_name),
        "last_name": "",
        "phone": data.get("phone", ""),
        "email": data.get("email", ""),
        "role": role,
        "language_code": callback.from_user.language_code or "en"
    }

    result = await api_client.register_user(user_data)

    await state.clear()

    if result:
        role_display = {
            "buyer": "Buyer",
            "organizer": "Organizer",
            "supplier": "Supplier"
        }.get(role, role)

        await callback.message.edit_text(
            f"Registration complete!\n\n"
            f"You are registered as: {role_display}\n\n"
            f"Use the menu below to navigate.",
            reply_markup=None
        )
        await callback.message.answer(
            "Welcome to GroupBuy Bot!",
            reply_markup=get_main_keyboard(role)
        )
    else:
        await callback.message.edit_text(
            "Registration failed. Please try again later.\n"
            "Use /start to restart.",
            reply_markup=None
        )

    await callback.answer()


async def start_registration(message: Message, state: FSMContext):
    """Start the registration process"""
    await state.set_state(RegistrationStates.waiting_for_name)
    await message.answer(
        "Welcome to GroupBuy Bot!\n\n"
        "Let's get you registered.\n\n"
        "Please enter your name:"
    )
