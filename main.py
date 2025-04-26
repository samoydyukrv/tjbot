import logging
import sqlite3
import pandas as pd
import os
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InputMediaPhoto,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
)
from datetime import datetime

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Stages
DATE, PAIR, RESULT, NOTE, SCREENSHOT, HISTORY_YEAR, HISTORY_MONTH, HISTORY_FILTER, TRADE_LIST, TRADE_ACTION, EDIT_DATE, EDIT_PAIR, EDIT_RESULT, EDIT_NOTE, EDIT_SCREENSHOT = range(15)

# Database
conn = sqlite3.connect("trades.db", check_same_thread=False)
c = conn.cursor()
c.execute(
    """CREATE TABLE IF NOT EXISTS trades
             (id INTEGER PRIMARY KEY, user_id INTEGER, date TEXT, pair TEXT, result TEXT, note TEXT, screenshot TEXT)"""
)
conn.commit()

# Start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[
        KeyboardButton("\ud83d\udcc8 Add Trade"),
        KeyboardButton("\ud83d\udcdc History"),
        KeyboardButton("\ud83d\udcca Winrate")
    ]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Welcome to your Trading Journal!", reply_markup=reply_markup)

# Add Trade Flow
async def add_trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Enter trade date (YYYY-MM-DD):")
    return DATE

async def handle_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['date'] = update.message.text
    await update.message.reply_text("Enter trading pair (e.g., XAUUSD):")
    return PAIR

async def handle_pair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['pair'] = update.message.text
    await update.message.reply_text("Enter result (e.g., +3.5%):")
    return RESULT

async def handle_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['result'] = update.message.text
    await update.message.reply_text("Optional: Add a note for this trade:")
    return NOTE

async def handle_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['note'] = update.message.text
    await ask_screenshot(update)
    return SCREENSHOT

async def ask_screenshot(update: Update):
    buttons = [[InlineKeyboardButton("Skip \u23ed\ufe0f", callback_data="skip_screenshot")]]
    if update.message:
        await update.message.reply_text("Send a screenshot or skip:", reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await update.callback_query.edit_message_text("Send a screenshot or skip:", reply_markup=InlineKeyboardMarkup(buttons))

async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = update.message.photo[-1].file_id
    context.user_data['screenshot'] = photo_file
    await save_trade(update, context)
    return ConversationHandler.END

async def skip_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    context.user_data['screenshot'] = None
    await save_trade(update, context)
    return ConversationHandler.END

async def save_trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data
    c.execute("INSERT INTO trades (user_id, date, pair, result, note, screenshot) VALUES (?, ?, ?, ?, ?, ?)",
              (update.effective_user.id, data['date'], data['pair'], data['result'], data['note'], data['screenshot']))
    conn.commit()
    if update.message:
        await update.message.reply_text("Trade saved successfully \u2705")
    else:
        await update.callback_query.edit_message_text("Trade saved successfully \u2705")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Trade entry cancelled \u274c")
    return ConversationHandler.END

# History and Edit Flow
async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c.execute("SELECT DISTINCT substr(date, 1, 4) FROM trades WHERE user_id = ?", (update.effective_user.id,))
    years = [row[0] for row in c.fetchall()]
    if not years:
        await update.message.reply_text("No trade history found.")
        return ConversationHandler.END
    buttons = [[InlineKeyboardButton(year, callback_data=f"year_{year}")] for year in years]
    await update.message.reply_text("Choose a year:", reply_markup=InlineKeyboardMarkup(buttons))
    return HISTORY_YEAR

async def select_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    year = query.data.split("_")[1]
    context.user_data['year'] = year
    c.execute("SELECT DISTINCT substr(date, 6, 2) FROM trades WHERE user_id = ? AND substr(date, 1, 4) = ?", (query.from_user.id, year))
    months = [row[0] for row in c.fetchall()]
    buttons = [[InlineKeyboardButton(month, callback_data=f"month_{month}")] for month in months]
    await query.edit_message_text("Choose a month:", reply_markup=InlineKeyboardMarkup(buttons))
    return HISTORY_MONTH

async def select_month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    month = query.data.split("_")[1]
    context.user_data['month'] = month
    await show_trade_list(update, context)
    return TRADE_LIST

async def show_trade_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id if update.message else update.callback_query.from_user.id
    year = context.user_data['year']
    month = context.user_data['month']
    c.execute("SELECT id, date, pair, result FROM trades WHERE user_id = ? AND substr(date, 1, 4) = ? AND substr(date, 6, 2) = ?",
              (user_id, year, month))
    trades = c.fetchall()
    if not trades:
        await update.callback_query.edit_message_text("No trades found.")
        return ConversationHandler.END
    buttons = [[InlineKeyboardButton(f"{trade[1]} {trade[2]} {trade[3]}", callback_data=f"trade_{trade[0]}")] for trade in trades]
    await update.callback_query.edit_message_text("Choose a trade:", reply_markup=InlineKeyboardMarkup(buttons))
    return TRADE_ACTION

async def show_trade_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    trade_id = query.data.split("_")[1]
    context.user_data['trade_id'] = trade_id

    c.execute("SELECT date, pair, result, note, screenshot FROM trades WHERE id = ?", (trade_id,))
    trade = c.fetchone()
    if not trade:
        await query.edit_message_text("Trade not found.")
        return ConversationHandler.END

    text = f"\ud83d\uddd3 Date: {trade[0]}\n\ud83d\udcb1 Pair: {trade[1]}\n\ud83d\udcca Result: {trade[2]}\n\ud83d\udcdd Note: {trade[3]}"
    buttons = [
        [InlineKeyboardButton("\u270f\ufe0f Edit", callback_data="edit_trade"), InlineKeyboardButton("\u274c Delete", callback_data="delete_trade")]
    ]
    if trade[4]:
        await query.message.reply_photo(photo=trade[4], caption=text, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(buttons))
    return TRADE_ACTION

async def delete_trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    trade_id = context.user_data['trade_id']
    c.execute("DELETE FROM trades WHERE id = ?", (trade_id,))
    conn.commit()
    await query.edit_message_text("Trade deleted successfully \u274c")
    return ConversationHandler.END

async def edit_trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Enter new date (YYYY-MM-DD) or skip:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Skip \u23ed\ufe0f", callback_data="skip_edit_date")]]))
    return EDIT_DATE

# Utilities
def safe_result_parse(result: str) -> float:
    try:
        return float(result.replace("%", "").replace("+", "").strip())
    except:
        return 0.0

# Winrate
async def winrate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c.execute("SELECT result FROM trades WHERE user_id = ?", (update.effective_user.id,))
    results = c.fetchall()
    wins = sum(1 for r in results if safe_result_parse(r[0]) > 0)
    total = len(results)
    if total == 0:
        await update.message.reply_text("No trades found.")
    else:
        rate = wins / total * 100
        await update.message.reply_text(f"Your winrate: {rate:.2f}% \u2705")

# App setup
app = ApplicationBuilder().token("8096949835:AAHrXR7aY9QnUr_JJhYb9N06dYdVvMfBhMo").build()

conv_handler = ConversationHandler(
    entry_points=[
        MessageHandler(filters.Regex("^\ud83d\udcc8 Add Trade$"), add_trade),
        MessageHandler(filters.Regex("^\ud83d\udcdc History$"), history)
    ],
    states={
        DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_date)],
        PAIR: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_pair)],
        RESULT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_result)],
        NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_note)],
        SCREENSHOT: [
            MessageHandler(filters.PHOTO, handle_screenshot),
            CallbackQueryHandler(skip_screenshot, pattern="^skip_screenshot$")
        ],
        HISTORY_YEAR: [CallbackQueryHandler(select_year, pattern="^year_.*")],
        HISTORY_MONTH: [CallbackQueryHandler(select_month, pattern="^month_.*")],
        TRADE_LIST: [CallbackQueryHandler(show_trade_details, pattern="^trade_.*")],
        TRADE_ACTION: [
            CallbackQueryHandler(delete_trade, pattern="^delete_trade$"),
            CallbackQueryHandler(edit_trade, pattern="^edit_trade$"),
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)]
)

app.add_handler(CommandHandler("start", start))
app.add_handler(conv_handler)
app.add_handler(MessageHandler(filters.Regex("^\ud83d\udcca Winrate$"), winrate))

app.run_polling()
