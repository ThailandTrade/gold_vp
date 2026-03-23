"""Compare TPSL: TP sur close (ancien) vs TP sur high/low au target (corrige)."""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
from dotenv import load_dotenv; load_dotenv()
from phase1_poc_calculator import get_conn, compute_atr, get_trading_days
from phase3_analyze import load_candles_5m
from strats import compute_indicators, detect_all
from strat_exits import STRAT_EXITS, DEFAULT_EXIT

conn = get_conn()
candles = load_candles_5m(conn)
daily_atr, global_atr = compute_atr(conn)
trading_days = get_trading_days(conn)
cur = conn.cursor()
cur.execute("""SELECT DATE_TRUNC('month', time), AVG(ask-bid) FROM market_ticks_xauusd WHERE ask>bid AND ask-bid<10 GROUP BY 1""")
monthly_spread = {r[0].strftime("%Y-%m"): float(r[1]) for r in cur.fetchall()}
cur.close(); conn.close()
avg_sp = np.mean(list(monthly_spread.values()))

def prev_day(day):
    for di, d in enumerate(trading_days):
        if d >= day: return trading_days[di-1] if di > 0 else None
    return None
def get_sp(day):
    return 2 * monthly_spread.get(str(day.year)+"-"+str(day.month).zfill(2), avg_sp)

OPEN_STRATS = {'TOK_FADE','TOK_PREVEXT','LON_GAP','LON_BIGGAP','LON_KZ','LON_TOKEND','LON_PREV','NY_GAP','NY_LONEND','NY_LONMOM','NY_DAYMOM'}
PORTFOLIO = ['PO3_SWEEP','ALL_3SOLDIERS','LON_KZ','LON_TOKEND','ALL_PSAR_EMA','ALL_FVG_BULL',
             'ALL_CONSEC_REV','ALL_MACD_RSI','ALL_FIB_618','TOK_BIG','TOK_2BAR']

c = candles.copy()
c = compute_indicators(c)

def sim_tpsl_old(cdf, pos, entry, d, atr, sl_val, tp_val, check_entry):
    """Ancien: TP sur CLOSE, exit au CLOSE."""
    stop = entry + sl_val*atr if d == 'short' else entry - sl_val*atr
    target = entry + tp_val*atr if d == 'long' else entry - tp_val*atr
    start = 0 if check_entry else 1
    for j in range(start, min(288, len(cdf)-pos)):
        b = cdf.iloc[pos+j]
        if j == 0:
            if d == 'long' and b['low'] <= stop: return j, stop
            if d == 'short' and b['high'] >= stop: return j, stop
            continue
        if d == 'long':
            if b['low'] <= stop: return j, stop
            if b['close'] >= target: return j, b['close']
        else:
            if b['high'] >= stop: return j, stop
            if b['close'] <= target: return j, b['close']
    n = min(288, len(cdf)-pos-1)
    if n > 0: return n, cdf.iloc[pos+n]['close']
    return 1, entry

def sim_tpsl_new(cdf, pos, entry, d, atr, sl_val, tp_val, check_entry):
    """Corrige: TP sur HIGH/LOW, exit au TARGET."""
    stop = entry + sl_val*atr if d == 'short' else entry - sl_val*atr
    target = entry + tp_val*atr if d == 'long' else entry - tp_val*atr
    start = 0 if check_entry else 1
    for j in range(start, min(288, len(cdf)-pos)):
        b = cdf.iloc[pos+j]
        if j == 0:
            if d == 'long' and b['low'] <= stop: return j, stop
            if d == 'short' and b['high'] >= stop: return j, stop
            continue
        if d == 'long':
            if b['low'] <= stop: return j, stop
            if b['high'] >= target: return j, target
        else:
            if b['high'] >= stop: return j, stop
            if b['low'] <= target: return j, target
    n = min(288, len(cdf)-pos-1)
    if n > 0: return n, cdf.iloc[pos+n]['close']
    return 1, entry

# Collect signals
signals = []
prev_d = None; trig = {}; day_atr = None; prev_day_data = None; prev2_day_data = None
for ci in range(200, len(c)):
    row = c.iloc[ci]; ct = row['ts_dt']; today = ct.date()
    hour = ct.hour + ct.minute / 60.0
    if today != prev_d:
        if prev_d:
            yc = c[c['date']==prev_d]
            if len(yc) > 0:
                prev2_day_data = prev_day_data
                prev_day_data = {'open':float(yc.iloc[0]['open']),'close':float(yc.iloc[-1]['close']),
                                 'high':float(yc['high'].max()),'low':float(yc['low'].min()),
                                 'range':float(yc['high'].max()-yc['low'].min()),
                                 'body':float(yc.iloc[-1]['close']-yc.iloc[0]['open'])}
        prev_d = today; trig = {}
        pd_ = prev_day(today); day_atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    atr = day_atr
    if atr == 0 or atr is None: continue
    ds = pd.Timestamp(today.year,today.month,today.day,0,0,tz='UTC')
    te = pd.Timestamp(today.year,today.month,today.day,6,0,tz='UTC')
    ls = pd.Timestamp(today.year,today.month,today.day,8,0,tz='UTC')
    ns = pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC')
    tv = c[(c['ts_dt']>=ds)&(c['ts_dt']<=ct)]
    tok = tv[tv['ts_dt']<te]; lon = tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<ns)]
    def add(sn, d, e):
        if sn in PORTFOLIO:
            signals.append({'sn':sn,'dir':d,'entry':e,'ci':ci,'atr':atr,'date':today})
    detect_all(c, ci, row, ct, today, hour, atr, trig, tv, tok, lon, prev_day_data, add, prev2_day_data)

# Compare exits
print(f"{'='*90}")
print(f"  COMPARAISON TP SUR CLOSE vs TP SUR HIGH/LOW AU TARGET")
print(f"{'='*90}")
print(f"\n  {len(signals)} signaux collectes\n")

results_old = {}; results_new = {}
for sig in signals:
    sn = sig['sn']; d = sig['dir']; ci = sig['ci']; atr = sig['atr']
    entry = sig['entry']
    is_open = sn in OPEN_STRATS
    cfg = STRAT_EXITS.get(sn, DEFAULT_EXIT)
    sl_val = cfg[1]; tp_val = cfg[2]

    b_old, ex_old = sim_tpsl_old(c, ci, entry, d, atr, sl_val, tp_val, is_open)
    b_new, ex_new = sim_tpsl_new(c, ci, entry, d, atr, sl_val, tp_val, is_open)

    pnl_old = ((ex_old-entry) if d=='long' else (entry-ex_old)) - get_sp(sig['date'])
    pnl_new = ((ex_new-entry) if d=='long' else (entry-ex_new)) - get_sp(sig['date'])

    results_old.setdefault(sn,[]).append(pnl_old)
    results_new.setdefault(sn,[]).append(pnl_new)

print(f"  {'Strat':>22s} {'n':>5s} {'PF_old':>7s} {'PF_new':>7s} {'WR_old':>7s} {'WR_new':>7s} {'Avg_old':>8s} {'Avg_new':>8s}")
print(f"  {'-'*80}")
for sn in PORTFOLIO:
    if sn not in results_old: continue
    old = results_old[sn]; new = results_new[sn]
    n = len(old)
    gp_o = sum(p for p in old if p>0); gl_o = abs(sum(p for p in old if p<0))+0.001
    gp_n = sum(p for p in new if p>0); gl_n = abs(sum(p for p in new if p<0))+0.001
    wr_o = sum(1 for p in old if p>0)/n*100
    wr_n = sum(1 for p in new if p>0)/n*100
    print(f"  {sn:>22s} {n:5d} {gp_o/gl_o:7.2f} {gp_n/gl_n:7.2f} {wr_o:6.0f}% {wr_n:6.0f}% {np.mean(old):+8.3f} {np.mean(new):+8.3f}")

# Combo comparison
def eval_combo_from_results(res, capital=1000.0, risk=0.01):
    combined = []
    for sig in signals:
        sn = sig['sn']
        if sn not in res: continue
        idx = len([s for s in signals[:signals.index(sig)] if s['sn']==sn])
        if idx >= len(res[sn]): continue
        cfg = STRAT_EXITS.get(sn, DEFAULT_EXIT)
        combined.append((sig['ci'], sig['ci']+10, 1 if sig['dir']=='long' else -1,
                         res[sn][idx], cfg[1], sig['atr'],
                         str(sig['date'].year)+"-"+str(sig['date'].month).zfill(2), sn))
    combined.sort(key=lambda x: (x[0], x[7]))
    active = []; accepted = []
    for ei, xi, di, pnl_oz, sl_atr, atr, mo, _sn in combined:
        active = [(axi, ad) for axi, ad in active if axi >= ei]
        if any(ad != di for _, ad in active): continue
        accepted.append((ei, xi, di, pnl_oz, sl_atr, atr, mo, _sn))
        active.append((xi, di))
    n = len(accepted)
    cap = capital; peak = cap; max_dd = 0; gp = 0; gl = 0; wins = 0; months = {}
    for ei, xi, di, pnl_oz, sl_atr, atr, mo, _sn in accepted:
        pnl = pnl_oz * (cap * risk) / (sl_atr * atr)
        cap += pnl
        if cap > peak: peak = cap
        dd = (cap - peak) / peak
        if dd < max_dd: max_dd = dd
        if pnl > 0: gp += pnl; wins += 1
        else: gl += abs(pnl)
        months[mo] = months.get(mo, 0.0) + pnl
    mdd = max_dd * 100; ret = (cap - capital) / capital * 100
    pm = sum(1 for v in months.values() if v > 0)
    return n, gp/(gl+0.01), wins/n*100 if n>0 else 0, mdd, ret, pm, len(months)

print(f"\n  {'':>22s} {'n':>6s} {'PF':>6s} {'WR':>5s} {'DD':>8s} {'Rend':>10s} {'M+':>5s}")
print(f"  {'-'*65}")
n,pf,wr,dd,ret,pm,tm = eval_combo_from_results(results_old)
print(f"  {'TP sur CLOSE (ancien)':>22s} {n:6d} {pf:6.2f} {wr:4.0f}% {dd:+7.1f}% {ret:+9.0f}% {pm}/{tm}")
n,pf,wr,dd,ret,pm,tm = eval_combo_from_results(results_new)
print(f"  {'TP sur HIGH (corrige)':>22s} {n:6d} {pf:6.2f} {wr:4.0f}% {dd:+7.1f}% {ret:+9.0f}% {pm}/{tm}")
print()
