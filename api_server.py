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

app = FastAPI(title="HydraTrader API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── STATE en memoire ──
_lock = threading.Lock()
_state = {}  # account -> {state, history, last_push}


@app.post("/push/{account}")
async def push(account: str, data: dict):
    """VPS pousse l'etat MT5 chaque seconde."""
    with _lock:
        if account not in _state:
            _state[account] = {'state': {}, 'history': [], 'bt_compare': {}, 'last_push': None}
        _state[account]['state'] = data.get('state', {})
        _state[account]['last_push'] = datetime.now(timezone.utc).isoformat()
        if 'history' in data and data['history']:
            _state[account]['history'] = data['history']
        if 'bt_compare' in data and data['bt_compare']:
            _state[account]['bt_compare'] = data['bt_compare']
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
                'bt_compare': d.get('bt_compare', {}),
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
<title>HydraTrader Live</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { background:#f5f6f8; color:#1a1a2e; font-family:'Inter',sans-serif; font-size:13px; }

  /* Header */
  .header { background:#fff; border-bottom:2px solid #e8eaed; padding:16px 32px; display:flex; align-items:center; justify-content:space-between; }
  .header h1 { font-size:20px; font-weight:700; color:#1a1a2e; }
  .header h1 span { color:#2563eb; }
  .status-bar { display:flex; gap:16px; align-items:center; font-size:12px; color:#6b7280; }
  .status-dot { width:8px; height:8px; border-radius:50%; display:inline-block; margin-right:4px; }
  .dot-green { background:#10b981; }
  .dot-gray { background:#d1d5db; }

  /* Layout */
  .container { padding:24px 32px; }
  .grid { display:grid; grid-template-columns:1fr 1fr; gap:24px; }

  /* Cards */
  .card { background:#fff; border-radius:12px; padding:20px 24px; box-shadow:0 1px 3px rgba(0,0,0,0.06); border:1px solid #e8eaed; }
  .card-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; }
  .card-header h2 { font-size:16px; font-weight:700; color:#1a1a2e; text-transform:uppercase; letter-spacing:1px; }
  .card-header .broker { font-size:11px; color:#6b7280; font-weight:400; }
  .card-header .live-dot { font-size:11px; color:#10b981; }
  .updated { font-size:11px; color:#9ca3af; margin-bottom:16px; }

  /* Metrics */
  .metrics { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:20px; }
  .metric { background:#f9fafb; border-radius:8px; padding:12px; border:1px solid #f0f1f3; }
  .metric .label { font-size:11px; color:#6b7280; font-weight:500; text-transform:uppercase; letter-spacing:0.5px; }
  .metric .value { font-size:22px; font-weight:700; margin-top:4px; color:#1a1a2e; }
  .metric .value.green { color:#059669; }
  .metric .value.red { color:#dc2626; }

  /* Sections */
  .section { margin-top:16px; }
  .section-title { font-size:12px; font-weight:600; color:#6b7280; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:10px; padding-bottom:6px; border-bottom:1px solid #f0f1f3; }

  /* Positions table */
  table { width:100%; border-collapse:collapse; font-size:12px; }
  th { text-align:left; color:#6b7280; font-weight:600; font-size:11px; text-transform:uppercase; letter-spacing:0.5px; padding:6px 8px; border-bottom:2px solid #e8eaed; }
  td { padding:8px; border-bottom:1px solid #f0f1f3; vertical-align:middle; }
  tr:hover { background:#f9fafb; }
  .dir-long { color:#059669; font-weight:600; }
  .dir-short { color:#dc2626; font-weight:600; }
  .pnl-pos { color:#059669; font-weight:600; }
  .pnl-neg { color:#dc2626; font-weight:600; }
  .strat-name { color:#2563eb; font-weight:500; }
  .sym { font-weight:600; }

  /* No data */
  .empty { color:#9ca3af; font-style:italic; padding:12px 0; }

  /* Candle bar */
  .candle-row { display:flex; justify-content:space-between; padding:4px 0; font-size:12px; color:#4b5563; border-bottom:1px solid #f9fafb; }
  .candle-sym { font-weight:600; color:#1a1a2e; min-width:80px; }
  .candle-r { font-weight:600; }

  /* Expander */
  .expander-btn { cursor:pointer; user-select:none; color:#2563eb; font-weight:500; }
  .expander-btn:hover { text-decoration:underline; }
  .expander-body { display:none; margin-top:8px; max-height:400px; overflow-y:auto; }
  .expander-body.open { display:block; }
  .hist-summary { background:#f0f7ff; border-radius:6px; padding:8px 12px; margin-bottom:8px; font-size:12px; color:#1e40af; }

  /* Footer */
  .footer { padding:12px 32px; text-align:center; font-size:11px; color:#9ca3af; }
</style>
</head><body>

<div class="header">
  <h1>Hydra<span>Trader</span> &mdash; Live</h1>
  <div class="status-bar" id="statusbar">Connexion...</div>
</div>

<div class="container">
  <div class="grid" id="accounts"></div>
</div>

<div class="footer">HydraTrader Trading System &mdash; refresh 1s</div>

<script>
const API = '';
const ACCOUNTS = ['5ers', 'ftmo'];

function fmt(n,d=0){if(n==null)return'-';return Number(n).toLocaleString('en-US',{minimumFractionDigits:d,maximumFractionDigits:d});}
function pnl$(v){return v>=0?'<span class="pnl-pos">+$'+fmt(v,2)+'</span>':'<span class="pnl-neg">-$'+fmt(Math.abs(v),2)+'</span>';}
function dirClass(d){return d==='long'?'dir-long':'dir-short';}
function timeShort(s){return s?(s+'').slice(11,16):'';}

function renderAccount(acc, data) {
  if(!data||!data.state||!data.state.account_info){
    return '<div class="card"><div class="card-header"><h2>'+acc.toUpperCase()+'</h2></div><div class="empty">En attente de donnees du VPS...</div></div>';
  }
  const s=data.state, a=s.account_info||{}, pos=s.positions||[], trades=s.today_trades||[], candles=s.candles||{}, hist=data.history||[];
  let h='<div class="card">';

  // Header
  h+='<div class="card-header"><h2>'+acc.toUpperCase()+' <span class="broker">'+( s.broker||'')+'</span></h2>';
  h+='<span class="live-dot"><span class="status-dot dot-green"></span> Live</span></div>';
  h+='<div class="updated">'+timeShort(s.ts)+' UTC</div>';

  // Metrics
  h+='<div class="metrics">';
  h+='<div class="metric"><div class="label">Balance</div><div class="value">$'+fmt(a.balance)+'</div></div>';
  h+='<div class="metric"><div class="label">Equity</div><div class="value">$'+fmt(a.equity)+'</div></div>';
  const pnlCls=(s.today_pnl||0)>=0?'green':'red';
  h+='<div class="metric"><div class="label">PnL Jour</div><div class="value '+pnlCls+'">$'+(s.today_pnl>=0?'+':'')+fmt(s.today_pnl,2)+'</div></div>';
  h+='<div class="metric"><div class="label">Trades</div><div class="value">'+(s.today_count||0)+'</div></div>';
  h+='</div>';

  // Positions
  h+='<div class="section"><div class="section-title">Positions ouvertes ('+pos.length+')</div>';
  if(pos.length===0){h+='<div class="empty">Aucune position ouverte</div>';}
  else{
    h+='<table><tr><th>Sym</th><th>Strat</th><th>Dir</th><th>Entry</th><th>Current</th><th>SL</th><th>PnL</th><th>Lots</th></tr>';
    for(const p of pos){
      h+='<tr><td class="sym">'+p.symbol+'</td><td class="strat-name">'+(p.comment||'')+'</td>';
      h+='<td class="'+dirClass(p.dir)+'">'+p.dir.toUpperCase()+'</td>';
      h+='<td>'+fmt(p.entry,2)+'</td><td>'+fmt(p.current,2)+'</td><td>'+fmt(p.sl,2)+'</td>';
      h+='<td>'+pnl$(p.pnl)+'</td><td>'+p.volume+'</td></tr>';
    }
    h+='</table>';
  }
  h+='</div>';

  // Trades du jour: compare BT vs Live (valeurs pre-calculees par le pusher)
  const btc=data.bt_compare||{};
  const btSyms=Object.keys(btc);
  let hasRows=false;
  for(const sym of btSyms){if((btc[sym]||{}).rows&&btc[sym].rows.length>0) hasRows=true;}
  if(hasRows){
    let totalBtR=0,totalLvR=0,totalDelta=0;
    for(const sym of btSyms){
      const info=btc[sym]||{}; const rows=(info.rows||[]).sort((a,b)=>a.strat.localeCompare(b.strat));
      h+='<div class="section"><div class="section-title">'+sym+' &mdash; BT vs Live (ATR='+fmt(info.atr,2)+')</div>';
      h+='<table><tr><th>Strat</th><th>BT Dir</th><th>BT Entry</th><th>BT Exit</th><th>BT R</th><th>LV Dir</th><th>LV Entry</th><th>LV Exit</th><th>LV R</th><th>LV $</th><th>Delta</th></tr>';
      for(const row of rows){
        const bt=row.bt; const lv=row.lv;
        const triggered=bt||lv;
        const rs=triggered?'':'style="color:#c0c0c0"';
        let bD='',bE='',bX='',bR='',lD='',lE='',lX='',lR='',dl='';
        if(bt){
          bD='<span class="'+dirClass(bt.dir)+'">'+bt.dir.toUpperCase()+'</span>';
          bE=fmt(bt.entry,2); bX=fmt(bt.exit,2);
          const rv=bt.pnl_r||0; totalBtR+=rv;
          bR='<span class="'+(rv>=0?'pnl-pos':'pnl-neg')+'">'+(rv>=0?'+':'')+rv.toFixed(2)+'R</span>';
        }
        let lUsd='';
        if(lv){
          lD='<span class="'+dirClass(lv.dir)+'">'+lv.dir.toUpperCase()+'</span>';
          lE=fmt(lv.entry,2); lX=fmt(lv.exit,2);
          const rv=lv.pnl_r||0; totalLvR+=rv;
          lR='<span class="'+(rv>=0?'pnl-pos':'pnl-neg')+'">'+(rv>=0?'+':'')+rv.toFixed(2)+'R</span>';
          const usd=lv.pnl_usd||0;
          lUsd='<span class="'+(usd>=0?'pnl-pos':'pnl-neg')+'">$'+(usd>=0?'+':'')+fmt(usd,2)+'</span>';
        }
        if(row.delta!=null){
          const d=row.delta; totalDelta+=d;
          dl='<span class="'+(d>=0?'pnl-pos':'pnl-neg')+'">'+(d>=0?'+':'')+d.toFixed(2)+'R</span>';
        }
        h+='<tr '+rs+'><td class="strat-name">'+row.strat+'</td>';
        h+='<td>'+bD+'</td><td>'+bE+'</td><td>'+bX+'</td><td>'+bR+'</td>';
        h+='<td>'+lD+'</td><td>'+lE+'</td><td>'+lX+'</td><td>'+lR+'</td><td>'+lUsd+'</td><td>'+dl+'</td></tr>';
      }
      // Total $ from today_trades
      const totalUsd=trades.reduce((s,t)=>s+(t.pnl||0),0);
      h+='<tr style="font-weight:700;border-top:2px solid #e8eaed"><td>TOTAL</td><td></td><td></td><td></td>';
      h+='<td><span class="'+(totalBtR>=0?'pnl-pos':'pnl-neg')+'">'+(totalBtR>=0?'+':'')+totalBtR.toFixed(2)+'R</span></td>';
      h+='<td></td><td></td><td></td>';
      h+='<td><span class="'+(totalLvR>=0?'pnl-pos':'pnl-neg')+'">'+(totalLvR>=0?'+':'')+totalLvR.toFixed(2)+'R</span></td>';
      h+='<td><span class="'+(totalUsd>=0?'pnl-pos':'pnl-neg')+'">$'+(totalUsd>=0?'+':'')+fmt(totalUsd,2)+'</span></td>';
      h+='<td><span class="'+(totalDelta>=0?'pnl-pos':'pnl-neg')+'">'+(totalDelta>=0?'+':'')+totalDelta.toFixed(2)+'R</span></td></tr>';
      h+='</table></div>';
    }
  }

  // Candles
  const syms=Object.keys(candles).filter(s=>candles[s]&&candles[s].close);
  if(syms.length>0){
    h+='<div class="section"><div class="section-title">Dernieres bougies</div>';
    for(const sym of syms){
      const c=candles[sym]; const rng=(c.high-c.low).toFixed(1);
      h+='<div class="candle-row"><span class="candle-sym">'+sym+'</span>';
      h+='<span>'+timeShort(c.time)+'</span>';
      h+='<span>O '+fmt(c.open,1)+'</span><span>H '+fmt(c.high,1)+'</span><span>L '+fmt(c.low,1)+'</span><span>C '+fmt(c.close,1)+'</span>';
      h+='<span class="candle-r">R '+rng+'</span></div>';
    }
    h+='</div>';
  }

  // History
  if(hist.length>0){
    const tp=hist.reduce((s,t)=>s+(t.pnl||0),0);
    const w=hist.filter(t=>(t.pnl||0)>0).length;
    const wr=(w/hist.length*100).toFixed(0);
    const hid="hist-"+acc;
    h+='<div class="section"><div class="section-title expander-btn" onclick="document.getElementById(&quot;'+hid+'&quot;).classList.toggle(&quot;open&quot;)">Historique ('+hist.length+' trades)</div>';
    h+='<div id="'+hid+'" class="expander-body">';
    h+='<div class="hist-summary">'+hist.length+' trades &bull; WR '+wr+'% &bull; PnL $'+(tp>=0?'+':'')+fmt(tp,2)+'</div>';
    h+='<table><tr><th>Date</th><th>Sym</th><th>Strat</th><th>Dir</th><th>Entry</th><th>Exit</th><th>PnL</th></tr>';
    for(const t of hist.slice(-50).reverse()){
      h+='<tr><td>'+timeShort(t.time_close)+'</td><td class="sym">'+(t.symbol||'')+'</td><td class="strat-name">'+(t.comment||'')+'</td>';
      h+='<td class="'+dirClass(t.dir||'')+'">'+((t.dir||'').toUpperCase())+'</td>';
      h+='<td>'+fmt(t.entry,2)+'</td><td>'+fmt(t.exit,2)+'</td>';
      h+='<td>'+pnl$(t.pnl||0)+'</td></tr>';
    }
    h+='</table></div></div>';
  }

  h+='</div>';
  return h;
}

async function refresh(){
  try{
    const r=await fetch(API+'/state');
    const data=await r.json();
    let html='';
    for(const acc of ACCOUNTS) html+=renderAccount(acc,data[acc]||{});
    document.getElementById('accounts').innerHTML=html;

    const parts=Object.keys(data).map(a=>{
      const lp=data[a]?.last_push;
      const ago=lp?Math.round((Date.now()-new Date(lp).getTime())/1000):999;
      const dot=ago<10?'dot-green':'dot-gray';
      return '<span class="status-dot '+dot+'"></span> '+a.toUpperCase()+' '+( ago<999?ago+'s ago':'offline');
    });
    document.getElementById('statusbar').innerHTML=parts.join(' &nbsp;&bull;&nbsp; ');
  }catch(e){
    document.getElementById('statusbar').innerHTML='<span style="color:#dc2626">API error</span>';
  }
}

refresh();
setInterval(refresh,1000);
</script>
</body></html>"""
