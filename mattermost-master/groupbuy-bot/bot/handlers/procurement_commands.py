"""
Procurement command handlers
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from api_client import api_client
from keyboards import (
    get_procurements_keyboard, get_procurement_detail_keyboard,
    get_categories_keyboard, get_main_keyboard
)


class ProcurementCreationStates(StatesGroup):
    """States for procurement creation"""
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_category = State()
    waiting_for_target_amount = State()
    waiting_for_unit = State()
    waiting_for_city = State()
    waiting_for_deadline = State()
    waiting_for_stop_amount = State()
    confirmation = State()


class JoinProcurementStates(StatesGroup):
    """States for joining procurement"""
    waiting_for_quantity = State()


router = Router()


@router.message(Command("procurements"))
async def cmd_procurements(message: Message):
    """Handle /procurements command"""
    procurements = await api_client.get_procurements(status="active")

    if not procurements:
        await message.answer("No active procurements available.")
        return

    await message.answer(
        f"*Active Procurements ({len(procurements)})*\n\n"
        "Select a procurement to view details:",
        parse_mode="Markdown",
        reply_markup=get_procurements_keyboard(procurements)
    )


@router.message(F.text == "Procurements")
async def text_procurements(message: Message):
    """Handle 'Procurements' text button"""
    await cmd_procurements(message)


@router.message(Command("my_procurements"))
async def cmd_my_procurements(message: Message):
    """Handle /my_procurements command"""
    user = await api_client.get_user_by_platform(
        platform="telegram",
        platform_user_id=str(message.from_user.id)
    )

    if not user:
        await message.answer("You are not registered. Use /start to register.")
        return

    result = await api_client.get_user_procurements(user["id"])

    if not result:
        await message.answer("You don't have any procurements.")
        return

    organized = result.get("organized", [])
    participating = result.get("participating", [])

    response = ""

    if organized:
        response += "*Your Organized Procurements:*\n\n"
        for proc in organized[:5]:
            status_emoji = get_status_emoji(proc.get("status", ""))
            response += (
                f"{status_emoji} *{proc.get('title', '')}*\n"
                f"  Status: {proc.get('status', '')}\n"
                f"  Collected: {proc.get('current_amount', 0)}/{proc.get('target_amount', 0)} RUB\n"
                f"  Participants: {proc.get('participant_count', 0)}\n"
                f"  Days left: {proc.get('days_left', 0)}\n\n"
            )

    if participating:
        response += "\n*Procurements You're In:*\n\n"
        for proc in participating[:5]:
            status_emoji = get_status_emoji(proc.get("status", ""))
            response += (
                f"{status_emoji} *{proc.get('title', '')}*\n"
                f"  Your amount: {proc.get('my_amount', 0)} RUB\n"
                f"  Progress: {proc.get('progress', 0)}%\n\n"
            )

    if not response:
        response = "You don't have any procurements."

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Refresh", callback_data="refresh_my_procurements"),
            InlineKeyboardButton(text="Stats", callback_data="procurement_stats")
        ]
    ])

    await message.answer(
        response,
        parse_mode="Markdown",
        reply_markup=keyboard
    )


@router.message(F.text == "My Orders")
async def text_my_orders(message: Message):
    """Handle 'My Orders' text button"""
    await cmd_my_procurements(message)


@router.callback_query(F.data.startswith("view_proc_"))
async def view_procurement(callback: CallbackQuery):
    """View procurement details"""
    procurement_id = int(callback.data.split("_")[2])

    user = await api_client.get_user_by_platform(
        platform="telegram",
        platform_user_id=str(callback.from_user.id)
    )

    user_id = user["id"] if user else None

    procurement = await api_client.get_procurement_details(procurement_id, user_id)

    if not procurement:
        await callback.answer("Procurement not found", show_alert=True)
        return

    message_text = format_procurement_details(procurement)

    await callback.message.edit_text(
        message_text,
        parse_mode="Markdown",
        reply_markup=get_procurement_detail_keyboard(
            procurement_id,
            procurement.get("can_join", False)
        )
    )
    await callback.answer()


@router.callback_query(F.data.startswith("join_proc_"))
async def join_procurement(callback: CallbackQuery, state: FSMContext):
    """Start joining a procurement"""
    procurement_id = int(callback.data.split("_")[2])

    await state.update_data(procurement_id=procurement_id)
    await state.set_state(JoinProcurementStates.waiting_for_quantity)

    await callback.message.edit_text(
        "Enter the quantity you want to order:",
        reply_markup=None
    )
    await callback.answer()


@router.message(JoinProcurementStates.waiting_for_quantity)
async def process_join_quantity(message: Message, state: FSMContext):
    """Process quantity for joining"""
    try:
        quantity = float(message.text)
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
    except ValueError:
        await message.answer("Please enter a valid positive number.")
        return

    data = await state.get_data()
    procurement_id = data.get("procurement_id")

    # Get procurement to calculate amount
    procurement = await api_client.get_procurement_details(procurement_id)

    if not procurement:
        await message.answer("Procurement not found.")
        await state.clear()
        return

    price_per_unit = float(procurement.get("price_per_unit", 0)) or 100
    amount = quantity * price_per_unit

    user = await api_client.get_user_by_platform(
        platform="telegram",
        platform_user_id=str(message.from_user.id)
    )

    if not user:
        await message.answer("You are not registered.")
        await state.clear()
        return

    result = await api_client.join_procurement(
        procurement_id=procurement_id,
        user_id=user["id"],
        quantity=quantity,
        amount=amount
    )

    await state.clear()

    if result:
        await message.answer(
            f"Successfully joined!\n\n"
            f"Quantity: {quantity}\n"
            f"Amount: {amount} RUB\n\n"
            f"You can now access the procurement chat.",
            reply_markup=get_main_keyboard(user.get("role", "buyer"))
        )
    else:
        await message.answer(
            "Failed to join procurement. Please try again.",
            reply_markup=get_main_keyboard(user.get("role", "buyer"))
        )


@router.callback_query(F.data.startswith("refresh_proc_"))
async def refresh_procurement(callback: CallbackQuery):
    """Refresh procurement details"""
    procurement_id = int(callback.data.split("_")[2])
    # Reuse view_procurement logic
    callback.data = f"view_proc_{procurement_id}"
    await view_procurement(callback)


@router.callback_query(F.data == "back_to_procurements")
async def back_to_procurements(callback: CallbackQuery):
    """Go back to procurements list"""
    procurements = await api_client.get_procurements(status="active")

    if not procurements:
        await callback.message.edit_text("No active procurements available.")
        return

    await callback.message.edit_text(
        f"*Active Procurements ({len(procurements)})*\n\n"
        "Select a procurement to view details:",
        parse_mode="Markdown",
        reply_markup=get_procurements_keyboard(procurements)
    )
    await callback.answer()


@router.callback_query(F.data == "filter_city")
async def filter_by_city(callback: CallbackQuery):
    """Filter procurements by city"""
    await callback.message.edit_text(
        "Enter city name to filter:",
        reply_markup=None
    )
    # Would need state handling for city input
    await callback.answer("Feature coming soon", show_alert=True)


@router.callback_query(F.data == "filter_category")
async def filter_by_category(callback: CallbackQuery):
    """Filter procurements by category"""
    categories = await api_client.get_categories()

    if not categories:
        await callback.answer("No categories available", show_alert=True)
        return

    await callback.message.edit_text(
        "Select category:",
        reply_markup=get_categories_keyboard(categories)
    )
    await callback.answer()


@router.message(Command("create_procurement"))
async def cmd_create_procurement(message: Message, state: FSMContext):
    """Handle /create_procurement command"""
    user = await api_client.get_user_by_platform(
        platform="telegram",
        platform_user_id=str(message.from_user.id)
    )

    if not user:
        await message.answer("You are not registered. Use /start to register.")
        return

    if user.get("role") != "organizer":
        await message.answer(
            "Only organizers can create procurements.\n"
            "Change your role in /profile to become an organizer."
        )
        return

    await state.update_data(organizer_id=user["id"])
    await state.set_state(ProcurementCreationStates.waiting_for_title)

    await message.answer(
        "*Create New Procurement*\n\n"
        "Enter the title for your procurement:",
        parse_mode="Markdown"
    )


@router.message(F.text == "Create Procurement")
async def text_create_procurement(message: Message, state: FSMContext):
    """Handle 'Create Procurement' text button"""
    await cmd_create_procurement(message, state)


@router.message(ProcurementCreationStates.waiting_for_title)
async def process_title(message: Message, state: FSMContext):
    """Process procurement title"""
    title = message.text.strip()

    if len(title) < 5:
        await message.answer("Title must be at least 5 characters.")
        return

    await state.update_data(title=title)
    await state.set_state(ProcurementCreationStates.waiting_for_description)

    await message.answer("Enter description for the procurement:")


@router.message(ProcurementCreationStates.waiting_for_description)
async def process_description(message: Message, state: FSMContext):
    """Process procurement description"""
    description = message.text.strip()

    if len(description) < 10:
        await message.answer("Description must be at least 10 characters.")
        return

    await state.update_data(description=description)
    await state.set_state(ProcurementCreationStates.waiting_for_target_amount)

    await message.answer("Enter target amount in RUB (minimum 1000):")


@router.message(ProcurementCreationStates.waiting_for_target_amount)
async def process_target_amount(message: Message, state: FSMContext):
    """Process target amount"""
    try:
        amount = float(message.text)
        if amount < 1000:
            await message.answer("Minimum target amount is 1000 RUB.")
            return
    except ValueError:
        await message.answer("Please enter a valid number.")
        return

    await state.update_data(target_amount=amount)
    await state.set_state(ProcurementCreationStates.waiting_for_city)

    await message.answer("Enter city for the procurement:")


@router.message(ProcurementCreationStates.waiting_for_city)
async def process_city(message: Message, state: FSMContext):
    """Process city"""
    city = message.text.strip()

    if len(city) < 2:
        await message.answer("Please enter a valid city name.")
        return

    await state.update_data(city=city)

    data = await state.get_data()

    # Create the procurement (deadline 90 days from now)
    from datetime import datetime, timezone, timedelta
    deadline = (datetime.now(timezone.utc) + timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ")

    procurement_data = {
        "title": data.get("title"),
        "description": data.get("description"),
        "target_amount": data.get("target_amount"),
        "city": city,
        "organizer_id": data.get("organizer_id"),
        "deadline": deadline,
        "unit": "units",
        "status": "active"
    }

    result = await api_client.create_procurement(procurement_data)

    await state.clear()

    if result:
        await message.answer(
            f"Procurement created successfully!\n\n"
            f"*{result.get('title', '')}*\n"
            f"Target: {result.get('target_amount', 0)} RUB\n"
            f"City: {result.get('city', '')}\n\n"
            f"Share with potential participants to start collecting!",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard("organizer")
        )
    else:
        await message.answer(
            "Failed to create procurement. Please try again.",
            reply_markup=get_main_keyboard("organizer")
        )


def get_status_emoji(status: str) -> str:
    """Get emoji for procurement status"""
    emoji_map = {
        "draft": "\U0001F4DD",       # 📝
        "active": "\u2705",           # ✅
        "stopped": "\u23F8\uFE0F",    # ⏸️
        "payment": "\U0001F4B3",      # 💳
        "completed": "\u2714\uFE0F",  # ✔️
        "cancelled": "\u274C",        # ❌
    }
    return emoji_map.get(status, "")


def format_procurement_details(procurement: dict) -> str:
    """Format procurement details for display"""
    status_emoji = get_status_emoji(procurement.get("status", ""))

    text = f"{status_emoji} *{procurement.get('title', '')}*\n\n"
    text += f"*Description:* {procurement.get('description', '')}\n\n"
    text += f"*Organizer:* {procurement.get('organizer_name', 'Unknown')}\n"
    text += f"*Category:* {procurement.get('category_name', 'General')}\n"
    text += f"*City:* {procurement.get('city', 'Unknown')}\n\n"
    text += f"*Target:* {procurement.get('target_amount', 0)} RUB\n"
    text += f"*Collected:* {procurement.get('current_amount', 0)} RUB ({procurement.get('progress', 0)}%)\n"
    text += f"*Participants:* {procurement.get('participant_count', 0)}\n"
    text += f"*Unit:* {procurement.get('unit', 'units')}\n\n"
    text += f"*Deadline:* {procurement.get('deadline', '')[:10]}\n"
    text += f"*Status:* {procurement.get('status_display', procurement.get('status', ''))}\n"

    if procurement.get("stop_at_amount"):
        text += f"*Stop amount:* {procurement.get('stop_at_amount')} RUB\n"

    if procurement.get("can_join"):
        text += "\n*You can join this procurement!*"

    return text
