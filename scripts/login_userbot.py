#!/usr/bin/env python3
"""Login userbot en 2 pasos controlados (Telethon).
Paso 1: python login_userbot.py send <phone>  → envía código, guarda phone_code_hash
Paso 2: python login_userbot.py sign <phone> <code> → firma y guarda sesión
"""
import sys, os, json, asyncio

PHONE = sys.argv[2] if len(sys.argv) > 2 else ""
MODE = sys.argv[1] if len(sys.argv) > 1 else ""
CODE = sys.argv[3] if len(sys.argv) > 3 else None

API_ID = int(os.environ.get("TG_API_ID", "YOUR_API_ID"))
API_HASH = os.environ.get("TG_API_HASH", "YOUR_API_HASH")
SESSION = os.path.expanduser("~/.fabella/data/telegram_userbot.session")
STATE_PATH = os.path.expanduser("~/.fabella/data/tg_login_state.json")
os.makedirs(os.path.dirname(SESSION), exist_ok=True)

from telethon import TelegramClient

client = TelegramClient(SESSION, API_ID, API_HASH)

async def main():
    await client.connect()
    try:
        if MODE == "send":
            sent = await client.send_code_request(PHONE)
            json.dump({"phone": PHONE, "phone_code_hash": sent.phone_code_hash}, open(STATE_PATH, "w"))
            print(f"📲 CODIGO ENVIADO a {PHONE} — pásamelo para el paso 2 (sign)")
        elif MODE == "sign":
            state = json.load(open(STATE_PATH))
            await client.sign_in(phone=state["phone"], code=CODE, phone_code_hash=state["phone_code_hash"])
            me = await client.get_me()
            print(f"✅ SESION OK: {me.first_name} (id {me.id}) — guardada en {SESSION}")
        else:
            print("uso: login_userbot.py send|sign <phone> [code]")
    finally:
        await client.disconnect()

asyncio.run(main())
