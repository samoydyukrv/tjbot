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
    filters,
    ConversationHandler,
)
from datetime import datetime

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define stages
DATE, PAIR, RESULT, NOTE, SCREENSHOT, HISTORY_YEAR, HISTORY_MONTH, HISTORY_FILTER = range(8)

# Connect to SQLite
conn = sqlite3.connect("trades.db", check_same_thread=False)
c = conn.cursor()
c.execute(
    """CREATE TABLE IF NOT EXISTS trades
             (id INTEGER PRIMARY KEY, user_id INTEGER, date TEXT, pair TEXT, result TEXT, note TEXT, screenshot TEXT)"""
)
conn.commit()

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[
        KeyboardButton("📈 Add Trade"),
        KeyboardButton("📜 History"),
        KeyboardButton("📊 Winrate")
    ]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Welcome to your Trading Journal!", reply_markup=reply_markup)

# Entry point for conversation
async def add_trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Enter trade date (YYYY-MM-DD):")
    return DATE

async def handle_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['date'] = update.message.text
    await update.message.reply_text("Enter trading pair (e.g. XAUUSD):")
    return PAIR

async def handle_pair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['pair'] = update.message.text
    await update.message.reply_text("Enter result (e.g. +3.5%):")
    return RESULT

async def handle_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['result'] = update.message.text
    await update.message.reply_text("Optional: Add a note for this trade")
    return NOTE

async def handle_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['note'] = update.message.text
    await update.message.reply_text("You can now send a screenshot or type /skip if none")
    return SCREENSHOT

async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = update.message.photo[-1].file_id
    context.user_data['screenshot'] = photo_file
    await save_trade(update, context)
    return ConversationHandler.END

async def skip_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['screenshot'] = None
    await save_trade(update, context)
    return ConversationHandler.END

async def save_trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data
    c.execute("INSERT INTO trades (user_id, date, pair, result, note, screenshot) VALUES (?, ?, ?, ?, ?, ?)",
              (update.effective_user.id, data['date'], data['pair'], data['result'], data['note'], data['screenshot']))
    conn.commit()
    await update.message.reply_text("Trade saved successfully ✅")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Trade entry cancelled ❌")
    return ConversationHandler.END

# --- History browsing ---
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
    filter_buttons = [
        [
            InlineKeyboardButton("🔁 All", callback_data="filter_all"),
            InlineKeyboardButton("✅ Profit", callback_data="filter_profit"),
            InlineKeyboardButton("❌ Loss", callback_data="filter_loss"),
        ]
    ]
    await query.edit_message_text("Choose filter:", reply_markup=InlineKeyboardMarkup(filter_buttons))
    return HISTORY_FILTER

async def filter_trades(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    filter_type = query.data.split("_")[1]
    year = context.user_data["year"]
    month = context.user_data["month"]
    user_id = query.from_user.id

    c.execute(
        "SELECT date, pair, result, note, screenshot FROM trades WHERE user_id = ? AND substr(date, 1, 4) = ? AND substr(date, 6, 2) = ?",
        (user_id, year, month)
    )
    trades = c.fetchall()

    if filter_type == "profit":
        trades = [t for t in trades if safe_result_parse(t[2]) > 0]
    elif filter_type == "loss":
        trades = [t for t in trades if safe_result_parse(t[2]) < 0]

    if not trades:
        await query.edit_message_text("No trades found for selected filter.")
        return ConversationHandler.END

    for trade in trades:
        text = f"📅 {trade[0]}\n💱 {trade[1]}\n📊 {trade[2]}\n📝 {trade[3]}"
        if trade[4]:
            await context.bot.send_photo(chat_id=user_id, photo=trade[4], caption=text)
        else:
            await context.bot.send_message(chat_id=user_id, text=text)

    return ConversationHandler.END

def safe_result_parse(result: str) -> float:
    try:
        return float(result.replace("%", "").replace("+", "").strip())
    except:
        return 0.0

# --- Winrate ---
async def winrate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c.execute("SELECT result FROM trades WHERE user_id = ?", (update.effective_user.id,))
    results = c.fetchall()
    wins = 0
    for r in results:
        try:
            if float(r[0].replace('%', '')) > 0:
                wins += 1
        except:
            continue
    total = len(results)
    if total == 0:
        await update.message.reply_text("No trades found.")
    else:
        rate = wins / total * 100
        await update.message.reply_text(f"Your winrate: {rate:.2f}% ✅")

EXPORT_FOLDER = "exports"
os.makedirs(EXPORT_FOLDER, exist_ok=True)

async def export_trades(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect("trades.db")
    cursor = conn.cursor()

    cursor.execute("SELECT date, pair, result, note FROM trades WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("You don’t have any saved trades yet.")
        return

    df = pd.DataFrame(rows, columns=["Date", "Pair", "Result", "Note"])
    file_path = os.path.join(EXPORT_FOLDER, f"user_{user_id}_trades.xlsx")
    df.to_excel(file_path, index=False)

    await update.message.reply_document(document=open(file_path, "rb"), filename=f"trades_{user_id}.xlsx")


app = ApplicationBuilder().token("YOUR_BOT_TOKEN_HERE").build()

conv_handler = ConversationHandler(
    entry_points=[
        MessageHandler(filters.Regex("^📈 Add Trade$"), add_trade),
        MessageHandler(filters.Regex("^📜 History$"), history)
    ],
    states={
        DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_date)],
        PAIR: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_pair)],
        RESULT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_result)],
        NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_note)],
        SCREENSHOT: [
            MessageHandler(filters.PHOTO, handle_screenshot),
            CommandHandler("skip", skip_screenshot)
        ],
        HISTORY_YEAR: [CallbackQueryHandler(select_year, pattern="^year_.*")],
        HISTORY_MONTH: [CallbackQueryHandler(select_month, pattern="^month_.*")],
        HISTORY_FILTER: [CallbackQueryHandler(filter_trades, pattern="^filter_.*")],
    },
    fallbacks=[CommandHandler("cancel", cancel)]
)

app.add_handler(CommandHandler("start", start))
app.add_handler(conv_handler)
app.add_handler(MessageHandler(filters.Regex("^📊 Winrate$"), winrate))
app.add_handler(CommandHandler("export", export_trades))

app.run_polling()
