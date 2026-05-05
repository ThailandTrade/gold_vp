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
    sw = """const CACHE='hydra-v3';
self.addEventListener('install',e=>{self.skipWaiting();});
self.addEventListener('activate',e=>{
  e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));
});
self.addEventListener('fetch',e=>{
  const u=new URL(e.request.url);
  // / and /state always network-first (HTML and live data)
  if(u.pathname==='/'||u.pathname==='/state'||u.pathname.startsWith('/state/')||u.pathname==='/health'){
    e.respondWith(fetch(e.request).then(r=>{
      const c=r.clone();
      caches.open(CACHE).then(ca=>ca.put(e.request,c)).catch(()=>{});
      return r;
    }).catch(()=>caches.match(e.request)));
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

  /* Period selector */
  .period-tabs { display:flex; gap:5px; margin-top:8px; flex-wrap:wrap; }
  .period-chip { padding:5px 10px; border-radius:6px; background:#f5f6f8; border:1px solid #e8eaed; color:#6b7280; font-size:11px; font-weight:600; cursor:pointer; transition:all 0.15s; }
  .period-chip:hover { background:#eef0f3; }
  .period-chip.active { background:#2563eb; color:#fff; border-color:#2563eb; }

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
  .tcard-tf { color:#6b7280; font-size:10px; font-weight:500; margin-left:4px; padding:1px 4px; background:#f3f4f6; border-radius:3px; }
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

  /* Sparkline (small) */
  .spark { width:100%; height:80px; }
  .spark-axis { stroke:#e8eaed; stroke-width:1; }
  .spark-line { fill:none; stroke:#2563eb; stroke-width:2; }
  .spark-area { fill:url(#spark-grad); }
  .spark-dd { fill:none; stroke:#dc2626; stroke-width:1.5; stroke-dasharray:3,2; }

  /* Full chart */
  .chart-wrap { overflow-x:auto; -webkit-overflow-scrolling:touch; }
  .chart-svg { width:100%; min-width:680px; height:240px; display:block; }
  @media (min-width:768px) { .chart-svg { height:280px; min-width:0; } }
  .chart-grid { stroke:#f0f1f3; stroke-width:1; }
  .chart-axis-label { font-size:10px; fill:#6b7280; font-family:'Inter',sans-serif; }
  .chart-line { fill:none; stroke:#2563eb; stroke-width:2; }
  .chart-area { fill:url(#eq-grad); }
  .chart-baseline { stroke:#9ca3af; stroke-width:1; stroke-dasharray:3,3; }
  .chart-peak-line { stroke:#059669; stroke-width:1; stroke-dasharray:2,4; }
  .chart-marker { fill:#2563eb; stroke:#fff; stroke-width:2; }
  .chart-marker.peak { fill:#059669; }
  .chart-marker.trough { fill:#dc2626; }
  .chart-tooltip-label { font-size:11px; font-weight:600; }
  .chart-summary { display:flex; gap:14px; margin-top:6px; flex-wrap:wrap; font-size:11px; color:#6b7280; }
  .chart-summary span b { color:#1a1a2e; font-weight:700; }
  .chart-summary .green b { color:#059669; }
  .chart-summary .red b { color:#dc2626; }

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
  .log-row { padding:6px 0; border-bottom:1px solid #f0f1f3; font-size:11px; display:flex; gap:8px; align-items:center; cursor:pointer; }
  .log-row:hover { background:#f9fafb; }
  .log-row:last-child { border-bottom:none; }
  .log-time { color:#9ca3af; min-width:42px; font-variant-numeric:tabular-nums; }
  .log-tag { padding:1px 6px; border-radius:3px; font-size:9px; font-weight:700; text-transform:uppercase; min-width:48px; text-align:center; }
  .log-tag.entry { background:#dbeafe; color:#1e40af; }
  .log-tag.exit-w { background:#d1fae5; color:#065f46; }
  .log-tag.exit-l { background:#fee2e2; color:#991b1b; }

  /* Clickable */
  .tcard { cursor:pointer; transition:transform 0.1s, box-shadow 0.1s; }
  .tcard:hover { box-shadow:0 2px 8px rgba(37,99,235,0.12); border-color:#2563eb; }
  .tcard:active { transform:scale(0.99); }
  .clickable { cursor:pointer; }
  .clickable:hover { background:#f9fafb; }

  /* Modal / drill-down */
  .modal { position:fixed; inset:0; z-index:100; display:flex; align-items:center; justify-content:center; }
  .modal.hidden { display:none; }
  .modal-backdrop { position:absolute; inset:0; background:rgba(15,23,42,0.5); backdrop-filter:blur(2px); }
  .modal-content { position:relative; background:#fff; border-radius:12px; max-width:640px; width:calc(100% - 20px); max-height:90vh; overflow-y:auto; box-shadow:0 10px 40px rgba(0,0,0,0.2); display:flex; flex-direction:column; }
  .modal-header { display:flex; align-items:center; justify-content:space-between; padding:14px 16px; border-bottom:1px solid #e8eaed; position:sticky; top:0; background:#fff; z-index:1; border-radius:12px 12px 0 0; }
  .modal-title { font-size:14px; font-weight:700; color:#1a1a2e; }
  .modal-title .sub { font-weight:400; color:#6b7280; font-size:11px; margin-left:6px; }
  .modal-back { background:transparent; border:none; font-size:18px; cursor:pointer; color:#6b7280; padding:4px 8px; }
  .modal-close { background:transparent; border:none; font-size:22px; cursor:pointer; color:#6b7280; padding:0 4px; line-height:1; }
  .modal-close:hover { color:#1a1a2e; }
  .modal-body { padding:14px 16px; }
  @media (max-width: 600px) {
    .modal { align-items:stretch; }
    .modal-content { max-width:none; width:100%; max-height:none; border-radius:0; }
    .modal-header { border-radius:0; }
  }

  /* Drill content */
  .drill-grid { display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-bottom:12px; }
  .drill-cell { background:#f9fafb; border-radius:6px; padding:8px 10px; }
  .drill-cell .lbl { font-size:9px; color:#6b7280; text-transform:uppercase; letter-spacing:0.4px; font-weight:600; }
  .drill-cell .val { font-size:13px; font-weight:600; color:#1a1a2e; margin-top:2px; }
  .drill-section { margin-bottom:14px; }
  .drill-section h4 { font-size:11px; color:#6b7280; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:6px; padding-bottom:4px; border-bottom:1px solid #e8eaed; }
  .drill-row { display:flex; justify-content:space-between; padding:5px 0; font-size:12px; border-bottom:1px solid #f0f1f3; }
  .drill-row:last-child { border-bottom:none; }
  .drill-row .k { color:#6b7280; }
  .drill-row .v { font-weight:600; color:#1a1a2e; }

  /* BT vs LV aligned table */
  .vs-tbl { width:100%; border-collapse:collapse; margin-bottom:14px; font-size:12px; }
  .vs-tbl th, .vs-tbl td { padding:7px 10px; border-bottom:1px solid #f0f1f3; text-align:right; }
  .vs-tbl thead th { background:#f9fafb; font-size:10px; text-transform:uppercase; letter-spacing:0.4px; color:#6b7280; font-weight:700; }
  .vs-tbl thead th.h-bt { color:#7c3aed; }
  .vs-tbl thead th.h-lv { color:#2563eb; }
  .vs-tbl tbody th { text-align:left; font-weight:500; color:#6b7280; font-size:11px; background:#fafbfc; width:80px; }
  .vs-tbl tbody td { font-weight:600; color:#1a1a2e; font-variant-numeric:tabular-nums; }
  .vs-tbl tbody tr:last-child th, .vs-tbl tbody tr:last-child td { border-bottom:none; }

  /* Top lists (Home) */
  .toplist { display:flex; flex-direction:column; gap:4px; }
  .toprow { display:flex; align-items:center; gap:8px; padding:8px 10px; background:#fafbfc; border:1px solid #e8eaed; border-radius:6px; cursor:pointer; transition:all 0.1s; }
  .toprow:hover { background:#f0f7ff; border-color:#2563eb; }
  .toprow .name { flex:1; font-weight:600; }
  .toprow .stats { color:#6b7280; font-size:11px; display:flex; gap:8px; }
  .toprow .pnl { font-weight:700; min-width:70px; text-align:right; }

  /* Legacy table */
  .legacy-tbl { width:100%; border-collapse:separate; border-spacing:0; font-size:12px; min-width:900px; background:#fff; }
  .legacy-tbl th { background:#fafbfc; color:#6b7280; font-weight:600; font-size:10px; text-transform:uppercase; letter-spacing:0.4px; padding:9px 8px; border-bottom:1px solid #e8eaed; position:sticky; top:0; z-index:1; }
  .legacy-tbl thead tr:first-child th { font-weight:700; color:#4b5563; padding-top:10px; }
  .legacy-tbl thead .h-bt { color:#7c3aed; }
  .legacy-tbl thead .h-lv { color:#2563eb; }
  .legacy-tbl thead .h-delta { color:#9a7800; }
  .legacy-tbl td { padding:8px; border-bottom:1px solid #f0f1f3; vertical-align:middle; white-space:nowrap; font-variant-numeric:tabular-nums; }
  .legacy-tbl tr:hover td { background:#f9fafb; }
  .legacy-tbl tr:hover .col-strat { background:#f9fafb; }
  .legacy-tbl .col-strat { font-weight:600; color:#2563eb; position:sticky; left:0; background:#fff; z-index:1; box-shadow:1px 0 0 #e8eaed; }
  .legacy-tbl .sep-bt { border-left:1px solid #e8eaed; }
  .legacy-tbl .sep-lv { border-left:1px solid #e8eaed; }
  .legacy-tbl .sep-delta { border-left:1px solid #e8eaed; }
  .legacy-tbl tr.row-warn td:not(.col-strat) { background:#fffbeb; }
  .legacy-tbl tr.row-bad td:not(.col-strat) { background:#fef2f2; }
  .legacy-tbl tr.row-good td:not(.col-strat) { background:#f0fdf4; }
  .legacy-tbl tr.row-warn .col-strat { background:#fffbeb; }
  .legacy-tbl tr.row-bad .col-strat { background:#fef2f2; }
  .legacy-tbl tr.row-good .col-strat { background:#f0fdf4; }
  .legacy-tbl tfoot td { font-weight:700; background:#f5f6f8; color:#1a1a2e; padding:11px 8px; border-top:2px solid #e8eaed; border-bottom:none; }
  .legacy-tbl tfoot .col-strat { background:#f5f6f8; color:#1a1a2e; box-shadow:none; }
  .legacy-wrap { overflow-x:auto; -webkit-overflow-scrolling:touch; max-height:70vh; overflow-y:auto; border:1px solid #e8eaed; border-radius:8px; }
  .legacy-section-title { display:flex; align-items:center; gap:10px; margin:18px 0 8px; padding-bottom:6px; border-bottom:1px solid #e8eaed; }
  .legacy-section-title .sym { font-size:15px; font-weight:700; color:#1a1a2e; }
  .legacy-section-title .meta { font-size:11px; color:#6b7280; margin-left:auto; }

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
  <div class="period-tabs" id="period-tabs"></div>
</div>

<div class="main">
  <section class="kpis" id="kpis"></section>
  <nav class="tabs" id="tabs"></nav>
  <div id="tab-home" class="tab-content active"></div>
  <div id="tab-today" class="tab-content"></div>
  <div id="tab-open" class="tab-content"></div>
  <div id="tab-history" class="tab-content"></div>
  <div id="tab-bt" class="tab-content"></div>
  <div id="tab-logs" class="tab-content"></div>
  <div id="tab-legacy" class="tab-content"></div>
  <div id="tab-live" class="tab-content"></div>
</div>

<div id="modal" class="modal hidden">
  <div class="modal-backdrop" onclick="closeModal()"></div>
  <div class="modal-content">
    <div class="modal-header">
      <span id="modal-back-wrap"></span>
      <span class="modal-title" id="modal-title"></span>
      <button class="modal-close" onclick="closeModal()">&times;</button>
    </div>
    <div class="modal-body" id="modal-body"></div>
  </div>
</div>

<div class="footer">HydraTrader &mdash; refresh 1s</div>

<script>
const API='';
const ACCOUNTS=['5ers','ftmo','pepperstone'];
const ACCOUNT_TABS=['live',...ACCOUNTS]; // 'live' en premier (vue agregee positions ouvertes)
const MAX_DD={'5ers':4.0,'ftmo':10.0,'pepperstone':100.0};
const PERIODS=[
  {id:'today',label:'Jour'},
  {id:'yesterday',label:'Hier'},
  {id:'7d',label:'7j'},
  {id:'30d',label:'30j'},
  {id:'all',label:'Tout'},
];
let SELECTED=localStorage.getItem('hydra-acc')||'live';
let TAB=localStorage.getItem('hydra-tab')||'home';
let PERIOD=localStorage.getItem('hydra-period')||'today';
let LAST={};
let MODAL_STACK=[]; // pour bouton retour

function buildMergedData(allData){
  const merged={state:{account_info:{balance:0,equity:0,margin:0,free_margin:0,profit:0},positions:[],today_trades:[],today_pnl:0,today_count:0,candles:{},broker:'all',ts:null},history:[],bt_compare:{},last_push:null};
  for(const acc of ACCOUNTS){
    const d=allData[acc]||{};
    if(!d.state)continue;
    const s=d.state, a=s.account_info||{};
    merged.state.account_info.balance += a.balance||0;
    merged.state.account_info.equity += a.equity||0;
    merged.state.account_info.margin += a.margin||0;
    merged.state.account_info.free_margin += a.free_margin||0;
    merged.state.account_info.profit += a.profit||0;
    for(const p of (s.positions||[])) merged.state.positions.push({...p,_acc:acc});
    for(const t of (s.today_trades||[])) merged.state.today_trades.push({...t,_acc:acc});
    for(const t of (d.history||[])) merged.history.push({...t,_acc:acc});
    merged.state.today_pnl += s.today_pnl||0;
    merged.state.today_count += s.today_count||0;
    for(const sym of Object.keys(d.bt_compare||{})){
      const key=`${acc}:${sym}`;
      merged.bt_compare[key]={...d.bt_compare[sym],_acc:acc,_sym:sym};
    }
    if(s.ts&&(!merged.state.ts||s.ts>merged.state.ts))merged.state.ts=s.ts;
    if(d.last_push&&(!merged.last_push||d.last_push>merged.last_push))merged.last_push=d.last_push;
  }
  return merged;
}

function getAccData(){
  return SELECTED==='live'?buildMergedData(LAST):(LAST[SELECTED]||{});
}

function nowDate(data){const ts=data?.state?.ts;return ts?new Date(ts):new Date();}
function periodRange(periodId,data){
  const now=nowDate(data);
  const today=now.toISOString().slice(0,10);
  if(periodId==='today')return {from:today,to:today,label:'Jour'};
  if(periodId==='yesterday'){
    const d=new Date(now);d.setUTCDate(d.getUTCDate()-1);
    const ds=d.toISOString().slice(0,10);
    return {from:ds,to:ds,label:'Hier'};
  }
  if(periodId==='7d'){
    const d=new Date(now);d.setUTCDate(d.getUTCDate()-6);
    return {from:d.toISOString().slice(0,10),to:today,label:'7j'};
  }
  if(periodId==='30d'){
    const d=new Date(now);d.setUTCDate(d.getUTCDate()-29);
    return {from:d.toISOString().slice(0,10),to:today,label:'30j'};
  }
  return {from:null,to:null,label:'Tout'};
}
function getPeriodTrades(data){
  const r=periodRange(PERIOD,data);
  const tt=data?.state?.today_trades||[];
  const hist=data?.history||[];
  const seen=new Set(),all=[];
  for(const t of [...tt,...hist]){
    if(seen.has(t.ticket))continue;
    seen.add(t.ticket);
    all.push(t);
  }
  if(!r.from)return all;
  return all.filter(t=>{const d=(t.time_close||t.time_open||'').slice(0,10);return d>=r.from&&d<=r.to;});
}

function fmt(n,d=0){if(n==null||isNaN(n))return'-';return Number(n).toLocaleString('en-US',{minimumFractionDigits:d,maximumFractionDigits:d});}
function fmtUsd(v,d=0){const s=v>=0?'+':'-';return s+'$'+fmt(Math.abs(v),d);}
function pnlCls(v){return v>=0?'pnl-pos':'pnl-neg';}
function dirCls(d){return d==='long'?'dir-long':'dir-short';}
function timeHM(s){return s?(s+'').slice(11,16):'';}
function dateD(s){return s?(s+'').slice(0,10):'';}
function escapeH(s){return (s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}

// === Modal system ===
function openModal(title,html,push){
  if(push)MODAL_STACK.push({title:document.getElementById('modal-title').innerHTML,body:document.getElementById('modal-body').innerHTML});
  document.getElementById('modal-title').innerHTML=title;
  document.getElementById('modal-body').innerHTML=html;
  document.getElementById('modal-back-wrap').innerHTML=MODAL_STACK.length?'<button class="modal-back" onclick="modalBack()">&larr;</button>':'';
  document.getElementById('modal').classList.remove('hidden');
  document.body.style.overflow='hidden';
}
function closeModal(){
  document.getElementById('modal').classList.add('hidden');
  document.body.style.overflow='';
  MODAL_STACK=[];
}
function modalBack(){
  if(MODAL_STACK.length===0){closeModal();return;}
  const prev=MODAL_STACK.pop();
  document.getElementById('modal-title').innerHTML=prev.title;
  document.getElementById('modal-body').innerHTML=prev.body;
  document.getElementById('modal-back-wrap').innerHTML=MODAL_STACK.length?'<button class="modal-back" onclick="modalBack()">&larr;</button>':'';
}

// === BT match for live trade ===
// Trades poussent par vps_pusher ont les fields: symbol, tf, strat, comment ('STRAT|TF'), ticket
// bt_compare keys = 'sym|tf' (single account) ou 'acc:sym|tf' (live merged)
function stratOf(t){return t.strat||((t.comment||'').split('|')[0]);}
function tfOf(t){return t.tf||((t.comment||'').split('|')[1])||'15m';}
// Format pour affichage 'STRAT|TF' -> 'STRAT [TF]'
function fmtStratTf(commentOrKey){
  const parts=(commentOrKey||'').split('|');
  if(parts.length>=2)return `${escapeH(parts[0])} <span class="tcard-tf">[${escapeH(parts[1])}]</span>`;
  return escapeH(commentOrKey||'');
}

function findBtMatch(sym,strat,tf,data,acc,ticket){
  const btc=data?.bt_compare||{};
  const unitKey=`${sym}|${tf}`;
  // 1. Mode single account: cle directe 'sym|tf'
  let info=btc[unitKey];
  // 2. Mode LIVE merge: cle 'acc:sym|tf'
  if(!info && acc) info=btc[`${acc}:${unitKey}`];
  // 3. Fallback: chercher n'importe quelle cle qui finit par '|sym|tf' ou matche unitKey
  if(!info){
    for(const k of Object.keys(btc)){
      if(k===unitKey||k.endsWith(':'+unitKey)){info=btc[k];break;}
    }
  }
  if(!info)return null;
  const rows=(info.rows||[]).filter(r=>r.strat===strat);
  if(rows.length===0)return null;
  // Si ticket fourni, prefere matcher par ticket LV
  if(ticket){
    const byTicket=rows.find(r=>r.lv&&r.lv.ticket===ticket);
    if(byTicket)return {...byTicket,atr:info.atr,tf:info.tf,_acc:info._acc};
  }
  // Fallback: premier row (idx 0)
  return {...rows[0],atr:info.atr,tf:info.tf,_acc:info._acc};
}

// === Drill-down: trade ===
function openTradeByKey(key,push){
  const data=getAccData();
  const [scope,...rest]=key.split('|');
  let title='',body='';
  if(scope==='lv'){
    const ticket=parseInt(rest[0]);
    const all=[...(data.state?.today_trades||[]),...(data.history||[])];
    const t=all.find(x=>x.ticket===ticket);
    if(!t){body='<div class="empty">Trade introuvable</div>';}
    else{title=tradeTitle(t);body=renderTradeDrill(t,data);}
  }else if(scope==='op'){
    const ticket=parseInt(rest[0]);
    const p=(data.state?.positions||[]).find(x=>x.ticket===ticket);
    if(!p){body='<div class="empty">Position introuvable</div>';}
    else{title=tradeTitle(p)+' <span class="sub">OPEN</span>';body=renderPositionDrill(p,data);}
  }else if(scope==='bt'){
    const sym=rest[0],tf=rest[1],strat=rest[2];
    const m=findBtMatch(sym,strat,tf,data);
    if(!m){body='<div class="empty">BT introuvable</div>';}
    else{title=`${escapeH(sym)} <span class="sub">[${escapeH(tf)}] ${escapeH(strat)} (BT)</span>`;body=renderBtRowDrill(sym,strat,m,data);}
  }
  openModal(title,body,push);
}

function tradeTitle(t){
  const d=(t.dir||'').toUpperCase();
  return `${escapeH(t.symbol)} <span class="sub">${escapeH(stratOf(t))}<span class="tcard-tf">[${escapeH(tfOf(t))}]</span> ${d}</span>`;
}

function renderTradeDrill(t,data){
  const m=findBtMatch(t.symbol,stratOf(t),tfOf(t),data,t._acc,t.ticket);
  const pnl=t.pnl||0;
  const isLong=t.dir==='long';
  let h='';
  // Top metrics
  h+='<div class="drill-grid">';
  h+=`<div class="drill-cell"><div class="lbl">PnL $</div><div class="val ${pnlCls(pnl)}">${fmtUsd(pnl,2)}</div></div>`;
  if(m&&m.lv){h+=`<div class="drill-cell"><div class="lbl">PnL R</div><div class="val ${pnlCls(m.lv.pnl_r||0)}">${(m.lv.pnl_r>=0?'+':'')+(m.lv.pnl_r||0).toFixed(2)}R</div></div>`;}
  h+=`<div class="drill-cell"><div class="lbl">Volume</div><div class="val">${t.volume} lots</div></div>`;
  h+=`<div class="drill-cell"><div class="lbl">Direction</div><div class="val ${dirCls(t.dir)}">${(t.dir||'').toUpperCase()}</div></div>`;
  h+='</div>';

  // BT vs LV side-by-side if matched
  if(m&&m.bt){
    const bt=m.bt, lv=m.lv;
    const btPts=isLong?bt.exit-bt.entry:bt.entry-bt.exit;
    const lvPts=isLong?t.exit-t.entry:t.entry-t.exit;
    const btIn=bt.entry_time?dateD(bt.entry_time).slice(5)+' '+timeHM(bt.entry_time):'-';
    const btOut=bt.exit_time?dateD(bt.exit_time).slice(5)+' '+timeHM(bt.exit_time):'-';
    const lvIn=t.time_open?dateD(t.time_open).slice(5)+' '+timeHM(t.time_open):'-';
    const lvOut=t.time_close?dateD(t.time_close).slice(5)+' '+timeHM(t.time_close):'-';
    h+=`<table class="vs-tbl">
      <thead><tr><th></th><th class="h-bt">BACKTEST</th><th class="h-lv">LIVE</th></tr></thead>
      <tbody>
        <tr><th>Entry</th><td>${fmt(bt.entry,2)}</td><td>${fmt(t.entry,2)}</td></tr>
        <tr><th>Exit</th><td>${fmt(bt.exit,2)}</td><td>${fmt(t.exit,2)}</td></tr>
        <tr><th>R</th><td class="${pnlCls(bt.pnl_r||0)}">${(bt.pnl_r>=0?'+':'')+(bt.pnl_r||0).toFixed(2)}R</td><td class="${pnlCls((lv||{}).pnl_r||0)}">${lv?(lv.pnl_r>=0?'+':'')+(lv.pnl_r||0).toFixed(2)+'R':'-'}</td></tr>
        <tr><th>Pts</th><td>${(btPts>=0?'+':'')+btPts.toFixed(2)}</td><td>${(lvPts>=0?'+':'')+lvPts.toFixed(2)}</td></tr>
        <tr><th>$</th><td style="color:#9ca3af">-</td><td class="${pnlCls(pnl)}">${fmtUsd(pnl,2)}</td></tr>
        <tr><th>In</th><td>${btIn}</td><td>${lvIn}</td></tr>
        <tr><th>Out</th><td>${btOut}</td><td>${lvOut}</td></tr>
      </tbody>
    </table>`;
    // Slippage
    const slipEntry=isLong?(t.entry-m.bt.entry):(m.bt.entry-t.entry);
    const slipExit=isLong?(m.bt.exit-t.exit):(t.exit-m.bt.exit);
    const delta=m.delta||0;
    h+='<div class="drill-section"><h4>Slippage</h4>';
    h+=`<div class="drill-row"><span class="k">Slippage entree</span><span class="v ${slipEntry<=0?'pnl-pos':'pnl-neg'}">${slipEntry>=0?'+':''}${slipEntry.toFixed(2)} pts</span></div>`;
    h+=`<div class="drill-row"><span class="k">Slippage sortie</span><span class="v ${slipExit>=0?'pnl-pos':'pnl-neg'}">${slipExit>=0?'+':''}${slipExit.toFixed(2)} pts</span></div>`;
    h+=`<div class="drill-row"><span class="k">Delta R (BT - LV)</span><span class="v ${pnlCls(delta)}">${delta>=0?'+':''}${delta.toFixed(2)}R</span></div>`;
    h+=`<div class="drill-row"><span class="k">ATR du jour</span><span class="v">${fmt(m.atr,2)}</span></div>`;
    h+='</div>';
  }else{
    h+='<div class="drill-section"><h4>Trade Live</h4>';
    h+=`<div class="drill-row"><span class="k">Entry</span><span class="v">${fmt(t.entry,2)}</span></div>`;
    h+=`<div class="drill-row"><span class="k">Exit</span><span class="v">${fmt(t.exit,2)}</span></div>`;
    h+=`<div class="drill-row"><span class="k">Pts</span><span class="v">${fmt(((isLong?t.exit-t.entry:t.entry-t.exit)),2)}</span></div>`;
    h+='<div class="drill-row"><span class="k">BT match</span><span class="v" style="color:#9ca3af">Aucun</span></div>';
    h+='</div>';
  }

  // Meta
  h+='<div class="drill-section"><h4>Detail</h4>';
  h+=`<div class="drill-row"><span class="k">Ticket</span><span class="v">#${t.ticket||'-'}</span></div>`;
  h+=`<div class="drill-row"><span class="k">Strat</span><span class="v" style="color:#2563eb">${escapeH(stratOf(t))}<span class="tcard-tf">[${escapeH(tfOf(t))}]</span></span></div>`;
  h+=`<div class="drill-row"><span class="k">Open</span><span class="v">${dateD(t.time_open)} ${timeHM(t.time_open)}</span></div>`;
  h+=`<div class="drill-row"><span class="k">Close</span><span class="v">${dateD(t.time_close)} ${timeHM(t.time_close)}</span></div>`;
  if(t.time_open&&t.time_close){
    const dur=Math.round((new Date(t.time_close).getTime()-new Date(t.time_open).getTime())/60000);
    h+=`<div class="drill-row"><span class="k">Duree</span><span class="v">${dur} min</span></div>`;
  }
  h+='</div>';
  return h;
}

function renderPositionDrill(p,data){
  const m=findBtMatch(p.symbol,stratOf(p),tfOf(p),data,p._acc,p.ticket);
  const isLong=p.dir==='long';
  const elapsed=p.time_open?Math.round((Date.now()-new Date(p.time_open).getTime())/60000):0;
  const pnl=p.pnl||0;
  let h='';
  h+='<div class="drill-grid">';
  h+=`<div class="drill-cell"><div class="lbl">PnL flot</div><div class="val ${pnlCls(pnl)}">${fmtUsd(pnl,2)}</div></div>`;
  h+=`<div class="drill-cell"><div class="lbl">Direction</div><div class="val ${dirCls(p.dir)}">${(p.dir||'').toUpperCase()}</div></div>`;
  h+=`<div class="drill-cell"><div class="lbl">Volume</div><div class="val">${p.volume} lots</div></div>`;
  h+=`<div class="drill-cell"><div class="lbl">Elapsed</div><div class="val">${elapsed} min</div></div>`;
  h+='</div>';

  h+='<div class="drill-section"><h4>Position</h4>';
  h+=`<div class="drill-row"><span class="k">Entry (fill)</span><span class="v">${fmt(p.entry,2)}</span></div>`;
  h+=`<div class="drill-row"><span class="k">Current</span><span class="v">${fmt(p.current,2)}</span></div>`;
  h+=`<div class="drill-row"><span class="k">SL</span><span class="v" style="color:#dc2626">${fmt(p.sl,2)}</span></div>`;
  h+=`<div class="drill-row"><span class="k">TP</span><span class="v" style="color:#059669">${p.tp?fmt(p.tp,2):'-'}</span></div>`;
  if(p.swap)h+=`<div class="drill-row"><span class="k">Swap</span><span class="v">${fmtUsd(p.swap,2)}</span></div>`;
  h+='</div>';

  if(m&&m.bt){
    h+='<div class="drill-section"><h4>BT (signal)</h4>';
    h+=`<div class="drill-row"><span class="k">BT Entry (close signal)</span><span class="v">${fmt(m.bt.entry,2)}</span></div>`;
    const slip=isLong?(p.entry-m.bt.entry):(m.bt.entry-p.entry);
    h+=`<div class="drill-row"><span class="k">Slippage entree</span><span class="v ${slip<=0?'pnl-pos':'pnl-neg'}">${slip>=0?'+':''}${slip.toFixed(2)} pts</span></div>`;
    if(m.bt.exit&&m.bt.exit!==m.bt.entry){
      h+=`<div class="drill-row"><span class="k">BT Exit (deja sorti)</span><span class="v">${fmt(m.bt.exit,2)}</span></div>`;
      h+=`<div class="drill-row"><span class="k">BT R</span><span class="v ${pnlCls(m.bt.pnl_r||0)}">${(m.bt.pnl_r>=0?'+':'')+(m.bt.pnl_r||0).toFixed(2)}R</span></div>`;
    }
    h+=`<div class="drill-row"><span class="k">ATR jour</span><span class="v">${fmt(m.atr,2)}</span></div>`;
    h+='</div>';
  }

  h+='<div class="drill-section"><h4>Detail</h4>';
  h+=`<div class="drill-row"><span class="k">Ticket</span><span class="v">#${p.ticket}</span></div>`;
  h+=`<div class="drill-row"><span class="k">Strat</span><span class="v" style="color:#2563eb">${escapeH(stratOf(p))}<span class="tcard-tf">[${escapeH(tfOf(p))}]</span></span></div>`;
  h+=`<div class="drill-row"><span class="k">Time open</span><span class="v">${dateD(p.time_open)} ${timeHM(p.time_open)}</span></div>`;
  h+='</div>';
  return h;
}

function renderBtRowDrill(sym,strat,m,data){
  const bt=m.bt,lv=m.lv;
  let h='';
  const cellOr=v=>v||'<span style="color:#9ca3af">-</span>';
  const dirCell=o=>o?`<span class="${dirCls(o.dir)}">${(o.dir||'').toUpperCase()}</span>`:'<span style="color:#9ca3af">-</span>';
  const fmtCell=(o,k,d=2)=>o&&o[k]!=null?fmt(o[k],d):'<span style="color:#9ca3af">-</span>';
  const rCell=o=>o&&o.pnl_r!=null?`<span class="${pnlCls(o.pnl_r)}">${(o.pnl_r>=0?'+':'')+o.pnl_r.toFixed(2)}R</span>`:'<span style="color:#9ca3af">-</span>';
  const usdCell=o=>o&&o.pnl_usd!=null?`<span class="${pnlCls(o.pnl_usd)}">${fmtUsd(o.pnl_usd,2)}</span>`:'<span style="color:#9ca3af">-</span>';
  const tCell=(o,k)=>o&&o[k]?dateD(o[k]).slice(5)+' '+timeHM(o[k]):'<span style="color:#9ca3af">-</span>';
  h+=`<table class="vs-tbl">
    <thead><tr><th></th><th class="h-bt">BACKTEST</th><th class="h-lv">LIVE</th></tr></thead>
    <tbody>
      <tr><th>Dir</th><td>${dirCell(bt)}</td><td>${dirCell(lv)}</td></tr>
      <tr><th>Entry</th><td>${fmtCell(bt,'entry')}</td><td>${fmtCell(lv,'entry')}</td></tr>
      <tr><th>Exit</th><td>${fmtCell(bt,'exit')}</td><td>${fmtCell(lv,'exit')}</td></tr>
      <tr><th>R</th><td>${rCell(bt)}</td><td>${rCell(lv)}</td></tr>
      <tr><th>$</th><td style="color:#9ca3af">-</td><td>${usdCell(lv)}</td></tr>
      <tr><th>In</th><td>${tCell(bt,'entry_time')}</td><td>${tCell(lv,'entry_time')}</td></tr>
      <tr><th>Out</th><td>${tCell(bt,'exit_time')}</td><td>${tCell(lv,'exit_time')}</td></tr>
    </tbody>
  </table>`;

  if(m.delta!=null){
    h+='<div class="drill-section"><h4>Delta</h4>';
    h+=`<div class="drill-row"><span class="k">BT - LV</span><span class="v ${pnlCls(m.delta)}">${m.delta>=0?'+':''}${m.delta.toFixed(2)}R</span></div>`;
    h+=`<div class="drill-row"><span class="k">ATR jour</span><span class="v">${fmt(m.atr,2)}</span></div>`;
    h+='</div>';
  }
  return h;
}

// === Drill-down: instrument ===
function openInstrumentDrill(sym,push){
  const data=getAccData();
  const trades=getPeriodTrades(data).filter(t=>t.symbol===sym);
  const total=trades.reduce((s,t)=>s+(t.pnl||0),0);
  const wins=trades.filter(t=>(t.pnl||0)>0);
  const losses=trades.filter(t=>(t.pnl||0)<=0);
  const wr=trades.length?wins.length/trades.length*100:0;
  const gp=wins.reduce((s,t)=>s+t.pnl,0);
  const gl=losses.reduce((s,t)=>s+Math.abs(t.pnl),0);
  const pf=gl>0?gp/gl:(gp>0?99.99:0);
  const maxWin=wins.reduce((m,t)=>Math.max(m,t.pnl),0);
  const maxLoss=losses.reduce((m,t)=>Math.min(m,t.pnl),0);
  let h='';
  h+='<div class="drill-grid">';
  h+=`<div class="drill-cell"><div class="lbl">Total $</div><div class="val ${pnlCls(total)}">${fmtUsd(total,2)}</div></div>`;
  h+=`<div class="drill-cell"><div class="lbl">Trades</div><div class="val">${trades.length}</div></div>`;
  h+=`<div class="drill-cell"><div class="lbl">WR</div><div class="val">${wr.toFixed(0)}%</div></div>`;
  h+=`<div class="drill-cell"><div class="lbl">PF</div><div class="val ${pf>=1?'pnl-pos':'pnl-neg'}">${pf.toFixed(2)}</div></div>`;
  h+=`<div class="drill-cell"><div class="lbl">Best</div><div class="val pnl-pos">${fmtUsd(maxWin,2)}</div></div>`;
  h+=`<div class="drill-cell"><div class="lbl">Worst</div><div class="val pnl-neg">${fmtUsd(maxLoss,2)}</div></div>`;
  h+='</div>';

  // Per strat
  const byStrat={};
  for(const t of trades){const k=t.comment||'?';byStrat[k]=byStrat[k]||{n:0,$:0,w:0};byStrat[k].n++;byStrat[k].$+=(t.pnl||0);if((t.pnl||0)>0)byStrat[k].w++;}
  const stratList=Object.entries(byStrat).sort((a,b)=>b[1].$-a[1].$);
  if(stratList.length>0){
    h+='<div class="drill-section"><h4>Par strategie</h4><div class="toplist">';
    for(const [sn,st] of stratList){
      h+=`<div class="toprow" onclick="openStratDrill('${escapeH(sn)}',true)">
        <span class="name">${fmtStratTf(sn)}</span>
        <span class="stats">${st.n}t &middot; WR ${(st.w/st.n*100).toFixed(0)}%</span>
        <span class="pnl ${pnlCls(st.$)}">${fmtUsd(st.$,2)}</span>
      </div>`;
    }
    h+='</div></div>';
  }

  // Trades list
  if(trades.length>0){
    h+='<div class="drill-section"><h4>Trades</h4><div class="list">';
    const sorted=[...trades].sort((a,b)=>(b.time_close||b.time_open||'').localeCompare(a.time_close||a.time_open||''));
    for(const t of sorted){
      const pnl=t.pnl||0;
      h+=`<div class="tcard" onclick="openTradeByKey('lv|${t.ticket}',true)">
        <div class="tcard-head">
          <div><span class="tcard-strat">${escapeH(stratOf(t))}<span class="tcard-tf">[${escapeH(tfOf(t))}]</span></span> <span class="${dirCls(t.dir)}">${(t.dir||'').toUpperCase()}</span></div>
          <span class="tcard-pnl ${pnlCls(pnl)}">${fmtUsd(pnl,2)}</span>
        </div>
        <div class="tcard-meta"><span>${fmt(t.entry,2)}&rarr;${fmt(t.exit,2)}</span><span class="tcard-time">${dateD(t.time_close)} ${timeHM(t.time_close)}</span></div>
      </div>`;
    }
    h+='</div></div>';
  }
  openModal(`${escapeH(sym)} <span class="sub">${periodRange(PERIOD,data).label}</span>`,h,push);
}

// === Drill-down: strat ===
function openStratDrill(strat,push){
  const data=getAccData();
  const trades=getPeriodTrades(data).filter(t=>t.comment===strat);
  const total=trades.reduce((s,t)=>s+(t.pnl||0),0);
  const wins=trades.filter(t=>(t.pnl||0)>0);
  const losses=trades.filter(t=>(t.pnl||0)<=0);
  const wr=trades.length?wins.length/trades.length*100:0;
  const gp=wins.reduce((s,t)=>s+t.pnl,0);
  const gl=losses.reduce((s,t)=>s+Math.abs(t.pnl),0);
  const pf=gl>0?gp/gl:(gp>0?99.99:0);
  let h='';
  h+='<div class="drill-grid">';
  h+=`<div class="drill-cell"><div class="lbl">Total $</div><div class="val ${pnlCls(total)}">${fmtUsd(total,2)}</div></div>`;
  h+=`<div class="drill-cell"><div class="lbl">Trades</div><div class="val">${trades.length}</div></div>`;
  h+=`<div class="drill-cell"><div class="lbl">WR</div><div class="val">${wr.toFixed(0)}%</div></div>`;
  h+=`<div class="drill-cell"><div class="lbl">PF</div><div class="val ${pf>=1?'pnl-pos':'pnl-neg'}">${pf.toFixed(2)}</div></div>`;
  h+='</div>';

  // Per sym
  const bySym={};
  for(const t of trades){const k=t.symbol||'?';bySym[k]=bySym[k]||{n:0,$:0,w:0};bySym[k].n++;bySym[k].$+=(t.pnl||0);if((t.pnl||0)>0)bySym[k].w++;}
  const symList=Object.entries(bySym).sort((a,b)=>b[1].$-a[1].$);
  if(symList.length>0){
    h+='<div class="drill-section"><h4>Par instrument</h4><div class="toplist">';
    for(const [sym,st] of symList){
      h+=`<div class="toprow" onclick="openInstrumentDrill('${escapeH(sym)}',true)">
        <span class="name">${escapeH(sym)}</span>
        <span class="stats">${st.n}t &middot; WR ${(st.w/st.n*100).toFixed(0)}%</span>
        <span class="pnl ${pnlCls(st.$)}">${fmtUsd(st.$,2)}</span>
      </div>`;
    }
    h+='</div></div>';
  }

  if(trades.length>0){
    h+='<div class="drill-section"><h4>Trades</h4><div class="list">';
    const sorted=[...trades].sort((a,b)=>(b.time_close||b.time_open||'').localeCompare(a.time_close||a.time_open||''));
    for(const t of sorted){
      const pnl=t.pnl||0;
      h+=`<div class="tcard" onclick="openTradeByKey('lv|${t.ticket}',true)">
        <div class="tcard-head">
          <div><span class="tcard-sym">${escapeH(t.symbol)}</span> <span class="${dirCls(t.dir)}">${(t.dir||'').toUpperCase()}</span></div>
          <span class="tcard-pnl ${pnlCls(pnl)}">${fmtUsd(pnl,2)}</span>
        </div>
        <div class="tcard-meta"><span>${fmt(t.entry,2)}&rarr;${fmt(t.exit,2)}</span><span class="tcard-time">${dateD(t.time_close)} ${timeHM(t.time_close)}</span></div>
      </div>`;
    }
    h+='</div></div>';
  }
  openModal(`${escapeH(strat)} <span class="sub">${periodRange(PERIOD,data).label}</span>`,h,push);
}

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
  for(const acc of ACCOUNT_TABS){
    let a={},pnl=0,label=acc.toUpperCase();
    if(acc==='live'){
      const m=buildMergedData(allData);
      a=m.state.account_info;
      pnl=m.state.today_pnl||0;
      label='LIVE';
    } else {
      const d=allData[acc]||{};
      const s=d.state||{};
      a=s.account_info||{};
      pnl=s.today_pnl||0;
    }
    const cls=pnl>=0?'green':'red';
    const active=acc===SELECTED?'active':'';
    h+=`<button class="acc-tab ${active}" onclick="selectAcc('${acc}')">${label}<span class="acc-pnl ${cls}">${a.equity?'$'+fmt(a.equity):'--'} &middot; ${fmtUsd(pnl,0)}</span></button>`;
  }
  document.getElementById('acc-tabs').innerHTML=h;
}
function selectAcc(acc){SELECTED=acc;localStorage.setItem('hydra-acc',acc);render();}
function selectTab(t){TAB=t;localStorage.setItem('hydra-tab',t);render();}
function selectPeriod(p){PERIOD=p;localStorage.setItem('hydra-period',p);render();}

function renderPeriodTabs(){
  let h='';
  for(const p of PERIODS){
    h+=`<button class="period-chip ${p.id===PERIOD?'active':''}" onclick="selectPeriod('${p.id}')">${p.label}</button>`;
  }
  document.getElementById('period-tabs').innerHTML=h;
}

// === Render: KPI strip ===
function renderKpis(data){
  if(!data||!data.state||!data.state.account_info){
    document.getElementById('kpis').innerHTML='<div class="kpi"><div class="lbl">En attente</div><div class="val">...</div></div>';
    return;
  }
  const s=data.state, a=s.account_info, pos=s.positions||[], hist=data.history||[];
  const range=periodRange(PERIOD,data);
  const trades=getPeriodTrades(data);
  const periodPnl=trades.reduce((s,t)=>s+(t.pnl||0),0);
  const eq=a.equity||0, bal=a.balance||0;
  const flot=pos.reduce((s,p)=>s+(p.pnl||0),0);
  const eqInfo=buildEquity(hist,bal);
  const ddCur=Math.abs(eqInfo.curDd);
  const ddMax=eqInfo.maxDd;
  const ddLimit=SELECTED==='live'?Math.min(...ACCOUNTS.map(a=>MAX_DD[a]||10)):(MAX_DD[SELECTED]||10);
  const ddPct=Math.min(100,ddCur/ddLimit*100);
  let pf=0,wr=0;
  if(trades.length>0){
    const gp=trades.filter(t=>(t.pnl||0)>0).reduce((s,t)=>s+t.pnl,0);
    const gl=trades.filter(t=>(t.pnl||0)<=0).reduce((s,t)=>s+Math.abs(t.pnl),0);
    pf=gl>0?gp/gl:(gp>0?99.99:0);
    wr=trades.filter(t=>(t.pnl||0)>0).length/trades.length*100;
  }

  let h='';
  h+=`<div class="kpi"><div class="lbl">Equity</div><div class="val">$${fmt(eq,0)}</div><div class="sub">Bal $${fmt(bal,0)}</div></div>`;
  h+=`<div class="kpi"><div class="lbl">PnL ${range.label}</div><div class="val ${periodPnl>=0?'green':'red'}">${fmtUsd(periodPnl,2)}</div><div class="sub">${trades.length} trades</div></div>`;
  h+=`<div class="kpi"><div class="lbl">Drawdown</div><div class="val ${ddCur>ddLimit*0.7?'red':''}">${ddCur.toFixed(2)}%</div><div class="dd-bar"><div class="dd-fill" style="width:${ddPct}%"></div></div><div class="sub">limite ${ddLimit}% &middot; max ${ddMax.toFixed(2)}%</div></div>`;
  h+=`<div class="kpi"><div class="lbl">Open</div><div class="val">${pos.length}</div><div class="sub ${flot>=0?'pnl-pos':'pnl-neg'}">${pos.length?fmtUsd(flot,2)+' flot':'-'}</div></div>`;
  h+=`<div class="kpi"><div class="lbl">PF ${range.label}</div><div class="val ${pf>=1.5?'green':pf<1?'red':''}">${pf.toFixed(2)}</div><div class="sub">WR ${wr.toFixed(0)}%</div></div>`;
  h+=`<div class="kpi"><div class="lbl">Total Hist</div><div class="val">${hist.length}</div><div class="sub">${eqInfo.peak>0?'peak $'+fmt(eqInfo.peak,0):'-'}</div></div>`;
  document.getElementById('kpis').innerHTML=h;
}

// === Render: tab nav ===
function renderTabs(data){
  const s=data?.state||{};
  const pos=s.positions||[];
  const periodTrades=getPeriodTrades(data);
  const hist=data?.history||[];
  const btc=data?.bt_compare||{};
  let btCount=0; for(const k of Object.keys(btc))btCount+=(btc[k]?.rows||[]).length;
  const tabs=[
    {id:'home',label:'Home',n:0},
    {id:'today',label:'Trades',n:periodTrades.length},
    {id:'open',label:'Open',n:pos.length},
    {id:'history',label:'Histo',n:hist.length},
    {id:'bt',label:'BT/LV',n:btCount},
    {id:'logs',label:'Logs',n:pos.length+periodTrades.length},
    {id:'legacy',label:'Legacy',n:0},
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

// === Full equity chart with axes, grid, labels ===
function renderEquityChart(points, opts){
  if(!points||points.length<2)return '<div class="empty">Pas assez de points</div>';
  const o=opts||{};
  const baseline=o.baseline;
  const W=800,H=300;
  const PAD_L=64,PAD_R=14,PAD_T=14,PAD_B=32;
  const innerW=W-PAD_L-PAD_R, innerH=H-PAD_T-PAD_B;
  const eqs=points.map(p=>p.e);
  let eMin=eqs[0], eMax=eqs[0];
  for(const v of eqs){if(v<eMin)eMin=v; if(v>eMax)eMax=v;}
  if(baseline!=null){if(baseline<eMin)eMin=baseline; if(baseline>eMax)eMax=baseline;}
  const ePad=(eMax-eMin)*0.08||1;
  const yMin=eMin-ePad, yMax=eMax+ePad, ySpan=yMax-yMin||1;
  const ts=points.map((p,i)=>p.t?new Date(p.t).getTime():(i?Date.now():Date.now()-3600000));
  let tMin=ts[0],tMax=ts[0];
  for(const v of ts){if(v<tMin)tMin=v; if(v>tMax)tMax=v;}
  const tSpan=tMax-tMin||1;
  const xOf=t=>PAD_L+((t-tMin)/tSpan)*innerW;
  const yOf=v=>PAD_T+(1-(v-yMin)/ySpan)*innerH;

  // Y ticks
  const yTicks=5;
  let yAxis='';
  for(let i=0;i<yTicks;i++){
    const v=yMin+(ySpan*i/(yTicks-1));
    const y=yOf(v);
    yAxis+=`<line class="chart-grid" x1="${PAD_L}" x2="${W-PAD_R}" y1="${y}" y2="${y}"/>`;
    yAxis+=`<text class="chart-axis-label" x="${PAD_L-7}" y="${y+3}" text-anchor="end">$${fmt(v,0)}</text>`;
  }

  // X ticks (dates)
  const xTicks=5;
  let xAxis='';
  for(let i=0;i<xTicks;i++){
    const t=tMin+(tSpan*i/(xTicks-1));
    const x=xOf(t);
    xAxis+=`<line class="chart-grid" x1="${x}" x2="${x}" y1="${PAD_T}" y2="${H-PAD_B}"/>`;
    const d=new Date(t);
    const lbl=String(d.getUTCMonth()+1).padStart(2,'0')+'-'+String(d.getUTCDate()).padStart(2,'0');
    xAxis+=`<text class="chart-axis-label" x="${x}" y="${H-PAD_B+15}" text-anchor="middle">${lbl}</text>`;
  }

  // Equity line + area
  let path='', area='';
  for(let i=0;i<points.length;i++){
    const x=xOf(ts[i]), y=yOf(eqs[i]);
    if(!path){path=`M${x.toFixed(1)},${y.toFixed(1)}`; area=`M${x.toFixed(1)},${(H-PAD_B)} L${x.toFixed(1)},${y.toFixed(1)}`;}
    else { path+=` L${x.toFixed(1)},${y.toFixed(1)}`; area+=` L${x.toFixed(1)},${y.toFixed(1)}`; }
  }
  area+=` L${xOf(tMax).toFixed(1)},${(H-PAD_B)} Z`;

  // Baseline line
  let baselineLine='';
  if(baseline!=null && baseline>=yMin && baseline<=yMax){
    const yb=yOf(baseline);
    baselineLine=`<line class="chart-baseline" x1="${PAD_L}" x2="${W-PAD_R}" y1="${yb}" y2="${yb}"/><text class="chart-axis-label" x="${W-PAD_R-3}" y="${yb-3}" text-anchor="end" fill="#9ca3af">start $${fmt(baseline,0)}</text>`;
  }

  // Peak line (max point)
  let peakLine='', peakMarker='';
  let peakIdx=0; for(let i=0;i<eqs.length;i++)if(eqs[i]>eqs[peakIdx])peakIdx=i;
  if(eqs.length>1){
    const yp=yOf(eqs[peakIdx]);
    peakLine=`<line class="chart-peak-line" x1="${PAD_L}" x2="${W-PAD_R}" y1="${yp}" y2="${yp}"/><text class="chart-axis-label" x="${W-PAD_R-3}" y="${yp+12}" text-anchor="end" fill="#059669">peak $${fmt(eqs[peakIdx],0)}</text>`;
    peakMarker=`<circle class="chart-marker peak" cx="${xOf(ts[peakIdx])}" cy="${yp}" r="3.5"/>`;
  }

  // Current marker
  const lastIdx=points.length-1;
  const curMarker=`<circle class="chart-marker" cx="${xOf(ts[lastIdx])}" cy="${yOf(eqs[lastIdx])}" r="4"/>`;

  const grad=`<defs><linearGradient id="eq-grad" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stop-color="#2563eb" stop-opacity="0.3"/><stop offset="100%" stop-color="#2563eb" stop-opacity="0.02"/></linearGradient></defs>`;
  const svg=`<svg class="chart-svg" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet">${grad}${yAxis}${xAxis}<path class="chart-area" d="${area}"/>${baselineLine}${peakLine}<path class="chart-line" d="${path}"/>${peakMarker}${curMarker}</svg>`;

  // Summary line
  const cur=eqs[lastIdx], peak=eqs[peakIdx];
  const dd=peak>0?(cur-peak)/peak*100:0;
  const startEq=baseline!=null?baseline:eqs[0];
  const totalRet=startEq>0?(cur-startEq)/startEq*100:0;
  const summary=`<div class="chart-summary">
    <span>Current <b>$${fmt(cur,0)}</b></span>
    <span>Peak <b class="green">$${fmt(peak,0)}</b></span>
    <span>Min <b class="red">$${fmt(Math.min(...eqs),0)}</b></span>
    <span>DD courant <b class="${dd<0?'red':'green'}">${dd.toFixed(2)}%</b></span>
    <span>Total <b class="${totalRet>=0?'green':'red'}">${(totalRet>=0?'+':'')+totalRet.toFixed(1)}%</b></span>
    <span>${points.length} pts</span>
  </div>`;

  return `<div class="chart-wrap">${svg}</div>${summary}`;
}

// === Render: HOME ===
function renderHome(data){
  const root=document.getElementById('tab-home');
  if(!data||!data.state){root.innerHTML='<div class="empty">Pas de donnees</div>';return;}
  const range=periodRange(PERIOD,data);
  const trades=getPeriodTrades(data);
  const a=data.state.account_info||{};
  const pos=data.state.positions||[];
  const flot=pos.reduce((s,p)=>s+(p.pnl||0),0);
  const total=trades.reduce((s,t)=>s+(t.pnl||0),0);
  const wins=trades.filter(t=>(t.pnl||0)>0);
  const losses=trades.filter(t=>(t.pnl||0)<=0);
  const gp=wins.reduce((s,t)=>s+t.pnl,0);
  const gl=losses.reduce((s,t)=>s+Math.abs(t.pnl),0);
  const pf=gl>0?gp/gl:(gp>0?99.99:0);
  const wr=trades.length?wins.length/trades.length*100:0;
  const maxWin=wins.reduce((m,t)=>Math.max(m,t.pnl),0);
  const maxLoss=losses.reduce((m,t)=>Math.min(m,t.pnl),0);
  const avgPnl=trades.length?total/trades.length:0;

  let h='';
  // Equity chart
  const hist=data.history||[];
  const eqInfo=buildEquity(hist,a.balance||0);
  if(eqInfo.points.length>=2){
    const startBal=eqInfo.points[0].e;
    h+=`<div class="card"><div class="card-title">Equity all-time</div>${renderEquityChart(eqInfo.points,{baseline:startBal})}</div>`;
  }

  // Big summary card
  h+=`<div class="card">
    <div class="card-title">Vue ${range.label}<span class="right ${pnlCls(total)}">${fmtUsd(total,2)}</span></div>
    <div class="drill-grid">
      <div class="drill-cell"><div class="lbl">Trades</div><div class="val">${trades.length}</div></div>
      <div class="drill-cell"><div class="lbl">WR</div><div class="val">${wr.toFixed(0)}%</div></div>
      <div class="drill-cell"><div class="lbl">PF</div><div class="val ${pf>=1?'pnl-pos':'pnl-neg'}">${pf.toFixed(2)}</div></div>
      <div class="drill-cell"><div class="lbl">Avg/trade</div><div class="val ${pnlCls(avgPnl)}">${fmtUsd(avgPnl,2)}</div></div>
      <div class="drill-cell"><div class="lbl">Best</div><div class="val pnl-pos">${fmtUsd(maxWin,2)}</div></div>
      <div class="drill-cell"><div class="lbl">Worst</div><div class="val pnl-neg">${fmtUsd(maxLoss,2)}</div></div>
    </div>
  </div>`;

  // Open positions teaser
  if(pos.length>0){
    h+=`<div class="card"><div class="card-title">Positions ouvertes (${pos.length})<span class="right ${pnlCls(flot)}">${fmtUsd(flot,2)} flot</span></div><div class="toplist">`;
    for(const p of pos){
      h+=`<div class="toprow" onclick="openTradeByKey('op|${p.ticket}',false)">
        <span class="name">${escapeH(p.symbol)}</span>
        <span class="stats">${escapeH(stratOf(p))}<span class="tcard-tf">[${escapeH(tfOf(p))}]</span> &middot; <span class="${dirCls(p.dir)}">${(p.dir||'').toUpperCase()}</span></span>
        <span class="pnl ${pnlCls(p.pnl||0)}">${fmtUsd(p.pnl||0,2)}</span>
      </div>`;
    }
    h+='</div></div>';
  }

  // Per instrument
  const bySym={};
  for(const t of trades){const k=t.symbol||'?';bySym[k]=bySym[k]||{n:0,$:0,w:0};bySym[k].n++;bySym[k].$+=(t.pnl||0);if((t.pnl||0)>0)bySym[k].w++;}
  const symList=Object.entries(bySym).sort((a,b)=>b[1].$-a[1].$);
  if(symList.length>0){
    h+='<div class="card"><div class="card-title">Par instrument<span class="right">'+symList.length+' sym</span></div><div class="toplist">';
    for(const [sym,st] of symList){
      h+=`<div class="toprow" onclick="openInstrumentDrill('${escapeH(sym)}',false)">
        <span class="name">${escapeH(sym)}</span>
        <span class="stats">${st.n}t &middot; WR ${(st.w/st.n*100).toFixed(0)}%</span>
        <span class="pnl ${pnlCls(st.$)}">${fmtUsd(st.$,2)}</span>
      </div>`;
    }
    h+='</div></div>';
  }

  // Per strat
  const byStrat={};
  for(const t of trades){const k=t.comment||'?';byStrat[k]=byStrat[k]||{n:0,$:0,w:0};byStrat[k].n++;byStrat[k].$+=(t.pnl||0);if((t.pnl||0)>0)byStrat[k].w++;}
  const stratList=Object.entries(byStrat).sort((a,b)=>b[1].$-a[1].$);
  if(stratList.length>0){
    h+='<div class="card"><div class="card-title">Par strategie<span class="right">'+stratList.length+' strats</span></div><div class="toplist">';
    for(const [sn,st] of stratList){
      h+=`<div class="toprow" onclick="openStratDrill('${escapeH(sn)}',false)">
        <span class="name">${fmtStratTf(sn)}</span>
        <span class="stats">${st.n}t &middot; WR ${(st.w/st.n*100).toFixed(0)}%</span>
        <span class="pnl ${pnlCls(st.$)}">${fmtUsd(st.$,2)}</span>
      </div>`;
    }
    h+='</div></div>';
  }

  if(trades.length===0&&pos.length===0)h+='<div class="empty">Aucune activite sur la periode</div>';

  root.innerHTML=h;
}

// === Render: TRADES (period-filtered) ===
function renderToday(data){
  const root=document.getElementById('tab-today');
  if(!data||!data.state){root.innerHTML='<div class="empty">Pas de donnees</div>';return;}
  const s=data.state, hist=data.history||[], a=s.account_info||{};
  const range=periodRange(PERIOD,data);
  const trades=getPeriodTrades(data);
  const periodPnl=trades.reduce((s,t)=>s+(t.pnl||0),0);
  const eqInfo=buildEquity(hist,a.balance||0);
  const recent=eqInfo.points.slice(-Math.min(100,eqInfo.points.length));
  let h='';
  if(recent.length>=2){
    h+=`<div class="card"><div class="card-title">Equity (${recent.length} derniers points)</div>${renderEquityChart(recent)}</div>`;
  }
  h+=`<div class="card"><div class="card-title">Trades ${range.label}<span class="right">${trades.length} trades &middot; ${fmtUsd(periodPnl,2)}</span></div>`;
  if(trades.length===0)h+='<div class="empty">Aucun trade sur la periode</div>';
  else{
    const sorted=[...trades].sort((a,b)=>(b.time_open||'').localeCompare(a.time_open||''));
    h+='<div class="list">';
    for(const t of sorted){
      const pnl=t.pnl||0;
      h+=`<div class="tcard" onclick="openTradeByKey('lv|${t.ticket}',false)">
        <div class="tcard-head">
          <div><span class="tcard-sym">${escapeH(t.symbol)}</span> <span class="tcard-strat">${escapeH(stratOf(t))}<span class="tcard-tf">[${escapeH(tfOf(t))}]</span></span></div>
          <span class="tcard-pnl ${pnlCls(pnl)}">${fmtUsd(pnl,2)}</span>
        </div>
        <div class="tcard-meta">
          <span class="${dirCls(t.dir)}">${(t.dir||'').toUpperCase()}</span>
          <span>${fmt(t.entry,2)} &rarr; ${fmt(t.exit,2)}</span>
          <span>${t.volume} lots</span>
          <span class="tcard-time">${dateD(t.time_open)} ${timeHM(t.time_open)}-${timeHM(t.time_close)}</span>
        </div>
      </div>`;
    }
    h+='</div>';
  }
  h+='</div>';
  root.innerHTML=h;
}

// Helper: rend une carte position (SL toujours a gauche, TP toujours a droite)
function renderPositionCard(p,opts){
  const o=opts||{};
  const isLong=p.dir==='long';
  const cls=isLong?'long':'short';
  const sl=p.sl||p.entry;
  const tp=p.tp||0;
  const pnl=p.pnl||0;
  // Mapping commun: gauche=SL, droite=TP. Loss zone gauche, profit zone droite.
  // Pour long: bar low=SL (price), bar high=TP (price). Position lineaire normale.
  // Pour short: SL>entry>TP en prix, mais visuellement on inverse pour avoir SL a gauche.
  let curPos,entryPos;
  if(isLong){
    const lo=sl, hi=tp>0?tp:p.entry+(p.entry-sl);
    curPos=hi>lo?(p.current-lo)/(hi-lo)*100:50;
    entryPos=hi>lo?(p.entry-lo)/(hi-lo)*100:50;
  } else {
    const tpPx=tp>0?tp:p.entry-(sl-p.entry);
    const lo=tpPx, hi=sl;
    // Inverser: SL (hi) -> 0%, TP (lo) -> 100%
    curPos=hi>lo?100-(p.current-lo)/(hi-lo)*100:50;
    entryPos=hi>lo?100-(p.entry-lo)/(hi-lo)*100:50;
  }
  curPos=Math.max(2,Math.min(98,curPos));
  // Loss zone: SL a entry (gauche), Profit zone: entry a TP (droite)
  const lossWidth=entryPos;
  const profitWidth=100-entryPos;
  const tOpen=p.time_open||'';
  const elapsed=tOpen?Math.round((Date.now()-new Date(tOpen).getTime())/60000):0;
  const elapsedStr=elapsed>=60?`${Math.floor(elapsed/60)}h${(elapsed%60).toString().padStart(2,'0')}`:`${elapsed}m`;
  const accBadge=o.showAcc&&p._acc?`<span class="tcard-time" style="background:#1a1a2e;color:#fff;padding:1px 6px;border-radius:4px;font-size:10px;font-weight:700;text-transform:uppercase">${p._acc}</span>`:'';
  return `<div class="tcard pos-card ${cls}" onclick="openTradeByKey('op|${p.ticket}',false)">
    <div class="tcard-head">
      <div>${accBadge?accBadge+' ':''}<span class="tcard-sym">${escapeH(p.symbol)}</span> <span class="tcard-strat">${escapeH(stratOf(p))}<span class="tcard-tf">[${escapeH(tfOf(p))}]</span></span> <span class="${dirCls(p.dir)}">${(p.dir||'').toUpperCase()}</span></div>
      <span class="tcard-pnl ${pnlCls(pnl)}">${fmtUsd(pnl,2)}</span>
    </div>
    <div class="pos-bar">
      <div class="zone-loss" style="left:0%;width:${lossWidth}%"></div>
      <div class="zone-profit" style="left:${entryPos}%;width:${profitWidth}%"></div>
      <div class="marker" style="left:${curPos}%"></div>
      <span class="label-sl">SL ${fmt(sl,2)}</span>
      <span class="label-entry" style="left:${entryPos}%">${fmt(p.entry,2)}</span>
      ${tp>0?`<span class="label-tp">TP ${fmt(tp,2)}</span>`:''}
    </div>
    <div class="tcard-meta">
      <span>Now ${fmt(p.current,2)}</span>
      <span>${p.volume} lots</span>
      <span class="tcard-time">${elapsedStr}</span>
    </div>
  </div>`;
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
    const showAcc=SELECTED==='live';
    for(const p of pos){h+=renderPositionCard(p,{showAcc});}
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

  // Equity full chart
  if(eqInfo.points.length>1){
    const startBal=eqInfo.points[0].e;
    h+=`<div class="card"><div class="card-title">Equity all-time<span class="right">max DD ${eqInfo.maxDd.toFixed(2)}%</span></div>${renderEquityChart(eqInfo.points,{baseline:startBal})}</div>`;
  }

  // Recent trades
  h+=`<div class="card"><div class="card-title">${hist.length} trades historique</div>`;
  if(hist.length===0){h+='<div class="empty">Aucun trade</div>';}
  else{
    const sorted=[...hist].sort((a,b)=>(b.time_close||'').localeCompare(a.time_close||'')).slice(0,40);
    h+='<div class="list">';
    for(const t of sorted){
      const pnl=t.pnl||0;
      h+=`<div class="tcard" onclick="openTradeByKey('lv|${t.ticket}',false)">
        <div class="tcard-head">
          <div><span class="tcard-sym">${escapeH(t.symbol)}</span> <span class="tcard-strat">${escapeH(stratOf(t))}<span class="tcard-tf">[${escapeH(tfOf(t))}]</span></span></div>
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
  for(const symKey of syms){
    const info=btc[symKey];
    const rows=info?.rows||[];
    // _sym dans le merge LIVE = unitKey 'sym|tf', sinon symKey lui-meme = unitKey
    const unitKey=info?._sym||symKey;
    const realSym=info?.symbol||unitKey.split('|')[0];
    const realTf=info?.tf||unitKey.split('|')[1]||'15m';
    const realAcc=info?._acc;
    for(const row of rows){
      if(row.bt&&row.lv){
        matched++;
        const d=row.delta||0;
        sumAbsDelta+=Math.abs(d);
        topDiv.push({sym:realSym,tf:realTf,acc:realAcc,strat:row.strat,delta:d,bt:row.bt.pnl_r,lv:row.lv.pnl_r});
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
      const symLbl=t.acc?`[${t.acc}] ${t.sym}`:t.sym;
      h+=`<div class="tcard" onclick="openTradeByKey('bt|${escapeH(t.sym)}|${escapeH(t.tf)}|${escapeH(t.strat)}',false)">
        <div class="tcard-head">
          <div><span class="tcard-sym">${escapeH(symLbl)}</span> <span class="tcard-tf">[${escapeH(t.tf)}]</span> <span class="tcard-strat">${escapeH(t.strat)}</span></div>
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
  for(const symKey of syms.sort()){
    const info=btc[symKey];
    const rows=info?.rows||[];
    const matchedRows=rows.filter(r=>r.bt&&r.lv);
    if(rows.length===0)continue;
    const sumBt=rows.reduce((s,r)=>s+(r.bt?.pnl_r||0),0);
    const sumLv=rows.reduce((s,r)=>s+(r.lv?.pnl_r||0),0);
    const sumDelta=matchedRows.reduce((s,r)=>s+(r.delta||0),0);
    const atr=info.atr||0;
    const realSym=info._sym||symKey;
    const realAcc=info._acc;
    const symLbl=realAcc?`[${realAcc}] ${realSym}`:realSym;
    h+=`<div class="tcard" onclick="openInstrumentDrill('${escapeH(realSym)}',false)">
      <div class="tcard-head">
        <span class="tcard-sym">${escapeH(symLbl)}</span>
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

// === Render: LIVE (positions ouvertes toutes props, presentation cards style Open) ===
function renderLive(){
  const root=document.getElementById('tab-live');
  const positions=[];
  for(const acc of ACCOUNTS){
    const d=LAST[acc]||{};
    if(!d.state)continue;
    for(const p of (d.state.positions||[])){
      positions.push({...p,_acc:acc});
    }
  }
  positions.sort((a,b)=>(a._acc||'').localeCompare(b._acc||'')||(a.time_open||'').localeCompare(b.time_open||''));

  let totalFlot=0,totalEquity=0,totalBalance=0;
  const byAcc={};
  for(const acc of ACCOUNTS){
    const d=LAST[acc]||{};
    const a=d.state?.account_info||{};
    const flot=(d.state?.positions||[]).reduce((s,p)=>s+(p.pnl||0),0);
    byAcc[acc]={count:(d.state?.positions||[]).length,flot,equity:a.equity||0,balance:a.balance||0};
    totalFlot+=flot;
    totalEquity+=a.equity||0;
    totalBalance+=a.balance||0;
  }

  let h='';
  h+='<div class="kpis" style="margin-bottom:14px">';
  h+=`<div class="kpi"><div class="lbl">Equity totale</div><div class="val">$${fmt(totalEquity,0)}</div><div class="sub">balance $${fmt(totalBalance,0)}</div></div>`;
  h+=`<div class="kpi"><div class="lbl">PnL flottant</div><div class="val ${totalFlot>=0?'green':'red'}">${fmtUsd(totalFlot,2)}</div><div class="sub">${positions.length} positions</div></div>`;
  for(const acc of ACCOUNTS){
    const a=byAcc[acc];
    h+=`<div class="kpi"><div class="lbl">${acc.toUpperCase()}</div><div class="val">${a.count}</div><div class="sub ${a.flot>=0?'pnl-pos':'pnl-neg'}">${fmtUsd(a.flot,2)} flot</div></div>`;
  }
  h+='</div>';

  if(positions.length===0){
    h+='<div class="card"><div class="empty">Aucune position ouverte sur aucune prop</div></div>';
    root.innerHTML=h;
    return;
  }

  h+=`<div class="card"><div class="card-title">${positions.length} position(s) ouverte(s)<span class="right ${totalFlot>=0?'pnl-pos':'pnl-neg'}">${fmtUsd(totalFlot,2)} flot</span></div><div class="list">`;
  for(const p of positions){h+=renderPositionCard(p,{showAcc:true});}
  h+='</div></div>';

  root.innerHTML=h;
}

// === Render: LEGACY (vue tableaux complete style ancien dashboard) ===
function renderLegacy(data){
  const root=document.getElementById('tab-legacy');
  if(!data||!data.state||!data.state.account_info){root.innerHTML='<div class="empty">Pas de donnees</div>';return;}
  const s=data.state, a=s.account_info||{}, pos=s.positions||[], trades=s.today_trades||[], candles=s.candles||{}, hist=data.history||[];
  let h='<div class="card">';
  // Header
  h+=`<div class="card-title">${SELECTED.toUpperCase()} <span class="right">${escapeH(s.broker||'')} &middot; ${timeHM(s.ts)} UTC</span></div>`;
  // Metrics
  h+=`<div class="drill-grid">
    <div class="drill-cell"><div class="lbl">Balance</div><div class="val">$${fmt(a.balance)}</div></div>
    <div class="drill-cell"><div class="lbl">Equity</div><div class="val">$${fmt(a.equity)}</div></div>
    <div class="drill-cell"><div class="lbl">PnL Jour</div><div class="val ${(s.today_pnl||0)>=0?'pnl-pos':'pnl-neg'}">${fmtUsd(s.today_pnl||0,2)}</div></div>
    <div class="drill-cell"><div class="lbl">Trades</div><div class="val">${s.today_count||0}</div></div>
  </div>`;
  // Positions table
  h+='<div class="drill-section"><h4>Positions ouvertes ('+pos.length+')</h4>';
  if(pos.length===0)h+='<div class="empty">Aucune position</div>';
  else{
    h+='<div style="overflow-x:auto"><table style="font-size:11px"><tr><th>Sym</th><th>Strat</th><th>Dir</th><th>Entry</th><th>Current</th><th>SL</th><th>TP</th><th>PnL</th><th>Lots</th></tr>';
    for(const p of pos){
      h+=`<tr onclick="openTradeByKey('op|${p.ticket}',false)" class="clickable">
        <td class="sym">${escapeH(p.symbol)}</td><td class="strat-name">${escapeH(stratOf(p))}<span class="tcard-tf">[${escapeH(tfOf(p))}]</span></td>
        <td class="${dirCls(p.dir)}">${(p.dir||'').toUpperCase()}</td>
        <td>${fmt(p.entry,2)}</td><td>${fmt(p.current,2)}</td><td>${fmt(p.sl,2)}</td><td>${p.tp?fmt(p.tp,2):'-'}</td>
        <td class="${pnlCls(p.pnl||0)}">${fmtUsd(p.pnl||0,2)}</td><td>${fmt(p.volume,2)}</td>
      </tr>`;
    }
    h+='</table></div>';
  }
  h+='</div>';
  // BT vs Live per (instrument, TF)
  const btc=data.bt_compare||{};
  const btSyms=Object.keys(btc).sort();
  for(const symKey of btSyms){
    const info=btc[symKey]||{};
    const rows=(info.rows||[]).filter(r=>r.bt||r.lv).sort((a,b)=>a.strat.localeCompare(b.strat));
    if(rows.length===0)continue;
    // unitKey 'sym|tf' -> separer
    const unitKey=info._sym||symKey;
    const sym=info.symbol||unitKey.split('|')[0];
    const tf=info.tf||unitKey.split('|')[1]||'15m';
    const symLbl=info._acc?`[${info._acc}] ${sym} [${tf}]`:`${sym} [${tf}]`;
    let totalBtR=0,totalLvR=0,totalDelta=0,totalUsd=0;
    h+=`<div class="legacy-section-title"><span class="sym">${escapeH(symLbl)}</span><span class="meta">${rows.length} strats &middot; ATR ${fmt(info.atr,2)}</span></div>`;
    h+='<div class="legacy-wrap"><table class="legacy-tbl">';
    h+='<thead><tr>';
    h+='<th class="col-strat" rowspan="2">Strat</th>';
    h+='<th class="h-bt sep-bt" colspan="6" style="text-align:center;border-bottom:1px solid #e8eaed">BACKTEST</th>';
    h+='<th class="h-lv sep-lv" colspan="7" style="text-align:center;border-bottom:1px solid #e8eaed">LIVE</th>';
    h+='<th class="h-delta sep-delta" rowspan="2">&Delta;R</th>';
    h+='</tr><tr>';
    h+='<th class="sep-bt">Dir</th><th>Entry</th><th>Exit</th><th>R</th><th>In</th><th>Out</th>';
    h+='<th class="sep-lv">Dir</th><th>Entry</th><th>Exit</th><th>R</th><th>$</th><th>In</th><th>Out</th>';
    h+='</tr></thead><tbody>';
    for(const row of rows){
      const bt=row.bt,lv=row.lv;
      const m='<span style="color:#9ca3af">-</span>';
      let bD=m,bE=m,bX=m,bR=m,bIn=m,bOut=m,lD=m,lE=m,lX=m,lR=m,lUsd=m,lIn=m,lOut=m,dl=m;
      if(bt){
        bD=`<span class="${dirCls(bt.dir)}">${(bt.dir||'').toUpperCase()}</span>`;
        bE=fmt(bt.entry,2); bX=fmt(bt.exit,2);
        const rv=bt.pnl_r||0; totalBtR+=rv;
        bR=`<span class="${rv>=0?'pnl-pos':'pnl-neg'}">${(rv>=0?'+':'')+rv.toFixed(2)}</span>`;
        bIn=bt.entry_time?timeHM(bt.entry_time):m;
        bOut=bt.exit_time?timeHM(bt.exit_time):m;
      }
      if(lv){
        lD=`<span class="${dirCls(lv.dir)}">${(lv.dir||'').toUpperCase()}</span>`;
        lE=fmt(lv.entry,2); lX=fmt(lv.exit,2);
        const rv=lv.pnl_r||0; totalLvR+=rv;
        lR=`<span class="${rv>=0?'pnl-pos':'pnl-neg'}">${(rv>=0?'+':'')+rv.toFixed(2)}</span>`;
        const usd=lv.pnl_usd||0; totalUsd+=usd;
        lUsd=`<span class="${usd>=0?'pnl-pos':'pnl-neg'}">${fmtUsd(usd,0)}</span>`;
        lIn=lv.entry_time?timeHM(lv.entry_time):m;
        lOut=lv.exit_time?timeHM(lv.exit_time):m;
      }
      let rowCls='';
      if(row.delta!=null){
        const d=row.delta; totalDelta+=d;
        dl=`<b class="${d>=0?'pnl-pos':'pnl-neg'}">${(d>=0?'+':'')+d.toFixed(2)}</b>`;
        if(d<=-1.0)rowCls='row-bad';
        else if(d<=-0.5)rowCls='row-warn';
        else if(d>=0.5)rowCls='row-good';
      }
      const clickKey=lv&&lv.ticket?`lv|${lv.ticket}`:bt?`bt|${escapeH(sym)}|${escapeH(tf)}|${escapeH(row.strat)}`:'';
      const onclick=clickKey?`onclick="openTradeByKey('${clickKey}',false)"`:'';
      h+=`<tr ${onclick} ${clickKey?'class="clickable '+rowCls+'"':'class="'+rowCls+'"'}>
        <td class="col-strat">${escapeH(row.strat)}</td>
        <td class="sep-bt">${bD}</td><td>${bE}</td><td>${bX}</td><td>${bR}</td><td>${bIn}</td><td>${bOut}</td>
        <td class="sep-lv">${lD}</td><td>${lE}</td><td>${lX}</td><td>${lR}</td><td>${lUsd}</td><td>${lIn}</td><td>${lOut}</td>
        <td class="sep-delta">${dl}</td>
      </tr>`;
    }
    h+='</tbody><tfoot><tr>';
    h+='<td class="col-strat">TOTAL</td>';
    h+=`<td class="sep-bt" colspan="3"></td>
      <td><span class="${totalBtR>=0?'pnl-pos':'pnl-neg'}">${(totalBtR>=0?'+':'')+totalBtR.toFixed(2)}R</span></td>
      <td colspan="2"></td>
      <td class="sep-lv" colspan="3"></td>
      <td><span class="${totalLvR>=0?'pnl-pos':'pnl-neg'}">${(totalLvR>=0?'+':'')+totalLvR.toFixed(2)}R</span></td>
      <td><span class="${totalUsd>=0?'pnl-pos':'pnl-neg'}">${fmtUsd(totalUsd,0)}</span></td>
      <td colspan="2"></td>
      <td class="sep-delta"><span class="${totalDelta>=0?'pnl-pos':'pnl-neg'}">${(totalDelta>=0?'+':'')+totalDelta.toFixed(2)}R</span></td>`;
    h+='</tr></tfoot></table></div>';
  }
  // Candles
  const syms=Object.keys(candles).filter(sy=>candles[sy]&&candles[sy].close);
  if(syms.length>0){
    h+='<div class="drill-section"><h4>Dernieres bougies</h4>';
    for(const sym of syms){
      const c=candles[sym]; const rng=(c.high-c.low).toFixed(1);
      h+=`<div class="candle-row" style="display:flex;justify-content:space-between;padding:4px 0;font-size:11px;color:#4b5563;border-bottom:1px solid #f9fafb">
        <span style="font-weight:600;color:#1a1a2e;min-width:80px">${escapeH(sym)}</span>
        <span>${timeHM(c.time)}</span>
        <span>O ${fmt(c.open,1)}</span><span>H ${fmt(c.high,1)}</span><span>L ${fmt(c.low,1)}</span><span>C ${fmt(c.close,1)}</span>
        <span style="font-weight:600">R ${rng}</span>
      </div>`;
    }
    h+='</div>';
  }
  // History (last 50)
  if(hist.length>0){
    const tp=hist.reduce((s,t)=>s+(t.pnl||0),0);
    const w=hist.filter(t=>(t.pnl||0)>0).length;
    const wr=(w/hist.length*100).toFixed(0);
    h+=`<div class="drill-section"><h4>Historique (${hist.length} trades) &mdash; WR ${wr}% &mdash; PnL ${fmtUsd(tp,2)}</h4>`;
    h+='<div style="overflow-x:auto;max-height:400px"><table style="font-size:11px"><tr><th>Date</th><th>Sym</th><th>Strat</th><th>Dir</th><th>Entry</th><th>Exit</th><th>PnL</th></tr>';
    for(const t of [...hist].sort((a,b)=>(b.time_close||'').localeCompare(a.time_close||'')).slice(0,50)){
      h+=`<tr onclick="openTradeByKey('lv|${t.ticket}',false)" class="clickable">
        <td>${dateD(t.time_close).slice(5)} ${timeHM(t.time_close)}</td>
        <td class="sym">${escapeH(t.symbol)}</td><td class="strat-name">${escapeH(stratOf(t))}<span class="tcard-tf">[${escapeH(tfOf(t))}]</span></td>
        <td class="${dirCls(t.dir)}">${(t.dir||'').toUpperCase()}</td>
        <td>${fmt(t.entry,2)}</td><td>${fmt(t.exit,2)}</td>
        <td class="${pnlCls(t.pnl||0)}">${fmtUsd(t.pnl||0,2)}</td>
      </tr>`;
    }
    h+='</table></div></div>';
  }
  h+='</div>';
  root.innerHTML=h;
}

// === Render: LOGS (entries from positions + exits from period trades) ===
function renderLogs(data){
  const root=document.getElementById('tab-logs');
  if(!data||!data.state){root.innerHTML='<div class="empty">Pas de donnees</div>';return;}
  const range=periodRange(PERIOD,data);
  const pos=data.state.positions||[];
  const periodTrades=getPeriodTrades(data);
  const events=[];
  // Open positions: only show if today period (they're current, not historical)
  if(PERIOD==='today'){
    for(const p of pos){
      events.push({t:p.time_open,type:'entry',sym:p.symbol,strat:stratOf(p),tf:tfOf(p),dir:p.dir,pnl:p.pnl,extra:'OPEN',ticket:p.ticket});
    }
  }
  for(const t of periodTrades){
    events.push({t:t.time_close,type:(t.pnl||0)>=0?'exit-w':'exit-l',sym:t.symbol,strat:stratOf(t),tf:tfOf(t),dir:t.dir,pnl:t.pnl,extra:(t.pnl>=0?'WIN ':'LOSS ')+fmtUsd(t.pnl,2),ticket:t.ticket});
  }
  events.sort((a,b)=>(b.t||'').localeCompare(a.t||''));
  let h=`<div class="card"><div class="card-title">Evenements ${range.label} (${events.length})</div>`;
  if(events.length===0){h+='<div class="empty">Aucun evenement</div>';}
  else{
    for(const e of events.slice(0,150)){
      const lbl=e.type==='entry'?'ENTRY':e.type==='exit-w'?'WIN':'LOSS';
      const showDate=range.from!==range.to;
      const key=e.type==='entry'?`op|${e.ticket}`:`lv|${e.ticket}`;
      h+=`<div class="log-row" onclick="openTradeByKey('${key}',false)">
        <span class="log-time">${showDate?dateD(e.t).slice(5)+' ':''}${timeHM(e.t)}</span>
        <span class="log-tag ${e.type}">${lbl}</span>
        <span class="tcard-sym">${escapeH(e.sym)}</span>
        <span class="tcard-strat">${escapeH(e.strat)}</span><span class="tcard-tf">[${escapeH(e.tf||'')}]</span>
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
  renderAccTabs(LAST);
  // Show / hide controls based on account selection
  document.querySelectorAll('.tab-content').forEach(el=>el.classList.remove('active'));
  if(SELECTED==='live'){
    document.getElementById('period-tabs').style.display='none';
    document.getElementById('tabs').style.display='none';
    document.getElementById('kpis').style.display='none';
    document.getElementById('tab-live').classList.add('active');
    renderLive();
    return;
  }
  document.getElementById('period-tabs').style.display='';
  document.getElementById('tabs').style.display='';
  document.getElementById('kpis').style.display='';
  renderPeriodTabs();
  const data=getAccData();
  renderKpis(data);
  renderTabs(data);
  document.getElementById('tab-'+TAB).classList.add('active');
  if(TAB==='home')renderHome(data);
  else if(TAB==='today')renderToday(data);
  else if(TAB==='open')renderOpen(data);
  else if(TAB==='history')renderHistory(data);
  else if(TAB==='bt')renderBT(data);
  else if(TAB==='logs')renderLogs(data);
  else if(TAB==='legacy')renderLegacy(data);
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
