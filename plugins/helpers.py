import re
import logging
from pyrogram import Client
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import Config

logger = logging.getLogger(__name__)

MAX_PROJECTS_FREE = 3
MAX_DESTINATIONS_FREE = 3

async def is_premium_or_owner(user_id: int) -> bool:
    """Check if user is owner or auth (premium)."""
    from database import db
    if user_id in Config.BOT_OWNER_ID:
        return True
    return await db.is_auth(user_id)

async def get_channel_id_from_input(bot: Client, text: str, fwd_msg=None):
    """
    Try to extract channel ID from:
    1. Forward message
    2. Raw ID like -1001234567890
    3. @username
    Returns (chat_id, title) or (None, None)
    """
    # From forwarded message
    if fwd_msg and fwd_msg.forward_from_chat:
        chat = fwd_msg.forward_from_chat
        return chat.id, chat.title or str(chat.id)

    if not text:
        return None, None

    text = text.strip()

    # Numeric ID
    if re.match(r'^-?\d+$', text):
        cid = int(text)
        try:
            chat = await bot.get_chat(cid)
            return chat.id, chat.title or str(cid)
        except Exception:
            return cid, str(cid)

    # @username
    if text.startswith("@") or not text.startswith("-"):
        try:
            chat = await bot.get_chat(text)
            return chat.id, chat.title or text
        except Exception:
            return None, None

    return None, None

def back_btn(data: str):
    return InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data=data)]])

async def check_fsub(bot: Client, user_id: int) -> list:
    """
    Returns list of channels user hasn't joined yet.
    Each item: {"id": ..., "title": ..., "invite": ...}
    """
    from config import Config
    not_joined = []
    for ch in Config.FSUB_CHANNELS:
        try:
            member = await bot.get_chat_member(ch, user_id)
            from pyrogram.enums import ChatMemberStatus
            if member.status in [ChatMemberStatus.BANNED, ChatMemberStatus.LEFT]:
                raise Exception("not joined")
        except Exception:
            try:
                chat = await bot.get_chat(ch)
                invite = f"https://t.me/{chat.username}" if chat.username else None
                if not invite:
                    try:
                        link = await bot.export_chat_invite_link(ch)
                        invite = link
                    except Exception:
                        invite = None
                not_joined.append({
                    "id": ch,
                    "title": chat.title if hasattr(chat, "title") else str(ch),
                    "invite": invite
                })
            except Exception:
                not_joined.append({"id": ch, "title": str(ch), "invite": None})
    return not_joined

def fsub_markup(not_joined: list):
    """Build inline keyboard with join buttons + verified check."""
    buttons = []
    for ch in not_joined:
        row = []
        if ch.get("invite"):
            row.append(InlineKeyboardButton(ch["title"], url=ch["invite"]))
        else:
            row.append(InlineKeyboardButton(ch["title"], callback_data="fsub_noop"))
        buttons.append(row)
    buttons.append([InlineKeyboardButton("✅ Joined / Verify", callback_data="fsub_check")])
    return InlineKeyboardMarkup(buttons)
