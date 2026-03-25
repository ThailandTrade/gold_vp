"""Compare backtest vs live trades for today."""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd, numpy as np, json
from dotenv import load_dotenv; load_dotenv()
from phase1_poc_calculator import get_conn
from strats import detect_all, compute_indicators, sim_exit_custom
from strat_exits import STRAT_EXITS, DEFAULT_EXIT
from config_icm import PORTFOLIO
from datetime import date, datetime, timezone

OPEN_STRATS = {'TOK_FADE','TOK_PREVEXT','LON_GAP','LON_BIGGAP','LON_KZ','LON_TOKEND','LON_PREV','NY_GAP','NY_LONEND','NY_LONMOM','NY_DAYMOM'}

conn = get_conn(); conn.autocommit = True
cur = conn.cursor()
cur.execute("SELECT ts, open, high, low, close FROM candles_mt5_xauusd_5m ORDER BY ts DESC LIMIT 2000")
rows = cur.fetchall(); cur.close(); conn.close()
df = pd.DataFrame(rows, columns=['ts','open','high','low','close']).sort_values('ts').reset_index(drop=True)
df['ts_dt'] = pd.to_datetime(df['ts'], unit='ms', utc=True)
for c in ['open','high','low','close']: df[c] = df[c].astype(float)
df['date'] = df['ts_dt'].dt.date
df = compute_indicators(df)

today = datetime.now(timezone.utc).date()
yc = df[df['date'] < today].copy()
yc['pc'] = yc['close'].shift(1)
yc['tr'] = np.maximum(yc['high']-yc['low'], np.maximum(abs(yc['high']-yc['pc']), abs(yc['low']-yc['pc'])))
yc['atr'] = yc['tr'].ewm(span=14, adjust=False).mean()
atr = float(yc['atr'].iloc[-1])

last_day = yc['date'].iloc[-1]
dc = yc[yc['date']==last_day]
prev_day_data = {'open':float(dc.iloc[0]['open']),'close':float(dc.iloc[-1]['close']),
                 'high':float(dc['high'].max()),'low':float(dc['low'].min()),
                 'range':float(dc['high'].max()-dc['low'].min())}

# Backtest signals
trig = {}
signals = []
for ci in range(len(df)):
    row = df.iloc[ci]; ct = row['ts_dt']; d = ct.date()
    if d != today: continue
    hour = ct.hour + ct.minute / 60.0
    ds = pd.Timestamp(d.year,d.month,d.day,0,0,tz='UTC')
    te = pd.Timestamp(d.year,d.month,d.day,6,0,tz='UTC')
    ls = pd.Timestamp(d.year,d.month,d.day,8,0,tz='UTC')
    ns = pd.Timestamp(d.year,d.month,d.day,14,30,tz='UTC')
    tv = df[(df['ts_dt']>=ds)&(df['ts_dt']<=ct)]
    tok = tv[tv['ts_dt']<te]; lon = tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<ns)]
    def add(sn, d_dir, e):
        if sn not in PORTFOLIO: return
        signals.append((ci, sn, d_dir, e, str(ct)))
    detect_all(df, ci, row, ct, d, hour, atr, trig, tv, tok, lon, prev_day_data, add)

# Simulate with conflict filtering (like eval_combo)
bt_trades = []
active_positions = []
for ci, sn, d_dir, entry, ct_str in signals:
    is_open = sn in OPEN_STRATS
    exit_cfg = STRAT_EXITS.get(sn, DEFAULT_EXIT)
    etype, p1, p2, p3 = exit_cfg
    b, ex = sim_exit_custom(df, ci, entry, d_dir, atr, etype, p1, p2, p3, check_entry_candle=is_open)
    xi = ci + b
    di = 1 if d_dir == 'long' else -1
    active_positions = [(axi, ad) for axi, ad in active_positions if axi >= ci]
    if any(ad != di for _, ad in active_positions):
        bt_trades.append({'strat':sn,'dir':d_dir,'entry':entry,'exit':ex,'pnl_oz':0,
                          'bars':b,'entry_time':ct_str,'exit_time':str(df.iloc[min(xi,len(df)-1)]['ts_dt']),
                          'skipped':'conflit'})
        continue
    pnl = (ex - entry) if d_dir == 'long' else (entry - ex)
    active_positions.append((xi, di))
    bt_trades.append({'strat':sn,'dir':d_dir,'entry':entry,'exit':ex,'pnl_oz':pnl,
                      'bars':b,'entry_time':ct_str,'exit_time':str(df.iloc[min(xi,len(df)-1)]['ts_dt']),
                      'skipped':None})

# Live trades
with open('paper_icmarkets.json') as f:
    state = json.load(f)
live_trades = [t for t in state['trades'] if t['entry_time'].startswith(str(today))]
live_open = state['open_positions']

# Build maps
bt_map = {}
for t in bt_trades: bt_map.setdefault(t['strat'], []).append(t)
lv_map = {}
for t in live_trades: lv_map.setdefault(t['strat'], []).append(t)
all_sn = sorted(set(list(bt_map.keys()) + list(lv_map.keys())))

print(f"ATR: {atr:.2f} | Date: {today}")
bt_active = len([t for t in bt_trades if not t['skipped']])
bt_skip = len([t for t in bt_trades if t['skipped']])
print(f"Backtest: {bt_active} trades ({bt_skip} skipped) | Live: {len(live_trades)} trades + {len(live_open)} open")
print()

print(f"{'Strat':>20s} | {'BT':>6s} {'Entry':>10s} {'PnL oz':>9s} {'Time':>14s} | {'LV':>6s} {'Entry':>10s} {'PnL oz':>9s} {'Time':>14s} | {'E.diff':>7s} {'P.diff':>8s}")
print("-"*130)

bt_total = 0; lv_total = 0
for sn in all_sn:
    bts = bt_map.get(sn, [])
    lvs = lv_map.get(sn, [])
    n = max(len(bts), len(lvs))
    for i in range(n):
        bt = bts[i] if i < len(bts) else None
        lv = lvs[i] if i < len(lvs) else None

        if bt and bt['skipped']:
            bt_str = f"{bt['dir']:>6s} {bt['entry']:>10.2f} {'SKIP':>9s} {bt['entry_time'][11:16]:>5s}         "
        elif bt:
            bt_str = f"{bt['dir']:>6s} {bt['entry']:>10.2f} {bt['pnl_oz']:>+9.2f} {bt['entry_time'][11:16]:>5s}->{bt['exit_time'][11:16]:>5s}"
        else:
            bt_str = f"{'---':>6s} {'---':>10s} {'---':>9s} {'---':>14s}"

        if lv:
            lv_str = f"{lv['dir']:>6s} {lv['entry']:>10.2f} {lv['pnl_oz']:>+9.2f} {lv['entry_time'][11:16]:>5s}->{lv['exit_time'][11:16]:>5s}"
        else:
            lv_str = f"{'---':>6s} {'---':>10s} {'---':>9s} {'---':>14s}"

        if bt and not bt['skipped'] and lv:
            ediff = f"{lv['entry']-bt['entry']:>+7.2f}"
            pdiff = f"{lv['pnl_oz']-bt['pnl_oz']:>+8.2f}"
            bt_total += bt['pnl_oz']; lv_total += lv['pnl_oz']
        elif bt and bt['skipped'] and not lv:
            ediff = f"{'SKIP':>7s}"; pdiff = f"{'OK':>8s}"
        elif bt and bt['skipped'] and lv:
            ediff = f"{'BT.SKP':>7s}"; pdiff = f"{'':>8s}"
            lv_total += lv['pnl_oz']
        elif bt and not lv:
            ediff = f"{'LV.MIS':>7s}"; pdiff = f"{'':>8s}"
            bt_total += bt['pnl_oz']
        elif lv and not bt:
            ediff = f"{'BT.MIS':>7s}"; pdiff = f"{'':>8s}"
            lv_total += lv['pnl_oz']
        else:
            ediff = ''; pdiff = ''

        print(f"{sn:>20s} | {bt_str} | {lv_str} | {ediff} {pdiff}")

print("-"*130)
print(f"{'TOTAL':>20s} | {'':>6s} {'':>10s} {bt_total:>+9.2f} {'':>14s} | {'':>6s} {'':>10s} {lv_total:>+9.2f} {'':>14s} | {'':>7s} {lv_total-bt_total:>+8.2f}")

if live_open:
    print(f"\nPositions encore ouvertes (live):")
    for p in live_open:
        print(f"  {p['strat']:>22s} {p['strat_dir']:>6s} entry={p['entry']:.2f} stop={p['stop']:.2f} trail={p.get('trail_active',False)}")
