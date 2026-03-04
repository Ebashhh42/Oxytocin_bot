import os
import random
from datetime import datetime, timezone

from supabase import create_client, Client


def _db() -> Client:
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

def register_user(chat_id: int, username: str, first_name: str) -> None:
    _db().table("users").upsert(
        {"chat_id": chat_id, "username": username, "first_name": first_name},
        on_conflict="chat_id",
    ).execute()


def get_user(chat_id: int) -> dict | None:
    result = _db().table("users").select("*").eq("chat_id", chat_id).execute()
    return result.data[0] if result.data else None


def get_users_for_hour(hour: int) -> list[dict]:
    result = (
        _db()
        .table("users")
        .select("*")
        .eq("notify_hour", hour)
        .eq("notifications_enabled", True)
        .execute()
    )
    return result.data


def update_notify_hour(chat_id: int, hour: int) -> None:
    _db().table("users").update({"notify_hour": hour}).eq("chat_id", chat_id).execute()


def toggle_notifications(chat_id: int) -> bool:
    """Flip notifications_enabled and return the new value."""
    user = get_user(chat_id)
    if not user:
        return False
    new_val = not user["notifications_enabled"]
    _db().table("users").update({"notifications_enabled": new_val}).eq("chat_id", chat_id).execute()
    return new_val


# ---------------------------------------------------------------------------
# User quotes
# ---------------------------------------------------------------------------

def add_quote(chat_id: int, quote: str) -> None:
    _db().table("user_quotes").insert({"chat_id": chat_id, "quote": quote}).execute()


def get_user_quotes(chat_id: int) -> list[dict]:
    result = (
        _db()
        .table("user_quotes")
        .select("*")
        .eq("chat_id", chat_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


def get_random_user_quote(chat_id: int) -> dict | None:
    """Return a random saved quote and update its last_sent_at timestamp."""
    result = _db().table("user_quotes").select("*").eq("chat_id", chat_id).execute()
    if not result.data:
        return None
    quote = random.choice(result.data)
    _db().table("user_quotes").update(
        {"last_sent_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", quote["id"]).execute()
    return quote
