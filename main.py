import sqlite3
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile
from datetime import datetime
import asyncio

# --- Config ---
TOKEN = "8096949835:AAHrXR7aY9QnUr_JJhYb9N06dYdVvMfBhMo"

bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# --- Database ---
conn = sqlite3.connect("trades.db")
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS trades (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, pair TEXT, percent REAL, description TEXT)''')
conn.commit()

# --- States ---
class TradeStates(StatesGroup):
    adding_date = State()
    adding_pair = State()
    adding_percent = State()
    adding_description = State()

    editing_date = State()
    editing_pair = State()
    editing_percent = State()
    editing_description = State()

# --- Keyboards ---
def main_menu():
    kb = [
        [InlineKeyboardButton(text="➕ Add Trade", callback_data="add_trade")],
        [InlineKeyboardButton(text="📚 History", callback_data="view_history")],
        [InlineKeyboardButton(text="📈 Winrate", callback_data="view_winrate")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def trade_filters(year, month):
    kb = [
        [
            InlineKeyboardButton(text="All", callback_data=f"filter_all:{year}:{month}"),
            InlineKeyboardButton(text="Profit", callback_data=f"filter_profit:{year}:{month}"),
            InlineKeyboardButton(text="Loss", callback_data=f"filter_loss:{year}:{month}")
        ],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="back_to_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def edit_delete_kb(trade_id):
    kb = [
        [
            InlineKeyboardButton(text="✏️ Edit", callback_data=f"edit_trade:{trade_id}"),
            InlineKeyboardButton(text="🗑️ Delete", callback_data=f"delete_trade:{trade_id}")
        ],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="back_to_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- Handlers ---
@router.message(CommandStart())
async def start_handler(message: Message):
    await message.answer("Welcome to your Trading Journal!", reply_markup=main_menu())

@router.callback_query(lambda c: c.data == "add_trade")
async def add_trade(call: CallbackQuery, state: FSMContext):
    await call.message.answer("Enter date (YYYY-MM-DD):")
    await state.set_state(TradeStates.adding_date)

@router.message(TradeStates.adding_date)
async def add_date(message: Message, state: FSMContext):
    await state.update_data(date=message.text)
    await message.answer("Enter trading pair (e.g., BTC/USDT):")
    await state.set_state(TradeStates.adding_pair)

@router.message(TradeStates.adding_pair)
async def add_pair(message: Message, state: FSMContext):
    await state.update_data(pair=message.text)
    await message.answer("Enter percent result (e.g., 2.5 or -1.2):")
    await state.set_state(TradeStates.adding_percent)

@router.message(TradeStates.adding_percent)
async def add_percent(message: Message, state: FSMContext):
    await state.update_data(percent=float(message.text))
    await message.answer("Enter short description:")
    await state.set_state(TradeStates.adding_description)

@router.message(TradeStates.adding_description)
async def add_description(message: Message, state: FSMContext):
    data = await state.get_data()
    c.execute("INSERT INTO trades (date, pair, percent, description) VALUES (?, ?, ?, ?)",
              (data['date'], data['pair'], data['percent'], message.text))
    conn.commit()
    await message.answer("Trade saved!", reply_markup=main_menu())
    await state.clear()

@router.callback_query(lambda c: c.data == "view_history")
async def view_history(call: CallbackQuery, state: FSMContext):
    now = datetime.now()
    year = now.year
    month = now.month
    await call.message.answer("Choose filter:", reply_markup=trade_filters(year, month))

@router.callback_query(F.data.startswith("filter_"))
async def filter_trades(call: CallbackQuery, state: FSMContext):
    filter_type, year, month = call.data.split(":")
    year, month = int(year), int(month)
    
    start = f"{year}-{month:02d}-01"
    end_month = month + 1 if month < 12 else 1
    end_year = year if month < 12 else year + 1
    end = f"{end_year}-{end_month:02d}-01"

    if filter_type == "filter_all":
        c.execute("SELECT * FROM trades WHERE date >= ? AND date < ?", (start, end))
    elif filter_type == "filter_profit":
        c.execute("SELECT * FROM trades WHERE date >= ? AND date < ? AND percent > 0", (start, end))
    elif filter_type == "filter_loss":
        c.execute("SELECT * FROM trades WHERE date >= ? AND date < ? AND percent <= 0", (start, end))

    trades = c.fetchall()
    if not trades:
        await call.message.answer("No trades found.", reply_markup=main_menu())
        return

    for trade in trades:
        text = f"Date: {trade[1]}\nPair: {trade[2]}\nResult: {trade[3]}%"
        await call.message.answer(text, reply_markup=edit_delete_kb(trade[0]))

@router.callback_query(F.data.startswith("edit_trade:"))
async def edit_trade(call: CallbackQuery, state: FSMContext):
    trade_id = int(call.data.split(":")[1])
    await state.update_data(trade_id=trade_id)
    await call.message.answer("Enter new date (YYYY-MM-DD):")
    await state.set_state(TradeStates.editing_date)

@router.message(TradeStates.editing_date)
async def edit_date(message: Message, state: FSMContext):
    await state.update_data(new_date=message.text)
    await message.answer("Enter new trading pair:")
    await state.set_state(TradeStates.editing_pair)

@router.message(TradeStates.editing_pair)
async def edit_pair(message: Message, state: FSMContext):
    await state.update_data(new_pair=message.text)
    await message.answer("Enter new percent result:")
    await state.set_state(TradeStates.editing_percent)

@router.message(TradeStates.editing_percent)
async def edit_percent(message: Message, state: FSMContext):
    await state.update_data(new_percent=float(message.text))
    await message.answer("Enter new short description:")
    await state.set_state(TradeStates.editing_description)

@router.message(TradeStates.editing_description)
async def edit_description(message: Message, state: FSMContext):
    data = await state.get_data()
    c.execute("UPDATE trades SET date=?, pair=?, percent=?, description=? WHERE id=?",
              (data['new_date'], data['new_pair'], data['new_percent'], message.text, data['trade_id']))
    conn.commit()
    await message.answer("Trade updated!", reply_markup=main_menu())
    await state.clear()

@router.callback_query(F.data.startswith("delete_trade:"))
async def delete_trade(call: CallbackQuery, state: FSMContext):
    trade_id = int(call.data.split(":")[1])
    c.execute("DELETE FROM trades WHERE id=?", (trade_id,))
    conn.commit()
    await call.message.answer("Trade deleted.", reply_markup=main_menu())

@router.callback_query(lambda c: c.data == "view_winrate")
async def view_winrate(call: CallbackQuery, state: FSMContext):
    c.execute("SELECT COUNT(*), SUM(CASE WHEN percent > 0 THEN 1 ELSE 0 END) FROM trades")
    total, wins = c.fetchone()
    if total == 0:
        await call.message.answer("No trades yet.", reply_markup=main_menu())
        return
    winrate = (wins / total) * 100
    await call.message.answer(f"Winrate: {winrate:.2f}%", reply_markup=main_menu())

@router.callback_query(lambda c: c.data == "back_to_menu")
async def back_to_menu(call: CallbackQuery, state: FSMContext):
    await call.message.answer("Main Menu:", reply_markup=main_menu())

# --- Start Bot ---
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
