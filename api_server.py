"""
API Server + Dashboard — tourne sur le laptop avec ngrok.
Recoit les push des VPS, sert le dashboard HTML.

Usage:
  uvicorn api_server:app --host 0.0.0.0 --port 8001
  ngrok http --domain=unprolongable-nonexternalized-elizabet.ngrok-free.dev 8001
  → Dashboard: http://localhost:8001/
"""
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, Response
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


@app.get("/manifest.json")
async def manifest():
    return JSONResponse({
        "name": "HydraTrader Live",
        "short_name": "HydraTrader",
        "description": "Live trading dashboard MT5 multi-comptes",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "orientation": "any",
        "background_color": "#f5f6f8",
        "theme_color": "#1a1a2e",
        "icons": [
            {"src": "/icon.svg", "sizes": "192x192", "type": "image/svg+xml", "purpose": "any maskable"},
            {"src": "/icon.svg", "sizes": "512x512", "type": "image/svg+xml", "purpose": "any maskable"},
        ],
    })


@app.get("/icon.svg")
async def icon_svg():
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><rect width="512" height="512" rx="96" fill="#1a1a2e"/><text x="256" y="340" text-anchor="middle" font-family="Inter,sans-serif" font-size="320" font-weight="700" fill="#2563eb">H</text></svg>'
    return Response(content=svg, media_type="image/svg+xml")


@app.get("/sw.js")
async def service_worker():
    sw = """const CACHE='hydra-v1';
self.addEventListener('install',e=>{self.skipWaiting();});
self.addEventListener('activate',e=>{e.waitUntil(self.clients.claim());});
self.addEventListener('fetch',e=>{
  const u=new URL(e.request.url);
  if(u.pathname==='/state'||u.pathname.startsWith('/state/')||u.pathname==='/health'){
    e.respondWith(fetch(e.request).catch(()=>caches.match(e.request)));
    e.waitUntil(caches.open(CACHE).then(c=>fetch(e.request).then(r=>c.put(e.request,r.clone())).catch(()=>{})));
    return;
  }
  e.respondWith(caches.match(e.request).then(r=>r||fetch(e.request).then(resp=>{
    if(resp.ok)caches.open(CACHE).then(c=>c.put(e.request,resp.clone()));
    return resp;
  })));
});"""
    return Response(content=sw, media_type="application/javascript")


DASHBOARD_HTML = """<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<meta name="theme-color" content="#1a1a2e">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="HydraTrader">
<title>HydraTrader</title>
<link rel="manifest" href="/manifest.json">
<link rel="icon" type="image/svg+xml" href="/icon.svg">
<link rel="apple-touch-icon" href="/icon.svg">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  * { margin:0; padding:0; box-sizing:border-box; -webkit-tap-highlight-color:transparent; }
  body { background:#f5f6f8; color:#1a1a2e; font-family:'Inter',sans-serif; font-size:13px; padding-bottom:env(safe-area-inset-bottom); }

  /* Header */
  .header { background:#fff; border-bottom:1px solid #e8eaed; padding:10px 14px; position:sticky; top:0; z-index:10; }
  .header-row { display:flex; align-items:center; justify-content:space-between; gap:10px; }
  .header h1 { font-size:15px; font-weight:700; color:#1a1a2e; }
  .header h1 span { color:#2563eb; }
  .status { font-size:10px; color:#6b7280; display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
  .dot { width:7px; height:7px; border-radius:50%; display:inline-block; margin-right:3px; }
  .dot-green { background:#10b981; box-shadow:0 0 0 2px rgba(16,185,129,0.18); }
  .dot-gray { background:#d1d5db; }
  .dot-red { background:#dc2626; }

  /* Account selector */
  .acc-tabs { display:flex; gap:6px; margin-top:8px; }
  .acc-tab { flex:1; padding:8px 10px; border-radius:8px; background:#f5f6f8; border:1px solid #e8eaed; color:#6b7280; font-weight:600; font-size:12px; cursor:pointer; transition:all 0.15s; text-transform:uppercase; letter-spacing:0.5px; }
  .acc-tab:hover { background:#eef0f3; }
  .acc-tab.active { background:#1a1a2e; color:#fff; border-color:#1a1a2e; }
  .acc-tab .acc-pnl { display:block; font-size:10px; font-weight:500; margin-top:2px; }
  .acc-tab .acc-pnl.green { color:#10b981; }
  .acc-tab .acc-pnl.red { color:#fca5a5; }
  .acc-tab.active .acc-pnl { color:#fff; opacity:0.85; }

  /* Container */
  .main { padding:12px; max-width:1200px; margin:0 auto; }

  /* KPI strip */
  .kpis { display:grid; grid-template-columns:repeat(2,1fr); gap:8px; margin-bottom:12px; }
  .kpi { background:#fff; border:1px solid #e8eaed; border-radius:10px; padding:10px 12px; }
  .kpi .lbl { font-size:10px; color:#6b7280; text-transform:uppercase; letter-spacing:0.5px; font-weight:600; }
  .kpi .val { font-size:18px; font-weight:700; color:#1a1a2e; margin-top:2px; line-height:1.1; }
  .kpi .val.green { color:#059669; }
  .kpi .val.red { color:#dc2626; }
  .kpi .sub { font-size:10px; color:#9ca3af; margin-top:2px; }

  /* DD bar in kpi */
  .dd-bar { height:4px; background:#e8eaed; border-radius:2px; overflow:hidden; margin-top:5px; }
  .dd-bar .dd-fill { height:100%; background:linear-gradient(90deg,#10b981,#f59e0b,#dc2626); transition:width 0.3s; }

  /* Tabs */
  .tabs { display:flex; gap:0; margin-bottom:12px; background:#fff; border:1px solid #e8eaed; border-radius:10px; padding:4px; overflow-x:auto; -webkit-overflow-scrolling:touch; }
  .tab { flex:1; padding:8px 6px; background:transparent; border:none; color:#6b7280; font-weight:600; font-size:11px; cursor:pointer; border-radius:7px; white-space:nowrap; min-width:fit-content; transition:all 0.15s; text-transform:uppercase; letter-spacing:0.3px; }
  .tab:hover { color:#1a1a2e; }
  .tab.active { background:#2563eb; color:#fff; }
  .tab .badge { display:inline-block; background:rgba(0,0,0,0.1); padding:1px 5px; border-radius:6px; font-size:9px; margin-left:3px; }
  .tab.active .badge { background:rgba(255,255,255,0.25); }

  /* Tab content */
  .tab-content { display:none; }
  .tab-content.active { display:block; }

  /* Card */
  .card { background:#fff; border:1px solid #e8eaed; border-radius:10px; padding:12px; margin-bottom:10px; }
  .card-title { font-size:11px; color:#6b7280; text-transform:uppercase; letter-spacing:0.5px; font-weight:600; margin-bottom:8px; }
  .card-title .right { float:right; color:#1a1a2e; font-weight:500; text-transform:none; }
  .empty { color:#9ca3af; font-style:italic; padding:12px 4px; text-align:center; font-size:12px; }

  /* Trade card */
  .tcard { padding:10px; border:1px solid #e8eaed; border-radius:8px; margin-bottom:6px; background:#fafbfc; }
  .tcard-head { display:flex; justify-content:space-between; align-items:center; margin-bottom:5px; gap:8px; }
  .tcard-sym { font-weight:700; font-size:13px; }
  .tcard-strat { color:#2563eb; font-size:11px; font-weight:500; }
  .tcard-time { font-size:10px; color:#9ca3af; }
  .tcard-meta { display:flex; gap:10px; font-size:11px; color:#6b7280; flex-wrap:wrap; }
  .tcard-pnl { font-weight:700; font-size:13px; }
  .pnl-pos { color:#059669; }
  .pnl-neg { color:#dc2626; }
  .dir-long { color:#059669; font-weight:600; }
  .dir-short { color:#dc2626; font-weight:600; }
  .badge-r { display:inline-block; padding:2px 6px; border-radius:4px; font-size:11px; font-weight:600; }
  .badge-r.pos { background:#d1fae5; color:#059669; }
  .badge-r.neg { background:#fee2e2; color:#dc2626; }

  /* Position with progress */
  .pos-card { border-left:3px solid #2563eb; }
  .pos-card.short { border-left-color:#dc2626; }
  .pos-card.long { border-left-color:#059669; }
  .pos-bar { position:relative; height:24px; background:#f5f6f8; border-radius:5px; margin:8px 0 6px; overflow:hidden; }
  .pos-bar .zone-loss { position:absolute; height:100%; background:linear-gradient(90deg,#fee2e2,#fecaca); }
  .pos-bar .zone-profit { position:absolute; height:100%; background:linear-gradient(90deg,#d1fae5,#a7f3d0); }
  .pos-bar .marker { position:absolute; top:-2px; bottom:-2px; width:2px; background:#1a1a2e; }
  .pos-bar .label-sl { position:absolute; left:4px; top:50%; transform:translateY(-50%); font-size:10px; color:#dc2626; font-weight:600; }
  .pos-bar .label-tp { position:absolute; right:4px; top:50%; transform:translateY(-50%); font-size:10px; color:#059669; font-weight:600; }
  .pos-bar .label-entry { position:absolute; top:50%; transform:translate(-50%,-50%); font-size:10px; color:#6b7280; font-weight:500; background:rgba(255,255,255,0.9); padding:0 3px; border-radius:2px; }

  /* Sparkline */
  .spark { width:100%; height:80px; }
  .spark-axis { stroke:#e8eaed; stroke-width:1; }
  .spark-line { fill:none; stroke:#2563eb; stroke-width:2; }
  .spark-area { fill:url(#spark-grad); }
  .spark-dd { fill:none; stroke:#dc2626; stroke-width:1.5; stroke-dasharray:3,2; }

  /* Calendar heatmap */
  .calendar { display:grid; grid-template-columns:repeat(13,1fr); gap:3px; margin:8px 0; }
  .cal-cell { aspect-ratio:1; border-radius:4px; font-size:9px; display:flex; flex-direction:column; align-items:center; justify-content:center; color:#fff; font-weight:600; padding:2px; text-align:center; line-height:1.1; }
  .cal-cell.empty { background:#f0f1f3; color:#9ca3af; }
  .cal-cell .mo { font-size:8px; opacity:0.85; }
  .cal-cell .v { font-size:9px; }

  /* BT score */
  .score-banner { padding:14px; border-radius:10px; margin-bottom:10px; }
  .score-banner.good { background:linear-gradient(135deg,#d1fae5,#a7f3d0); border:1px solid #6ee7b7; }
  .score-banner.warn { background:linear-gradient(135deg,#fef3c7,#fde68a); border:1px solid #fcd34d; }
  .score-banner.bad { background:linear-gradient(135deg,#fee2e2,#fecaca); border:1px solid #fca5a5; }
  .score-banner h3 { font-size:13px; margin-bottom:4px; }
  .score-banner p { font-size:11px; color:#4b5563; }
  .score-banner .big { font-size:24px; font-weight:700; }

  /* Logs */
  .log-row { padding:6px 0; border-bottom:1px solid #f0f1f3; font-size:11px; display:flex; gap:8px; align-items:center; }
  .log-row:last-child { border-bottom:none; }
  .log-time { color:#9ca3af; min-width:42px; font-variant-numeric:tabular-nums; }
  .log-tag { padding:1px 6px; border-radius:3px; font-size:9px; font-weight:700; text-transform:uppercase; min-width:48px; text-align:center; }
  .log-tag.entry { background:#dbeafe; color:#1e40af; }
  .log-tag.exit-w { background:#d1fae5; color:#065f46; }
  .log-tag.exit-l { background:#fee2e2; color:#991b1b; }

  /* Compact list */
  .list { display:flex; flex-direction:column; gap:5px; }
  .footer { padding:10px 12px; text-align:center; font-size:10px; color:#9ca3af; }

  /* Desktop */
  @media (min-width: 768px) {
    body { font-size:13px; }
    .header { padding:14px 24px; }
    .header h1 { font-size:18px; }
    .header-row { gap:20px; }
    .acc-tabs { margin-top:0; max-width:280px; }
    .main { padding:18px 24px; }
    .kpis { grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:16px; }
    .kpi { padding:14px 16px; }
    .kpi .val { font-size:22px; }
    .tab { font-size:12px; padding:9px 12px; }
    .card { padding:16px; }
    .calendar { gap:5px; }
    .cal-cell { font-size:11px; }
    .cal-cell .mo { font-size:10px; }
    .cal-cell .v { font-size:11px; }
    .spark { height:120px; }
  }
  @media (min-width: 1024px) {
    .kpis { grid-template-columns:repeat(6,1fr); }
    .header h1 { font-size:20px; }
  }
</style>
</head><body>

<div class="header">
  <div class="header-row">
    <h1>Hydra<span>Trader</span></h1>
    <div class="status" id="status">Connexion...</div>
  </div>
  <div class="acc-tabs" id="acc-tabs"></div>
</div>

<div class="main">
  <section class="kpis" id="kpis"></section>
  <nav class="tabs" id="tabs"></nav>
  <div id="tab-today" class="tab-content active"></div>
  <div id="tab-open" class="tab-content"></div>
  <div id="tab-history" class="tab-content"></div>
  <div id="tab-bt" class="tab-content"></div>
  <div id="tab-logs" class="tab-content"></div>
</div>

<div class="footer">HydraTrader &mdash; refresh 1s</div>

<script>
const API='';
const ACCOUNTS=['5ers','ftmo'];
const MAX_DD={'5ers':4.0,'ftmo':10.0};
let SELECTED=localStorage.getItem('hydra-acc')||'ftmo';
let TAB=localStorage.getItem('hydra-tab')||'today';
let LAST={};

function fmt(n,d=0){if(n==null||isNaN(n))return'-';return Number(n).toLocaleString('en-US',{minimumFractionDigits:d,maximumFractionDigits:d});}
function fmtUsd(v,d=0){const s=v>=0?'+':'-';return s+'$'+fmt(Math.abs(v),d);}
function pnlCls(v){return v>=0?'pnl-pos':'pnl-neg';}
function dirCls(d){return d==='long'?'dir-long':'dir-short';}
function timeHM(s){return s?(s+'').slice(11,16):'';}
function dateD(s){return s?(s+'').slice(0,10):'';}
function escapeH(s){return (s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}

// === Calculs ===
function buildEquity(history,balance){
  const sorted=[...history].sort((a,b)=>(a.time_close||'').localeCompare(b.time_close||''));
  let cum=0,peak=balance,maxDdAbs=0;
  const startBal=balance-sorted.reduce((s,t)=>s+(t.pnl||0),0);
  cum=startBal; peak=startBal;
  const points=[{t:sorted[0]?.time_close||null,e:startBal,dd:0}];
  for(const t of sorted){
    cum+=t.pnl||0;
    if(cum>peak)peak=cum;
    const dd=peak>0?(cum-peak)/peak*100:0;
    if(dd<-Math.abs(maxDdAbs))maxDdAbs=Math.abs(dd);
    points.push({t:t.time_close,e:cum,dd:dd});
  }
  const curDd=peak>0?(balance-peak)/peak*100:0;
  return {points,peak,curDd,maxDd:maxDdAbs};
}

function monthlyPnl(history){
  const m={};
  for(const t of history){
    const k=(t.time_close||'').slice(0,7);
    if(!k)continue;
    m[k]=(m[k]||0)+(t.pnl||0);
  }
  return m;
}

// === Render: account tabs ===
function renderAccTabs(allData){
  let h='';
  for(const acc of ACCOUNTS){
    const d=allData[acc]||{};
    const s=d.state||{};
    const a=s.account_info||{};
    const pnl=s.today_pnl||0;
    const cls=pnl>=0?'green':'red';
    const active=acc===SELECTED?'active':'';
    h+=`<button class="acc-tab ${active}" onclick="selectAcc('${acc}')">${acc.toUpperCase()}<span class="acc-pnl ${cls}">${a.equity?'$'+fmt(a.equity):'--'} &middot; ${fmtUsd(pnl,0)}</span></button>`;
  }
  document.getElementById('acc-tabs').innerHTML=h;
}
function selectAcc(acc){SELECTED=acc;localStorage.setItem('hydra-acc',acc);render();}
function selectTab(t){TAB=t;localStorage.setItem('hydra-tab',t);render();}

// === Render: KPI strip ===
function renderKpis(data){
  if(!data||!data.state||!data.state.account_info){
    document.getElementById('kpis').innerHTML='<div class="kpi"><div class="lbl">En attente</div><div class="val">...</div></div>';
    return;
  }
  const s=data.state, a=s.account_info, pos=s.positions||[], hist=data.history||[];
  const todayPnl=s.today_pnl||0;
  const todayCnt=s.today_count||0;
  const eq=a.equity||0, bal=a.balance||0;
  const flot=pos.reduce((s,p)=>s+(p.pnl||0),0);
  const eqInfo=buildEquity(hist,bal);
  const ddCur=Math.abs(eqInfo.curDd);
  const ddMax=eqInfo.maxDd;
  const ddLimit=MAX_DD[SELECTED]||10;
  const ddPct=Math.min(100,ddCur/ddLimit*100);
  // PF/WR today
  const tt=s.today_trades||[];
  let pf=0,wr=0;
  if(tt.length>0){
    const gp=tt.filter(t=>(t.pnl||0)>0).reduce((s,t)=>s+t.pnl,0);
    const gl=tt.filter(t=>(t.pnl||0)<=0).reduce((s,t)=>s+Math.abs(t.pnl),0);
    pf=gl>0?gp/gl:(gp>0?99.99:0);
    wr=tt.filter(t=>(t.pnl||0)>0).length/tt.length*100;
  }

  let h='';
  h+=`<div class="kpi"><div class="lbl">Equity</div><div class="val">$${fmt(eq,0)}</div><div class="sub">Bal $${fmt(bal,0)}</div></div>`;
  h+=`<div class="kpi"><div class="lbl">PnL Jour</div><div class="val ${todayPnl>=0?'green':'red'}">${fmtUsd(todayPnl,2)}</div><div class="sub">${todayCnt} trades</div></div>`;
  h+=`<div class="kpi"><div class="lbl">Drawdown</div><div class="val ${ddCur>ddLimit*0.7?'red':''}">${ddCur.toFixed(2)}%</div><div class="dd-bar"><div class="dd-fill" style="width:${ddPct}%"></div></div><div class="sub">limite ${ddLimit}% &middot; max ${ddMax.toFixed(2)}%</div></div>`;
  h+=`<div class="kpi"><div class="lbl">Open</div><div class="val">${pos.length}</div><div class="sub ${flot>=0?'pnl-pos':'pnl-neg'}">${pos.length?fmtUsd(flot,2)+' flot':'-'}</div></div>`;
  h+=`<div class="kpi"><div class="lbl">PF Jour</div><div class="val ${pf>=1.5?'green':pf<1?'red':''}">${pf.toFixed(2)}</div><div class="sub">WR ${wr.toFixed(0)}%</div></div>`;
  h+=`<div class="kpi"><div class="lbl">Total Hist</div><div class="val">${hist.length}</div><div class="sub">${eqInfo.peak>0?'peak $'+fmt(eqInfo.peak,0):'-'}</div></div>`;
  document.getElementById('kpis').innerHTML=h;
}

// === Render: tab nav ===
function renderTabs(data){
  const s=data?.state||{};
  const pos=s.positions||[];
  const tt=s.today_trades||[];
  const hist=data?.history||[];
  const btc=data?.bt_compare||{};
  let btCount=0; for(const k of Object.keys(btc))btCount+=(btc[k]?.rows||[]).length;
  const tabs=[
    {id:'today',label:'Jour',n:tt.length},
    {id:'open',label:'Open',n:pos.length},
    {id:'history',label:'Histo',n:hist.length},
    {id:'bt',label:'BT vs LV',n:btCount},
    {id:'logs',label:'Logs',n:pos.length+hist.length},
  ];
  let h='';
  for(const t of tabs){
    h+=`<button class="tab ${t.id===TAB?'active':''}" onclick="selectTab('${t.id}')">${t.label}${t.n?'<span class="badge">'+t.n+'</span>':''}</button>`;
  }
  document.getElementById('tabs').innerHTML=h;
}

// === Sparkline ===
function sparkline(points,key,height,colorLine,colorArea){
  if(!points||points.length<2)return '<div class="empty">Pas assez de donnees</div>';
  const w=800,h=height||80,pad=4;
  const vals=points.map(p=>p[key]);
  const min=Math.min(...vals),max=Math.max(...vals);
  const span=max-min||1;
  const dx=(w-pad*2)/(points.length-1);
  let d='',a='';
  for(let i=0;i<points.length;i++){
    const x=pad+i*dx;
    const y=h-pad-(vals[i]-min)/span*(h-pad*2);
    d+=(i===0?'M':'L')+x+','+y+' ';
    a+=(i===0?'M'+x+','+(h-pad)+' L':'L')+x+','+y+' ';
  }
  a+='L'+(pad+(points.length-1)*dx)+','+(h-pad)+' Z';
  const grad=`<defs><linearGradient id="spark-grad" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stop-color="${colorLine}" stop-opacity="0.3"/><stop offset="100%" stop-color="${colorLine}" stop-opacity="0"/></linearGradient></defs>`;
  return `<svg class="spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">${grad}<path d="${a}" fill="url(#spark-grad)"/><path class="spark-line" d="${d}" stroke="${colorLine}"/></svg>`;
}

// === Render: TODAY ===
function renderToday(data){
  const root=document.getElementById('tab-today');
  if(!data||!data.state){root.innerHTML='<div class="empty">Pas de donnees</div>';return;}
  const s=data.state, tt=s.today_trades||[], hist=data.history||[], a=s.account_info||{};
  const eqInfo=buildEquity(hist,a.balance||0);
  const recent=eqInfo.points.slice(-100);
  let h='';
  h+=`<div class="card"><div class="card-title">Equity (${recent.length} pts)<span class="right">$${fmt(a.equity,0)}</span></div>`;
  h+=sparkline(recent,'e',null,'#2563eb');
  h+='</div>';
  h+=`<div class="card"><div class="card-title">Trades aujourd'hui<span class="right">${tt.length} trades &middot; ${fmtUsd(s.today_pnl||0,2)}</span></div>`;
  if(tt.length===0)h+='<div class="empty">Aucun trade aujourd\\'hui</div>';
  else{
    const sorted=[...tt].sort((a,b)=>(b.time_open||'').localeCompare(a.time_open||''));
    h+='<div class="list">';
    for(const t of sorted){
      const pnl=t.pnl||0;
      h+=`<div class="tcard">
        <div class="tcard-head">
          <div><span class="tcard-sym">${escapeH(t.symbol)}</span> <span class="tcard-strat">${escapeH(t.comment)}</span></div>
          <span class="tcard-pnl ${pnlCls(pnl)}">${fmtUsd(pnl,2)}</span>
        </div>
        <div class="tcard-meta">
          <span class="${dirCls(t.dir)}">${(t.dir||'').toUpperCase()}</span>
          <span>${fmt(t.entry,2)} &rarr; ${fmt(t.exit,2)}</span>
          <span>${t.volume} lots</span>
          <span class="tcard-time">${timeHM(t.time_open)}-${timeHM(t.time_close)}</span>
        </div>
      </div>`;
    }
    h+='</div>';
  }
  h+='</div>';
  root.innerHTML=h;
}

// === Render: OPEN positions ===
function renderOpen(data){
  const root=document.getElementById('tab-open');
  if(!data||!data.state){root.innerHTML='<div class="empty">Pas de donnees</div>';return;}
  const pos=data.state.positions||[];
  let h='';
  if(pos.length===0){h='<div class="card"><div class="empty">Aucune position ouverte</div></div>';}
  else{
    const flot=pos.reduce((s,p)=>s+(p.pnl||0),0);
    h+=`<div class="card"><div class="card-title">${pos.length} position(s) ouverte(s)<span class="right ${flot>=0?'pnl-pos':'pnl-neg'}">${fmtUsd(flot,2)} flot</span></div>`;
    h+='<div class="list">';
    for(const p of pos){
      const isLong=p.dir==='long';
      const cls=isLong?'long':'short';
      const sl=p.sl||p.entry;
      const tp=p.tp||0;
      // Range: SL ... entry ... TP (long) or TP ... entry ... SL (short)
      let lo,hi,curPos;
      if(isLong){
        lo=sl; hi=tp>0?tp:p.entry+(p.entry-sl);
        curPos=hi>lo?(p.current-lo)/(hi-lo)*100:50;
      } else {
        lo=tp>0?tp:p.entry-(sl-p.entry); hi=sl;
        curPos=hi>lo?(p.current-lo)/(hi-lo)*100:50;
      }
      curPos=Math.max(2,Math.min(98,curPos));
      const entryPos=hi>lo?((p.entry-lo)/(hi-lo))*100:50;
      const lossSide=isLong?0:entryPos;
      const lossWidth=isLong?entryPos:(100-entryPos);
      const profitSide=isLong?entryPos:0;
      const profitWidth=isLong?(100-entryPos):entryPos;
      const pnl=p.pnl||0;
      const tOpen=p.time_open||'';
      const elapsed=tOpen?Math.round((Date.now()-new Date(tOpen).getTime())/60000):0;
      h+=`<div class="tcard pos-card ${cls}">
        <div class="tcard-head">
          <div><span class="tcard-sym">${escapeH(p.symbol)}</span> <span class="tcard-strat">${escapeH(p.comment)}</span> <span class="${dirCls(p.dir)}">${(p.dir||'').toUpperCase()}</span></div>
          <span class="tcard-pnl ${pnlCls(pnl)}">${fmtUsd(pnl,2)}</span>
        </div>
        <div class="pos-bar">
          <div class="zone-loss" style="left:${lossSide}%;width:${lossWidth}%"></div>
          <div class="zone-profit" style="left:${profitSide}%;width:${profitWidth}%"></div>
          <div class="marker" style="left:${curPos}%"></div>
          <span class="label-sl">SL ${fmt(sl,2)}</span>
          <span class="label-entry" style="left:${entryPos}%">${fmt(p.entry,2)}</span>
          ${tp>0?`<span class="label-tp">TP ${fmt(tp,2)}</span>`:''}
        </div>
        <div class="tcard-meta">
          <span>Now ${fmt(p.current,2)}</span>
          <span>${p.volume} lots</span>
          <span class="tcard-time">${elapsed}m elapsed</span>
        </div>
      </div>`;
    }
    h+='</div></div>';
  }
  root.innerHTML=h;
}

// === Render: HISTORY ===
function renderHistory(data){
  const root=document.getElementById('tab-history');
  if(!data){root.innerHTML='<div class="empty">Pas de donnees</div>';return;}
  const hist=data.history||[];
  const a=data.state?.account_info||{};
  const eqInfo=buildEquity(hist,a.balance||0);
  let h='';

  // Calendar
  const monthly=monthlyPnl(hist);
  const months=Object.keys(monthly).sort().slice(-13);
  if(months.length>0){
    const maxAbs=Math.max(...months.map(m=>Math.abs(monthly[m])))||1;
    h+=`<div class="card"><div class="card-title">Calendrier mensuel<span class="right">${months.filter(m=>monthly[m]>0).length}/${months.length} M+</span></div>`;
    h+='<div class="calendar">';
    for(const m of months){
      const v=monthly[m]||0;
      const intensity=Math.min(1,Math.abs(v)/maxAbs);
      const bg=v>=0?`rgba(5,150,105,${0.3+intensity*0.7})`:`rgba(220,38,38,${0.3+intensity*0.7})`;
      const lbl=m.slice(5);
      h+=`<div class="cal-cell" style="background:${bg}"><span class="mo">${m.slice(2,4)}/${lbl}</span><span class="v">${fmtUsd(v,0)}</span></div>`;
    }
    h+='</div></div>';
  }

  // Equity full + DD chart
  if(eqInfo.points.length>1){
    h+=`<div class="card"><div class="card-title">Equity all-time<span class="right">peak $${fmt(eqInfo.peak,0)} &middot; max DD ${eqInfo.maxDd.toFixed(2)}%</span></div>`;
    h+=sparkline(eqInfo.points,'e',null,'#2563eb');
    h+='</div>';
  }

  // Recent trades
  h+=`<div class="card"><div class="card-title">${hist.length} trades historique</div>`;
  if(hist.length===0){h+='<div class="empty">Aucun trade</div>';}
  else{
    const sorted=[...hist].sort((a,b)=>(b.time_close||'').localeCompare(a.time_close||'')).slice(0,40);
    h+='<div class="list">';
    for(const t of sorted){
      const pnl=t.pnl||0;
      h+=`<div class="tcard">
        <div class="tcard-head">
          <div><span class="tcard-sym">${escapeH(t.symbol)}</span> <span class="tcard-strat">${escapeH(t.comment)}</span></div>
          <span class="tcard-pnl ${pnlCls(pnl)}">${fmtUsd(pnl,2)}</span>
        </div>
        <div class="tcard-meta">
          <span class="${dirCls(t.dir)}">${(t.dir||'').toUpperCase()}</span>
          <span>${fmt(t.entry,2)} &rarr; ${fmt(t.exit,2)}</span>
          <span class="tcard-time">${dateD(t.time_close)} ${timeHM(t.time_close)}</span>
        </div>
      </div>`;
    }
    h+='</div>';
  }
  h+='</div>';
  root.innerHTML=h;
}

// === Render: BT vs LV ===
function renderBT(data){
  const root=document.getElementById('tab-bt');
  const btc=data?.bt_compare||{};
  const syms=Object.keys(btc);
  if(syms.length===0){root.innerHTML='<div class="card"><div class="empty">Pas de comparaison BT disponible</div></div>';return;}

  // Score: count rows with both BT and LV, compute avg |delta|
  let matched=0,nLv=0,nBt=0,sumAbsDelta=0,topDiv=[];
  for(const sym of syms){
    const rows=btc[sym]?.rows||[];
    for(const row of rows){
      if(row.bt&&row.lv){
        matched++;
        const d=row.delta||0;
        sumAbsDelta+=Math.abs(d);
        topDiv.push({sym,strat:row.strat,delta:d,bt:row.bt.pnl_r,lv:row.lv.pnl_r});
      }
      if(row.bt)nBt++;
      if(row.lv)nLv++;
    }
  }
  const avgPenalty=matched>0?sumAbsDelta/matched:0;
  const align=nBt>0?(matched/nBt*100):0;
  let scoreCls='good',scoreLbl='Aligne';
  if(avgPenalty>0.3){scoreCls='bad';scoreLbl='Divergent';}
  else if(avgPenalty>0.1){scoreCls='warn';scoreLbl='Surveille';}

  let h='';
  h+=`<div class="score-banner ${scoreCls}">
    <h3>${scoreLbl} BT vs Live</h3>
    <div class="big">${align.toFixed(0)}%</div>
    <p>${matched} matches sur ${nBt} BT &middot; penalite moy <b>${avgPenalty.toFixed(3)}R</b> &middot; LV-only ${nLv-matched} &middot; BT-only ${nBt-matched}</p>
  </div>`;

  topDiv.sort((a,b)=>Math.abs(b.delta)-Math.abs(a.delta));
  const top=topDiv.slice(0,5);
  if(top.length>0){
    h+=`<div class="card"><div class="card-title">Top divergences du jour</div><div class="list">`;
    for(const t of top){
      const cls=t.delta>=0?'pnl-pos':'pnl-neg';
      h+=`<div class="tcard">
        <div class="tcard-head">
          <div><span class="tcard-sym">${escapeH(t.sym)}</span> <span class="tcard-strat">${escapeH(t.strat)}</span></div>
          <span class="badge-r ${t.delta>=0?'pos':'neg'}">${t.delta>=0?'+':''}${t.delta.toFixed(2)}R</span>
        </div>
        <div class="tcard-meta">
          <span>BT <b class="${t.bt>=0?'pnl-pos':'pnl-neg'}">${t.bt>=0?'+':''}${t.bt.toFixed(2)}R</b></span>
          <span>LV <b class="${t.lv>=0?'pnl-pos':'pnl-neg'}">${t.lv>=0?'+':''}${t.lv.toFixed(2)}R</b></span>
        </div>
      </div>`;
    }
    h+='</div></div>';
  }

  // Per-instrument summary
  h+='<div class="card"><div class="card-title">Detail par instrument</div><div class="list">';
  for(const sym of syms.sort()){
    const rows=btc[sym]?.rows||[];
    const matchedRows=rows.filter(r=>r.bt&&r.lv);
    if(rows.length===0)continue;
    const sumBt=rows.reduce((s,r)=>s+(r.bt?.pnl_r||0),0);
    const sumLv=rows.reduce((s,r)=>s+(r.lv?.pnl_r||0),0);
    const sumDelta=matchedRows.reduce((s,r)=>s+(r.delta||0),0);
    const atr=btc[sym].atr||0;
    h+=`<div class="tcard">
      <div class="tcard-head">
        <span class="tcard-sym">${escapeH(sym)}</span>
        <span class="tcard-time">${rows.length} strats &middot; ATR ${fmt(atr,2)}</span>
      </div>
      <div class="tcard-meta">
        <span>BT <b class="${sumBt>=0?'pnl-pos':'pnl-neg'}">${sumBt>=0?'+':''}${sumBt.toFixed(2)}R</b></span>
        <span>LV <b class="${sumLv>=0?'pnl-pos':'pnl-neg'}">${sumLv>=0?'+':''}${sumLv.toFixed(2)}R</b></span>
        <span>&Delta; <b class="${sumDelta>=0?'pnl-pos':'pnl-neg'}">${sumDelta>=0?'+':''}${sumDelta.toFixed(2)}R</b></span>
      </div>
    </div>`;
  }
  h+='</div></div>';

  root.innerHTML=h;
}

// === Render: LOGS (entries from positions + exits from history) ===
function renderLogs(data){
  const root=document.getElementById('tab-logs');
  if(!data||!data.state){root.innerHTML='<div class="empty">Pas de donnees</div>';return;}
  const pos=data.state.positions||[];
  const hist=data.history||[];
  const events=[];
  for(const p of pos){
    events.push({t:p.time_open,type:'entry',sym:p.symbol,strat:p.comment,dir:p.dir,pnl:p.pnl,extra:'OPEN'});
  }
  for(const t of hist.slice(-100)){
    events.push({t:t.time_close,type:(t.pnl||0)>=0?'exit-w':'exit-l',sym:t.symbol,strat:t.comment,dir:t.dir,pnl:t.pnl,extra:(t.pnl>=0?'WIN ':'LOSS ')+fmtUsd(t.pnl,2)});
  }
  events.sort((a,b)=>(b.t||'').localeCompare(a.t||''));
  let h='<div class="card"><div class="card-title">Evenements recents (' + events.length + ')</div>';
  if(events.length===0){h+='<div class="empty">Aucun evenement</div>';}
  else{
    for(const e of events.slice(0,80)){
      const lbl=e.type==='entry'?'ENTRY':e.type==='exit-w'?'WIN':'LOSS';
      h+=`<div class="log-row">
        <span class="log-time">${timeHM(e.t)}</span>
        <span class="log-tag ${e.type}">${lbl}</span>
        <span class="tcard-sym">${escapeH(e.sym)}</span>
        <span class="tcard-strat">${escapeH(e.strat)}</span>
        <span class="${dirCls(e.dir)}">${(e.dir||'').toUpperCase()}</span>
        <span style="margin-left:auto;font-size:11px;color:#6b7280">${escapeH(e.extra)}</span>
      </div>`;
    }
  }
  h+='</div>';
  root.innerHTML=h;
}

// === Main render ===
function render(){
  // Account tabs
  renderAccTabs(LAST);
  const data=LAST[SELECTED]||{};
  renderKpis(data);
  renderTabs(data);
  // Show active tab
  document.querySelectorAll('.tab-content').forEach(el=>el.classList.remove('active'));
  document.getElementById('tab-'+TAB).classList.add('active');
  // Render selected tab
  if(TAB==='today')renderToday(data);
  else if(TAB==='open')renderOpen(data);
  else if(TAB==='history')renderHistory(data);
  else if(TAB==='bt')renderBT(data);
  else if(TAB==='logs')renderLogs(data);
}

async function refresh(){
  try{
    const r=await fetch(API+'/state');
    const data=await r.json();
    LAST=data;
    render();
    // Status
    const parts=ACCOUNTS.map(a=>{
      const lp=data[a]?.last_push;
      const ago=lp?Math.round((Date.now()-new Date(lp).getTime())/1000):999;
      const dot=ago<10?'dot-green':ago<60?'dot-gray':'dot-red';
      return `<span><span class="dot ${dot}"></span>${a.toUpperCase()} ${ago<999?ago+'s':'off'}</span>`;
    });
    document.getElementById('status').innerHTML=parts.join('');
  }catch(e){
    document.getElementById('status').innerHTML='<span style="color:#dc2626">API error</span>';
  }
}

refresh();
setInterval(refresh,1000);

if('serviceWorker' in navigator){
  navigator.serviceWorker.register('/sw.js').catch(e=>console.warn('SW reg failed',e));
}
</script>
</body></html>"""
