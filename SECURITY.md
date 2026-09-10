# Security Policy

## Reporting a vulnerability

Email **gonzalo@cadenceslab.com** (or open a private security advisory on
GitHub). Please don't open public issues for security problems.

## The most important thing: the session file

A `*.session` file is **full access to the linked Telegram account** — whoever
holds the file can read and send messages as that account. Therefore:

- never commit it, never share it, never paste it into an issue or a chat;
- it is gitignored on purpose — keep it that way;
- if it leaks: Telegram → *Settings → Devices* → terminate the session, delete
  the file, and log in again to create a fresh one.

## What Fabella does and does not protect

- The web console requires `X-Fabella-Token` on `/api/*`; the token is
  generated locally on first run (`~/.fabella/fabella_token.txt`).
- The Bot API port binds to `127.0.0.1` by default. The web console binds
  `0.0.0.0` — **do not expose it to the open internet** without a tunnel plus
  an auth layer (see `docs/tunnel.md`).
- Messages travel through your machine and your account only — there is no
  third-party server in the middle, and no encryption beyond what Telegram
  MTProto itself provides.
- Anti-abuse on Telegram's side is out of anyone's control: automation on a
  user account can lead to limits or bans. See the disclaimer in the README.
