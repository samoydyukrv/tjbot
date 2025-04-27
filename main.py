import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

bot = Bot(token="8096949835:AAHrXR7aY9QnUr_JJhYb9N06dYdVvMfBhMo")
dp = Dispatcher()

# --- Database setup ---
conn = sqlite3.connect("trades.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER,
    month INTEGER,
    date TEXT,
    pair TEXT,
    percent TEXT,
    comment TEXT,
    screenshot TEXT
)
""")
conn.commit()

# --- Helper functions ---
def get_years():
    cursor.execute("SELECT DISTINCT year FROM trades ORDER BY year DESC")
    return [str(row[0]) for row in cursor.fetchall()]

def get_months(year):
    cursor.execute("SELECT DISTINCT month FROM trades WHERE year = ? ORDER BY month DESC", (year,))
    return [str(row[0]) for row in cursor.fetchall()]

def get_trades(year, month, filter_type):
    query = "SELECT id, date, pair, percent FROM trades WHERE year = ? AND month = ?"
    params = [year, month]
    if filter_type == "profitable":
        query += " AND CAST(percent AS FLOAT) > 0"
    elif filter_type == "losing":
        query += " AND CAST(percent AS FLOAT) <= 0"
    query += " ORDER BY date DESC"
    cursor.execute(query, params)
    return cursor.fetchall()

def get_trade(trade_id):
    cursor.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
    return cursor.fetchone()

def add_trade(year, month, date, pair, percent, comment, screenshot):
    cursor.execute("INSERT INTO trades (year, month, date, pair, percent, comment, screenshot) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (year, month, date, pair, percent, comment, screenshot))
    conn.commit()

def update_trade(trade_id, field, value):
    cursor.execute(f"UPDATE trades SET {field} = ? WHERE id = ?", (value, trade_id))
    conn.commit()

def delete_trade(trade_id):
    cursor.execute("DELETE FROM trades WHERE id = ?", (trade_id,))
    conn.commit()

# --- Handlers ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Welcome to your trading journal!", reply_markup=main_menu())

def main_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="Add trade", callback_data="add_trade")
    builder.button(text="View history", callback_data="view_history")
    builder.adjust(1)
    return builder.as_markup()

@dp.callback_query(lambda c: c.data == "view_history")
async def view_history(callback: types.CallbackQuery):
    years = get_years()
    if not years:
        await callback.message.answer("No trades found.", reply_markup=main_menu())
        return
    builder = InlineKeyboardBuilder()
    for year in years:
        builder.button(text=year, callback_data=f"year_{year}")
    builder.button(text="Back", callback_data="back_main")
    builder.adjust(2)
    await callback.message.edit_text("Select year:", reply_markup=builder.as_markup())

@dp.callback_query(lambda c: c.data.startswith("year_"))
async def select_year(callback: types.CallbackQuery):
    year = int(callback.data.split("_")[1])
    months = get_months(year)
    builder = InlineKeyboardBuilder()
    for month in months:
        builder.button(text=month, callback_data=f"month_{year}_{month}")
    builder.button(text="Back", callback_data="view_history")
    builder.adjust(3)
    await callback.message.edit_text(f"Select month for {year}:", reply_markup=builder.as_markup())

@dp.callback_query(lambda c: c.data.startswith("month_"))
async def select_month(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    year, month = parts[1], parts[2]
    builder = InlineKeyboardBuilder()
    builder.button(text="All trades", callback_data=f"filter_{year}_{month}_all")
    builder.button(text="Profitable only", callback_data=f"filter_{year}_{month}_profitable")
    builder.button(text="Losing only", callback_data=f"filter_{year}_{month}_losing")
    builder.button(text="Back", callback_data=f"year_{year}")
    builder.adjust(1)
    await callback.message.edit_text(f"Choose filter for {year}/{month}:", reply_markup=builder.as_markup())

@dp.callback_query(lambda c: c.data.startswith("filter_"))
async def select_filter(callback: types.CallbackQuery):
    _, year, month, filter_type = callback.data.split("_")
    trades = get_trades(int(year), int(month), filter_type)
    builder = InlineKeyboardBuilder()
    for trade in trades:
        trade_id, date, pair, percent = trade
        builder.button(text=f"{date} {pair} {percent}%", callback_data=f"trade_{trade_id}")
    builder.button(text="Back", callback_data=f"month_{year}_{month}")
    builder.adjust(1)
    await callback.message.edit_text("Select trade:", reply_markup=builder.as_markup())

@dp.callback_query(lambda c: c.data.startswith("trade_"))
async def view_trade(callback: types.CallbackQuery):
    trade_id = int(callback.data.split("_")[1])
    trade = get_trade(trade_id)
    if not trade:
        await callback.message.answer("Trade not found.", reply_markup=main_menu())
        return
    id, year, month, date, pair, percent, comment, screenshot = trade
    text = f"**Date:** {date}\n**Pair:** {pair}\n**Percent:** {percent}%\n**Comment:** {comment}"
    builder = InlineKeyboardBuilder()
    if screenshot:
        builder.button(text="Screenshot", url=screenshot)
    builder.button(text="Edit", callback_data=f"edit_{id}")
    builder.button(text="Delete", callback_data=f"delete_{id}")
    builder.button(text="Back", callback_data=f"filter_{year}_{month}_all")
    builder.adjust(2)
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=builder.as_markup())

@dp.callback_query(lambda c: c.data.startswith("delete_"))
async def confirm_delete(callback: types.CallbackQuery):
    trade_id = int(callback.data.split("_")[1])
    builder = InlineKeyboardBuilder()
    builder.button(text="Yes, delete", callback_data=f"confirm_delete_{trade_id}")
    builder.button(text="Cancel", callback_data=f"trade_{trade_id}")
    builder.adjust(2)
    await callback.message.edit_text("Are you sure you want to delete this trade?", reply_markup=builder.as_markup())

@dp.callback_query(lambda c: c.data.startswith("confirm_delete_"))
async def delete_confirmed(callback: types.CallbackQuery):
    trade_id = int(callback.data.split("_")[2])
    delete_trade(trade_id)
    await callback.message.answer("Trade deleted.", reply_markup=main_menu())

@dp.callback_query(lambda c: c.data.startswith("edit_"))
async def start_edit(callback: types.CallbackQuery):
    trade_id = int(callback.data.split("_")[1])
    builder = InlineKeyboardBuilder()
    builder.button(text="Edit Date", callback_data=f"edit_field_{trade_id}_date")
    builder.button(text="Edit Pair", callback_data=f"edit_field_{trade_id}_pair")
    builder.button(text="Edit Percent", callback_data=f"edit_field_{trade_id}_percent")
    builder.button(text="Edit Comment", callback_data=f"edit_field_{trade_id}_comment")
    builder.button(text="Edit Screenshot", callback_data=f"edit_field_{trade_id}_screenshot")
    builder.button(text="Cancel", callback_data=f"trade_{trade_id}")
    builder.adjust(1)
    await callback.message.edit_text("Select field to edit:", reply_markup=builder.as_markup())

@dp.callback_query(lambda c: c.data.startswith("edit_field_"))
async def edit_field(callback: types.CallbackQuery, state: dict = {}):
    parts = callback.data.split("_")
    trade_id = int(parts[2])
    field = parts[3]
    state["editing"] = (trade_id, field)
    await callback.message.answer(f"Send new value for {field} (or type /skip to leave unchanged):")

@dp.message(Command("skip"))
async def skip_edit(message: types.Message, state: dict = {}):
    if "editing" not in state:
        await message.answer("No active editing.")
        return
    trade_id, _ = state.pop("editing")
    await message.answer("Edit skipped.", reply_markup=main_menu())

@dp.message()
async def save_edit(message: types.Message, state: dict = {}):
    if "editing" not in state:
        await message.answer("Use /start to begin.", reply_markup=main_menu())
        return
    trade_id, field = state.pop("editing")
    update_trade(trade_id, field, message.text)
    await message.answer(f"{field.capitalize()} updated.", reply_markup=main_menu())

@dp.callback_query(lambda c: c.data == "add_trade")
async def add_trade_start(callback: types.CallbackQuery, state: dict = {}):
    state["adding"] = {}
    await callback.message.answer("Enter year (e.g., 2025):")

@dp.message()
async def add_trade_process(message: types.Message, state: dict = {}):
    if "adding" not in state:
        return
    adding = state["adding"]
    if "year" not in adding:
        adding["year"] = int(message.text)
        await message.answer("Enter month (e.g., 4):")
    elif "month" not in adding:
        adding["month"] = int(message.text)
        await message.answer("Enter date (e.g., 2025-04-27):")
    elif "date" not in adding:
        adding["date"] = message.text
        await message.answer("Enter pair (e.g., BTC/USD):")
    elif "pair" not in adding:
        adding["pair"] = message.text
        await message.answer("Enter percent (e.g., 5 or -3):")
    elif "percent" not in adding:
        adding["percent"] = message.text
        await message.answer("Enter comment (or '-' if none):")
    elif "comment" not in adding:
        adding["comment"] = message.text
        await message.answer("Send screenshot URL (or '-' if none):")
    elif "screenshot" not in adding:
        adding["screenshot"] = None if message.text == "-" else message.text
        add_trade(**adding)
        state.pop("adding")
        await message.answer("Trade added successfully!", reply_markup=main_menu())

# --- Run the bot ---
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
