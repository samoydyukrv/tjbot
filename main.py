# import asyncio
# import sqlite3
# from aiogram import Bot, Dispatcher, types, F
# from aiogram.filters import Command
# from aiogram.fsm.context import FSMContext
# from aiogram.fsm.state import State, StatesGroup
# from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
# from aiogram.utils.keyboard import InlineKeyboardBuilder

# bot = Bot(token="8096949835:AAHrXR7aY9QnUr_JJhYb9N06dYdVvMfBhMo")
# dp = Dispatcher()

# # --- Database setup ---
# conn = sqlite3.connect("trades.db")
# cursor = conn.cursor()
# cursor.execute("""
# CREATE TABLE IF NOT EXISTS trades (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     year INTEGER,
#     month INTEGER,
#     date TEXT,
#     pair TEXT,
#     percent TEXT,
#     comment TEXT,
#     screenshot TEXT
# )
# """)
# conn.commit()

# # --- States ---
# class AddTrade(StatesGroup):
#     year = State()
#     month = State()
#     date = State()
#     pair = State()
#     percent = State()
#     comment = State()
#     screenshot = State()

# class EditTrade(StatesGroup):
#     waiting_value = State()

# # --- Helper functions ---
# def get_years():
#      cursor.execute("SELECT DISTINCT year FROM trades ORDER BY year DESC")
#      return [str(row[0]) for row in cursor.fetchall()]

# def get_months(year):
#     cursor.execute("SELECT DISTINCT month FROM trades WHERE year = ? ORDER BY month DESC", (year,))
#     return [str(row[0]) for row in cursor.fetchall()]

# def get_trades(year, month, filter_type):
#     query = "SELECT id, date, pair, percent FROM trades WHERE year = ? AND month = ?"
#     params = [year, month]
#     if filter_type == "profitable":
#         query += " AND CAST(percent AS FLOAT) > 0"
#     elif filter_type == "losing":
#         query += " AND CAST(percent AS FLOAT) <= 0"
#     query += " ORDER BY date DESC"
#     cursor.execute(query, params)
#     return cursor.fetchall()

# def get_trade(trade_id):
#     cursor.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
#     return cursor.fetchone()

# def add_trade(year, month, date, pair, percent, comment, screenshot):
#     cursor.execute("INSERT INTO trades (year, month, date, pair, percent, comment, screenshot) VALUES (?, ?, ?, ?, ?, ?, ?)",
#                    (year, month, date, pair, percent, comment, screenshot))
#     conn.commit()

# def update_trade(trade_id, field, value):
#     cursor.execute(f"UPDATE trades SET {field} = ? WHERE id = ?", (value, trade_id))
#     conn.commit()

# def delete_trade(trade_id):
#     cursor.execute("DELETE FROM trades WHERE id = ?", (trade_id,))
#     conn.commit()

# # --- Keyboards ---
# def main_menu():
#     builder = InlineKeyboardBuilder()
#     builder.button(text="Add trade", callback_data="add_trade")
#     builder.button(text="View history", callback_data="view_history")
#     builder.adjust(1)
#     return builder.as_markup()

# # --- Handlers ---
# @dp.message(Command("start"))
# async def cmd_start(message: types.Message):
#     await message.answer("Welcome to your trading journal!", reply_markup=main_menu())

# @dp.callback_query(F.data == "view_history")
# async def view_history(callback: types.CallbackQuery):
#     years = get_years()
#     if not years:
#         await callback.message.answer("No trades found.", reply_markup=main_menu())
#         return
#     builder = InlineKeyboardBuilder()
#     for year in years:
#         builder.button(text=year, callback_data=f"year_{year}")
#     builder.button(text="Back", callback_data="back_main")
#     builder.adjust(2)
#     await callback.message.edit_text("Select year:", reply_markup=builder.as_markup())

# @dp.callback_query(F.data.startswith("year_"))
# async def select_year(callback: types.CallbackQuery):
#     year = int(callback.data.split("_")[1])
#     months = get_months(year)
#     builder = InlineKeyboardBuilder()
#     for month in months:
#         builder.button(text=month, callback_data=f"month_{year}_{month}")
#     builder.button(text="Back", callback_data="view_history")
#     builder.adjust(3)
#     await callback.message.edit_text(f"Select month for {year}:", reply_markup=builder.as_markup())

# @dp.callback_query(F.data.startswith("month_"))
# async def select_month(callback: types.CallbackQuery):
#     parts = callback.data.split("_")
#     year, month = parts[1], parts[2]
#     builder = InlineKeyboardBuilder()
#     builder.button(text="All trades", callback_data=f"filter_{year}_{month}_all")
#     builder.button(text="Profitable only", callback_data=f"filter_{year}_{month}_profitable")
#     builder.button(text="Losing only", callback_data=f"filter_{year}_{month}_losing")
#     builder.button(text="Back", callback_data=f"year_{year}")
#     builder.adjust(1)
#     await callback.message.edit_text(f"Choose filter for {year}/{month}:", reply_markup=builder.as_markup())

# @dp.callback_query(F.data.startswith("filter_"))
# async def select_filter(callback: types.CallbackQuery):
#     _, year, month, filter_type = callback.data.split("_")
#     trades = get_trades(int(year), int(month), filter_type)
#     builder = InlineKeyboardBuilder()
#     for trade in trades:
#         trade_id, date, pair, percent = trade
#         builder.button(text=f"{date} {pair} {percent}%", callback_data=f"trade_{trade_id}")
#     builder.button(text="Back", callback_data=f"month_{year}_{month}")
#     builder.adjust(1)
#     await callback.message.edit_text("Select trade:", reply_markup=builder.as_markup())

# @dp.callback_query(F.data.startswith("trade_"))
# async def view_trade(callback: types.CallbackQuery):
#     trade_id = int(callback.data.split("_")[1])
#     trade = get_trade(trade_id)
#     if not trade:
#         await callback.message.answer("Trade not found.", reply_markup=main_menu())
#         return
#     id, year, month, date, pair, percent, comment, screenshot = trade
#     text = f"**Date:** {date}\n**Pair:** {pair}\n**Percent:** {percent}%\n**Comment:** {comment}"
#     builder = InlineKeyboardBuilder()
#     if screenshot:
#         builder.button(text="Screenshot", url=screenshot)
#     builder.button(text="Edit", callback_data=f"edit_{id}")
#     builder.button(text="Delete", callback_data=f"delete_{id}")
#     builder.button(text="Back", callback_data=f"filter_{year}_{month}_all")
#     builder.adjust(2)
#     await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=builder.as_markup())

# @dp.callback_query(F.data.startswith("delete_"))
# async def confirm_delete(callback: types.CallbackQuery):
#     trade_id = int(callback.data.split("_")[1])
#     builder = InlineKeyboardBuilder()
#     builder.button(text="Yes, delete", callback_data=f"confirm_delete_{trade_id}")
#     builder.button(text="Cancel", callback_data=f"trade_{trade_id}")
#     builder.adjust(2)
#     await callback.message.edit_text("Are you sure you want to delete this trade?", reply_markup=builder.as_markup())

# @dp.callback_query(F.data.startswith("confirm_delete_"))
# async def delete_confirmed(callback: types.CallbackQuery):
#     trade_id = int(callback.data.split("_")[2])
#     delete_trade(trade_id)
#     await callback.message.answer("Trade deleted.", reply_markup=main_menu())

# # --- Adding trades ---
# @dp.callback_query(F.data == "add_trade")
# async def add_trade_start(callback: types.CallbackQuery, state: FSMContext):
#     await state.set_state(AddTrade.year)
#     await callback.message.answer("Enter year (e.g., 2025):")

# @dp.message(AddTrade.year)
# async def add_trade_year(message: types.Message, state: FSMContext):
#     await state.update_data(year=int(message.text))
#     await state.set_state(AddTrade.month)
#     await message.answer("Enter month (e.g., 4):")

# @dp.message(AddTrade.month)
# async def add_trade_month(message: types.Message, state: FSMContext):
#     await state.update_data(month=int(message.text))
#     await state.set_state(AddTrade.date)
#     await message.answer("Enter date (e.g., 2025-04-27):")

# @dp.message(AddTrade.date)
# async def add_trade_date(message: types.Message, state: FSMContext):
#     await state.update_data(date=message.text)
#     await state.set_state(AddTrade.pair)
#     await message.answer("Enter pair (e.g., BTC/USD):")

# @dp.message(AddTrade.pair)
# async def add_trade_pair(message: types.Message, state: FSMContext):
#     await state.update_data(pair=message.text)
#     await state.set_state(AddTrade.percent)
#     await message.answer("Enter percent (e.g., 5 or -3):")

# @dp.message(AddTrade.percent)
# async def add_trade_percent(message: types.Message, state: FSMContext):
#     await state.update_data(percent=message.text)
#     await state.set_state(AddTrade.comment)
#     await message.answer("Enter comment (or '-' if none):")

# @dp.message(AddTrade.comment)
# async def add_trade_comment(message: types.Message, state: FSMContext):
#     await state.update_data(comment=message.text)
#     await state.set_state(AddTrade.screenshot)
#     await message.answer("Send screenshot URL (or '-' if none):")

# @dp.message(AddTrade.screenshot)
# async def add_trade_screenshot(message: types.Message, state: FSMContext):
#     data = await state.get_data()
#     screenshot = None if message.text == "-" else message.text
#     add_trade(
#         data["year"],
#         data["month"],
#         data["date"],
#         data["pair"],
#         data["percent"],
#         data["comment"],
#         screenshot
#     )
#     await state.clear()
#     await message.answer("Trade added successfully!", reply_markup=main_menu())

# # --- Editing trades ---
# # @dp.callback_query(F.data.startswith("edit_"))
# # async def edit_trade_start(callback: types.CallbackQuery, state: FSMContext):
# #     trade_id = int(callback.data.split("_")[-1])
# #     print('edit_trade_start---------------->', callback.data)
# #     await state.update_data(edit_id=trade_id)
# #     builder = InlineKeyboardBuilder()
# #     fields = ["date", "pair", "percent", "comment", "screenshot"]
# #     for field in fields:
# #         builder.button(text=f"Edit {field.capitalize()}", callback_data=f"edit_field_{field}")
# #     builder.button(text="Cancel", callback_data=f"trade_{trade_id}")
# #     builder.adjust(1)
# #     await callback.message.edit_text("Select field to edit:", reply_markup=builder.as_markup())

# @dp.callback_query(F.data.startswith("edit_field_"))
# async def edit_field_choose(callback: types.CallbackQuery, state: FSMContext):
#     field = callback.data.split("_")[-1]
#     print('edit_field_choose---------------->', callback.data)
#     await state.update_data(edit_field=field)
#     await state.set_state(EditTrade.waiting_value)
#     await callback.message.answer(f"Send new value for {field}:")

# @dp.callback_query(F.data.startswith("edit_"))
# async def edit_trade_start(callback: types.CallbackQuery, state: FSMContext):
#     trade_id = int(callback.data.split("_")[-1])
#     print('edit_trade_start---------------->', callback.data)
#     await state.update_data(edit_id=trade_id)
#     builder = InlineKeyboardBuilder()
#     fields = ["date", "pair", "percent", "comment", "screenshot"]
#     for field in fields:
#         builder.button(text=f"Edit {field.capitalize()}", callback_data=f"edit_field_{field}")
#     builder.button(text="Cancel", callback_data=f"trade_{trade_id}")
#     builder.adjust(1)
#     await callback.message.edit_text("Select field to edit:", reply_markup=builder.as_markup())

# @dp.message(EditTrade.waiting_value)
# async def edit_field_value(message: types.Message, state: FSMContext):
#     data = await state.get_data()
#     update_trade(data["edit_id"], data["edit_field"], message.text)
#     await state.clear()
#     await message.answer(f"{data['edit_field'].capitalize()} updated.", reply_markup=main_menu())

# # --- Run the bot ---
# async def main():
#     await dp.start_polling(bot)

# if __name__ == "__main__":
#     asyncio.run(main())


import asyncio
import asyncpg
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

bot = Bot(token="8096949835:AAHrXR7aY9QnUr_JJhYb9N06dYdVvMfBhMo")
dp = Dispatcher()

# --- Database setup ---
db_pool: asyncpg.Pool = None

async def init_db():
    global db_pool
    db_pool = await asyncpg.create_pool(
        dsn="postgresql://postgres:hnyQbQRvVyWqaVvQGczHdoUgUFZSwhgK@switchyard.proxy.rlwy.net:40120/railway",
        min_size=1,
        max_size=5,
    )
    async with db_pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS trades_main (
                id SERIAL PRIMARY KEY,
                year INTEGER,
                month INTEGER,
                date TEXT,
                pair TEXT,
                percent TEXT,
                comment TEXT,
                screenshot TEXT
            );
        """)
    print("✅ Database initialized and table 'trades_main' created.")

# --- States ---
class AddTrade(StatesGroup):
    year = State()
    month = State()
    date = State()
    pair = State()
    percent = State()
    comment = State()
    screenshot = State()

class EditTrade(StatesGroup):
    waiting_value = State()

# --- Helper functions ---
async def get_years():
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT DISTINCT year FROM trades_main ORDER BY year DESC")
        return [str(row["year"]) for row in rows]

async def get_months(year):
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT DISTINCT month FROM trades_main WHERE year = $1 ORDER BY month DESC", year)
        return [str(row["month"]) for row in rows]

async def get_trades(year, month, filter_type):
    async with db_pool.acquire() as conn:
        query = "SELECT id, date, pair, percent FROM trades_main WHERE year = $1 AND month = $2"
        if filter_type == "profitable":
            query += " AND CAST(percent AS FLOAT) > 0"
        elif filter_type == "losing":
            query += " AND CAST(percent AS FLOAT) <= 0"
        query += " ORDER BY date DESC"
        rows = await conn.fetch(query, year, month)
        return rows

async def get_trade(trade_id):
    async with db_pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM trades_main WHERE id = $1", trade_id)

async def add_trade(year, month, date, pair, percent, comment, screenshot):
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO trades_main (year, month, date, pair, percent, comment, screenshot)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """, year, month, date, pair, percent, comment, screenshot)

async def update_trade(trade_id, field, value):
    async with db_pool.acquire() as conn:
        await conn.execute(f"UPDATE trades_main SET {field} = $1 WHERE id = $2", value, trade_id)

async def delete_trade(trade_id):
    async with db_pool.acquire() as conn:
        await conn.execute("DELETE FROM trades_main WHERE id = $1", trade_id)

# --- Keyboards ---
def main_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="Add trade", callback_data="add_trade")
    builder.button(text="View history", callback_data="view_history")
    builder.adjust(1)
    return builder.as_markup()

# --- Handlers ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Welcome to your trading journal!", reply_markup=main_menu())

@dp.callback_query(F.data == "view_history")
async def view_history(callback: types.CallbackQuery):
    years = await get_years()
    if not years:
        await callback.message.answer("No trades found.", reply_markup=main_menu())
        return
    builder = InlineKeyboardBuilder()
    for year in years:
        builder.button(text=year, callback_data=f"year_{year}")
    builder.button(text="Back", callback_data="back_main")
    builder.adjust(2)
    await callback.message.edit_text("Select year:", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("year_"))
async def select_year(callback: types.CallbackQuery):
    year = int(callback.data.split("_")[1])
    months = await get_months(year)
    builder = InlineKeyboardBuilder()
    for month in months:
        builder.button(text=month, callback_data=f"month_{year}_{month}")
    builder.button(text="Back", callback_data="view_history")
    builder.adjust(3)
    await callback.message.edit_text(f"Select month for {year}:", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("month_"))
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

@dp.callback_query(F.data.startswith("filter_"))
async def select_filter(callback: types.CallbackQuery):
    _, year, month, filter_type = callback.data.split("_")
    trades = await get_trades(int(year), int(month), filter_type)
    builder = InlineKeyboardBuilder()
    for trade in trades:
        trade_id, date, pair, percent = trade["id"], trade["date"], trade["pair"], trade["percent"]
        builder.button(text=f"{date} {pair} {percent}%", callback_data=f"trade_{trade_id}")
    builder.button(text="Back", callback_data=f"month_{year}_{month}")
    builder.adjust(1)
    await callback.message.edit_text("Select trade:", reply_markup=builder.as_markup())

# @dp.callback_query(F.data.startswith("trade_"))
# async def view_trade(callback: types.CallbackQuery):
#     trade_id = int(callback.data.split("_")[1])
#     trade = await get_trade(trade_id)
#     if not trade:
#         await callback.message.answer("Trade not found.", reply_markup=main_menu())
#         return
#     text = f"**Date:** {trade['date']}\n**Pair:** {trade['pair']}\n**Percent:** {trade['percent']}%\n**Comment:** {trade['comment']}"
#     builder = InlineKeyboardBuilder()
#     if trade['screenshot']:
#         # builder.button(text="Screenshot", url=trade['screenshot'])
#         if trade['screenshot']:
#             # если есть скриншот - отправляем фото
#             await callback.message.answer_photo(
#                 photo=trade['screenshot'],
#                 caption=text,
#                 parse_mode="Markdown",
#                 reply_markup=builder.as_markup()
#             )
#         else:
#             # если нет скрина - просто текст
#             await callback.message.answer(
#                 text,
#                 parse_mode="Markdown",
#                 reply_markup=builder.as_markup()
#             )
#     builder.button(text="Edit", callback_data=f"edit_{trade_id}")
#     builder.button(text="Delete", callback_data=f"delete_{trade_id}")
#     builder.button(text="Back", callback_data=f"filter_{trade['year']}_{trade['month']}_all")
#     builder.adjust(2)
#     await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("trade_"))
async def view_trade(callback: types.CallbackQuery):
    trade_id = int(callback.data.split("_")[1])
    trade = await get_trade(trade_id)
    
    if not trade:
        await callback.message.answer("Trade not found.", reply_markup=main_menu())
        return

    text = (
        f"**Date:** {trade['date']}\n"
        f"**Pair:** {trade['pair']}\n"
        f"**Percent:** {trade['percent']}%\n"
        f"**Comment:** {trade['comment']}"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="Edit", callback_data=f"edit_{trade_id}")
    builder.button(text="Delete", callback_data=f"delete_{trade_id}")
    builder.button(text="Back", callback_data=f"filter_{trade['year']}_{trade['month']}_all")
    builder.adjust(2)

    if trade['screenshot']:
        # если есть скриншот - отправляем фото
        await callback.message.answer_photo(
            photo=trade['screenshot'],
            caption=text,
            parse_mode="Markdown",
            reply_markup=builder.as_markup()
        )
    else:
        # если нет скрина - просто текст
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=builder.as_markup())
        # await callback.message.answer(
        #     text,
        #     parse_mode="Markdown",
        #     reply_markup=builder.as_markup()
        # )

@dp.callback_query(F.data.startswith("delete_"))
async def confirm_delete(callback: types.CallbackQuery):
    trade_id = int(callback.data.split("_")[1])
    builder = InlineKeyboardBuilder()
    builder.button(text="Yes, delete", callback_data=f"confirm_delete_{trade_id}")
    builder.button(text="Cancel", callback_data=f"trade_{trade_id}")
    builder.adjust(2)
    await callback.message.edit_text("Are you sure you want to delete this trade?", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("confirm_delete_"))
async def delete_confirmed(callback: types.CallbackQuery):
    trade_id = int(callback.data.split("_")[2])
    await delete_trade(trade_id)
    await callback.message.answer("Trade deleted.", reply_markup=main_menu())

# --- Adding trades ---
@dp.callback_query(F.data == "add_trade")
async def add_trade_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddTrade.year)
    await callback.message.answer("Enter year (e.g., 2025):")

@dp.message(AddTrade.year)
async def add_trade_year(message: types.Message, state: FSMContext):
    await state.update_data(year=int(message.text))
    await state.set_state(AddTrade.month)
    await message.answer("Enter month (e.g., 4):")

@dp.message(AddTrade.month)
async def add_trade_month(message: types.Message, state: FSMContext):
    await state.update_data(month=int(message.text))
    await state.set_state(AddTrade.date)
    await message.answer("Enter date (e.g., 2025-04-27):")

@dp.message(AddTrade.date)
async def add_trade_date(message: types.Message, state: FSMContext):
    await state.update_data(date=message.text)
    await state.set_state(AddTrade.pair)
    await message.answer("Enter pair (e.g., BTC/USD):")

@dp.message(AddTrade.pair)
async def add_trade_pair(message: types.Message, state: FSMContext):
    await state.update_data(pair=message.text)
    await state.set_state(AddTrade.percent)
    await message.answer("Enter percent (e.g., 5 or -3):")

@dp.message(AddTrade.percent)
async def add_trade_percent(message: types.Message, state: FSMContext):
    await state.update_data(percent=message.text)
    await state.set_state(AddTrade.comment)
    await message.answer("Enter comment (or '-' if none):")

@dp.message(AddTrade.comment)
async def add_trade_comment(message: types.Message, state: FSMContext):
    await state.update_data(comment=message.text)
    await state.set_state(AddTrade.screenshot)
    await message.answer("Send screenshot URL (or '-' if none):")

@dp.message(AddTrade.screenshot)
async def add_trade_screenshot(message: types.Message, state: FSMContext):
    data = await state.get_data()
    screenshot = None if message.text == "-" else message.text
    await add_trade(
        data["year"],
        data["month"],
        data["date"],
        data["pair"],
        data["percent"],
        data["comment"],
        screenshot
    )
    await state.clear()
    await message.answer("Trade added successfully!", reply_markup=main_menu())

@dp.callback_query(F.data.startswith("edit_field_"))
async def edit_field_choose(callback: types.CallbackQuery, state: FSMContext):
    field = callback.data.split("_")[-1]
    print('edit_field_choose---------------->', callback.data)
    await state.update_data(edit_field=field)
    await state.set_state(EditTrade.waiting_value)
    await callback.message.answer(f"Send new value for {field}:")

@dp.callback_query(F.data.startswith("edit_"))
async def edit_trade_start(callback: types.CallbackQuery, state: FSMContext):
    trade_id = int(callback.data.split("_")[-1])
    print('edit_trade_start---------------->', callback.data)
    await state.update_data(edit_id=trade_id)
    builder = InlineKeyboardBuilder()
    fields = ["date", "pair", "percent", "comment", "screenshot"]
    for field in fields:
        builder.button(text=f"Edit {field.capitalize()}", callback_data=f"edit_field_{field}")
    builder.button(text="Cancel", callback_data=f"trade_{trade_id}")
    builder.adjust(1)
    await callback.message.edit_text("Select field to edit:", reply_markup=builder.as_markup())

@dp.message(EditTrade.waiting_value)
async def edit_field_value(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await update_trade(data["edit_id"], data["edit_field"], message.text)
    await state.clear()
    await message.answer(f"{data['edit_field'].capitalize()} updated.", reply_markup=main_menu())

# --- Startup ---
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

