"""
Core forwarding engine.
Listens to ALL channel messages and routes them per saved active projects.
"""
import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait, ChatWriteForbidden, ChannelInvalid, MessageIdInvalid
from database import db
from config import Config, temp

logger = logging.getLogger(__name__)

# In-memory cache: user_id -> Client (persistent per session)
_fwd_clients: dict = {}

# Duplicate tracking: set of (project_id_str, message_id)
_forwarded_ids: set = set()
_MAX_CACHE = 10000  # prevent unbounded growth


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


async def _get_fwd_client(user_id: int, bot_data: dict) -> Client | None:
    """Return cached client or create + start a new one."""
    global _fwd_clients
    if user_id in _fwd_clients:
        cl = _fwd_clients[user_id]
        if cl.is_connected:
            return cl
        # reconnect if disconnected
        try:
            await cl.start()
            return cl
        except Exception:
            _fwd_clients.pop(user_id, None)

    try:
        if bot_data.get("is_bot"):
            cl = Client(
                f"fwd_{user_id}",
                api_id=Config.API_ID,
                api_hash=Config.API_HASH,
                bot_token=bot_data["token"],
                in_memory=True,
            )
        else:
            cl = Client(
                f"fwd_{user_id}",
                api_id=Config.API_ID,
                api_hash=Config.API_HASH,
                session_string=bot_data["session"],
                in_memory=True,
            )
        await cl.start()
        _fwd_clients[user_id] = cl
        return cl
    except Exception as e:
        logger.error(f"Could not start forwarding client for user {user_id}: {e}")
        return None


async def _send_message(fwd_client: Client, message: Message, dest_id: int, forward_tag: bool):
    """Copy or forward a single message to dest_id."""
    try:
        if forward_tag:
            await fwd_client.forward_messages(
                chat_id=dest_id,
                from_chat_id=message.chat.id,
                message_ids=message.id,
            )
        else:
            # copy_message works for ALL types including video/document
            await fwd_client.copy_message(
                chat_id=dest_id,
                from_chat_id=message.chat.id,
                message_id=message.id,
            )
    except FloodWait as e:
        wait = e.value + 1
        logger.warning(f"FloodWait {wait}s, sleeping...")
        await asyncio.sleep(wait)
        await _send_message(fwd_client, message, dest_id, forward_tag)
    except (ChatWriteForbidden, ChannelInvalid) as e:
        logger.error(f"Cannot write to {dest_id}: {e}")
    except MessageIdInvalid:
        logger.warning(f"MessageIdInvalid for msg {message.id} -> {dest_id}, skipping")
    except Exception as e:
        logger.exception(f"Error forwarding to {dest_id}: {e}")


@Client.on_message(filters.channel & filters.incoming)
async def channel_message_handler(bot: Client, message: Message):
    """Handle new messages from any channel the bot is in."""
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

        user_id = project["user_id"]
        destinations = project.get("destinations", [])
        if not destinations:
            continue

        bot_data = await db.get_bot(user_id)
        if not bot_data:
            continue

        project_filters = project.get("filters") or db.default_filters()
        forward_tag = project.get("forward_tag", False)

        if not _passes_filter(message, project_filters):
            logger.debug(f"Message filtered out for project {project_id_str}")
            continue

        fwd_client = await _get_fwd_client(user_id, bot_data)
        if not fwd_client:
            continue

        # Mark as forwarded BEFORE sending to prevent race duplicate
        _forwarded_ids.add(dup_key)
        if len(_forwarded_ids) > _MAX_CACHE:
            # Drop oldest half to keep memory bounded
            old = list(_forwarded_ids)[:_MAX_CACHE // 2]
            for k in old:
                _forwarded_ids.discard(k)

        # Send to all destinations with 2s delay between each
        for dest in destinations:
            dest_id = dest["id"]
            await _send_message(fwd_client, message, dest_id, forward_tag)
            await asyncio.sleep(2)

        temp.forwardings += 1
