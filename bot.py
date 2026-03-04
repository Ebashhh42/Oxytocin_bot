import logging
import os

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

import database
import scheduler as sched

load_dotenv()

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TOKEN = os.environ["TELEGRAM_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]
PORT = int(os.environ.get("PORT", 8443))


# ---------------------------------------------------------------------------
# Keyboard helpers
# ---------------------------------------------------------------------------

def _settings_keyboard(notifications_enabled: bool) -> InlineKeyboardMarkup:
    notif_label = "🔔 Notifications: ON" if notifications_enabled else "🔕 Notifications: OFF"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🕐 Set notification time", callback_data="set_time")],
        [InlineKeyboardButton(notif_label, callback_data="toggle_notif")],
    ])


def _time_picker_keyboard() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for h in range(24):
        row.append(InlineKeyboardButton(f"{h:02d}:00", callback_data=f"hour_{h}"))
        if len(row) == 6:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("« Back", callback_data="back_settings")])
    return InlineKeyboardMarkup(rows)


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    database.register_user(user.id, user.username or "", user.first_name or "")
    await update.message.reply_text(
        f"Hello {user.first_name}! 🐱💛\n\n"
        "I'm the *Oxytocin Bot* — here to make your day a little warmer.\n\n"
        "Every day I'll send you:\n"
        "• A cute cat photo 🐱\n"
        "• An inspirational quote ✨\n"
        "• A reminder to spread kindness 💛\n\n"
        "*Commands:*\n"
        "/cat — Get a cat photo right now\n"
        "/addquote <text> — Save an inspiring quote\n"
        "/myquotes — View your saved quotes\n"
        "/settings — Configure notifications",
        parse_mode="Markdown",
    )


async def cmd_cat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cat_url = await sched.fetch_cat_image()
    if cat_url:
        await update.message.reply_photo(photo=cat_url, caption="Here's your cat! 🐱")
    else:
        await update.message.reply_text("Couldn't fetch a cat right now — try again in a moment!")


async def cmd_addquote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    quote = " ".join(context.args).strip()
    if not quote:
        await update.message.reply_text(
            "Please include the quote after the command.\n"
            "Example: /addquote Be the change you wish to see in the world."
        )
        return
    database.add_quote(update.effective_user.id, quote)
    await update.message.reply_text("Quote saved! 💛 I'll share it back with you someday.")


async def cmd_myquotes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    quotes = database.get_user_quotes(update.effective_user.id)
    if not quotes:
        await update.message.reply_text(
            "You haven't saved any quotes yet. Use /addquote to add one!"
        )
        return
    lines = [f"{i + 1}. {q['quote']}" for i, q in enumerate(quotes)]
    await update.message.reply_text(
        "📖 *Your saved quotes:*\n\n" + "\n\n".join(lines),
        parse_mode="Markdown",
    )


async def cmd_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_data = database.get_user(update.effective_user.id)
    if not user_data:
        await update.message.reply_text("Please use /start first.")
        return
    hour = user_data["notify_hour"]
    await update.message.reply_text(
        f"⚙️ *Settings*\n\nYour daily message is currently set to *{hour:02d}:00 UTC*.",
        parse_mode="Markdown",
        reply_markup=_settings_keyboard(user_data["notifications_enabled"]),
    )


# ---------------------------------------------------------------------------
# Inline keyboard callback
# ---------------------------------------------------------------------------

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    chat_id = query.from_user.id
    data = query.data

    if data == "toggle_notif":
        new_state = database.toggle_notifications(chat_id)
        await query.edit_message_reply_markup(reply_markup=_settings_keyboard(new_state))

    elif data == "set_time":
        await query.edit_message_text(
            "🕐 *Choose your daily notification time (UTC):*",
            parse_mode="Markdown",
            reply_markup=_time_picker_keyboard(),
        )

    elif data.startswith("hour_"):
        hour = int(data.split("_")[1])
        database.update_notify_hour(chat_id, hour)
        user_data = database.get_user(chat_id)
        await query.edit_message_text(
            f"✅ Daily message time set to *{hour:02d}:00 UTC*.",
            parse_mode="Markdown",
            reply_markup=_settings_keyboard(user_data["notifications_enabled"]),
        )

    elif data == "back_settings":
        user_data = database.get_user(chat_id)
        hour = user_data["notify_hour"]
        await query.edit_message_text(
            f"⚙️ *Settings*\n\nYour daily message is currently set to *{hour:02d}:00 UTC*.",
            parse_mode="Markdown",
            reply_markup=_settings_keyboard(user_data["notifications_enabled"]),
        )


# ---------------------------------------------------------------------------
# Scheduler lifecycle hooks
# ---------------------------------------------------------------------------

async def _post_init(application: Application) -> None:
    scheduler = sched.setup_scheduler(application.bot)
    application.bot_data["scheduler"] = scheduler
    scheduler.start()
    logger.info("Scheduler started.")


async def _post_shutdown(application: Application) -> None:
    scheduler = application.bot_data.get("scheduler")
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    app = (
        Application.builder()
        .token(TOKEN)
        .post_init(_post_init)
        .post_shutdown(_post_shutdown)
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("cat", cmd_cat))
    app.add_handler(CommandHandler("addquote", cmd_addquote))
    app.add_handler(CommandHandler("myquotes", cmd_myquotes))
    app.add_handler(CommandHandler("settings", cmd_settings))
    app.add_handler(CallbackQueryHandler(callback_handler))

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=f"{WEBHOOK_URL}/webhook",
        url_path="/webhook",
    )


if __name__ == "__main__":
    main()
