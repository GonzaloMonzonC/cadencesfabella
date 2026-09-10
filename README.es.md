# 🏗️ CadencesFaBela

**Cualquier framework de Bot API, sobre tu propia cuenta de Telegram.**
**Sin BotFather. Sin Bot API cloud. Sin pagar por petición.**

> 🇬🇧 English version: [README.md](README.md)
> 🌐 Guía divulgativa (por qué existe · BotFather vs cuenta real · quickstart): **https://fabella.pages.dev**

CadencesFaBela es un adaptador pequeño que emula una **Bot API local de Telegram**
(`getUpdates`, `sendMessage`, `getMe`, …) sobre **MTProto** y tu propia cuenta
de usuario ([Telethon](https://github.com/LonamiWebs/Telethon)). Todo lo que ya
hable Bot API — clientes long-polling, frameworks de chat, gateways de agentes —
funciona sin modificarse: solo hay que apuntar su base url a
`http://localhost:8086`.

Nació como apaño de fin de semana cuando Telegram empezó a monetizar el Bot API
cloud en **agosto de 2026**, y acabó en producción como el transporte de cuenta
personal del stack de agentes de Cadences Lab.

## Por qué existe

En agosto de 2026 Telegram empezó a vender "peticiones" del Bot API a través de
BotFather — sin avisar. Los tokens se estrangularon, los updates dejaron de
llegar, y los fallos parecían problemas de red (timeouts y 502 sin causa en la
red). CadencesFaBela elimina la dependencia: habla con Telegram como habla una persona
— MTProto con una cuenta real — y reexpone localmente la cómoda superficie del
Bot API.

> Hay un trade-off real: un userbot vive en zona gris de los ToS de Telegram.
> Lee el [disclaimer](#disclaimer) antes de desplegarlo. Este repo es la versión
> honesta del truco, no una promesa de seguridad.

## Arquitectura

```
Telegram (MTProto, tu cuenta)          Cualquier cliente Bot API
      │  Telethon                            │  HTTP (Bot API)
      ▼                                       ▼
┌─────────────────────────────────────────────────────┐
│  scripts/bridge_mtproto.py                          │
│   · Bot API local  :8086  (getUpdates/sendMessage)  │
│   · consola web    :8087  (chat + token)            │
└─────────────────────────────────────────────────────┘
```

- **Chat de trabajo por defecto**: los Mensajes guardados de tu cuenta (más
  chats vía `TG_ALLOWED_CHATS`).
- **El cliente no cambia**: solo su base url (`http://localhost:8086`).

## Inicio rápido (5 minutos)

### 0. Requisitos

- Python 3.10+, `pip install telethon`
- **Tus propias** credenciales de API en
  [my.telegram.org](https://my.telegram.org) → *API development tools*

> ⚠️ **No** uses las credenciales de clientes oficiales (ni las de un tutorial
> copiado) — va contra los ToS de Telegram y puede acarrear el baneo de tu
> cuenta. Crear tu propia app es gratis y se tarda un minuto.

### 1. Configura

```bash
cp .env.example .env    # rellena TG_API_ID / TG_API_HASH (o expórtalos)
```

### 2. Login en dos pasos

```bash
python scripts/login_userbot.py send +34XXXXXXXXX
# → te llega un código a la app de Telegram
python scripts/login_userbot.py sign +34XXXXXXXXX <codigo>
```

Esto crea el **fichero de sesión** (`~/.fabella/fabella.session` por defecto).
Trátalo como una contraseña: da acceso a la cuenta.

### 3. Arranca el bridge

```bash
python scripts/bridge_mtproto.py
```

- Bot API local → `http://localhost:8086`
- Consola web → `http://localhost:8087` (protegida por token)

### 4. Apunta tu framework

- **python-telegram-bot**:
  `.base_url("http://localhost:8086/bot")` en el builder (el segmento del token
  es opaco para el bridge).
- **Hermes Agent gateway**:
  ```bash
  hermes config set telegram.extra.base_url http://localhost:8086
  hermes config set telegram.extra.base_file_url http://localhost:8086
  ```
  y define `HERMES_TELEGRAM_DISABLE_FALLBACK_IPS=1` — si no, el transporte de
  fallback reescribe `localhost` a IPs reales de Telegram y nunca llega al
  bridge.
- Cualquier otra cosa que hable `getUpdates` / `sendMessage`.

## Configuración

| Variable | Defecto | Para qué |
|---|---|---|
| `TG_API_ID` / `TG_API_HASH` | *(obligatorio)* | **tus** credenciales — https://my.telegram.org |
| `TG_SESSION` | `~/.fabella/fabella.session` | ruta del fichero de sesión |
| `TG_BRIDGE_PORT` | `8086` | puerto Bot API local |
| `TG_WEB_PORT` | `8087` | puerto de la consola web |
| `TG_ALLOWED_CHATS` | *(vacío)* | chats extra que el userbot atiende (ids o usernames, separados por coma). Vacío = solo Mensajes guardados |
| `TG_BOT_CHAT_ID` | *(vacío)* | un chat extra permitido (p.ej. un chat de bot antiguo que quieras que siga respondiendo) |
| `TG_WEB_TOKEN` | auto | token que exige la consola en `/api/*`; se genera solo en el primer arranque |
| `TG_TOKEN_PATH` | `~/.fabella/fabella_token.txt` | dónde se guarda ese token |

## Qué es / qué NO es

**Es:** un adaptador de protocolo. Bot API por un lado, MTProto por el otro.
Los frameworks no cambian; solo la base url.

**NO es:**

- oficial, ni está afiliado a Telegram de ninguna forma;
- una forma de evitar baneos — los userbots son zona gris, y automatizar puede
  limitar cuentas;
- una implementación completa del Bot API: los mensajes de texto van de punta a
  punta; los medios son placeholder (`[media]`), y la mayoría de parámetros
  opcionales (teclados, modos inline, webhooks — esto es long-polling) no están
  implementados.

## Componentes

| Fichero | Rol |
|---|---|
| `scripts/bridge_mtproto.py` | el bridge: Bot API local + consola web + eventos MTProto |
| `scripts/login_userbot.py` | login en dos pasos → crea el fichero de sesión |
| `scripts/watchdog_fabella.py` | opcional: relanza el bridge si deja de responder |
| `scripts/bridge_puente.py` | ejemplo opcional: sondea el bridge y reenvía a `hermes chat` cuando el polling del gateway no corre |

## Notas de campo

Cosas pequeñas y no obvias que aprendimos en producción (ya están integradas,
pero conviene saberlas si haces fork):

- **El filtro anti-eco va por `message_id`, no por `msg.out`.** Los mensajes
  enviados desde el móvil también son `out=True` (misma cuenta, otra sesión) —
  filtrar por `out` se traga mensajes reales. El bridge registra los ids que
  envía él y solo ignora esos.
- **Las allowlists de chat necesitan id *y* username.** Los chats con username
  no matchean su id numérico.
- **PTB postea todo.** Si tu framework inicializa bien y luego nunca sondea,
  mira qué responde tu bridge a `POST getMe` — algunos clientes necesitan el
  camino de reconexión para arrancar el polling.
- **Los duplicados desincronizan la cola de updates.** Deja el ciclo de vida al
  watchdog; no lances un segundo bridge a mano.

## Seguridad

- El **fichero de sesión es la cuenta**: mantenlo fuera de git (está
  gitignored).
- El puerto Bot API escucha en `127.0.0.1`; la consola web en `0.0.0.0` y exige
  `X-Fabella-Token` en `/api/*`. No la expongas en crudo — pon delante un token
  y un túnel (o una red privada). Ver [SECURITY.md](SECURITY.md).

## Disclaimer

CadencesFaBela **no está afiliada a Telegram**. Operar un userbot puede violar los
Términos de Servicio de Telegram y puede acarrear limitaciones o baneos de
cuenta. Está pensado para automatización personal de **tu propia** cuenta.
**Úsalo bajo tu responsabilidad.**

## Estado

**v0.4 estable** (agosto 2026). Ver [CHANGELOG.md](CHANGELOG.md).

## Licencia

MIT — ver [LICENSE](LICENSE).

Parte del toolkit abierto de [Cadences Lab](https://github.com/GonzaloMonzonC):
[lumen-protocol](https://github.com/GonzaloMonzonC/lumen-protocol)
(protocolo · PDB · MVM) y la **tríada A·I·E** de agentes de referencia —
[Astrid](https://github.com/GonzaloMonzonC/astrid) *(evidencia)* ·
[Iris](https://github.com/GonzaloMonzonC/iris) *(hipótesis)* ·
[Elena](https://github.com/GonzaloMonzonC/elena) *(decisión)*.
