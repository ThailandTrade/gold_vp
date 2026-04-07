"""
API Server + Dashboard — tourne sur le laptop avec ngrok.
Recoit les push des VPS, sert le dashboard HTML.

Usage:
  uvicorn api_server:app --host 0.0.0.0 --port 8001
  ngrok http --domain=unprolongable-nonexternalized-elizabet.ngrok-free.dev 8001
  → Dashboard: http://localhost:8001/
"""
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
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


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return DASHBOARD_HTML


DASHBOARD_HTML = """<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<title>VP Swing Live</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { background:#0e1117; color:#fafafa; font-family:'Consolas','Monaco',monospace; font-size:13px; padding:20px; }
  h1 { color:#ff6b35; margin-bottom:20px; font-size:24px; }
  .grid { display:grid; grid-template-columns:1fr 1fr; gap:20px; }
  .card { background:#1a1d24; border-radius:8px; padding:16px; border:1px solid #2d3139; }
  .card h2 { color:#4da6ff; margin-bottom:12px; font-size:18px; }
  .metrics { display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin-bottom:16px; }
  .metric { background:#22262e; border-radius:6px; padding:10px; text-align:center; }
  .metric .label { color:#888; font-size:11px; }
  .metric .value { font-size:18px; font-weight:bold; margin-top:4px; }
  .green { color:#00d26a; }
  .red { color:#ff4757; }
  .section { margin-top:12px; }
  .section h3 { color:#ccc; font-size:14px; margin-bottom:8px; border-bottom:1px solid #2d3139; padding-bottom:4px; }
  .trade { padding:4px 0; border-bottom:1px solid #1f2229; }
  .pos { padding:6px 8px; background:#22262e; border-radius:4px; margin-bottom:4px; }
  .waiting { color:#888; font-style:italic; }
  .caption { color:#666; font-size:11px; margin-bottom:12px; }
  .events { background:#1a1d24; border-radius:8px; padding:16px; margin-top:20px; border:1px solid #2d3139; }
  .expander { cursor:pointer; color:#4da6ff; }
  .expander-content { display:none; margin-top:8px; max-height:400px; overflow-y:auto; }
  .expander-content.open { display:block; }
</style>
</head><body>
<h1>VP Swing &mdash; Live Dashboard</h1>
<div class="grid" id="accounts"></div>
<div class="events" id="status"></div>

<script>
const API = '';  // meme origine
const ACCOUNTS = ['5ers', 'ftmo'];

function fmt(n, d=0) { return n != null ? n.toLocaleString('en-US', {minimumFractionDigits:d, maximumFractionDigits:d}) : '-'; }
function pnlClass(v) { return v >= 0 ? 'green' : 'red'; }
function pnlSign(v) { return v >= 0 ? '+'+fmt(v,2) : fmt(v,2); }

function renderAccount(account, data) {
  if (!data || !data.state || !data.state.account_info) {
    return `<div class="card"><h2>${account.toUpperCase()}</h2><div class="waiting">En attente de donnees...</div></div>`;
  }
  const s = data.state;
  const a = s.account_info || {};
  const positions = s.positions || [];
  const trades = s.today_trades || [];
  const candles = s.candles || {};
  const hist = data.history || [];

  let html = `<div class="card"><h2>${account.toUpperCase()}</h2>`;
  html += `<div class="caption">Derniere maj: ${(s.ts||'').slice(0,19)}</div>`;

  // Metrics
  html += `<div class="metrics">
    <div class="metric"><div class="label">Balance</div><div class="value">$${fmt(a.balance)}</div></div>
    <div class="metric"><div class="label">Equity</div><div class="value">$${fmt(a.equity)}</div></div>
    <div class="metric"><div class="label">PnL jour</div><div class="value ${pnlClass(s.today_pnl)}">$${pnlSign(s.today_pnl)}</div></div>
    <div class="metric"><div class="label">Trades jour</div><div class="value">${s.today_count||0}</div></div>
  </div>`;

  // Positions
  html += `<div class="section"><h3>Positions ouvertes (${positions.length})</h3>`;
  if (positions.length === 0) html += `<div class="waiting">Aucune position</div>`;
  for (const p of positions) {
    const icon = p.pnl >= 0 ? '&#x1F7E2;' : '&#x1F534;';
    html += `<div class="pos">${icon} ${p.symbol} ${p.comment||''} ${p.dir.toUpperCase()} @ ${fmt(p.entry,2)} &rarr; ${fmt(p.current,2)} SL=${fmt(p.sl,2)} <span class="${pnlClass(p.pnl)}">$${pnlSign(p.pnl)}</span> (${p.volume}lots)</div>`;
  }
  html += `</div>`;

  // Today trades
  if (trades.length > 0) {
    html += `<div class="section"><h3>Trades du jour (${trades.length})</h3>`;
    for (const t of [...trades].reverse()) {
      const icon = t.pnl >= 0 ? '&#x1F7E2;' : '&#x1F534;';
      html += `<div class="trade">${icon} ${(t.time_close||'').slice(0,16)} ${t.symbol} ${t.comment||''} ${t.dir.toUpperCase()} ${fmt(t.entry,2)}&rarr;${fmt(t.exit,2)} <span class="${pnlClass(t.pnl)}">$${pnlSign(t.pnl)}</span></div>`;
    }
    html += `</div>`;
  }

  // Candles
  const syms = Object.keys(candles);
  if (syms.length > 0) {
    html += `<div class="section"><h3>Dernieres bougies</h3>`;
    for (const sym of syms) {
      const c = candles[sym];
      if (c && c.close) {
        const rng = (c.high - c.low).toFixed(1);
        html += `<div class="trade">${sym} ${(c.time||'').slice(0,16)} O=${fmt(c.open,1)} H=${fmt(c.high,1)} L=${fmt(c.low,1)} C=${fmt(c.close,1)} R=${rng}</div>`;
      }
    }
    html += `</div>`;
  }

  // History expander
  if (hist.length > 0) {
    const totalPnl = hist.reduce((s,t) => s + (t.pnl||0), 0);
    const wins = hist.filter(t => (t.pnl||0) > 0).length;
    const wr = (wins/hist.length*100).toFixed(0);
    html += `<div class="section"><h3 class="expander" onclick="this.nextElementSibling.classList.toggle('open')">Historique (${hist.length} trades) &#x25BC;</h3>`;
    html += `<div class="expander-content"><div style="margin-bottom:8px">Total: ${hist.length} trades | WR: ${wr}% | PnL: $${pnlSign(totalPnl)}</div>`;
    for (const t of hist.slice(-50).reverse()) {
      const icon = (t.pnl||0) >= 0 ? '&#x1F7E2;' : '&#x1F534;';
      html += `<div class="trade">${icon} ${(t.time_close||'').slice(0,16)} ${t.symbol||''} ${t.comment||''} ${(t.dir||'').toUpperCase()} ${fmt(t.entry,2)}&rarr;${fmt(t.exit,2)} <span class="${pnlClass(t.pnl||0)}">$${pnlSign(t.pnl||0)}</span></div>`;
    }
    html += `</div></div>`;
  }

  html += `</div>`;
  return html;
}

async function refresh() {
  try {
    const r = await fetch(API + '/state');
    const data = await r.json();
    let html = '';
    for (const acc of ACCOUNTS) {
      html += renderAccount(acc, data[acc] || {});
    }
    document.getElementById('accounts').innerHTML = html;

    const accs = Object.keys(data);
    const statusParts = accs.map(a => {
      const lp = data[a]?.last_push;
      return `${a.toUpperCase()}: ${lp ? lp.slice(11,19) : 'N/A'}`;
    });
    document.getElementById('status').innerHTML = `<span style="color:#666">Last push: ${statusParts.join(' | ')}</span>`;
  } catch(e) {
    document.getElementById('status').innerHTML = `<span class="red">API error: ${e.message}</span>`;
  }
}

refresh();
setInterval(refresh, 1000);
</script>
</body></html>"""
