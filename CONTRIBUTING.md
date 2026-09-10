# Contributing

PRs are welcome. Honest note: this is a small utility maintained by a small
team — issues may take a while (or may not be attended at all). If you need
guaranteed support, fork it; that is exactly what the MIT license is for.

## Dev setup

```bash
pip install telethon
cp .env.example .env    # add your own api_id / api_hash
python scripts/login_userbot.py send +34XXXXXXXXX
python scripts/bridge_mtproto.py
```

Test with a **secondary account** when you can: this is a userbot, and mistakes
hit the real account.

## Guidelines

- **Keep it small.** This is a bridge, not a framework. Stdlib-first; the only
  runtime dependency is `telethon`.
- Never commit `.env`, `*.session` files or tokens — they are gitignored; keep
  it that way.
- Match the existing style, and document the non-obvious: see *"Notes from the
  field"* in the README for the kind of thing worth writing down.

## In scope / out of scope

**In scope:** more of the Bot API surface (media, keyboards), robustness
(flood-wait handling), documentation.

**Out of scope:** spam tooling, mass account automation, or anything that turns
this bridge into an abuse vector.
