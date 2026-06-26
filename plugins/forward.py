"""
Core forwarding engine.
Listens to ALL channel messages and routes them per saved active projects.
"""
import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait, ChatWriteForbidden, ChannelInvalid
from database import db
from config import Config, temp

logger = logging.getLogger(__name__)


def _message_type(message: Message) -> str:
    if message.text or message.caption:
        if not any([message.photo, message.video, message.audio, message.document,
                    message.voice, message.animation, message.sticker, message.poll]):
            return "text"
    if message.photo: return "photo"
    if message.video: return "video"
    if message.audio: return "audio"
    if message.document: return "document"
    if message.voice: return "voice"
    if message.animation: return "animation"
    if message.sticker: return "sticker"
    if message.poll: return "poll"
    return "unknown"


def _passes_filter(message: Message, f: dict) -> bool:
    mtype = _message_type(message)
    return f.get(mtype, True)


async def _send_message(fwd_client: Client, message: Message, dest_id: int, forward_tag: bool):
    """Copy or forward a single message to dest_id."""
    try:
        if forward_tag:
            # Forward with tag
            await fwd_client.forward_messages(
                chat_id=dest_id,
                from_chat_id=message.chat.id,
                message_ids=message.id
            )
        else:
            # Copy without forward tag
            await message.copy(dest_id)
    except FloodWait as e:
        logger.warning(f"FloodWait {e.value}s, sleeping...")
        await asyncio.sleep(e.value + 1)
        await _send_message(fwd_client, message, dest_id, forward_tag)
    except (ChatWriteForbidden, ChannelInvalid) as e:
        logger.error(f"Cannot write to {dest_id}: {e}")
    except Exception as e:
        logger.exception(f"Error forwarding to {dest_id}: {e}")


@Client.on_message(filters.channel & filters.incoming)
async def channel_message_handler(bot: Client, message: Message):
    """Handle new messages from any channel the bot is in."""
    source_id = message.chat.id

    # Find all active projects with this source
    # We do a full scan; in production you'd want an indexed query
    # For now, search all projects efficiently
    from bson import ObjectId
    cursor = db.projects.find({"source_id": source_id, "active": True})
    projects = [p async for p in cursor]

    if not projects:
        return

    for project in projects:
        user_id = project["user_id"]
        destinations = project.get("destinations", [])
        if not destinations:
            continue

        # Get user's bot/userbot
        _bot_data = await db.get_bot(user_id)
        if not _bot_data:
            continue

        project_filters = project.get("filters") or db.default_filters()
        forward_tag = project.get("forward_tag", False)

        # Check filter
        if not _passes_filter(message, project_filters):
            logger.debug(f"Message filtered out for project {project['_id']}")
            continue

        # Create client for forwarding
        try:
            if _bot_data.get("is_bot"):
                fwd_client = Client(
                    f"fwd_{user_id}",
                    api_id=Config.API_ID,
                    api_hash=Config.API_HASH,
                    bot_token=_bot_data["token"],
                    in_memory=True
                )
            else:
                fwd_client = Client(
                    f"fwd_{user_id}",
                    api_id=Config.API_ID,
                    api_hash=Config.API_HASH,
                    session_string=_bot_data["session"],
                    in_memory=True
                )
            await fwd_client.start()
        except Exception as e:
            logger.error(f"Could not start forwarding client for user {user_id}: {e}")
            continue

        # Send to all destinations
        for dest in destinations:
            dest_id = dest["id"]
            await _send_message(fwd_client, message, dest_id, forward_tag)
            await asyncio.sleep(0.5)

        temp.forwardings += 1

        try:
            await fwd_client.stop()
        except Exception:
            pass
