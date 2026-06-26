from os import environ

class Config:
    API_ID = int(environ.get("API_ID", "0"))
    API_HASH = environ.get("API_HASH", "")
    BOT_TOKEN = environ.get("BOT_TOKEN", "")
    BOT_SESSION = environ.get("BOT_SESSION", "DoneForwardBot")
    DATABASE_URI = environ.get("DATABASE_URI", "")
    DATABASE_NAME = environ.get("DATABASE_NAME", "doneforward")
    BOT_OWNER_ID = [int(x) for x in environ.get("BOT_OWNER_ID", "0").split()]
    # Force subscribe channels (Telegram channel IDs or usernames, comma separated)
    FSUB_CHANNELS = [x.strip() for x in environ.get("FSUB_CHANNELS", "").split(",") if x.strip()]

class temp:
    BANNED_USERS = []
    forwardings = 0
