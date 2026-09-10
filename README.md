# 🏗️ CadencesFaBela

**Any Bot API framework, on your own Telegram account.**
**No BotFather. No cloud Bot API. No per-request fees.**

> 🇪🇸 Versión en español: [README.es.md](README.es.md)

CadencesFaBela is a small adapter that emulates a **local Telegram Bot API**
(`getUpdates`, `sendMessage`, `getMe`, …) on top of **MTProto** and your own
user account ([Telethon](https://github.com/LonamiWebs/Telethon)). Anything
that already speaks the Bot API — long-polling clients, chat frameworks, agent
gateways — works unmodified once you point its base URL at
`http://localhost:8086`.

It started as a weekend workaround when Telegram began monetizing the cloud
Bot API in **August 2026**, and ended up running in production as the
personal-account transport for Cadences Lab's agent stack.

## Why this exists

In August 2026 Telegram started selling Bot API "requests" through BotFather —
quietly. Tokens got throttled, updates stopped arriving, and the failures looked
like network trouble (timeouts and 502s with no cause in the network). CadencesFaBela
removes the dependency: it talks to Telegram the way a person does — MTProto
with a real account — and re-exposes the convenient Bot API surface locally.

> There is a real trade-off: a userbot lives in a grey area of Telegram's ToS.
> Read the [disclaimer](#disclaimer) before deploying. This repo is the honest
> version of the trick, not a promise of safety.

## Architecture

```
Telegram (MTProto, your account)          Any Bot API client
      │  Telethon                              │  HTTP (Bot API)
      ▼                                        ▼
┌─────────────────────────────────────────────────────┐
│  scripts/bridge_mtproto.py                          │
│   · local Bot API  :8086  (getUpdates/sendMessage)  │
│   · web console    :8087  (chat UI + token auth)    │
└─────────────────────────────────────────────────────┘
```

- **Default working chat**: Saved Messages of your account (extra chats via
  `TG_ALLOWED_CHATS`).
- **The client doesn't change**: only its base URL
  (`http://localhost:8086`).

## Quickstart (5 minutes)

### 0. Requirements

- Python 3.10+, `pip install telethon`
- **Your own** API credentials from
  [my.telegram.org](https://my.telegram.org) → *API development tools*

> ⚠️ Do **not** use the credentials of official clients (or ones copied from a
> tutorial) — that is against Telegram's ToS and can get your account banned.
> Creating your own app is free and takes a minute.

### 1. Configure

```bash
cp .env.example .env    # fill in TG_API_ID / TG_API_HASH (or just export them)
```

### 2. Log in (two steps)

```bash
python scripts/login_userbot.py send +34XXXXXXXXX
# → a login code arrives in your Telegram app
python scripts/login_userbot.py sign +34XXXXXXXXX <code>
```

This creates the **session file** (`~/.fabella/fabella.session` by default).
Treat it like a password: it grants access to the account.

### 3. Run the bridge

```bash
python scripts/bridge_mtproto.py
```

- Local Bot API → `http://localhost:8086`
- Web console → `http://localhost:8087` (token-protected)

### 4. Point your framework at it

- **python-telegram-bot**:
  `.base_url("http://localhost:8086/bot")` in the builder (the token segment
  is opaque to the bridge).
- **Hermes Agent gateway**:
  ```bash
  hermes config set telegram.extra.base_url http://localhost:8086
  hermes config set telegram.extra.base_file_url http://localhost:8086
  ```
  and set `HERMES_TELEGRAM_DISABLE_FALLBACK_IPS=1` — otherwise the fallback
  transport rewrites `localhost` to real Telegram IPs and never reaches the
  bridge.
- Anything else that speaks `getUpdates` / `sendMessage`.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `TG_API_ID` / `TG_API_HASH` | *(required)* | **your** app credentials — https://my.telegram.org |
| `TG_SESSION` | `~/.fabella/fabella.session` | session file path |
| `TG_BRIDGE_PORT` | `8086` | local Bot API port |
| `TG_WEB_PORT` | `8087` | web console port |
| `TG_ALLOWED_CHATS` | *(empty)* | extra chats the userbot answers (ids or usernames, comma-separated). Empty = Saved Messages only |
| `TG_BOT_CHAT_ID` | *(empty)* | one extra chat id kept allowed (e.g. an old bot chat you want answered) |
| `TG_WEB_TOKEN` | auto | token required by the console API (`/api/*`); auto-generated on first run |
| `TG_TOKEN_PATH` | `~/.fabella/fabella_token.txt` | where that token is stored |

## What it is / what it is NOT

**It is:** a protocol adapter. Bot API on one side, MTProto on the other.
Frameworks don't change; only the base URL does.

**It is NOT:**

- official, or affiliated with Telegram in any way;
- a way to avoid bans — userbots are a grey area, and automation can get
  accounts limited;
- a complete Bot API implementation: text messages work end-to-end; media is
  placeholder (`[media]`), and most optional parameters (keyboards, inline
  modes, webhooks — it's long-polling only) are not implemented.

## Components

| File | Role |
|---|---|
| `scripts/bridge_mtproto.py` | the bridge: local Bot API + web console + MTProto events |
| `scripts/login_userbot.py` | two-step login → creates the session file |
| `scripts/watchdog_fabella.py` | optional: relaunch the bridge if it stops answering |
| `scripts/bridge_puente.py` | optional example: poll the bridge and forward messages to `hermes chat` when the gateway's own polling isn't running |

## Notes from the field

Small, non-obvious things we learned running this in production (they're baked
in, but they're worth knowing if you fork):

- **Anti-echo must filter by `message_id`, not `msg.out`.** Messages sent from
  your phone are `out=True` too (same account, another session) — filtering by
  `out` swallows real messages. The bridge keeps a registry of its own sent ids
  and ignores only those.
- **Chat allowlists need id *and* username.** Chats with a username don't match
  their numeric id.
- **PTB posts everything.** If your framework initializes fine and then never
  polls, check what your bridge answers on `POST getMe` — some clients need the
  reconnect path to start polling.
- **Duplicates desync the update queue.** Let the watchdog own the lifecycle;
  don't launch a second bridge by hand.

## Security

- The **session file is the account**: keep it out of git (it's gitignored).
- The Bot API port binds to `127.0.0.1`; the web console binds `0.0.0.0` and
  requires `X-Fabella-Token` on `/api/*`. Don't expose it raw — put a token and
  a tunnel (or a private network) in front of it. See
  [SECURITY.md](SECURITY.md).

## Disclaimer

CadencesFaBela is **not affiliated with Telegram**. Operating a userbot may violate
Telegram's Terms of Service and can get accounts limited or banned. It is meant
for personal automation of **your own** account. **Use at your own risk.**

## Status

**v0.4 stable** (August 2026). See [CHANGELOG.md](CHANGELOG.md).

## License

MIT — see [LICENSE](LICENSE).

Part of the [Cadences Lab](https://github.com/GonzaloMonzonC) open toolkit:
[lumen-protocol](https://github.com/GonzaloMonzonC/lumen-protocol)
(protocol · PDB · MVM) and the **tríada A·I·E** of reference agents —
[Astrid](https://github.com/GonzaloMonzonC/astrid) *(evidence)* ·
[Iris](https://github.com/GonzaloMonzonC/iris) *(hypotheses)* ·
[Elena](https://github.com/GonzaloMonzonC/elena) *(decision)*.
