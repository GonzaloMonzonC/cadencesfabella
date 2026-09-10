#!/usr/bin/env python3
"""Two-step userbot login (Telethon).

Step 1: login_userbot.py send <phone>        -> sends the login code, stores phone_code_hash
Step 2: login_userbot.py sign <phone> <code> -> signs in and saves the session file
"""
import sys, os, json, asyncio


def _load_dotenv(path=".env"):
    """Minimal .env loader (KEY=VALUE lines). No dependencies."""
    if not os.path.isfile(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        os.environ.setdefault(key.strip(), val.strip())


_load_dotenv()

PHONE = sys.argv[2] if len(sys.argv) > 2 else ""
MODE = sys.argv[1] if len(sys.argv) > 1 else ""
CODE = sys.argv[3] if len(sys.argv) > 3 else None

_api_id = os.environ.get("TG_API_ID", "")
API_ID = int(_api_id) if _api_id.isdigit() else 0
API_HASH = os.environ.get("TG_API_HASH", "")
if not API_ID or not API_HASH:
    print("ERROR: set TG_API_ID and TG_API_HASH — create your own app at https://my.telegram.org")
    sys.exit(1)

SESSION = os.path.expanduser(os.environ.get("TG_SESSION", "~/.fabella/fabella.session"))
STATE_PATH = os.path.expanduser(os.environ.get("TG_LOGIN_STATE", "~/.fabella/tg_login_state.json"))
os.makedirs(os.path.dirname(SESSION), exist_ok=True)

from telethon import TelegramClient

client = TelegramClient(SESSION, API_ID, API_HASH)

async def main():
    await client.connect()
    try:
        if MODE == "send":
            sent = await client.send_code_request(PHONE)
            json.dump({"phone": PHONE, "phone_code_hash": sent.phone_code_hash}, open(STATE_PATH, "w"))
            print(f"📲 Code sent to {PHONE} — now run: sign <phone> <code>")
        elif MODE == "sign":
            state = json.load(open(STATE_PATH))
            await client.sign_in(phone=state["phone"], code=CODE, phone_code_hash=state["phone_code_hash"])
            me = await client.get_me()
            print(f"✅ Session OK: {me.first_name} (id {me.id}) — saved to {SESSION}")
        else:
            print("usage: login_userbot.py send|sign <phone> [code]")
    finally:
        await client.disconnect()

asyncio.run(main())
