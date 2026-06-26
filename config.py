from os import environ

class Config:
    API_ID = int(environ.get("API_ID", "38498066"))
    API_HASH = environ.get("API_HASH", "c9696114751feacdeb1b4487f5839a1a")
    BOT_TOKEN = environ.get("BOT_TOKEN", "")
    BOT_SESSION = environ.get("BOT_SESSION", "DoneForwardBot")
    DATABASE_URI = environ.get("DATABASE_URI", "mongodb+srv://devms786178_db_user:cEtMdLjmHF5EM2Pf@cluster0.xbqyvnn.mongodb.net/?appName=Cluster0")
    DATABASE_NAME = environ.get("DATABASE_NAME", "doneforward")
    BOT_OWNER_ID = [int(x) for x in environ.get("BOT_OWNER_ID", "8909902924").split()]
    # Force subscribe channels (Telegram channel IDs or usernames, comma separated)
    FSUB_CHANNELS = [x.strip() for x in environ.get("FSUB_CHANNELS", "-1003330631655,-1003910364346,-1004361013010").split(",") if x.strip()]

class temp:
    BANNED_USERS = []
    forwardings = 0
