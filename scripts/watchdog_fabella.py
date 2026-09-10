#!/usr/bin/env python3
"""Fabella watchdog: relaunch the bridge (:8086) if it fails twice in a row.
Silent when everything is OK."""
import subprocess, sys, os, time, urllib.request

PY = os.environ.get("FABELLA_PY") or sys.executable
SCRIPT = os.environ.get("FABELLA_BRIDGE_SCRIPT") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "bridge_mtproto.py"
)
LOG_PATH = os.path.expanduser(os.environ.get("FABELLA_LOG", "~/.fabella/watchdog.log"))

def check():
    try:
        r = urllib.request.urlopen("http://localhost:8086/bottest/getMe", timeout=5)
        return r.status == 200
    except Exception:
        return False

def main():
    fails = 0
    for _ in range(2):
        if check():
            return  # OK → silencioso
        fails += 1
        time.sleep(4)
    flags = (subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP) if os.name == "nt" else 0
    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        subprocess.Popen(
            [PY, SCRIPT],
            creationflags=flags,
            cwd=os.path.dirname(SCRIPT),
            stdout=open(LOG_PATH, "a"),
            stderr=subprocess.STDOUT,
        )
        print(f"🚨 Fabella bridge DOWN ({fails} fails) — relaunched {time.strftime('%H:%M')}")
    except Exception as e:
        print(f"🚨 Fabella bridge down and could not relaunch it: {e}")

if __name__ == "__main__":
    main()
