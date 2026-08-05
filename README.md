# CadencesFaBela 🏗️

> Consola personal sobre Telegram **sin depender del Bot API cloud de Telegram**.
> MTProto directo con tu cuenta (Telethon) — ni BotFather, ni Stars, ni peajes.

## Por qué existe

En agosto 2026 Telegram empezó a monetizar el Bot API cloud sin avisar (BotFather
vende "peticiones", tokens estrangulados en silencio → el gateway dejó de recibir
mensajes con timeouts y 502 sin causa en la red). CadencesFaBela elimina la
dependencia: habla por **MTProto con la cuenta personal**, que no tiene ese modelo.

## Arquitectura

```
Telegram (MTProto)                          Gateway Hermes
      │  Telethon (tu cuenta)                     │
      ▼                                          │
┌──────────────────────────┐   Bot API HTTP      │
│  bridge_mtproto.py       │◄────────────────────┘  telegram.extra.base_url
│  · Bot API local :8086   │  getUpdates/sendMessage  → http://localhost:8086
│  · Interfaz web   :8087  │
└──────────────────────────┘
      │
      └── Interfaz web CadencesFaBela (cualquier navegador/teléfono)
          · GET  /             → chat HTML
          · GET  /api/history  → hilo de Mensajes guardados
          · POST /api/send     → enviar al chat
```

- **Chat de trabajo**: "Mensajes guardados" de la cuenta (o `TG_ALLOWED_CHATS`)
- **El gateway de Hermes no se toca**: solo `hermes config set telegram.extra.base_url http://localhost:8086`
- **El protocolo Bot API se mantiene**: el adaptador PTB del gateway funciona igual

## Componentes

| Archivo | Función |
|---------|---------|
| `scripts/bridge_mtproto.py` | Bridge principal: Bot API local (:8086) + web (:8087) + eventos MTProto |
| `scripts/login_userbot.py` | Login en 2 pasos (send/sign) → crea la sesión `.session` |

## Config

Env vars del bridge (defaults para Telegram Desktop públicas):

```
TG_API_ID=YOUR_API_ID                # → reemplazar con app propia de my.telegram.org
TG_API_HASH=YOUR_API_HASH
TG_SESSION=~/.fabella/data/telegram_userbot.session
TG_BRIDGE_PORT=8086
TG_WEB_PORT=8087
TG_ALLOWED_CHATS=             # vacío = solo Saved Messages
```

## Arranque

```bash
# 1. Login (una vez): te llega un código a tu móvil
python login_userbot.py send +34XXXXXXXXX   # → código
python login_userbot.py sign +34XXXXXXXXX <codigo>

# 2. Bridge
python bridge_mtproto.py

# 3. Gateway apuntando al bridge
hermes config set telegram.extra.base_url http://localhost:8086
hermes config set telegram.extra.base_file_url http://localhost:8086

# 4. Consola web
#   local: http://localhost:8087
#   externo: https://console.example.com (tunnel l13, ver docs/tunnel.md)
```

## Tunnel externo

- **OPERATIVO**: https://console.example.com → localhost:8087 (200 verificado)
- CNAME `console.example.com` → tunnel `vm-api` (config.yml del servicio ya lo incluye)
- Proceso de usuario de respaldo: `cloudflared tunnel --config config.yml run` (mismo tunnel, cubre los 3 hostnames)
- vm-api/poli-api siguen en sus rutas reales (/ddp/health, /health) — la raíz `/` de ambos da 404 (no tienen ruta raíz, normal)

## Privacidad / Seguridad

- La sesión `.session` y los scripts viven en local (`~/.fabella/data/`)
- El bridge escucha solo en 127.0.0.1 para el Bot API; la web en 0.0.0.0 (LAN) — el tunnel externo es el acceso remoto
- La web no tiene auth: **no exponer :8087 directo a internet** salvo detrás del tunnel con control (pendiente: añadir token simple a /api/*)

## Roadmap

- [x] Userbot MTProto operativo (reemplaza Bot API cloud)
- [x] Interfaz web CadencesFaBela (:8087) + tunnel
- [ ] App propia en my.telegram.org (api_id/api_hash propios) cuando pase el cooldown
- [ ] Auth en la web (token en /api/*)
- [ ] Watchdog del bridge (cron)
- [ ] Multi-chat configurable por contacto
