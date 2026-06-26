"""
Core forwarding engine.
Bot itself (admin in both channels) copies messages from source to destination.
No secondary client needed — uses the main bot directly.
"""
import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait, ChatWriteForbidden, ChannelInvalid, MessageIdInvalid
from database import db
from config import temp

logger = logging.getLogger(__name__)

# Duplicate tracking: set of (project_id_str, message_id)
_forwarded_ids: set = set()
_MAX_CACHE = 10000


def _message_type(message: Message) -> str:
    if message.video:     return "video"
    if message.document:  return "document"
    if message.photo:     return "photo"
    if message.audio:     return "audio"
    if message.voice:     return "voice"
    if message.animation: return "animation"
    if message.sticker:   return "sticker"
    if message.poll:      return "poll"
    if message.text or message.caption:
        return "text"
    return "unknown"


def _passes_filter(message: Message, f: dict) -> bool:
    mtype = _message_type(message)
    return f.get(mtype, True)


async def _send_message(bot: Client, message: Message, dest_id: int, forward_tag: bool):
    """Copy or forward a single message to dest_id using the main bot."""
    try:
        if forward_tag:
            await bot.forward_messages(
                chat_id=dest_id,
                from_chat_id=message.chat.id,
                message_ids=message.id,
            )
        else:
            # copy_message: sends without "Forwarded from" tag
            # Works for video, document, photo, audio, voice, animation, text, etc.
            await bot.copy_message(
                chat_id=dest_id,
                from_chat_id=message.chat.id,
                message_id=message.id,
            )
    except FloodWait as e:
        wait = e.value + 1
        logger.warning(f"FloodWait {wait}s, sleeping...")
        await asyncio.sleep(wait)
        await _send_message(bot, message, dest_id, forward_tag)
    except (ChatWriteForbidden, ChannelInvalid) as e:
        logger.error(f"Cannot write to {dest_id}: {e}")
    except MessageIdInvalid:
        logger.warning(f"MessageIdInvalid for msg {message.id} -> {dest_id}, skipping")
    except Exception as e:
        logger.exception(f"Error copying to {dest_id}: {e}")


@Client.on_message(filters.channel & filters.incoming)
async def channel_message_handler(bot: Client, message: Message):
    """Handle new messages from any channel the bot is admin in."""
    source_id = message.chat.id

    # Find all active projects with this source
    from bson import ObjectId
    cursor = db.projects.find({"source_id": source_id, "active": True})
    projects = [p async for p in cursor]

    if not projects:
        return

    for project in projects:
        project_id_str = str(project["_id"])
        dup_key = (project_id_str, message.id)

        # Duplicate check
        if dup_key in _forwarded_ids:
            logger.debug(f"Duplicate msg {message.id} for project {project_id_str}, skipping")
            continue

        destinations = project.get("destinations", [])
        if not destinations:
            continue

        project_filters = project.get("filters") or db.default_filters()
        forward_tag = project.get("forward_tag", False)

        if not _passes_filter(message, project_filters):
            logger.debug(f"Message filtered out for project {project_id_str}")
            continue

        mtype = _message_type(message)
        logger.info(f"Copying [{mtype}] msg {message.id} from {source_id} for project {project_id_str}")

        # Mark before sending to prevent race duplicates
        _forwarded_ids.add(dup_key)
        if len(_forwarded_ids) > _MAX_CACHE:
            old = list(_forwarded_ids)[:_MAX_CACHE // 2]
            for k in old:
                _forwarded_ids.discard(k)

        # Send to all destinations with small delay
        for dest in destinations:
            dest_id = dest["id"]
            await _send_message(bot, message, dest_id, forward_tag)
            await asyncio.sleep(1)

        temp.forwardings += 1
        logger.info(f"Done. Total forwardings: {temp.forwardings}")
