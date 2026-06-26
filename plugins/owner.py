import asyncio
import time
import datetime
from database import db
from config import Config, temp
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated


# ─── Owner filter ─────────────────────────────────────────────────────────────
def owner_filter(_, __, message: Message) -> bool:
    return message.from_user and message.from_user.id in Config.BOT_OWNER_ID

owner_only = filters.create(owner_filter)


# ─── Broadcast ────────────────────────────────────────────────────────────────
@Client.on_message(filters.private & filters.command("broadcast") & owner_only & filters.reply)
async def broadcast_cmd(bot: Client, message: Message):
    b_msg = message.reply_to_message
    users = await db.get_all_users()
    sts = await message.reply_text("📢 Broadcasting...")
    start = time.time()
    success = failed = blocked = deleted = 0
    async for user in users:
        uid = user["id"]
        try:
            await b_msg.copy(uid)
            success += 1
            await asyncio.sleep(0.05)
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
            try:
                await b_msg.copy(uid)
                success += 1
            except Exception:
                failed += 1
        except UserIsBlocked:
            blocked += 1
        except InputUserDeactivated:
            await db.delete_user(uid)
            deleted += 1
        except Exception:
            failed += 1

    elapsed = datetime.timedelta(seconds=int(time.time() - start))
    await sts.edit(
        f"✅ <b>Broadcast Complete</b>\n\n"
        f"• Total: {success + failed + blocked + deleted}\n"
        f"• Success: {success}\n"
        f"• Blocked: {blocked}\n"
        f"• Deleted: {deleted}\n"
        f"• Failed: {failed}\n"
        f"• Time: {elapsed}"
    )


# ─── Auth / Unauth (Premium) ──────────────────────────────────────────────────
@Client.on_message(filters.private & filters.command("auth") & owner_only)
async def auth_cmd(bot: Client, message: Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply_text("Usage: /auth <user_id>")
        return
    uid = int(args[1])
    if not await db.is_user_exist(uid):
        await message.reply_text("❌ User not found in database.")
        return
    await db.auth_user(uid)
    try:
        await bot.send_message(uid, "🎉 You have been granted <b>Premium</b> access by the owner!")
    except Exception:
        pass
    await message.reply_text(f"✅ User <code>{uid}</code> granted Premium.")


@Client.on_message(filters.private & filters.command("unauth") & owner_only)
async def unauth_cmd(bot: Client, message: Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply_text("Usage: /unauth <user_id>")
        return
    uid = int(args[1])
    await db.unauth_user(uid)
    await message.reply_text(f"✅ Premium removed from <code>{uid}</code>.")


# ─── Ban / Unban ──────────────────────────────────────────────────────────────
@Client.on_message(filters.private & filters.command("ban") & owner_only)
async def ban_cmd(bot: Client, message: Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply_text("Usage: /ban <user_id>")
        return
    uid = int(args[1])
    await db.ban_user(uid)
    await message.reply_text(f"🚫 User <code>{uid}</code> banned.")


@Client.on_message(filters.private & filters.command("unban") & owner_only)
async def unban_cmd(bot: Client, message: Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply_text("Usage: /unban <user_id>")
        return
    uid = int(args[1])
    await db.unban_user(uid)
    await message.reply_text(f"✅ User <code>{uid}</code> unbanned.")


# ─── Stats ────────────────────────────────────────────────────────────────────
@Client.on_message(filters.private & filters.command("stats") & owner_only)
async def stats_cmd(bot: Client, message: Message):
    users = await db.total_users_count()
    projects = await db.total_projects_count()
    await message.reply_text(
        f"<b>📊 Bot Stats</b>\n\n"
        f"• Total Users: <code>{users}</code>\n"
        f"• Total Projects: <code>{projects}</code>\n"
        f"• Total Forwardings (session): <code>{temp.forwardings}</code>\n"
    )


# ─── List users ───────────────────────────────────────────────────────────────
@Client.on_message(filters.private & filters.command("users") & owner_only)
async def users_cmd(bot: Client, message: Message):
    users = await db.get_all_users()
    lines = []
    async for u in users:
        uid = u["id"]
        name = u.get("name", "?")
        status = "👑 Owner" if uid in Config.BOT_OWNER_ID else ("⭐" if u.get("is_auth") else "🆓")
        lines.append(f"{status} <code>{uid}</code> — {name}")
    text = "<b>👥 All Users</b>\n\n" + "\n".join(lines[:50]) if lines else "No users."
    await message.reply_text(text[:4000])


# ─── Ban middleware ───────────────────────────────────────────────────────────
@Client.on_message(filters.private & filters.incoming, group=-1)
async def ban_middleware(bot: Client, message: Message):
    if message.from_user and await db.is_banned(message.from_user.id):
        await message.reply_text("🚫 You are banned from using this bot.")
        message.stop_propagation()
