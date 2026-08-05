#!/usr/bin/env python3
"""Watchdog CadencesFaBela: si el bridge (:8086) no responde 2 veces seguidas, lo relanza.
Silencioso cuando todo OK (patrón no_agent)."""
import subprocess, sys, os, time, urllib.request

PY = r"C:\Users\<user>\.fabella\hermes-agent\venv\Scripts\python.exe"
SCRIPT = r"C:\Users\<user>\.fabella\scripts\bridge_mtproto.py"

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
    try:
        subprocess.Popen(
            [PY, SCRIPT],
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            cwd=os.path.dirname(SCRIPT),
            stdout=open(os.path.expanduser("~/.fabella/logs/fabella.log"), "a"),
            stderr=subprocess.STDOUT,
        )
        print(f"🚨 CadencesFaBela CAIDO ({fails} fails) — bridge relanzado {time.strftime('%H:%M')}")
    except Exception as e:
        print(f"🚨 CadencesFaBela caido y NO pude relanzarlo: {e}")

if __name__ == "__main__":
    main()
