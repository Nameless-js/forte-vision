"""Start React/Vite and the integrated local AI API with one command."""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import secrets
import shutil
import signal
import subprocess
import sys
import time
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-port", type=int, default=8000)
    parser.add_argument("--port", type=int, default=5173)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    node = shutil.which("node")
    vite = FRONTEND / "node_modules" / "vite" / "bin" / "vite.js"
    if not node or not vite.exists():
        raise SystemExit("Install frontend dependencies first: cd frontend; npm ci")
    env_file = FRONTEND / ".env"
    if not env_file.exists():
        env_file.write_text("API_KEY=" + secrets.token_urlsafe(32) + "\nDATABASE_BACKEND=sqlite\nFORTE_PROFILE=auto\n", encoding="utf-8")
    configured = {k:v for k,v in dotenv_values(env_file).items() if v is not None}
    environment = {**configured, **os.environ, "PYTHONUTF8":"1", "PYTHONIOENCODING":"utf-8"}
    if not environment.get("API_KEY"):
        key_file = FRONTEND / "runtime" / ".api-key"
        key_file.parent.mkdir(parents=True, exist_ok=True)
        if not key_file.exists():
            key_file.write_text(secrets.token_urlsafe(32), encoding="utf-8")
        environment["API_KEY"] = key_file.read_text(encoding="utf-8").strip()
    environment.setdefault("DATABASE_BACKEND", "sqlite")
    environment["API_PROXY_TARGET"] = f"http://127.0.0.1:{args.api_port}"
    def stop(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, stop)
    processes = []
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    try:
        processes.append(subprocess.Popen([sys.executable,"-m","uvicorn","frontend.backend.main:app","--host",args.host,"--port",str(args.api_port)], cwd=ROOT, env=environment, creationflags=flags))
        processes.append(subprocess.Popen([node,str(vite),"--host",args.host,"--port",str(args.port),"--strictPort"], cwd=FRONTEND, env=environment, creationflags=flags))
        print(f"Interface: http://{args.host}:{args.port} | API: http://{args.host}:{args.api_port}", flush=True)
        print("Local model enabled. Ctrl+C stops both services. API key stays server-side in frontend/.env.", flush=True)
        while all(p.poll() is None for p in processes):
            time.sleep(.5)
    except KeyboardInterrupt:
        pass
    finally:
        for process in processes:
            if process.poll() is None:
                try:
                    process.send_signal(signal.CTRL_BREAK_EVENT if os.name == "nt" else signal.SIGINT)
                except OSError:
                    pass
        for process in processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
