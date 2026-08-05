#!/usr/bin/env python3
"""
CadencesFaBela — Userbot MTProto → Bot API local + Interfaz web.

Telegram ha monetizado el Bot API cloud (BotFather vende "peticiones" sin avisar).
CadencesFaBela usa la CUENTA PERSONAL (Telethon/MTProto) como transporte:
  - El gateway de Hermes apunta su base_url a http://localhost:8086 y habla el
    MISMO protocolo HTTP del Bot API (getUpdates/sendMessage/...) — el bridge
    lo traduce a MTProto. Cero BotFather, cero Stars, cero api.telegram.org.
  - La interfaz web (http://localhost:8087) permite chatear desde cualquier
    navegador/teléfono: GET / → chat, GET /api/history → hilo, POST /api/send.

Chat de trabajo por defecto: SAVED MESSAGES ("Mensajes guardados") de tu cuenta.
Configurable con TG_ALLOWED_CHATS (ids/usernames separados por coma).

Env:
  TG_API_ID / TG_API_HASH   — de my.telegram.org (API development tools)
  TG_SESSION                — ruta de sesión (default ~/.fabella/data/telegram_userbot.session)
  TG_BRIDGE_PORT            — puerto Bot API local (default 8086)
  TG_WEB_PORT               — puerto interfaz web (default 8087)
  TG_ALLOWED_CHATS          — chats extra permitidos (vacío = solo Saved Messages)
"""
import asyncio
import json
import os
import threading
import time
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from telethon import TelegramClient, events

API_ID = int(os.environ.get("TG_API_ID", "YOUR_API_ID") or "YOUR_API_ID")
API_HASH = os.environ.get("TG_API_HASH", "YOUR_API_HASH")
SESSION = os.environ.get(
    "TG_SESSION",
    os.path.expanduser("~/.fabella/data/telegram_userbot.session"),
)
BRIDGE_PORT = int(os.environ.get("TG_BRIDGE_PORT", "8086"))
WEB_PORT = int(os.environ.get("TG_WEB_PORT", "8087"))
# Chats permitidos: Saved Messages (siempre) + el chat de your bot (id YOUR_CHAT_ID,
# el antiguo bot de BotFather — el userbot responde ahí como si fuera el bot)
# + extras vía TG_ALLOWED_CHATS (usernames o ids separados por coma)
_BOT_CHAT = os.environ.get("TG_BOT_CHAT_ID", "YOUR_CHAT_ID")
ALLOWED_CHATS = [_BOT_CHAT] + [c.strip().lower() for c in os.environ.get("TG_ALLOWED_CHATS", "").split(",") if c.strip()]

if not API_ID or not API_HASH:
    print("ERROR: TG_API_ID y TG_API_HASH son obligatorios (my.telegram.org → API development tools)")
    sys.exit(1)

client = TelegramClient(SESSION, API_ID, API_HASH)
loop = None

# ── Token de la interfaz web (se genera la primera vez) ──────────────────────
TOKEN_PATH = os.path.expanduser("~/.fabella/data/fabella_token.txt")
WEB_TOKEN = os.environ.get("TG_WEB_TOKEN", "")
if not WEB_TOKEN:
    try:
        if os.path.exists(TOKEN_PATH):
            WEB_TOKEN = open(TOKEN_PATH).read().strip()
        else:
            import secrets
            WEB_TOKEN = secrets.token_urlsafe(18)
            os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
            open(TOKEN_PATH, "w").write(WEB_TOKEN)
            print(f"[fabella] 🔑 Token web generado: {WEB_TOKEN} (guardado en {TOKEN_PATH})")
    except Exception as e:
        print(f"[fabella] warn: token web no disponible ({e}) — /api/* sin auth")

# ── Cola de updates (long polling compatible con PTB) ─────────────────────────
_updates = []
_updates_lock = threading.Lock()
_next_update_id = 1
_me_id = None

def _push_update(update_dict):
    global _next_update_id
    with _updates_lock:
        update_dict["update_id"] = _next_update_id
        _next_update_id += 1
        _updates.append(update_dict)

def _pop_updates(offset):
    global _updates
    with _updates_lock:
        if offset:
            _updates[:] = [u for u in _updates if u["update_id"] > offset]
        out, _updates = _updates, []
    return out

# ── Traducción MTProto → update PTB ───────────────────────────────────────────
def _chat_dict(chat):
    cid = chat.id
    title = getattr(chat, "title", None)
    if title:
        return {"id": cid, "type": "group", "title": title, "username": getattr(chat, "username", None) or ""}
    first = getattr(chat, "first_name", None) or ""
    last = getattr(chat, "last_name", None) or ""
    return {
        "id": cid, "type": "private",
        "first_name": first, "last_name": last,
        "username": getattr(chat, "username", None) or "",
        "title": (first + (" " + last if last else "")).strip(),
    }

def _from_dict(u):
    return {
        "id": u.id, "is_bot": False,
        "first_name": getattr(u, "first_name", None) or "",
        "last_name": getattr(u, "last_name", None) or "",
        "username": getattr(u, "username", None) or "",
        "language_code": "es",
    }

def _msg_to_update(msg, chat):
    return {
        "message": {
            "message_id": msg.id,
            "date": int(msg.date.timestamp()) if msg.date else int(time.time()),
            "chat": _chat_dict(chat),
            "from": _from_dict(msg.sender) if msg.sender else {"id": 0, "is_bot": False, "first_name": "?"},
            "text": msg.message or "",
        }
    }

async def _is_allowed(chat):
    if chat.id == _me_id:
        return True
    if not ALLOWED_CHATS:
        return False
    name = (chat.username or "").lower() or str(chat.id)
    return name in ALLOWED_CHATS

@client.on(events.NewMessage)
async def on_new(event):
    msg = event.message
    try:
        chat = await event.get_chat()
        if not await _is_allowed(chat):
            print(f"[fabella] ignorado chat {chat.id} (no permitido)")
            return
        print(f"[fabella] ← msg {msg.id} de {chat.id}: {str(msg.message or '')[:60]}")
        _push_update(_msg_to_update(msg, chat))
    except Exception as e:
        print(f"[fabella] error on_new: {e}")

# ── Helpers async para la web ─────────────────────────────────────────────────
def run_async(coro, timeout=30):
    return asyncio.run_coroutine_threadsafe(coro, loop).result(timeout=timeout)

def _history(chat_id, limit=50):
    async def _h():
        msgs = await client.get_messages(chat_id, limit=limit)
        out = []
        for m in reversed(msgs):
            out.append({
                "id": m.id,
                "date": m.date.strftime("%d/%m %H:%M") if m.date else "",
                "out": bool(m.out),
                "text": m.message or "[media]",
            })
        return out
    try:
        return run_async(_h())
    except Exception as e:
        return {"error": str(e)}

def _send(chat_id, text):
    async def _s():
        return await client.send_message(chat_id, str(text))
    try:
        sent = run_async(_s())
        return {"ok": True, "message_id": sent.id}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ── Interfaz web CadencesFaBela ───────────────────────────────────────────────
WEB_HTML = """<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CadencesFaBela</title>
<style>
:root{--bg:#0e1116;--card:#161b22;--bord:#2a3140;--txt:#e6e9ef;--dim:#8b93a5;--acc:#4f8cff;--mine:#1f6feb;--theirs:#21262e}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--txt);font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;height:100vh;display:flex;flex-direction:column}
header{padding:12px 18px;border-bottom:1px solid var(--bord);display:flex;align-items:center;gap:10px;background:var(--card)}
header .logo{width:30px;height:30px;border-radius:8px;background:linear-gradient(135deg,#4f8cff,#7c5cff);display:flex;align-items:center;justify-content:center;font-weight:700;color:#fff}
header h1{font-size:16px;font-weight:600}
header .sub{color:var(--dim);font-size:12px}
#chat{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:8px}
.msg{max-width:72%;padding:9px 13px;border-radius:14px;font-size:14px;line-height:1.45;white-space:pre-wrap;word-break:break-word}
.msg.mine{background:var(--mine);align-self:flex-end;border-bottom-right-radius:4px}
.msg.theirs{background:var(--theirs);align-self:flex-start;border-bottom-left-radius:4px}
.msg .t{display:block;font-size:10px;color:var(--dim);margin-top:4px}
#bar{display:flex;gap:8px;padding:12px;border-top:1px solid var(--bord);background:var(--card)}
#inp{flex:1;background:var(--bg);border:1px solid var(--bord);border-radius:10px;color:var(--txt);padding:10px 14px;font-size:14px;outline:none}
#inp:focus{border-color:var(--acc)}
#btn{background:var(--acc);border:none;border-radius:10px;color:#fff;padding:10px 20px;font-size:14px;font-weight:600;cursor:pointer}
#btn:hover{opacity:.9}
#status{color:var(--dim);font-size:12px;padding:0 18px 6px}
</style></head><body>
<header><div class="logo">F</div><div><h1>CadencesFaBela</h1><div class="sub">consola personal · MTProto directo</div></div></header>
<div id="status">conectando…</div>
<div id="chat"></div>
<div id="bar"><input id="inp" placeholder="Escribe a tu consola…" autocomplete="off"><button id="btn">Enviar</button></div>
<script>
const chat=document.getElementById('chat'),inp=document.getElementById('inp'),st=document.getElementById('status');
let last=0;
let tok=localStorage.getItem('fabella_token');
if(!tok){tok=prompt('Token de CadencesFaBela:');if(tok)localStorage.setItem('fabella_token',tok);}
function hdr(){return tok?{'X-Fabella-Token':tok}:{};}
function add(m){const d=document.createElement('div');d.className='msg '+(m.out?'mine':'theirs');
const t=document.createElement('span');t.className='t';t.textContent=m.date;
d.textContent=m.text;d.appendChild(t);chat.appendChild(d);chat.scrollTop=chat.scrollHeight;}
async function poll(){try{const r=await fetch('/api/history?after='+last,{headers:hdr()});
if(r.status===401){st.textContent='token incorrecto — recarga y pon el token';return;}
const j=await r.json();
if(j.ok){st.textContent='conectado · '+j.chat;for(const m of j.messages||[]){if(m.id>last){add(m);last=m.id;}}}
else st.textContent='error: '+(j.error||'?');}catch(e){st.textContent='sin conexión con el bridge';}
setTimeout(poll,2000);}
async function send(){const t=inp.value.trim();if(!t)return;inp.value='';
const r=await fetch('/api/send',{method:'POST',headers:{'Content-Type':'application/json',...hdr()},body:JSON.stringify({text:t})});
const j=await r.json();if(!j.ok)st.textContent='error al enviar: '+(j.error||'?');}
inp.addEventListener('keydown',e=>{if(e.key==='Enter')send();});
document.getElementById('btn').addEventListener('click',send);
poll();
</script></body></html>"""

# ── Servidores HTTP ───────────────────────────────────────────────────────────
def _ok(result=None):
    return json.dumps({"ok": True, "result": result}, ensure_ascii=False)

def _err(desc, code=400):
    return json.dumps({"ok": False, "error_code": code, "description": desc}, ensure_ascii=False)

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _read_body(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        return self.rfile.read(n).decode("utf-8", "replace") if n else ""

    def _respond(self, code, body, ctype="application/json"):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _check_web_auth(self):
        """/api/* requiere X-Fabella-Token (si WEB_TOKEN está definido)."""
        if not WEB_TOKEN:
            return True
        return self.headers.get("X-Fabella-Token") == WEB_TOKEN

    def _method(self):
        parts = self.path.split("?")[0].split("/")
        if len(parts) >= 3 and parts[1].startswith("bot"):
            return parts[2]
        return None

    def do_GET(self):
        p = self.path.split("?")[0]
        if p == "/" or p == "/index.html":
            self._respond(200, WEB_HTML, "text/html; charset=utf-8")
            return
        if p == "/api/history":
            if not self._check_web_auth():
                self._respond(401, _err("token requerido (X-Fabella-Token)", 401))
                return
            from urllib.parse import parse_qs
            qs = parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}
            after = int(qs.get("after", ["0"])[0] or 0)
            h = _history("me", 60)
            if isinstance(h, dict) and "error" in h:
                self._respond(200, json.dumps({"ok": False, "error": h["error"]}))
                return
            self._respond(200, json.dumps({"ok": True, "chat": "Mensajes guardados", "messages": h}, ensure_ascii=False))
            return
        m = self._method()
        if not m:
            self._respond(404, _err("not found"))
            return
        if m == "getUpdates":
            from urllib.parse import parse_qs
            qs = parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}
            offset = int(qs.get("offset", ["0"])[0] or 0)
            self._respond(200, _ok(_pop_updates(offset)))
        elif m == "getMe":
            self._respond(200, _ok({"id": _me_id or 0, "is_bot": False, "first_name": "CadencesFaBela", "username": "cadencesfabella"}))
        elif m == "getChat":
            self._respond(200, _ok({"id": _me_id or 0, "type": "private", "first_name": "user"}))
        elif m == "getMyCommands":
            self._respond(200, _ok([]))
        else:
            self._respond(200, _ok(True))

    def do_POST(self):
        p = self.path.split("?")[0]
        if p == "/api/send":
            if not self._check_web_auth():
                self._respond(401, _err("token requerido (X-Fabella-Token)", 401))
                return
            try:
                body = json.loads(self._read_body() or "{}")
            except Exception:
                body = {}
            r = _send("me", body.get("text", ""))
            self._respond(200, json.dumps(r, ensure_ascii=False))
            return
        m = self._method()
        if not m:
            self._respond(404, _err("not found"))
            return
        try:
            body = json.loads(self._read_body() or "{}")
        except Exception:
            body = {}
        if m == "sendMessage":
            chat_id = body.get("chat_id")
            text = body.get("text", "")
            if chat_id is None:
                self._respond(400, _err("chat_id required"))
                return
            if str(chat_id) == "me":
                chat_id = _me_id
            r = _send(int(chat_id), text)
            if r.get("ok"):
                self._respond(200, _ok({
                    "message_id": r["message_id"],
                    "date": int(time.time()),
                    "chat": {"id": int(chat_id), "type": "private", "first_name": "user"},
                    "text": str(text),
                }))
            else:
                self._respond(500, _err(f"send failed: {r.get('error')}"))
        else:
            self._respond(200, _ok(True))

# ── Main ──────────────────────────────────────────────────────────────────────
async def main():
    global _me_id, loop
    loop = asyncio.get_running_loop()
    await client.start()
    me = await client.get_me()
    _me_id = me.id
    print(f"[fabella] ✅ CadencesFaBela conectado como {me.first_name} (id {me.id})")

    srv = ThreadingHTTPServer(("127.0.0.1", BRIDGE_PORT), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print(f"[fabella] Bot API local  → http://localhost:{BRIDGE_PORT}  (telegram.extra.base_url del gateway)")

    web = ThreadingHTTPServer(("0.0.0.0", WEB_PORT), Handler)
    threading.Thread(target=web.serve_forever, daemon=True).start()
    print(f"[fabella] Interfaz web   → http://localhost:{WEB_PORT}  (CadencesFaBela, cualquier dispositivo de la LAN)")

    await client.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[fabella] detenido")
