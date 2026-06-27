"""
╔══════════════════════════════════════════════════════════════════╗
║              FURY AUTOMATION BOT - main.py                       ║
║  • BotFather Bot  → Control panel (/start, commands, /data)      ║
║  • Userbot        → Sends scheduled messages (chat + channel)    ║
╚══════════════════════════════════════════════════════════════════╝
"""

import asyncio
import os
import json
import random
import threading
from flask import Flask
from datetime import datetime, date

import pytz
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pyrogram.errors import FloodWait, PeerIdInvalid

from config import API_ID, API_HASH, BOT_TOKEN, STRING_SESSION, OWNER_ID

print(f"[config] API_ID     = {API_ID}")
print(f"[config] API_HASH   = {API_HASH}")
print(f"[config] BOT_TOKEN  = {BOT_TOKEN if BOT_TOKEN else 'MISSING ⚠️'}")
print(f"[config] STRING_SESSION = {STRING_SESSION if STRING_SESSION else 'MISSING ⚠️'}")
print(f"[config] OWNER_ID   = {OWNER_ID}")

# ════════════════════════════════════════════════════════════════════
#  TIMEZONE
# ════════════════════════════════════════════════════════════════════
IST = pytz.timezone("Asia/Kolkata")


# ════════════════════════════════════════════════════════════════════
#  SAVE DATA  (savedata.json)
# ════════════════════════════════════════════════════════════════════
SAVE_DATA_FILE = "savedata.json"

def _load_savedata() -> dict:
    try:
        with open(SAVE_DATA_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_savedata(data: dict):
    try:
        with open(SAVE_DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[savedata] write error: {e}")

def record_step(step_name: str, detail: str):
    """Called every time userbot successfully sends a message."""
    data = _load_savedata()
    today = str(date.today())
    if today not in data:
        data[today] = {"steps": []}
    data[today]["steps"].append({
        "step": step_name,
        "detail": detail,
        "time": datetime.now(IST).strftime("%H:%M:%S")
    })
    _save_savedata(data)


# ════════════════════════════════════════════════════════════════════
#  LIVE-CHANGEABLE STEP TEXTS
#  Each batch has 2 command steps: 3rd step and 12th step
# ════════════════════════════════════════════════════════════════════
STEP_TEXTS: dict = {
    "step3":  "your step3 msg here",  # your 1st batch first command
    "step12": "your step12 msg here",  # your 1st batch second command
    "step19":  "your step19 msg here",  # your 2nd batch first command
    "step28": "your step28 msg here",  # your 2nd batch second command
    "step35":  "your step35 msg here",  # your 3rd batch first command
    "step44": "your step44 msg here",  # your 3rd batch second command
    "step51":  "your step51 msg here",  # your 4th batch first command
    "step60": "your step60 msg here",  # your 4th batch second command
    "step67":  "your step67 msg here",  # your 5th batch first command
    "step76": "your step76 msg here",  # your 5th batch second command
}


# ════════════════════════════════════════════════════════════════════
#  RANDOM IMAGE LIST  (for /start command)
# ════════════════════════════════════════════════════════════════════
IMAGE_LIST = [
    "https://graph.org/file/0ffe5c1245b874d4a9bf1-3b2481397f6f380c85.jpg",
    "https://graph.org/file/fae9ed988db074ba5c2f5-ad0a0037cc1bdddbdd.jpg",
    "https://graph.org/file/d24b9bd4d0592a07ad746-de047531c5efafafce.jpg",
    "https://graph.org/file/30b2b264822802cfca0e5-955b8cb8bd0ef5da16.jpg",
    "https://graph.org/file/06d5077e2fe5442e1dbb4-77cb51eecc0aab0608.jpg",
    "https://graph.org/file/47792b7d2acd7ab812e65-ae8e8c3b1071eb2b23.jpg",
    "https://graph.org/file/8ea482ae6278601bae5c5-b1475ac9b0622a6cd7.jpg",
    "https://graph.org/file/648d50f45bf0dd06cd12a-129509de7ebc2c6036.jpg",
    "https://graph.org/file/5312e32455e56860c75cb-b56bedb77b7cf93227.jpg",
    "https://graph.org/file/977afb0f88089d227a19d-443ba34add7d83a182.jpg",
]


# ════════════════════════════════════════════════════════════════════
#  PYROGRAM CLIENTS
# ════════════════════════════════════════════════════════════════════

print("[init] Creating BotFather client...")
bot = Client(
    "fury_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)

print("[init] Creating Userbot client...")
userbot = Client(
    "fury_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=STRING_SESSION,
)
print("[init] Both clients created ✅")


# ════════════════════════════════════════════════════════════════════
#  PEER CACHE WARM-UP
# ════════════════════════════════════════════════════════════════════
TARGET_CHATS = [
    8757350577,
    -1004490369392,
    -1003028157033,
    8715662594,
    -1004478451764,
    8951680134,
]

async def warmup_peers():
    try:
        async for _ in userbot.get_dialogs():
            pass
        print("[warmup] dialogs synced ✅")
    except Exception as e:
        print(f"[warmup] get_dialogs skipped (non-fatal): {e}")

    for cid in TARGET_CHATS:
        try:
            await userbot.resolve_peer(cid)
            print(f"[warmup] peer cached ✅ → {cid}")
        except Exception as e:
            print(f"[warmup] peer cache pending for {cid} (will retry on send): {e}")
        await asyncio.sleep(0.3)


async def peer_warmup_loop():
    while True:
        await asyncio.sleep(3 * 60 * 60)
        print("[warmup] periodic peer refresh...")
        await warmup_peers()


async def safe_send(chat_id, text):
    last_err = None
    for attempt in range(3):
        try:
            return await userbot.send_message(chat_id=chat_id, text=text)
        except FloodWait as e:
            wait_for = getattr(e, "value", getattr(e, "x", 5))
            print(f"[safe_send] FloodWait {wait_for}s for {chat_id}, waiting then retrying...")
            await asyncio.sleep(wait_for + 1)
            last_err = e
        except PeerIdInvalid as e:
            print(f"[safe_send] Peer cache miss for {chat_id}, re-resolving then retrying...")
            try:
                await userbot.resolve_peer(chat_id)
            except Exception:
                pass
            last_err = e
    raise last_err


# ════════════════════════════════════════════════════════════════════
#  OWNER CHECK FILTER
# ════════════════════════════════════════════════════════════════════
def owner_only(_, __, message: Message) -> bool:
    return message.from_user and message.from_user.id == OWNER_ID

owner_filter = filters.create(owner_only)


# ════════════════════════════════════════════════════════════════════
#  ── BOT COMMANDS ────────────────────────────────────────────────
# ════════════════════════════════════════════════════════════════════

# ── /start ───────────────────────────────────────────────────────────────────
@bot.on_message(filters.command("start") & filters.private)
async def cmd_start(_, message: Message):
    if message.from_user.id != OWNER_ID:
        await message.reply_text("🚫 Sorry Dude you are Not my Owner 😊.")
        return

    photo = random.choice(IMAGE_LIST)
    caption = (
        "👋 **Hey Boss!😎**\n\n"
        "✅ **Fury Automation Bot is Active!**\n\n"
        "🤖 Userbot is running and handling all scheduled tasks.\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📌 **Available Commands:**\n"
        "• /start — Bot status\n"
        "• /step3 — 1st batch first cmd | /step12 — 1st batch second cmd\n"
        "• /step19 — 2nd batch first cmd | /step28 — 2nd batch second cmd\n"
        "• /step35 — 3rd batch first cmd | /step44 — 3rd batch second cmd\n"
        "• /step51 — 4th batch first cmd | /step60 — 4th batch second cmd\n"
        "• /step67 — 5th batch first cmd | /step76 — 5th batch second cmd\n"
        "• /data — View today's bot activity log\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "💪 **All systems go. Let's crush it!**\n\n"
        "Powerd by: Team Toxic"
    )
    try:
        await message.reply_photo(photo=photo, caption=caption)
    except Exception:
        await message.reply_text(caption)


# ── /step3 (1st batch first command) ─────────────────────────────────────────
@bot.on_message(filters.command("step3") & filters.private & owner_filter)
async def cmd_step3(_, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "**Usage:**\n`/step3 Your new message here`\n\n"
            f"**Current text:**\n{STEP_TEXTS['step3']}"
        )
    STEP_TEXTS["step3"] = message.text.split(None, 1)[1]
    await message.reply_text(
        f"✅ **Step3 Text Updated!**\n\n📝 **New Message:**\n{STEP_TEXTS['step3']}\n\nPowerd by: Team Toxic"
    )


# ── /step12 (1st batch second command) ─────────────────────────────────────────
@bot.on_message(filters.command("step12") & filters.private & owner_filter)
async def cmd_step12(_, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "**Usage:**\n`/step12 Your new message here`\n\n"
            f"**Current text:**\n{STEP_TEXTS['step12']}"
        )
    STEP_TEXTS["step12"] = message.text.split(None, 1)[1]
    await message.reply_text(
        f"✅ **Step12 Text Updated!**\n\n📝 **New Message:**\n{STEP_TEXTS['step12']}\n\nPowerd by: Team Toxic"
    )


# ── /step19 (2nd batch first command) ─────────────────────────────────────────
@bot.on_message(filters.command("step19") & filters.private & owner_filter)
async def cmd_step19(_, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "**Usage:**\n`/step19 Your new message here`\n\n"
            f"**Current text:**\n{STEP_TEXTS['step19']}"
        )
    STEP_TEXTS["step19"] = message.text.split(None, 1)[1]
    await message.reply_text(
        f"✅ **Step19 Text Updated!**\n\n📝 **New Message:**\n{STEP_TEXTS['step19']}\n\nPowerd by: Team Toxic"
    )


# ── /step28 (2nd batch second command) ─────────────────────────────────────────
@bot.on_message(filters.command("step28") & filters.private & owner_filter)
async def cmd_step28(_, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "**Usage:**\n`/step28 Your new message here`\n\n"
            f"**Current text:**\n{STEP_TEXTS['step28']}"
        )
    STEP_TEXTS["step28"] = message.text.split(None, 1)[1]
    await message.reply_text(
        f"✅ **Step28 Text Updated!**\n\n📝 **New Message:**\n{STEP_TEXTS['step28']}\n\nPowerd by: Team Toxic"
    )


# ── /step35 (3rd batch first command) ─────────────────────────────────────────
@bot.on_message(filters.command("step35") & filters.private & owner_filter)
async def cmd_step35(_, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "**Usage:**\n`/step35 Your new message here`\n\n"
            f"**Current text:**\n{STEP_TEXTS['step35']}"
        )
    STEP_TEXTS["step35"] = message.text.split(None, 1)[1]
    await message.reply_text(
        f"✅ **Step35 Text Updated!**\n\n📝 **New Message:**\n{STEP_TEXTS['step35']}\n\nPowerd by: Team Toxic"
    )


# ── /step44 (3rd batch second command) ─────────────────────────────────────────
@bot.on_message(filters.command("step44") & filters.private & owner_filter)
async def cmd_step44(_, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "**Usage:**\n`/step44 Your new message here`\n\n"
            f"**Current text:**\n{STEP_TEXTS['step44']}"
        )
    STEP_TEXTS["step44"] = message.text.split(None, 1)[1]
    await message.reply_text(
        f"✅ **Step44 Text Updated!**\n\n📝 **New Message:**\n{STEP_TEXTS['step44']}\n\nPowerd by: Team Toxic"
    )


# ── /step51 (4th batch first command) ─────────────────────────────────────────
@bot.on_message(filters.command("step51") & filters.private & owner_filter)
async def cmd_step51(_, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "**Usage:**\n`/step51 Your new message here`\n\n"
            f"**Current text:**\n{STEP_TEXTS['step51']}"
        )
    STEP_TEXTS["step51"] = message.text.split(None, 1)[1]
    await message.reply_text(
        f"✅ **Step51 Text Updated!**\n\n📝 **New Message:**\n{STEP_TEXTS['step51']}\n\nPowerd by: Team Toxic"
    )


# ── /step60 (4th batch second command) ─────────────────────────────────────────
@bot.on_message(filters.command("step60") & filters.private & owner_filter)
async def cmd_step60(_, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "**Usage:**\n`/step60 Your new message here`\n\n"
            f"**Current text:**\n{STEP_TEXTS['step60']}"
        )
    STEP_TEXTS["step60"] = message.text.split(None, 1)[1]
    await message.reply_text(
        f"✅ **Step60 Text Updated!**\n\n📝 **New Message:**\n{STEP_TEXTS['step60']}\n\nPowerd by: Team Toxic"
    )


# ── /step67 (5th batch first command) ─────────────────────────────────────────
@bot.on_message(filters.command("step67") & filters.private & owner_filter)
async def cmd_step67(_, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "**Usage:**\n`/step67 Your new message here`\n\n"
            f"**Current text:**\n{STEP_TEXTS['step67']}"
        )
    STEP_TEXTS["step67"] = message.text.split(None, 1)[1]
    await message.reply_text(
        f"✅ **Step67 Text Updated!**\n\n📝 **New Message:**\n{STEP_TEXTS['step67']}\n\nPowerd by: Team Toxic"
    )


# ── /step76 (5th batch second command) ─────────────────────────────────────────
@bot.on_message(filters.command("step76") & filters.private & owner_filter)
async def cmd_step76(_, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "**Usage:**\n`/step76 Your new message here`\n\n"
            f"**Current text:**\n{STEP_TEXTS['step76']}"
        )
    STEP_TEXTS["step76"] = message.text.split(None, 1)[1]
    await message.reply_text(
        f"✅ **Step76 Text Updated!**\n\n📝 **New Message:**\n{STEP_TEXTS['step76']}\n\nPowerd by: Team Toxic"
    )


# ── /data  (show today's activity log from savedata.json) ────────────────────
@bot.on_message(filters.command("data") & filters.private & owner_filter)
async def cmd_data(_, message: Message):
    data = _load_savedata()
    today = str(date.today())

    if today not in data or not data[today]["steps"]:
        return await message.reply_text(
            f"📅 **Date:** `{today}`\n\n"
            "⚠️ No work recorded for today yet.\n"
            "Bot may not have run any steps today."
        )

    steps = data[today]["steps"]
    first_step = steps[0]
    last_step  = steps[-1]

    details_text = ""
    for s in steps:
        details_text += f"  • `{s['time']}` — **{s['step']}**: {s['detail']}\n"

    msg = (
        f"📅 **Date:** `{today}`\n\n"
        f"🔰 **First Step:** {first_step['step']} at `{first_step['time']}`\n"
        f"🏁 **Last Step:**  {last_step['step']} at `{last_step['time']}`\n\n"
        f"📋 **All Steps Today:**\n{details_text}\n"
        "✅ **This Date's Work: Done ✅**\n\n"
        "Powerd by: Team Toxic"
    )
    await message.reply_text(msg)


# ── Catch-all: non-owner trying any command ───────────────────────────────────
@bot.on_message(filters.private & ~owner_filter)
async def reject_non_owner(_, message: Message):
    if message.text and message.text.startswith("/"):
        await message.reply_text("🚫 Sorry Dude you are Not my Owner 😊.")


# ════════════════════════════════════════════════════════════════════
#  ── USERBOT SCHEDULER ───────────────────────────────────────────
# ════════════════════════════════════════════════════════════════════

def _now_ist_str() -> str:
    """Return current IST time as HH:MM:SS"""
    return datetime.now(IST).strftime("%H:%M:%S")


async def run_scheduler():
    print("[scheduler] Entered run_scheduler ✅")
    await asyncio.sleep(5)
    print("[scheduler] Initial 5s sleep done, starting infinite loop...")

    last_sent: dict = {}

    STEP_TIMES = {
        # ══ BATCH 1: #1st batch ══
        "step1": "22:30:01",
        "step2": "22:30:26",
        "step3": "22:30:59",
        "step4": "22:31:30",
        "step5": "22:31:59",
        "step6": "22:32:30",
        "step7": "22:32:59",
        "step8": "22:33:30",
        "step9": "22:33:59",
        "step10": "22:34:30",
        "step11": "22:34:59",
        "step12": "22:35:30",
        "step13": "22:35:59",
        "step14": "22:36:30",
        "step15": "22:47:59",
        "step16": "22:48:30",
        # ══ BATCH 2: #2nd batch ══
        "step17": "22:49:01",
        "step18": "22:49:26",
        "step19": "22:49:59",
        "step20": "22:50:30",
        "step21": "22:50:59",
        "step22": "22:51:30",
        "step23": "22:51:59",
        "step24": "22:52:30",
        "step25": "22:52:59",
        "step26": "22:53:30",
        "step27": "22:53:59",
        "step28": "22:54:30",
        "step29": "22:54:59",
        "step30": "22:55:30",
        "step31": "22:56:59",
        "step32": "22:57:30",
        # ══ BATCH 3: #3rd batch ══
        "step33": "22:58:01",
        "step34": "22:58:26",
        "step35": "22:58:59",
        "step36": "22:59:30",
        "step37": "22:59:59",
        "step38": "23:00:30",
        "step39": "23:00:59",
        "step40": "23:01:30",
        "step41": "23:01:59",
        "step42": "23:02:30",
        "step43": "23:02:59",
        "step44": "23:03:30",
        "step45": "23:03:59",
        "step46": "23:04:30",
        "step47": "23:15:59",
        "step48": "23:16:30",
        # ══ BATCH 4: #4th batch ══
        "step49": "23:17:01",
        "step50": "23:17:26",
        "step51": "23:17:59",
        "step52": "23:18:30",
        "step53": "23:18:59",
        "step54": "23:19:30",
        "step55": "23:19:59",
        "step56": "23:20:30",
        "step57": "23:20:59",
        "step58": "23:21:30",
        "step59": "23:21:59",
        "step60": "23:22:30",
        "step61": "23:22:59",
        "step62": "23:23:30",
        "step63": "23:34:59",
        "step64": "23:35:30",
        # ══ BATCH 5: #5th batch ══
        "step65": "23:36:01",
        "step66": "23:36:26",
        "step67": "23:36:59",
        "step68": "23:37:30",
        "step69": "23:37:59",
        "step70": "23:38:30",
        "step71": "23:38:59",
        "step72": "23:39:30",
        "step73": "23:39:59",
        "step74": "23:40:30",
        "step75": "23:40:59",
        "step76": "23:41:30",
        "step77": "23:41:59",
        "step78": "23:42:30",
        "step79": "23:53:59",
        "step80": "23:54:30",
    }

    while True:
        now_str = _now_ist_str()
        today_str = str(date.today())


        # ════════════════════════════════════════════════════════════
        # #1st batch
        # ════════════════════════════════════════════════════════════
        # ════════════════════════════════════════════════════════════
        #  STEP 1  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step1 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step1"] and last_sent.get("step1") != today_str:
            print(f"[step1] Attempting to send @ {_now_ist_str()}...")
            try:
                step1_text = "your step1 message"
                await safe_send(
                    chat_id=8757350577,          # your step1 chat id here
                    text=step1_text
                )
                record_step("Step-1", f"DM → step1 target | {step1_text[:40]} | Powerd by: Team Toxic")
                print(f"[step1] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step1] ❌ ERROR: {e}")
            last_sent["step1"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 2  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step2 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step2"] and last_sent.get("step2") != today_str:
            print(f"[step2] Attempting to send @ {_now_ist_str()}...")
            try:
                step2_text = "your step2 message"
                await safe_send(
                    chat_id=8757350577,          # your step2 chat id here
                    text=step2_text
                )
                record_step("Step-2", f"DM → step2 target | {step2_text[:40]} | Powerd by: Team Toxic")
                print(f"[step2] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step2] ❌ ERROR: {e}")
            last_sent["step2"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 3  (changeable via /step3)
        #  Type   : DM (personal chat)  — text changeable via /step3
        #  Target : your step3 chat id here
        #  Text   : STEP_TEXTS["step3"]  ← changeable via /step3
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step3"] and last_sent.get("step3") != today_str:
            print(f"[step3] Attempting to send @ {_now_ist_str()}...")
            try:
                await safe_send(
                    chat_id=8757350577,          # your step3 chat id here
                    text=STEP_TEXTS["step3"]
                )
                record_step("Step-3", f"DM → step3 target | {STEP_TEXTS['step3'][:40]} | Powerd by: Team Toxic")
                print(f"[step3] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step3] ❌ ERROR: {e}")
            last_sent["step3"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 4  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step4 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step4"] and last_sent.get("step4") != today_str:
            print(f"[step4] Attempting to send @ {_now_ist_str()}...")
            try:
                step4_text = "your step4 message"
                await safe_send(
                    chat_id=8757350577,          # your step4 chat id here
                    text=step4_text
                )
                record_step("Step-4", f"DM → step4 target | {step4_text[:40]} | Powerd by: Team Toxic")
                print(f"[step4] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step4] ❌ ERROR: {e}")
            last_sent["step4"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 5  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step5 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step5"] and last_sent.get("step5") != today_str:
            print(f"[step5] Attempting to send @ {_now_ist_str()}...")
            try:
                step5_text = "your step5 message"
                await safe_send(
                    chat_id=8757350577,          # your step5 chat id here
                    text=step5_text
                )
                record_step("Step-5", f"DM → step5 target | {step5_text[:40]} | Powerd by: Team Toxic")
                print(f"[step5] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step5] ❌ ERROR: {e}")
            last_sent["step5"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 6  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step6 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step6"] and last_sent.get("step6") != today_str:
            print(f"[step6] Attempting to send @ {_now_ist_str()}...")
            try:
                step6_text = "your step6 message"
                await safe_send(
                    chat_id=8757350577,          # your step6 chat id here
                    text=step6_text
                )
                record_step("Step-6", f"DM → step6 target | {step6_text[:40]} | Powerd by: Team Toxic")
                print(f"[step6] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step6] ❌ ERROR: {e}")
            last_sent["step6"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 7  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step7 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step7"] and last_sent.get("step7") != today_str:
            print(f"[step7] Attempting to send @ {_now_ist_str()}...")
            try:
                step7_text = "your step7 message"
                await safe_send(
                    chat_id=8757350577,          # your step7 chat id here
                    text=step7_text
                )
                record_step("Step-7", f"DM → step7 target | {step7_text[:40]} | Powerd by: Team Toxic")
                print(f"[step7] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step7] ❌ ERROR: {e}")
            last_sent["step7"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 8  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step8 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step8"] and last_sent.get("step8") != today_str:
            print(f"[step8] Attempting to send @ {_now_ist_str()}...")
            try:
                step8_text = "your step8 message"
                await safe_send(
                    chat_id=8757350577,          # your step8 chat id here
                    text=step8_text
                )
                record_step("Step-8", f"DM → step8 target | {step8_text[:40]} | Powerd by: Team Toxic")
                print(f"[step8] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step8] ❌ ERROR: {e}")
            last_sent["step8"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 9  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step9 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step9"] and last_sent.get("step9") != today_str:
            print(f"[step9] Attempting to send @ {_now_ist_str()}...")
            try:
                step9_text = "your step9 message"
                await safe_send(
                    chat_id=8757350577,          # your step9 chat id here
                    text=step9_text
                )
                record_step("Step-9", f"DM → step9 target | {step9_text[:40]} | Powerd by: Team Toxic")
                print(f"[step9] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step9] ❌ ERROR: {e}")
            last_sent["step9"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 10  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step10 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step10"] and last_sent.get("step10") != today_str:
            print(f"[step10] Attempting to send @ {_now_ist_str()}...")
            try:
                step10_text = "your step10 message"
                await safe_send(
                    chat_id=8757350577,          # your step10 chat id here
                    text=step10_text
                )
                record_step("Step-10", f"DM → step10 target | {step10_text[:40]} | Powerd by: Team Toxic")
                print(f"[step10] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step10] ❌ ERROR: {e}")
            last_sent["step10"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 11  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step11 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step11"] and last_sent.get("step11") != today_str:
            print(f"[step11] Attempting to send @ {_now_ist_str()}...")
            try:
                step11_text = "your step11 message"
                await safe_send(
                    chat_id=8757350577,          # your step11 chat id here
                    text=step11_text
                )
                record_step("Step-11", f"DM → step11 target | {step11_text[:40]} | Powerd by: Team Toxic")
                print(f"[step11] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step11] ❌ ERROR: {e}")
            last_sent["step11"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 12  (changeable via /step12)
        #  Type   : DM (personal chat)  — text changeable via /step12
        #  Target : your step12 chat id here
        #  Text   : STEP_TEXTS["step12"]  ← changeable via /step12
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step12"] and last_sent.get("step12") != today_str:
            print(f"[step12] Attempting to send @ {_now_ist_str()}...")
            try:
                await safe_send(
                    chat_id=8757350577,          # your step12 chat id here
                    text=STEP_TEXTS["step12"]
                )
                record_step("Step-12", f"DM → step12 target | {STEP_TEXTS['step12'][:40]} | Powerd by: Team Toxic")
                print(f"[step12] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step12] ❌ ERROR: {e}")
            last_sent["step12"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 13  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step13 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step13"] and last_sent.get("step13") != today_str:
            print(f"[step13] Attempting to send @ {_now_ist_str()}...")
            try:
                step13_text = "your step13 message"
                await safe_send(
                    chat_id=8757350577,          # your step13 chat id here
                    text=step13_text
                )
                record_step("Step-13", f"DM → step13 target | {step13_text[:40]} | Powerd by: Team Toxic")
                print(f"[step13] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step13] ❌ ERROR: {e}")
            last_sent["step13"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 14  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step14 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step14"] and last_sent.get("step14") != today_str:
            print(f"[step14] Attempting to send @ {_now_ist_str()}...")
            try:
                step14_text = "your step14 message"
                await safe_send(
                    chat_id=8757350577,          # your step14 chat id here
                    text=step14_text
                )
                record_step("Step-14", f"DM → step14 target | {step14_text[:40]} | Powerd by: Team Toxic")
                print(f"[step14] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step14] ❌ ERROR: {e}")
            last_sent["step14"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 15  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step15 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step15"] and last_sent.get("step15") != today_str:
            print(f"[step15] Attempting to send @ {_now_ist_str()}...")
            try:
                step15_text = "your step15 message"
                await safe_send(
                    chat_id=8757350577,          # your step15 chat id here
                    text=step15_text
                )
                record_step("Step-15", f"DM → step15 target | {step15_text[:40]} | Powerd by: Team Toxic")
                print(f"[step15] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step15] ❌ ERROR: {e}")
            last_sent["step15"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 16  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step16 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step16"] and last_sent.get("step16") != today_str:
            print(f"[step16] Attempting to send @ {_now_ist_str()}...")
            try:
                step16_text = "your step16 message"
                await safe_send(
                    chat_id=8757350577,          # your step16 chat id here
                    text=step16_text
                )
                record_step("Step-16", f"DM → step16 target | {step16_text[:40]} | Powerd by: Team Toxic")
                print(f"[step16] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step16] ❌ ERROR: {e}")
            last_sent["step16"] = today_str

        # #1st batch

        # ════════════════════════════════════════════════════════════
        # #2nd batch
        # ════════════════════════════════════════════════════════════
        # ════════════════════════════════════════════════════════════
        #  STEP 17  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step17 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step17"] and last_sent.get("step17") != today_str:
            print(f"[step17] Attempting to send @ {_now_ist_str()}...")
            try:
                step17_text = "your step17 message"
                await safe_send(
                    chat_id=8757350577,          # your step17 chat id here
                    text=step17_text
                )
                record_step("Step-17", f"DM → step17 target | {step17_text[:40]} | Powerd by: Team Toxic")
                print(f"[step17] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step17] ❌ ERROR: {e}")
            last_sent["step17"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 18  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step18 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step18"] and last_sent.get("step18") != today_str:
            print(f"[step18] Attempting to send @ {_now_ist_str()}...")
            try:
                step18_text = "your step18 message"
                await safe_send(
                    chat_id=8757350577,          # your step18 chat id here
                    text=step18_text
                )
                record_step("Step-18", f"DM → step18 target | {step18_text[:40]} | Powerd by: Team Toxic")
                print(f"[step18] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step18] ❌ ERROR: {e}")
            last_sent["step18"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 19  (changeable via /step19)
        #  Type   : DM (personal chat)  — text changeable via /step19
        #  Target : your step19 chat id here
        #  Text   : STEP_TEXTS["step19"]  ← changeable via /step19
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step19"] and last_sent.get("step19") != today_str:
            print(f"[step19] Attempting to send @ {_now_ist_str()}...")
            try:
                await safe_send(
                    chat_id=8757350577,          # your step19 chat id here
                    text=STEP_TEXTS["step19"]
                )
                record_step("Step-19", f"DM → step19 target | {STEP_TEXTS['step19'][:40]} | Powerd by: Team Toxic")
                print(f"[step19] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step19] ❌ ERROR: {e}")
            last_sent["step19"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 20  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step20 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step20"] and last_sent.get("step20") != today_str:
            print(f"[step20] Attempting to send @ {_now_ist_str()}...")
            try:
                step20_text = "your step20 message"
                await safe_send(
                    chat_id=8757350577,          # your step20 chat id here
                    text=step20_text
                )
                record_step("Step-20", f"DM → step20 target | {step20_text[:40]} | Powerd by: Team Toxic")
                print(f"[step20] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step20] ❌ ERROR: {e}")
            last_sent["step20"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 21  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step21 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step21"] and last_sent.get("step21") != today_str:
            print(f"[step21] Attempting to send @ {_now_ist_str()}...")
            try:
                step21_text = "your step21 message"
                await safe_send(
                    chat_id=8757350577,          # your step21 chat id here
                    text=step21_text
                )
                record_step("Step-21", f"DM → step21 target | {step21_text[:40]} | Powerd by: Team Toxic")
                print(f"[step21] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step21] ❌ ERROR: {e}")
            last_sent["step21"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 22  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step22 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step22"] and last_sent.get("step22") != today_str:
            print(f"[step22] Attempting to send @ {_now_ist_str()}...")
            try:
                step22_text = "your step22 message"
                await safe_send(
                    chat_id=8757350577,          # your step22 chat id here
                    text=step22_text
                )
                record_step("Step-22", f"DM → step22 target | {step22_text[:40]} | Powerd by: Team Toxic")
                print(f"[step22] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step22] ❌ ERROR: {e}")
            last_sent["step22"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 23  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step23 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step23"] and last_sent.get("step23") != today_str:
            print(f"[step23] Attempting to send @ {_now_ist_str()}...")
            try:
                step23_text = "your step23 message"
                await safe_send(
                    chat_id=8757350577,          # your step23 chat id here
                    text=step23_text
                )
                record_step("Step-23", f"DM → step23 target | {step23_text[:40]} | Powerd by: Team Toxic")
                print(f"[step23] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step23] ❌ ERROR: {e}")
            last_sent["step23"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 24  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step24 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step24"] and last_sent.get("step24") != today_str:
            print(f"[step24] Attempting to send @ {_now_ist_str()}...")
            try:
                step24_text = "your step24 message"
                await safe_send(
                    chat_id=8757350577,          # your step24 chat id here
                    text=step24_text
                )
                record_step("Step-24", f"DM → step24 target | {step24_text[:40]} | Powerd by: Team Toxic")
                print(f"[step24] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step24] ❌ ERROR: {e}")
            last_sent["step24"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 25  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step25 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step25"] and last_sent.get("step25") != today_str:
            print(f"[step25] Attempting to send @ {_now_ist_str()}...")
            try:
                step25_text = "your step25 message"
                await safe_send(
                    chat_id=8757350577,          # your step25 chat id here
                    text=step25_text
                )
                record_step("Step-25", f"DM → step25 target | {step25_text[:40]} | Powerd by: Team Toxic")
                print(f"[step25] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step25] ❌ ERROR: {e}")
            last_sent["step25"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 26  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step26 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step26"] and last_sent.get("step26") != today_str:
            print(f"[step26] Attempting to send @ {_now_ist_str()}...")
            try:
                step26_text = "your step26 message"
                await safe_send(
                    chat_id=8757350577,          # your step26 chat id here
                    text=step26_text
                )
                record_step("Step-26", f"DM → step26 target | {step26_text[:40]} | Powerd by: Team Toxic")
                print(f"[step26] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step26] ❌ ERROR: {e}")
            last_sent["step26"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 27  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step27 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step27"] and last_sent.get("step27") != today_str:
            print(f"[step27] Attempting to send @ {_now_ist_str()}...")
            try:
                step27_text = "your step27 message"
                await safe_send(
                    chat_id=8757350577,          # your step27 chat id here
                    text=step27_text
                )
                record_step("Step-27", f"DM → step27 target | {step27_text[:40]} | Powerd by: Team Toxic")
                print(f"[step27] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step27] ❌ ERROR: {e}")
            last_sent["step27"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 28  (changeable via /step28)
        #  Type   : DM (personal chat)  — text changeable via /step28
        #  Target : your step28 chat id here
        #  Text   : STEP_TEXTS["step28"]  ← changeable via /step28
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step28"] and last_sent.get("step28") != today_str:
            print(f"[step28] Attempting to send @ {_now_ist_str()}...")
            try:
                await safe_send(
                    chat_id=8757350577,          # your step28 chat id here
                    text=STEP_TEXTS["step28"]
                )
                record_step("Step-28", f"DM → step28 target | {STEP_TEXTS['step28'][:40]} | Powerd by: Team Toxic")
                print(f"[step28] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step28] ❌ ERROR: {e}")
            last_sent["step28"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 29  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step29 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step29"] and last_sent.get("step29") != today_str:
            print(f"[step29] Attempting to send @ {_now_ist_str()}...")
            try:
                step29_text = "your step29 message"
                await safe_send(
                    chat_id=8757350577,          # your step29 chat id here
                    text=step29_text
                )
                record_step("Step-29", f"DM → step29 target | {step29_text[:40]} | Powerd by: Team Toxic")
                print(f"[step29] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step29] ❌ ERROR: {e}")
            last_sent["step29"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 30  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step30 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step30"] and last_sent.get("step30") != today_str:
            print(f"[step30] Attempting to send @ {_now_ist_str()}...")
            try:
                step30_text = "your step30 message"
                await safe_send(
                    chat_id=8757350577,          # your step30 chat id here
                    text=step30_text
                )
                record_step("Step-30", f"DM → step30 target | {step30_text[:40]} | Powerd by: Team Toxic")
                print(f"[step30] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step30] ❌ ERROR: {e}")
            last_sent["step30"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 31  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step31 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step31"] and last_sent.get("step31") != today_str:
            print(f"[step31] Attempting to send @ {_now_ist_str()}...")
            try:
                step31_text = "your step31 message"
                await safe_send(
                    chat_id=8757350577,          # your step31 chat id here
                    text=step31_text
                )
                record_step("Step-31", f"DM → step31 target | {step31_text[:40]} | Powerd by: Team Toxic")
                print(f"[step31] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step31] ❌ ERROR: {e}")
            last_sent["step31"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 32  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step32 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step32"] and last_sent.get("step32") != today_str:
            print(f"[step32] Attempting to send @ {_now_ist_str()}...")
            try:
                step32_text = "your step32 message"
                await safe_send(
                    chat_id=8757350577,          # your step32 chat id here
                    text=step32_text
                )
                record_step("Step-32", f"DM → step32 target | {step32_text[:40]} | Powerd by: Team Toxic")
                print(f"[step32] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step32] ❌ ERROR: {e}")
            last_sent["step32"] = today_str

        # #2nd batch

        # ════════════════════════════════════════════════════════════
        # #3rd batch
        # ════════════════════════════════════════════════════════════
        # ════════════════════════════════════════════════════════════
        #  STEP 33  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step33 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step33"] and last_sent.get("step33") != today_str:
            print(f"[step33] Attempting to send @ {_now_ist_str()}...")
            try:
                step33_text = "your step33 message"
                await safe_send(
                    chat_id=8757350577,          # your step33 chat id here
                    text=step33_text
                )
                record_step("Step-33", f"DM → step33 target | {step33_text[:40]} | Powerd by: Team Toxic")
                print(f"[step33] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step33] ❌ ERROR: {e}")
            last_sent["step33"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 34  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step34 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step34"] and last_sent.get("step34") != today_str:
            print(f"[step34] Attempting to send @ {_now_ist_str()}...")
            try:
                step34_text = "your step34 message"
                await safe_send(
                    chat_id=8757350577,          # your step34 chat id here
                    text=step34_text
                )
                record_step("Step-34", f"DM → step34 target | {step34_text[:40]} | Powerd by: Team Toxic")
                print(f"[step34] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step34] ❌ ERROR: {e}")
            last_sent["step34"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 35  (changeable via /step35)
        #  Type   : DM (personal chat)  — text changeable via /step35
        #  Target : your step35 chat id here
        #  Text   : STEP_TEXTS["step35"]  ← changeable via /step35
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step35"] and last_sent.get("step35") != today_str:
            print(f"[step35] Attempting to send @ {_now_ist_str()}...")
            try:
                await safe_send(
                    chat_id=8757350577,          # your step35 chat id here
                    text=STEP_TEXTS["step35"]
                )
                record_step("Step-35", f"DM → step35 target | {STEP_TEXTS['step35'][:40]} | Powerd by: Team Toxic")
                print(f"[step35] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step35] ❌ ERROR: {e}")
            last_sent["step35"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 36  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step36 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step36"] and last_sent.get("step36") != today_str:
            print(f"[step36] Attempting to send @ {_now_ist_str()}...")
            try:
                step36_text = "your step36 message"
                await safe_send(
                    chat_id=8757350577,          # your step36 chat id here
                    text=step36_text
                )
                record_step("Step-36", f"DM → step36 target | {step36_text[:40]} | Powerd by: Team Toxic")
                print(f"[step36] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step36] ❌ ERROR: {e}")
            last_sent["step36"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 37  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step37 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step37"] and last_sent.get("step37") != today_str:
            print(f"[step37] Attempting to send @ {_now_ist_str()}...")
            try:
                step37_text = "your step37 message"
                await safe_send(
                    chat_id=8757350577,          # your step37 chat id here
                    text=step37_text
                )
                record_step("Step-37", f"DM → step37 target | {step37_text[:40]} | Powerd by: Team Toxic")
                print(f"[step37] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step37] ❌ ERROR: {e}")
            last_sent["step37"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 38  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step38 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step38"] and last_sent.get("step38") != today_str:
            print(f"[step38] Attempting to send @ {_now_ist_str()}...")
            try:
                step38_text = "your step38 message"
                await safe_send(
                    chat_id=8757350577,          # your step38 chat id here
                    text=step38_text
                )
                record_step("Step-38", f"DM → step38 target | {step38_text[:40]} | Powerd by: Team Toxic")
                print(f"[step38] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step38] ❌ ERROR: {e}")
            last_sent["step38"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 39  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step39 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step39"] and last_sent.get("step39") != today_str:
            print(f"[step39] Attempting to send @ {_now_ist_str()}...")
            try:
                step39_text = "your step39 message"
                await safe_send(
                    chat_id=8757350577,          # your step39 chat id here
                    text=step39_text
                )
                record_step("Step-39", f"DM → step39 target | {step39_text[:40]} | Powerd by: Team Toxic")
                print(f"[step39] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step39] ❌ ERROR: {e}")
            last_sent["step39"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 40  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step40 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step40"] and last_sent.get("step40") != today_str:
            print(f"[step40] Attempting to send @ {_now_ist_str()}...")
            try:
                step40_text = "your step40 message"
                await safe_send(
                    chat_id=8757350577,          # your step40 chat id here
                    text=step40_text
                )
                record_step("Step-40", f"DM → step40 target | {step40_text[:40]} | Powerd by: Team Toxic")
                print(f"[step40] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step40] ❌ ERROR: {e}")
            last_sent["step40"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 41  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step41 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step41"] and last_sent.get("step41") != today_str:
            print(f"[step41] Attempting to send @ {_now_ist_str()}...")
            try:
                step41_text = "your step41 message"
                await safe_send(
                    chat_id=8757350577,          # your step41 chat id here
                    text=step41_text
                )
                record_step("Step-41", f"DM → step41 target | {step41_text[:40]} | Powerd by: Team Toxic")
                print(f"[step41] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step41] ❌ ERROR: {e}")
            last_sent["step41"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 42  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step42 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step42"] and last_sent.get("step42") != today_str:
            print(f"[step42] Attempting to send @ {_now_ist_str()}...")
            try:
                step42_text = "your step42 message"
                await safe_send(
                    chat_id=8757350577,          # your step42 chat id here
                    text=step42_text
                )
                record_step("Step-42", f"DM → step42 target | {step42_text[:40]} | Powerd by: Team Toxic")
                print(f"[step42] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step42] ❌ ERROR: {e}")
            last_sent["step42"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 43  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step43 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step43"] and last_sent.get("step43") != today_str:
            print(f"[step43] Attempting to send @ {_now_ist_str()}...")
            try:
                step43_text = "your step43 message"
                await safe_send(
                    chat_id=8757350577,          # your step43 chat id here
                    text=step43_text
                )
                record_step("Step-43", f"DM → step43 target | {step43_text[:40]} | Powerd by: Team Toxic")
                print(f"[step43] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step43] ❌ ERROR: {e}")
            last_sent["step43"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 44  (changeable via /step44)
        #  Type   : DM (personal chat)  — text changeable via /step44
        #  Target : your step44 chat id here
        #  Text   : STEP_TEXTS["step44"]  ← changeable via /step44
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step44"] and last_sent.get("step44") != today_str:
            print(f"[step44] Attempting to send @ {_now_ist_str()}...")
            try:
                await safe_send(
                    chat_id=8757350577,          # your step44 chat id here
                    text=STEP_TEXTS["step44"]
                )
                record_step("Step-44", f"DM → step44 target | {STEP_TEXTS['step44'][:40]} | Powerd by: Team Toxic")
                print(f"[step44] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step44] ❌ ERROR: {e}")
            last_sent["step44"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 45  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step45 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step45"] and last_sent.get("step45") != today_str:
            print(f"[step45] Attempting to send @ {_now_ist_str()}...")
            try:
                step45_text = "your step45 message"
                await safe_send(
                    chat_id=8757350577,          # your step45 chat id here
                    text=step45_text
                )
                record_step("Step-45", f"DM → step45 target | {step45_text[:40]} | Powerd by: Team Toxic")
                print(f"[step45] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step45] ❌ ERROR: {e}")
            last_sent["step45"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 46  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step46 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step46"] and last_sent.get("step46") != today_str:
            print(f"[step46] Attempting to send @ {_now_ist_str()}...")
            try:
                step46_text = "your step46 message"
                await safe_send(
                    chat_id=8757350577,          # your step46 chat id here
                    text=step46_text
                )
                record_step("Step-46", f"DM → step46 target | {step46_text[:40]} | Powerd by: Team Toxic")
                print(f"[step46] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step46] ❌ ERROR: {e}")
            last_sent["step46"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 47  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step47 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step47"] and last_sent.get("step47") != today_str:
            print(f"[step47] Attempting to send @ {_now_ist_str()}...")
            try:
                step47_text = "your step47 message"
                await safe_send(
                    chat_id=8757350577,          # your step47 chat id here
                    text=step47_text
                )
                record_step("Step-47", f"DM → step47 target | {step47_text[:40]} | Powerd by: Team Toxic")
                print(f"[step47] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step47] ❌ ERROR: {e}")
            last_sent["step47"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 48  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step48 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step48"] and last_sent.get("step48") != today_str:
            print(f"[step48] Attempting to send @ {_now_ist_str()}...")
            try:
                step48_text = "your step48 message"
                await safe_send(
                    chat_id=8757350577,          # your step48 chat id here
                    text=step48_text
                )
                record_step("Step-48", f"DM → step48 target | {step48_text[:40]} | Powerd by: Team Toxic")
                print(f"[step48] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step48] ❌ ERROR: {e}")
            last_sent["step48"] = today_str

        # #3rd batch

        # ════════════════════════════════════════════════════════════
        # #4th batch
        # ════════════════════════════════════════════════════════════
        # ════════════════════════════════════════════════════════════
        #  STEP 49  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step49 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step49"] and last_sent.get("step49") != today_str:
            print(f"[step49] Attempting to send @ {_now_ist_str()}...")
            try:
                step49_text = "your step49 message"
                await safe_send(
                    chat_id=8757350577,          # your step49 chat id here
                    text=step49_text
                )
                record_step("Step-49", f"DM → step49 target | {step49_text[:40]} | Powerd by: Team Toxic")
                print(f"[step49] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step49] ❌ ERROR: {e}")
            last_sent["step49"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 50  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step50 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step50"] and last_sent.get("step50") != today_str:
            print(f"[step50] Attempting to send @ {_now_ist_str()}...")
            try:
                step50_text = "your step50 message"
                await safe_send(
                    chat_id=8757350577,          # your step50 chat id here
                    text=step50_text
                )
                record_step("Step-50", f"DM → step50 target | {step50_text[:40]} | Powerd by: Team Toxic")
                print(f"[step50] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step50] ❌ ERROR: {e}")
            last_sent["step50"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 51  (changeable via /step51)
        #  Type   : DM (personal chat)  — text changeable via /step51
        #  Target : your step51 chat id here
        #  Text   : STEP_TEXTS["step51"]  ← changeable via /step51
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step51"] and last_sent.get("step51") != today_str:
            print(f"[step51] Attempting to send @ {_now_ist_str()}...")
            try:
                await safe_send(
                    chat_id=8757350577,          # your step51 chat id here
                    text=STEP_TEXTS["step51"]
                )
                record_step("Step-51", f"DM → step51 target | {STEP_TEXTS['step51'][:40]} | Powerd by: Team Toxic")
                print(f"[step51] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step51] ❌ ERROR: {e}")
            last_sent["step51"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 52  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step52 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step52"] and last_sent.get("step52") != today_str:
            print(f"[step52] Attempting to send @ {_now_ist_str()}...")
            try:
                step52_text = "your step52 message"
                await safe_send(
                    chat_id=8757350577,          # your step52 chat id here
                    text=step52_text
                )
                record_step("Step-52", f"DM → step52 target | {step52_text[:40]} | Powerd by: Team Toxic")
                print(f"[step52] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step52] ❌ ERROR: {e}")
            last_sent["step52"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 53  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step53 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step53"] and last_sent.get("step53") != today_str:
            print(f"[step53] Attempting to send @ {_now_ist_str()}...")
            try:
                step53_text = "your step53 message"
                await safe_send(
                    chat_id=8757350577,          # your step53 chat id here
                    text=step53_text
                )
                record_step("Step-53", f"DM → step53 target | {step53_text[:40]} | Powerd by: Team Toxic")
                print(f"[step53] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step53] ❌ ERROR: {e}")
            last_sent["step53"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 54  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step54 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step54"] and last_sent.get("step54") != today_str:
            print(f"[step54] Attempting to send @ {_now_ist_str()}...")
            try:
                step54_text = "your step54 message"
                await safe_send(
                    chat_id=8757350577,          # your step54 chat id here
                    text=step54_text
                )
                record_step("Step-54", f"DM → step54 target | {step54_text[:40]} | Powerd by: Team Toxic")
                print(f"[step54] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step54] ❌ ERROR: {e}")
            last_sent["step54"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 55  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step55 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step55"] and last_sent.get("step55") != today_str:
            print(f"[step55] Attempting to send @ {_now_ist_str()}...")
            try:
                step55_text = "your step55 message"
                await safe_send(
                    chat_id=8757350577,          # your step55 chat id here
                    text=step55_text
                )
                record_step("Step-55", f"DM → step55 target | {step55_text[:40]} | Powerd by: Team Toxic")
                print(f"[step55] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step55] ❌ ERROR: {e}")
            last_sent["step55"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 56  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step56 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step56"] and last_sent.get("step56") != today_str:
            print(f"[step56] Attempting to send @ {_now_ist_str()}...")
            try:
                step56_text = "your step56 message"
                await safe_send(
                    chat_id=8757350577,          # your step56 chat id here
                    text=step56_text
                )
                record_step("Step-56", f"DM → step56 target | {step56_text[:40]} | Powerd by: Team Toxic")
                print(f"[step56] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step56] ❌ ERROR: {e}")
            last_sent["step56"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 57  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step57 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step57"] and last_sent.get("step57") != today_str:
            print(f"[step57] Attempting to send @ {_now_ist_str()}...")
            try:
                step57_text = "your step57 message"
                await safe_send(
                    chat_id=8757350577,          # your step57 chat id here
                    text=step57_text
                )
                record_step("Step-57", f"DM → step57 target | {step57_text[:40]} | Powerd by: Team Toxic")
                print(f"[step57] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step57] ❌ ERROR: {e}")
            last_sent["step57"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 58  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step58 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step58"] and last_sent.get("step58") != today_str:
            print(f"[step58] Attempting to send @ {_now_ist_str()}...")
            try:
                step58_text = "your step58 message"
                await safe_send(
                    chat_id=8757350577,          # your step58 chat id here
                    text=step58_text
                )
                record_step("Step-58", f"DM → step58 target | {step58_text[:40]} | Powerd by: Team Toxic")
                print(f"[step58] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step58] ❌ ERROR: {e}")
            last_sent["step58"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 59  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step59 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step59"] and last_sent.get("step59") != today_str:
            print(f"[step59] Attempting to send @ {_now_ist_str()}...")
            try:
                step59_text = "your step59 message"
                await safe_send(
                    chat_id=8757350577,          # your step59 chat id here
                    text=step59_text
                )
                record_step("Step-59", f"DM → step59 target | {step59_text[:40]} | Powerd by: Team Toxic")
                print(f"[step59] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step59] ❌ ERROR: {e}")
            last_sent["step59"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 60  (changeable via /step60)
        #  Type   : DM (personal chat)  — text changeable via /step60
        #  Target : your step60 chat id here
        #  Text   : STEP_TEXTS["step60"]  ← changeable via /step60
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step60"] and last_sent.get("step60") != today_str:
            print(f"[step60] Attempting to send @ {_now_ist_str()}...")
            try:
                await safe_send(
                    chat_id=8757350577,          # your step60 chat id here
                    text=STEP_TEXTS["step60"]
                )
                record_step("Step-60", f"DM → step60 target | {STEP_TEXTS['step60'][:40]} | Powerd by: Team Toxic")
                print(f"[step60] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step60] ❌ ERROR: {e}")
            last_sent["step60"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 61  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step61 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step61"] and last_sent.get("step61") != today_str:
            print(f"[step61] Attempting to send @ {_now_ist_str()}...")
            try:
                step61_text = "your step61 message"
                await safe_send(
                    chat_id=8757350577,          # your step61 chat id here
                    text=step61_text
                )
                record_step("Step-61", f"DM → step61 target | {step61_text[:40]} | Powerd by: Team Toxic")
                print(f"[step61] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step61] ❌ ERROR: {e}")
            last_sent["step61"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 62  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step62 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step62"] and last_sent.get("step62") != today_str:
            print(f"[step62] Attempting to send @ {_now_ist_str()}...")
            try:
                step62_text = "your step62 message"
                await safe_send(
                    chat_id=8757350577,          # your step62 chat id here
                    text=step62_text
                )
                record_step("Step-62", f"DM → step62 target | {step62_text[:40]} | Powerd by: Team Toxic")
                print(f"[step62] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step62] ❌ ERROR: {e}")
            last_sent["step62"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 63  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step63 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step63"] and last_sent.get("step63") != today_str:
            print(f"[step63] Attempting to send @ {_now_ist_str()}...")
            try:
                step63_text = "your step63 message"
                await safe_send(
                    chat_id=8757350577,          # your step63 chat id here
                    text=step63_text
                )
                record_step("Step-63", f"DM → step63 target | {step63_text[:40]} | Powerd by: Team Toxic")
                print(f"[step63] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step63] ❌ ERROR: {e}")
            last_sent["step63"] = today_str
        # ════════════════════════════════════════════════════════════
        #  STEP 64  (hardcoded)
        #  Type   : DM (personal chat)
        #  Target : your step64 chat id here
        # ════════════════════════════════════════════════════════════
        if now_str == STEP_TIMES["step64"] and last_sent.get("step64") != today_str:
            print(f"[step64] Attempting to send @ {_now_ist_str()}...")
            try:
                step64_text = "your step64 message"
                await safe_send(
                    chat_id=8757350577,          # your step64 chat id here
                    text=step64_text
                )
                record_step("Step-64", f"DM → step64 target | {step64_text[:40]} | Powerd by: Team Toxic")
                print(f"[step64] ✅ sent @ {_now_ist_str()}")
            except Exception as e:
                print(f"[step64] ❌ ERROR: {e}")
            last_sent["step64"] = today_str

        # #4th batch

        # ════════════════════════════════════════════════════════════
        # #5th batch

        await asyncio.sleep(0.5)


# ════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ════════════════════════════════════════════════════════════════════
async def main():
    print("=" * 60)
    print("MAIN FUNCTION ENTERED ✅")
    print("=" * 60)

    print("Starting BotFather bot...")
    try:
        await asyncio.wait_for(bot.start(), timeout=60)
        print("✅ BotFather bot started")
    except asyncio.TimeoutError:
        print("❌ BOT START TIMEOUT (60s) — BOT_TOKEN invalid ya network issue")
        raise
    except Exception as e:
        print(f"❌ BOT START ERROR: {type(e).__name__}: {e}")
        raise

    print("Starting Userbot...")
    try:
        await asyncio.wait_for(userbot.start(), timeout=60)
        print("✅ Userbot started")
    except asyncio.TimeoutError:
        print("❌ USERBOT START TIMEOUT (60s) — STRING_SESSION expired ya invalid")
        raise
    except Exception as e:
        err_str = str(e)
        if "unpack requires a buffer" in err_str or "struct.error" in err_str:
            print("❌ USERBOT START ERROR: STRING_SESSION CORRUPT/INVALID ⚠️")
            print("❌ Fix: Pyrogram se naya STRING_SESSION generate karo aur Render env var update karo")
            print("❌ Generate karne ka code:")
            print('   from pyrogram import Client')
            print('   async with Client("session", api_id=API_ID, api_hash=API_HASH) as app:')
            print('       print(await app.export_session_string())')
        else:
            print(f"❌ USERBOT START ERROR: {type(e).__name__}: {e}")
        raise

    print("Warming up peer cache...")
    try:
        await warmup_peers()
        print("✅ Peer cache warm-up done")
    except Exception as e:
        print(f"⚠️ Peer warm-up had issues (non-fatal, will self-heal on send): {e}")

    asyncio.create_task(peer_warmup_loop())
    asyncio.create_task(run_scheduler())
    print("⏰ Scheduler running (Asia/Kolkata IST)")

    print("=" * 60)
    print("🚀 ALL SYSTEMS LIVE — Fury Automation is running!")
    print("=" * 60)

    await idle()

# ─── Flask keep-alive server for Render ───────────────────────────────────────
flask_app = Flask(__name__)

@flask_app.route('/')
def index():
    return 'Bot is running!'

def run_flask():
    port = int(os.environ.get("PORT", 8000))
    flask_app.run(host="0.0.0.0", port=port)

# Start Flask in background thread so Render detects open port
threading.Thread(target=run_flask, daemon=True).start()
# ─────────────────────────────────────────


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

