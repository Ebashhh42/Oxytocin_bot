# Oxytocin Bot 🐱💛

A Telegram bot that sends daily feel-good content to induce a little oxytocin — cute cat photos, inspirational quotes, and kindness reminders. Users can also save their own quotes to be shared back with them randomly.

## Features

- Daily broadcast (at each user's chosen time) containing:
  - A random cute cat photo from [The Cat API](https://thecatapi.com)
  - An inspirational quote from [ZenQuotes](https://zenquotes.io)
  - A kindness reminder
  - One of the user's own saved quotes (25% chance)
- `/cat` — request a cat photo on demand
- `/addquote` — save a personal quote
- `/myquotes` — view all saved quotes
- `/settings` — toggle notifications on/off and pick notification time (UTC)

## Project Structure

```
.
├── bot.py          # Entry point, webhook server, command & callback handlers
├── database.py     # Supabase read/write helpers
├── scheduler.py    # APScheduler hourly broadcast job
├── requirements.txt
├── render.yaml     # Render deployment config
└── .env.example    # Environment variable template
```

## 1. Create the Supabase Tables

Open the **SQL Editor** in your Supabase project dashboard and run:

```sql
-- Users table
create table if not exists users (
  chat_id            bigint primary key,
  username           text not null default '',
  first_name         text not null default '',
  notify_hour        int  not null default 9,
  notifications_enabled boolean not null default true,
  created_at         timestamptz not null default now()
);

-- User quotes table
create table if not exists user_quotes (
  id           uuid primary key default gen_random_uuid(),
  chat_id      bigint not null references users(chat_id) on delete cascade,
  quote        text not null,
  created_at   timestamptz not null default now(),
  last_sent_at timestamptz
);
```

## 2. Create the Telegram Bot

1. Open Telegram and message [@BotFather](https://t.me/BotFather).
2. Send `/newbot` and follow the prompts.
3. Copy the **bot token**.

## 3. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```
TELEGRAM_TOKEN=...
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=...
WEBHOOK_URL=https://your-service.onrender.com
```

> `WEBHOOK_URL` should be your Render service's public URL (no trailing slash). You get this after the first deploy.

## 4. Deploy to Render

1. Push this repository to GitHub.
2. Go to [render.com](https://render.com) → **New Web Service** → connect your repo.
3. Render will detect `render.yaml` automatically.
4. Add the four environment variables in the Render dashboard under **Environment**.
5. Deploy. Once the service is live, copy its URL and set it as `WEBHOOK_URL`, then redeploy.

## 5. Run Locally (optional)

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in values
python bot.py
```

> For local development, use a tunnelling tool like [ngrok](https://ngrok.com) to expose your local port and set its URL as `WEBHOOK_URL`.

## Bot Commands Reference

| Command | Description |
|---|---|
| `/start` | Register and see the welcome message |
| `/cat` | Get a random cat photo immediately |
| `/addquote <text>` | Save a personal quote |
| `/myquotes` | List all your saved quotes |
| `/settings` | Toggle notifications / change notification time |
