import asyncio
import json
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, InputFile

# Constants
TOKEN = '8096949835:AAHrXR7aY9QnUr_JJhYb9N06dYdVvMfBhMo'
DB_FILE = 'trades.json'

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

# FSM States
class AddTrade(StatesGroup):
    date = State()
    pair = State()
    result = State()
    comment = State()
    screenshot = State()

class EditTrade(StatesGroup):
    field = State()
    value = State()

# Keyboards
main_keyboard = types.ReplyKeyboardMarkup(
    keyboard=[
        [types.KeyboardButton(text="Add Trade"), types.KeyboardButton(text="History")],
    ],
    resize_keyboard=True
)

cancel_keyboard = types.ReplyKeyboardMarkup(
    keyboard=[[types.KeyboardButton(text="Cancel")]],
    resize_keyboard=True
)

back_cancel_keyboard = types.InlineKeyboardMarkup(
    inline_keyboard=[
        [types.InlineKeyboardButton(text="Back", callback_data="back")],
        [types.InlineKeyboardButton(text="Cancel", callback_data="cancel")]
    ]
)

def filters_keyboard():
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="All", callback_data="filter_all"),
             types.InlineKeyboardButton(text="Profitable", callback_data="filter_profitable"),
             types.InlineKeyboardButton(text="Losing", callback_data="filter_losing")],
            [types.InlineKeyboardButton(text="Back", callback_data="back"),
             types.InlineKeyboardButton(text="Cancel", callback_data="cancel")]
        ]
    )

def edit_delete_keyboard(trade_id):
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="Edit", callback_data=f"edit_{trade_id}")],
            [types.InlineKeyboardButton(text="Delete", callback_data=f"delete_{trade_id}")],
            [types.InlineKeyboardButton(text="Back", callback_data="back"),
             types.InlineKeyboardButton(text="Cancel", callback_data="cancel")]
        ]
    )

# Helpers
def load_trades():
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, 'r') as f:
        return json.load(f)

def save_trades(trades):
    with open(DB_FILE, 'w') as f:
        json.dump(trades, f, indent=4)

def generate_trade_id():
    return str(int(datetime.now().timestamp() * 1000))

# Handlers
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer("Welcome to your Trading Journal!", reply_markup=main_keyboard)

@dp.message(lambda m: m.text == "Add Trade")
async def start_add_trade(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Enter the date (e.g., 2025-04-26):", reply_markup=cancel_keyboard)
    await state.set_state(AddTrade.date)

@dp.message(lambda m: m.text == "Cancel")
async def cancel_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Operation canceled.", reply_markup=main_keyboard)

@dp.message(AddTrade.date)
async def add_trade_date(message: types.Message, state: FSMContext):
    await state.update_data(date=message.text)
    await message.answer("Enter the trading pair (e.g., BTC/USDT):")
    await state.set_state(AddTrade.pair)

@dp.message(AddTrade.pair)
async def add_trade_pair(message: types.Message, state: FSMContext):
    await state.update_data(pair=message.text)
    await message.answer("Enter the result (%) (e.g., 5 or -3):")
    await state.set_state(AddTrade.result)

@dp.message(AddTrade.result)
async def add_trade_result(message: types.Message, state: FSMContext):
    await state.update_data(result=message.text)
    await message.answer("Enter a comment:")
    await state.set_state(AddTrade.comment)

@dp.message(AddTrade.comment)
async def add_trade_comment(message: types.Message, state: FSMContext):
    await state.update_data(comment=message.text)
    await message.answer("Send a screenshot or type 'Skip':")
    await state.set_state(AddTrade.screenshot)

@dp.message(AddTrade.screenshot)
async def add_trade_screenshot(message: types.Message, state: FSMContext):
    data = await state.get_data()
    trades = load_trades()

    screenshot = None
    if message.photo:
        screenshot = message.photo[-1].file_id
    elif message.text.lower() != 'skip':
        screenshot = message.text

    new_trade = {
        "id": generate_trade_id(),
        "date": data['date'],
        "pair": data['pair'],
        "result": data['result'],
        "comment": data['comment'],
        "screenshot": screenshot
    }

    trades.append(new_trade)
    save_trades(trades)

    await message.answer("Trade saved!", reply_markup=main_keyboard)
    await state.clear()

@dp.message(lambda m: m.text == "History")
async def history_start(message: types.Message, state: FSMContext):
    trades = load_trades()
    if not trades:
        await message.answer("No trades yet.", reply_markup=main_keyboard)
        return

    years = sorted(set(t['date'][:4] for t in trades))
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[[types.InlineKeyboardButton(text=year, callback_data=f"year_{year}")] for year in years] + [
            [types.InlineKeyboardButton(text="Back", callback_data="back"),
             types.InlineKeyboardButton(text="Cancel", callback_data="cancel")]
        ]
    )
    await message.answer("Choose a year:", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith("year_"))
async def choose_year(call: CallbackQuery, state: FSMContext):
    year = call.data.split("_")[1]
    trades = load_trades()
    months = sorted(set(t['date'][5:7] for t in trades if t['date'].startswith(year)))

    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[[types.InlineKeyboardButton(text=month, callback_data=f"month_{year}_{month}")] for month in months] + [
            [types.InlineKeyboardButton(text="Back", callback_data="back"),
             types.InlineKeyboardButton(text="Cancel", callback_data="cancel")]
        ]
    )
    await call.message.edit_text("Choose a month:", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith("month_"))
async def choose_month(call: CallbackQuery, state: FSMContext):
    _, year, month = call.data.split("_")
    await state.update_data(selected_year=year, selected_month=month)
    await call.message.edit_text("Choose a filter:", reply_markup=filters_keyboard())

@dp.callback_query(lambda c: c.data.startswith("filter_"))
async def filter_trades(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    year = data['selected_year']
    month = data['selected_month']
    filter_type = call.data.split("_")[1]

    trades = load_trades()
    filtered = [
        t for t in trades if t['date'].startswith(f"{year}-{month}")
    ]

    if filter_type == "profitable":
        filtered = [t for t in filtered if float(t['result']) > 0]
    elif filter_type == "losing":
        filtered = [t for t in filtered if float(t['result']) <= 0]

    if not filtered:
        await call.message.edit_text("No trades found.", reply_markup=back_cancel_keyboard)
        return

    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(
                text=f"{t['date']} | {t['pair']} | {t['result']}%",
                callback_data=f"view_{t['id']}"
            )] for t in filtered
        ] + [
            [types.InlineKeyboardButton(text="Back", callback_data="back"),
             types.InlineKeyboardButton(text="Cancel", callback_data="cancel")]
        ]
    )

    await call.message.edit_text("Choose a trade:", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith("view_"))
async def view_trade(call: CallbackQuery, state: FSMContext):
    trade_id = call.data.split("_")[1]
    trades = load_trades()
    trade = next((t for t in trades if t['id'] == trade_id), None)

    if not trade:
        await call.message.edit_text("Trade not found.", reply_markup=back_cancel_keyboard)
        return

    text = (
        f"<b>Date:</b> {trade['date']}\n"
        f"<b>Pair:</b> {trade['pair']}\n"
        f"<b>Result:</b> {trade['result']}%\n"
        f"<b>Comment:</b> {trade['comment']}"
    )

    if trade['screenshot']:
        await call.message.answer_photo(trade['screenshot'], caption=text, reply_markup=edit_delete_keyboard(trade_id))
    else:
        await call.message.edit_text(text, reply_markup=edit_delete_keyboard(trade_id))

@dp.callback_query(lambda c: c.data.startswith("edit_"))
async def edit_trade(call: CallbackQuery, state: FSMContext):
    trade_id = call.data.split("_")[1]
    await state.update_data(editing_id=trade_id)
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="Date", callback_data="editfield_date"),
             types.InlineKeyboardButton(text="Pair", callback_data="editfield_pair")],
            [types.InlineKeyboardButton(text="Result", callback_data="editfield_result"),
             types.InlineKeyboardButton(text="Comment", callback_data="editfield_comment")],
            [types.InlineKeyboardButton(text="Screenshot", callback_data="editfield_screenshot")],
            [types.InlineKeyboardButton(text="Back", callback_data="back"),
             types.InlineKeyboardButton(text="Cancel", callback_data="cancel")]
        ]
    )
    await call.message.edit_text("Choose a field to edit:", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith("editfield_"))
async def edit_field(call: CallbackQuery, state: FSMContext):
    field = call.data.split("_")[1]
    await state.update_data(edit_field=field)
    await call.message.edit_text(f"Send new {field} value or type 'Skip':", reply_markup=cancel_keyboard)
    await state.set_state(EditTrade.value)

@dp.message(EditTrade.value)
async def save_edited_field(message: types.Message, state: FSMContext):
    data = await state.get_data()
    trade_id = data['editing_id']
    field = data['edit_field']
    trades = load_trades()

    for trade in trades:
        if trade['id'] == trade_id:
            if field == "screenshot" and message.photo:
                trade[field] = message.photo[-1].file_id
            elif message.text.lower() != "skip":
                trade[field] = message.text
            break

    save_trades(trades)
    await message.answer("Trade updated successfully!", reply_markup=main_keyboard)
    await state.clear()

# Start polling
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
