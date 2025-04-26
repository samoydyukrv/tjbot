import logging
import sqlite3
from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode
from datetime import datetime
import asyncio

TOKEN = "8096949835:AAHrXR7aY9QnUr_JJhYb9N06dYdVvMfBhMo"
bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# Database
conn = sqlite3.connect("trades.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    pair TEXT,
    result REAL,
    comment TEXT,
    screenshot TEXT
)
""")
conn.commit()

# FSM States
class AddTrade(StatesGroup):
    date = State()
    pair = State()
    result = State()
    comment = State()
    screenshot = State()

class EditTrade(StatesGroup):
    field = State()
    new_value = State()

class History(StatesGroup):
    year = State()
    month = State()
    filter = State()
    viewing = State()

# Keyboards
def main_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Add Trade", callback_data="add_trade")],
        [InlineKeyboardButton(text="📖 History", callback_data="history")],
        [InlineKeyboardButton(text="📈 Win Rate", callback_data="win_rate")]
    ])
    return keyboard

def yes_no_keyboard(trade_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Yes", callback_data=f"confirm_delete:{trade_id}"),
         InlineKeyboardButton(text="❌ No", callback_data="cancel_delete")]
    ])

def edit_keyboard(trade_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Edit", callback_data=f"edit_trade:{trade_id}"),
         InlineKeyboardButton(text="🗑 Delete", callback_data=f"delete_trade:{trade_id}")]
    ])

# Start
@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer("Welcome! Choose an action:", reply_markup=main_menu())

# Main menu handler
@dp.callback_query(F.data.in_(["add_trade", "history", "win_rate"]))
async def handle_menu(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    if call.data == "add_trade":
        await call.message.answer("Enter date (YYYY-MM-DD):")
        await state.set_state(AddTrade.date)
    elif call.data == "history":
        years = list({row[0][:4] for row in cursor.execute("SELECT date FROM trades").fetchall()})
        years.sort()
        if not years:
            await call.message.answer("No trades found.")
            return
        keyboard = InlineKeyboardBuilder()
        for year in years:
            keyboard.button(text=year, callback_data=f"year:{year}")
        await call.message.answer("Select year:", reply_markup=keyboard.as_markup())
        await state.set_state(History.year)
    elif call.data == "win_rate":
        trades = cursor.execute("SELECT result FROM trades").fetchall()
        if not trades:
            await call.message.answer("No trades found.")
            return
        wins = sum(1 for r in trades if r[0] > 0)
        total = len(trades)
        win_rate = (wins / total) * 100
        await call.message.answer(f"Win rate: {win_rate:.2f}%")

# Add Trade
@dp.message(AddTrade.date)
async def add_date(message: types.Message, state: FSMContext):
    await state.update_data(date=message.text)
    await message.answer("Enter pair (e.g., BTC/USDT):")
    await state.set_state(AddTrade.pair)

@dp.message(AddTrade.pair)
async def add_pair(message: types.Message, state: FSMContext):
    await state.update_data(pair=message.text)
    await message.answer("Enter result % (e.g., 3.5 or -1.2):")
    await state.set_state(AddTrade.result)

@dp.message(AddTrade.result)
async def add_result(message: types.Message, state: FSMContext):
    await state.update_data(result=float(message.text))
    await message.answer("Enter comment:")
    await state.set_state(AddTrade.comment)

@dp.message(AddTrade.comment)
async def add_comment(message: types.Message, state: FSMContext):
    await state.update_data(comment=message.text)
    await message.answer("Send screenshot (or type 'no'):")
    await state.set_state(AddTrade.screenshot)

@dp.message(AddTrade.screenshot)
async def add_screenshot(message: types.Message, state: FSMContext):
    data = await state.get_data()
    screenshot = message.photo[-1].file_id if message.photo else (None if message.text.lower() == "no" else message.text)
    cursor.execute(
        "INSERT INTO trades (date, pair, result, comment, screenshot) VALUES (?, ?, ?, ?, ?)",
        (data["date"], data["pair"], data["result"], data["comment"], screenshot)
    )
    conn.commit()
    await message.answer("Trade added!", reply_markup=main_menu())
    await state.clear()

# History navigation
@dp.callback_query(F.data.startswith("year:"))
async def select_year(call: types.CallbackQuery, state: FSMContext):
    year = call.data.split(":")[1]
    await state.update_data(year=year)
    months = list({row[0][5:7] for row in cursor.execute("SELECT date FROM trades WHERE date LIKE ?", (f"{year}-%",)).fetchall()})
    months.sort()
    keyboard = InlineKeyboardBuilder()
    for month in months:
        keyboard.button(text=month, callback_data=f"month:{month}")
    await call.message.answer("Select month:", reply_markup=keyboard.as_markup())
    await state.set_state(History.month)

@dp.callback_query(F.data.startswith("month:"))
async def select_month(call: types.CallbackQuery, state: FSMContext):
    month = call.data.split(":")[1]
    await state.update_data(month=month)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="All", callback_data="filter:all"),
         InlineKeyboardButton(text="Profitable", callback_data="filter:profitable"),
         InlineKeyboardButton(text="Losing", callback_data="filter:losing")]
    ])
    await call.message.answer("Select filter:", reply_markup=keyboard)
    await state.set_state(History.filter)

@dp.callback_query(F.data.startswith("filter:"))
async def select_filter(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    year, month = data["year"], data["month"]
    filter_type = call.data.split(":")[1]
    query = f"SELECT id, date, pair, result FROM trades WHERE date LIKE '{year}-{month}%'"
    rows = cursor.execute(query).fetchall()
    if filter_type == "profitable":
        rows = [r for r in rows if r[3] > 0]
    elif filter_type == "losing":
        rows = [r for r in rows if r[3] <= 0]
    if not rows:
        await call.message.answer("No trades found.")
        return
    keyboard = InlineKeyboardBuilder()
    for r in rows:
        text = f"{r[1]} {r[2]} {r[3]}%"
        keyboard.button(text=text, callback_data=f"view_trade:{r[0]}")
    await call.message.answer("Trades:", reply_markup=keyboard.as_markup())
    await state.set_state(History.viewing)

@dp.callback_query(F.data.startswith("view_trade:"))
async def view_trade(call: types.CallbackQuery):
    trade_id = int(call.data.split(":")[1])
    trade = cursor.execute("SELECT * FROM trades WHERE id = ?", (trade_id,)).fetchone()
    text = f"<b>Date:</b> {trade[1]}\n<b>Pair:</b> {trade[2]}\n<b>Result:</b> {trade[3]}%\n<b>Comment:</b> {trade[4]}"
    if trade[5]:
        await call.message.answer_photo(trade[5], caption=text, reply_markup=edit_keyboard(trade_id))
    else:
        await call.message.answer(text, reply_markup=edit_keyboard(trade_id))

# Delete trade
@dp.callback_query(F.data.startswith("delete_trade:"))
async def delete_trade_prompt(call: types.CallbackQuery):
    trade_id = int(call.data.split(":")[1])
    await call.message.answer("Are you sure you want to delete this trade?", reply_markup=yes_no_keyboard(trade_id))

@dp.callback_query(F.data.startswith("confirm_delete:"))
async def confirm_delete(call: types.CallbackQuery):
    trade_id = int(call.data.split(":")[1])
    cursor.execute("DELETE FROM trades WHERE id = ?", (trade_id,))
    conn.commit()
    await call.message.answer("Trade deleted.", reply_markup=main_menu())

@dp.callback_query(F.data == "cancel_delete")
async def cancel_delete(call: types.CallbackQuery):
    await call.message.answer("Deletion canceled.", reply_markup=main_menu())

# Edit trade
@dp.callback_query(F.data.startswith("edit_trade:"))
async def edit_trade_start(call: types.CallbackQuery, state: FSMContext):
    trade_id = int(call.data.split(":")[1])
    await state.update_data(edit_id=trade_id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Date", callback_data="edit_field:date")],
        [InlineKeyboardButton(text="💱 Pair", callback_data="edit_field:pair")],
        [InlineKeyboardButton(text="📈 Result", callback_data="edit_field:result")],
        [InlineKeyboardButton(text="📝 Comment", callback_data="edit_field:comment")],
        [InlineKeyboardButton(text="🖼 Screenshot", callback_data="edit_field:screenshot")]
    ])
    await call.message.answer("What do you want to edit?", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("edit_field:"))
async def edit_field_prompt(call: types.CallbackQuery, state: FSMContext):
    field = call.data.split(":")[1]
    data = await state.get_data()
    trade = cursor.execute("SELECT * FROM trades WHERE id = ?", (data["edit_id"],)).fetchone()
    fields = {"date": 1, "pair": 2, "result": 3, "comment": 4, "screenshot": 5}
    old_value = trade[fields[field]]
    await state.update_data(field=field)
    if field == "screenshot":
        if old_value:
            await call.message.answer_photo(old_value, caption="Send new screenshot or type 'skip' to leave unchanged.")
        else:
            await call.message.answer("Send new screenshot or type 'skip' to leave unchanged.")
    else:
        await call.message.answer(f"Current {field}: {old_value}\nSend new value or type 'skip' to leave unchanged.")
    await state.set_state(EditTrade.new_value)

@dp.message(EditTrade.new_value)
async def edit_value(message: types.Message, state: FSMContext):
    data = await state.get_data()
    field = data["field"]
    trade_id = data["edit_id"]
    if message.text.lower() == "skip":
        await message.answer("No changes made.", reply_markup=main_menu())
    else:
        if field == "screenshot":
            new_value = message.photo[-1].file_id if message.photo else message.text
        elif field == "result":
            new_value = float(message.text)
        else:
            new_value = message.text
        cursor.execute(f"UPDATE trades SET {field} = ? WHERE id = ?", (new_value, trade_id))
        conn.commit()
        await message.answer(f"{field.capitalize()} updated!", reply_markup=main_menu())
    await state.clear()

# Error handler (на случай любого сбоя чтобы не зависало)
@dp.errors()
async def errors_handler(update: types.Update, exception):
    logging.error(f"Error: {exception}")
    return True

# Run
async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

