# Changelog

All notable changes to this project are documented in this file.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) ·
Versioning: [Semantic Versioning](https://semver.org/).

## [0.4.0] - 2026-08-05

### Fixed
- **Web console → gateway flow**: `POST /api/send` now injects an update, so
  messages sent from the console also reach the client's polling loop.
- First full end-to-end verification: message in → reply out (13.7 s round
  trip).

### Notes
- Marked **stable**. The bridge lifecycle belongs to the watchdog — don't
  launch duplicates by hand (they desync the update queue).

## [0.3.0] - 2026-08-04

### Added
- Anti-echo filter by **sent-`message_id` registry** instead of `msg.out`:
  messages sent from other sessions of the same account (e.g. the phone) pass
  through, while the userbot's own replies no longer loop back.
- Chat allowlist now matches by **numeric id AND username** (chat ids that also
  have a username were being rejected).

## [0.2.0] - 2026-08-01

### Added
- Web console (`:8087`): chat UI, `GET /api/history`, `POST /api/send`.
- External access through a reverse tunnel (operational).

## [0.1.0] - 2026-07-28

### Added
- Initial MTProto userbot: local Bot API emulation over a personal account
  (`getUpdates`, `sendMessage`, `getMe`), two-step login, session file.
