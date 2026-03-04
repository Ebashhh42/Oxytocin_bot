import logging
import random
from datetime import datetime, timezone

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot

import database

logger = logging.getLogger(__name__)

KINDNESS_REMINDERS = [
    "Today's mission: do one small kind thing for someone. A smile, a kind word, or holding a door open goes a long way. 💛",
    "Reach out to someone you haven't spoken to in a while. A simple 'thinking of you' can mean the world. 🌸",
    "Spread some warmth today — compliment a stranger, thank a coworker, or leave a positive note for someone. 🌟",
    "Remember: kindness is free. Share it generously today! 🤗",
    "One kind act can ripple further than you'll ever know. What will yours be today? 🌊",
    "Be the reason someone smiles today. You have that power. ✨",
    "Check in on a friend. Sometimes the people who seem fine are the ones who need it most. 💙",
]


async def fetch_cat_image() -> str | None:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.thecatapi.com/v1/images/search",
                params={"mime_types": "jpg,png"},
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json()[0]["url"]
    except Exception as exc:
        logger.error("Failed to fetch cat image: %s", exc)
        return None


async def fetch_quote() -> str:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://zenquotes.io/api/random", timeout=10)
            resp.raise_for_status()
            data = resp.json()[0]
            return f'"{data["q"]}" — {data["a"]}'
    except Exception as exc:
        logger.error("Failed to fetch quote: %s", exc)
        return '"The best way to find yourself is to lose yourself in the service of others." — Gandhi'


async def broadcast_to_users(bot: Bot, hour: int) -> None:
    users = database.get_users_for_hour(hour)
    if not users:
        logger.info("No users scheduled for hour %02d:00 UTC", hour)
        return

    logger.info("Broadcasting to %d user(s) at %02d:00 UTC", len(users), hour)

    cat_url = await fetch_cat_image()
    quote = await fetch_quote()
    reminder = random.choice(KINDNESS_REMINDERS)

    for user in users:
        chat_id = user["chat_id"]
        try:
            if cat_url:
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=cat_url,
                    caption="Your daily dose of cuteness 🐱",
                )
            await bot.send_message(
                chat_id=chat_id,
                text=f"✨ *Quote of the day:*\n{quote}",
                parse_mode="Markdown",
            )
            await bot.send_message(chat_id=chat_id, text=reminder)

            # 25% chance to send one of the user's own stored quotes
            if random.random() < 0.25:
                user_quote = database.get_random_user_quote(chat_id)
                if user_quote:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=f'💭 *A quote you once saved:*\n"{user_quote["quote"]}"',
                        parse_mode="Markdown",
                    )
        except Exception as exc:
            logger.error("Failed to send to user %d: %s", chat_id, exc)


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()

    async def _hourly_job() -> None:
        hour = datetime.now(timezone.utc).hour
        await broadcast_to_users(bot, hour)

    scheduler.add_job(_hourly_job, "cron", minute=0)
    return scheduler
