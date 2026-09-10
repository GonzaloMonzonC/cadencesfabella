#!/usr/bin/env python3
"""
Fabella ⇄ Hermes CLI bridge (optional example integration).

Polls the local Fabella bridge (getUpdates) and forwards each message to
`hermes chat -q` with a persistent session; the reply goes back through the
bridge's sendMessage. Useful when the gateway's own polling isn't running.
"""
import json, os, re, shutil, subprocess, sys, time, urllib.request, urllib.parse

BRIDGE = os.environ.get("FABELLA_BRIDGE_URL", "http://localhost:8086")
HERMES = os.environ.get("HERMES_BIN") or shutil.which("hermes") or "hermes"
TOKEN = os.environ.get("FABELLA_BOT_TOKEN", "bottest")
SESSION_ID_FILE = os.path.expanduser(os.environ.get("FABELLA_TG_SESSION_FILE", "~/.fabella/tg_session.txt"))
last_update_id = 0

def get_session_id():
    if os.path.exists(SESSION_ID_FILE):
        return open(SESSION_ID_FILE).read().strip()
    return None

def save_session_id(sid):
    os.makedirs(os.path.dirname(SESSION_ID_FILE), exist_ok=True)
    open(SESSION_ID_FILE, "w").write(sid)

def get_updates():
    global last_update_id
    try:
        params = urllib.parse.urlencode({"offset": last_update_id + 1, "timeout": 2})
        url = f"{BRIDGE}/{TOKEN}/getUpdates?{params}"
        with urllib.request.urlopen(url, timeout=6) as r:
            resp = json.loads(r.read().decode())
            updates = resp.get("result", [])
            for u in updates:
                last_update_id = max(last_update_id, u.get("update_id", 0))
            return updates
    except Exception:
        return []

def send_via_bridge(chat_id, text):
    try:
        d = json.dumps({"chat_id": chat_id, "text": str(text)[:4000]}).encode()
        req = urllib.request.Request(f"{BRIDGE}/{TOKEN}/sendMessage", data=d, method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"ok": False, "error": str(e)}

def main():
    global last_update_id
    session_id = get_session_id()
    
    # No persistent session yet: create an initial one (with a seed message)
    if not session_id:
        print("[bridge] Creating persistent Hermes session...")
        try:
            r = subprocess.run(
                [HERMES, "chat", "-q", "/start", "--max-turns", "1"],
                capture_output=True, text=True, timeout=60,
                cwd=os.path.expanduser("~"),
                env={**os.environ, "HERMES_NO_TTY": "1"}
            )
            m = re.search(r"Session:\s+(\S+)", r.stdout)
            if m:
                session_id = m.group(1)
                save_session_id(session_id)
                print(f"[bridge] Session: {session_id}")
            else:
                print("[bridge] Could not create initial session — continuing without persistence")
                session_id = None
        except Exception as e:
            print(f"[bridge] Error creating initial session: {e}")
            session_id = None

    print("[bridge] Fabella bridge active — polling every 3s...")
    while True:
        try:
            updates = get_updates()
            for u in updates:
                msg = u.get("message", {})
                text = msg.get("text", "")
                chat = msg.get("chat", {})
                cid = chat.get("id", 0)
                if not text or not cid:
                    continue
                print(f"[bridge] ← {cid}: {text[:80]}")
                try:
                    cmd = [HERMES, "chat", "-q", text, "--max-turns", "1"]
                    if session_id:
                        cmd += ["--resume", session_id]
                    result = subprocess.run(
                        cmd, capture_output=True, text=True, timeout=120,
                        cwd=os.path.expanduser("~"),
                        env={**os.environ, "HERMES_NO_TTY": "1"}
                    )
                    out = result.stdout
                    # Update session_id if it changed
                    m = re.search(r"Session:\s+(\S+)", out)
                    if m:
                        session_id = m.group(1)
                        save_session_id(session_id)
                    # Extract the reply
                    lines = [l for l in out.splitlines() if l.strip() and not l.startswith("Session:") and len(l.strip()) > 10]
                    if not lines:
                        print(f"  [bridge] no reply")
                        continue
                    resp_text = lines[-1].strip()
                    # If the reply contains "Session:" again, take the previous line
                    if "Session:" in resp_text:
                        resp_text = lines[-2].strip() if len(lines) >= 2 else resp_text
                    r = send_via_bridge(cid, resp_text[:2000])
                    if r.get("ok"):
                        print(f"  [bridge] → msg {r['result'].get('message_id','?')} ({len(resp_text)} chars)")
                    else:
                        print(f"  [bridge] send error: {r.get('error','?')}")
                except subprocess.TimeoutExpired:
                    print("  [bridge] hermes chat timed out")
                except Exception as e:
                    print(f"  [bridge] error: {type(e).__name__}: {e}")
        except Exception as e:
            print(f"[bridge] loop error: {e}")
        time.sleep(3)

if __name__ == "__main__":
    main()
