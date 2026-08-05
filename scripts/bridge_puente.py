#!/usr/bin/env python3
"""
CadencesFaBela Puente — GET getUpdates del bridge, hermes chat -q (con sesión persistente),
respuesta vía sendMessage del bridge.
"""
import json, os, re, subprocess, sys, time, urllib.request, urllib.parse

BRIDGE = "http://localhost:8086"
HERMES = r"C:\Users\<user>\.fabella\hermes-agent\venv\Scripts\hermes.exe"
TOKEN = "bottest"
SESSION_ID_FILE = os.path.expanduser("~/.fabella/data/fabella_tg_session.txt")
last_update_id = 0

def get_session_id():
    if os.path.exists(SESSION_ID_FILE):
        return open(SESSION_ID_FILE).read().strip()
    return None

def save_session_id(sid):
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
    
    # Si no tenemos sesión persistente, crear una inicial (con mensaje semilla)
    if not session_id:
        print("[puente] Creando sesión persistente para Telegram...")
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
                print(f"[puente] Sesión: {session_id}")
            else:
                print("[puente] No se pudo crear sesión inicial, usando sin persistencia")
                session_id = None
        except Exception as e:
            print(f"[puente] Error creando sesión inicial: {e}")
            session_id = None

    print("[puente] CadencesFaBela puente activo — vigilando cada 3s...")
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
                print(f"[puente] ← {cid}: {text[:80]}")
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
                    # Actualizar session_id si cambió
                    m = re.search(r"Session:\s+(\S+)", out)
                    if m:
                        session_id = m.group(1)
                        save_session_id(session_id)
                    # Extraer la respuesta
                    lines = [l for l in out.splitlines() if l.strip() and not l.startswith("Session:") and len(l.strip()) > 10]
                    if not lines:
                        print(f"  [puente] sin respuesta")
                        continue
                    resp_text = lines[-1].strip()
                    # Si la respuesta contiene "Session:" otra vez, tomar la penúltima
                    if "Session:" in resp_text:
                        resp_text = lines[-2].strip() if len(lines) >= 2 else resp_text
                    r = send_via_bridge(cid, resp_text[:2000])
                    if r.get("ok"):
                        print(f"  [puente] → msg {r['result'].get('message_id','?')} ({len(resp_text)} chars)")
                    else:
                        print(f"  [puente] send error: {r.get('error','?')}")
                except subprocess.TimeoutExpired:
                    print("  [puente] hermes chat timeout")
                except Exception as e:
                    print(f"  [puente] error: {type(e).__name__}: {e}")
        except Exception as e:
            print(f"[puente] loop error: {e}")
        time.sleep(3)

if __name__ == "__main__":
    main()
