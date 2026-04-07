"""
API Server — tourne sur le laptop avec ngrok.
Recoit les push des VPS, sert le dashboard.

Usage:
  uvicorn api_server:app --host 0.0.0.0 --port 8001
  ngrok http --domain=unprolongable-nonexternalized-elizabet.ngrok-free.dev 8001
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import threading, time
from datetime import datetime, timezone

app = FastAPI(title="VP Swing API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── STATE en memoire ──
_lock = threading.Lock()
_state = {}  # account -> {state, history, last_push}


@app.post("/push/{account}")
async def push(account: str, data: dict):
    """VPS pousse l'etat MT5 chaque seconde."""
    with _lock:
        if account not in _state:
            _state[account] = {'state': {}, 'history': [], 'last_push': None}
        _state[account]['state'] = data.get('state', {})
        _state[account]['last_push'] = datetime.now(timezone.utc).isoformat()
        # History: remplace si fourni
        if 'history' in data and data['history']:
            _state[account]['history'] = data['history']
    return {"ok": True}


@app.get("/state")
async def get_all_states():
    """Dashboard lit tout l'etat."""
    with _lock:
        result = {}
        for account, d in _state.items():
            result[account] = {
                'state': d['state'],
                'history': d['history'],
                'last_push': d['last_push'],
            }
    return result


@app.get("/state/{account}")
async def get_account_state(account: str):
    """Dashboard lit l'etat d'un compte."""
    with _lock:
        d = _state.get(account, {})
    return d


@app.get("/health")
async def health():
    with _lock:
        accounts = {k: v['last_push'] for k, v in _state.items()}
    return {"status": "ok", "accounts": accounts}
