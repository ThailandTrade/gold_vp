"""
Optimisation v4 — TOUTES les strategies decouvertes.
14 strats: B, D2, FADE, GAP, KZ, 2BAR + NY1st, TOKEND, FADENY + LON1st, TOK1st, 3BAR + FAILIB, NY1st_wick
"""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
from itertools import combinations
from dotenv import load_dotenv
from datetime import datetime, timedelta
load_dotenv()
from phase1_poc_calculator import (
    get_conn, compute_vp, load_ticks_for_period, compute_atr, get_trading_days
)
from phase3_analyze import load_candles_5m

SLIPPAGE = 0.10

def sim_trail(cdf, pos, entry, d, sl, atr, mx, act, trail):
    best = entry
    stop = entry + sl*atr if d == 'short' else entry - sl*atr
    ta = False
    for j in range(1, mx+1):
        if pos+j >= len(cdf): break
        b = cdf.iloc[pos+j]
        if d == 'long':
            if b['low'] <= stop: return j, stop - SLIPPAGE
            if b['high'] > best: best = b['high']
            if not ta and (best-entry) >= act*atr: ta = True
            if ta: stop = max(stop, best - trail*atr)
        else:
            if b['high'] >= stop: return j, stop + SLIPPAGE
            if b['low'] < best: best = b['low']
            if not ta and (entry-best) >= act*atr: ta = True
            if ta: stop = min(stop, best + trail*atr)
    if pos+mx < len(cdf): return mx, cdf.iloc[pos+mx]['close']
    return mx, entry

conn = get_conn()
candles = load_candles_5m(conn)
daily_atr, global_atr = compute_atr(conn)
trading_days = get_trading_days(conn)

cur = conn.cursor()
cur.execute("""SELECT DATE_TRUNC('month', time), AVG(ask-bid)
    FROM market_ticks_xauusd WHERE ask>bid AND ask-bid<10 GROUP BY 1""")
monthly_spread = {r[0].strftime("%Y-%m"): float(r[1]) for r in cur.fetchall()}
cur.close()
avg_sp = np.mean(list(monthly_spread.values()))

def prev_day(day):
    for di, d in enumerate(trading_days):
        if d >= day: return trading_days[di-1] if di > 0 else None
    return None

def get_sp(day):
    return 2 * monthly_spread.get(str(day.year)+"-"+str(day.month).zfill(2), avg_sp)

n_td = len(set(candles['date'].unique()))
SL, ACT, TRAIL = 0.75, 0.5, 0.3  # params trailing par defaut

print("Collecte de TOUTES les strats...")
S = {}

# ── B: IB Tokyo 0h-1h UP ──
print("  B..."); t = []
for day in trading_days:
    p = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC')) & (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(p) < 18: continue
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    lvl = p.iloc[:12]['high'].max()
    for i in range(12, len(p)):
        if p.iloc[i]['close'] > lvl:
            pi = candles.index.get_loc(p.index[i]); e = p.iloc[i]['close']
            b, ex = sim_trail(candles, pi, e, 'long', SL, atr, 24, ACT, TRAIL)
            t.append({'date':day,'dir':'long','sl_atr':SL,'pnl_oz':(ex-e)-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b}); break
S['A'] = t

# ── D2: IB Tokyo 5h UP body>50% ──
print("  D2..."); t = []
for day in trading_days:
    p = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,5,0,tz='UTC')) & (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(p) < 6: continue
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    lvl = p.iloc[:3]['high'].max()
    for i in range(3, len(p)):
        r = p.iloc[i]
        if r['close'] > lvl:
            body = abs(r['close']-r['open']); rng = r['high']-r['low']
            if rng > 0 and body/rng >= 0.5:
                pi = candles.index.get_loc(p.index[i]); e = r['close']
                b, ex = sim_trail(candles, pi, e, 'long', SL, atr, 24, ACT, TRAIL)
                t.append({'date':day,'dir':'long','sl_atr':SL,'pnl_oz':(ex-e)-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b})
            break
S['B'] = t

# ── FADE: Tokyo >1ATR -> inverse London open ──
print("  FADE..."); t = []
for day in trading_days:
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    tok = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC')) & (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(tok) < 10: continue
    m = (tok.iloc[-1]['close'] - tok.iloc[0]['open']) / atr
    if abs(m) < 1.0: continue
    lon = candles[candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
    if len(lon) < 6: continue
    pi = candles.index.get_loc(lon.index[0]); e = lon.iloc[0]['open']
    d = 'short' if m > 0 else 'long'
    b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
    pnl = (ex-e) if d == 'long' else (e-ex)
    t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b})
S['C'] = t

# ── GAP: Gap Tokyo-London >0.5ATR continuation ──
print("  GAP..."); t = []
for day in trading_days:
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    tc = candles[candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC')]
    if len(tc) < 5: continue
    tok_close = tc.iloc[-1]['close']
    lon = candles[candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
    if len(lon) < 6: continue
    lon_open = lon.iloc[0]['open']
    gap = (lon_open - tok_close) / atr
    if abs(gap) < 0.5: continue
    pi = candles.index.get_loc(lon.index[0]); e = lon_open
    d = 'long' if gap > 0 else 'short'
    b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
    pnl = (ex-e) if d == 'long' else (e-ex)
    t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b})
S['D'] = t

# ── KZ: London Kill Zone fade 8h-10h ──
print("  KZ..."); t = []
for day in trading_days:
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    kz = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')) & (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,10,0,tz='UTC'))]
    if len(kz) < 20: continue
    m = (kz.iloc[-1]['close'] - kz.iloc[0]['open']) / atr
    if abs(m) < 0.5: continue
    post = candles[candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,10,0,tz='UTC')]
    if len(post) < 6: continue
    pi = candles.index.get_loc(post.index[0]); e = post.iloc[0]['open']
    d = 'short' if m > 0 else 'long'
    b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
    pnl = (ex-e) if d == 'long' else (e-ex)
    t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b})
S['E'] = t

# ── 2BAR: Tokyo two-bar reversal ──
print("  2BAR..."); t = []
for day in trading_days:
    p = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC')) & (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(p) < 8: continue
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    for i in range(1, len(p)):
        b1b = p.iloc[i-1]['close']-p.iloc[i-1]['open']; b2b = p.iloc[i]['close']-p.iloc[i]['open']
        if abs(b1b)<0.5*atr or abs(b2b)<0.5*atr: continue
        if b1b*b2b >= 0 or abs(b2b) <= abs(b1b): continue
        pi = candles.index.get_loc(p.index[i]); e = p.iloc[i]['close']
        d = 'long' if b2b > 0 else 'short'
        b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
        pnl = (ex-e) if d == 'long' else (e-ex)
        t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b}); break
S['F'] = t

# ── NY1st: 1ere bougie NY >0.3ATR ──
print("  NY1st..."); t = []
for day in trading_days:
    p = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC')) & (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,21,30,tz='UTC'))]
    if len(p) < 6: continue
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    first = p.iloc[0]; body = first['close'] - first['open']
    if abs(body) < 0.3*atr: continue
    d = 'long' if body > 0 else 'short'
    if len(p) < 2: continue
    pi = candles.index.get_loc(p.index[1]); e = p.iloc[1]['open']
    b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
    pnl = (ex-e) if d == 'long' else (e-ex)
    t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b})
S['G'] = t

# ── TOKEND: Tokyo end 3b >1ATR continuation ──
print("  TOKEND..."); t = []
for day in trading_days:
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    tok = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC')) & (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(tok) < 9: continue
    last3 = tok.iloc[-3:]
    m = (last3.iloc[-1]['close'] - last3.iloc[0]['open']) / atr
    if abs(m) < 1.0: continue
    lon = candles[candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
    if len(lon) < 6: continue
    pi = candles.index.get_loc(lon.index[0]); e = lon.iloc[0]['open']
    d = 'long' if m > 0 else 'short'
    b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
    pnl = (ex-e) if d == 'long' else (e-ex)
    t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b})
S['H'] = t

# ── FADENY: Fading NY 1h >1ATR ──
print("  FADENY..."); t = []
for day in trading_days:
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    ny1 = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC')) & (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,15,30,tz='UTC'))]
    if len(ny1) < 10: continue
    m = (ny1.iloc[-1]['close'] - ny1.iloc[0]['open']) / atr
    if abs(m) < 1.0: continue
    post = candles[candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,15,30,tz='UTC')]
    if len(post) < 6: continue
    pi = candles.index.get_loc(post.index[0]); e = post.iloc[0]['open']
    d = 'short' if m > 0 else 'long'
    b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
    pnl = (ex-e) if d == 'long' else (e-ex)
    t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b})
S['I'] = t

# ── LON1st: 1ere bougie London >0.3ATR ──
print("  LON1st..."); t = []
for day in trading_days:
    p = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')) & (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))]
    if len(p) < 6: continue
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    first = p.iloc[0]; body = first['close'] - first['open']
    if abs(body) < 0.3*atr: continue
    d = 'long' if body > 0 else 'short'
    if len(p) < 2: continue
    pi = candles.index.get_loc(p.index[1]); e = p.iloc[1]['open']
    b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
    pnl = (ex-e) if d == 'long' else (e-ex)
    t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b})
S['J'] = t

# ── TOK1st: 1ere bougie Tokyo >0.3ATR ──
print("  TOK1st..."); t = []
for day in trading_days:
    p = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC')) & (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(p) < 6: continue
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    first = p.iloc[0]; body = first['close'] - first['open']
    if abs(body) < 0.3*atr: continue
    d = 'long' if body > 0 else 'short'
    if len(p) < 2: continue
    pi = candles.index.get_loc(p.index[1]); e = p.iloc[1]['open']
    b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
    pnl = (ex-e) if d == 'long' else (e-ex)
    t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b})
S['K'] = t

# ── 3BAR: Tokyo three-bar (grosse+inside+grosse continuation) ──
print("  3BAR..."); t = []
for day in trading_days:
    p = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC')) & (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(p) < 10: continue
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    for i in range(2, len(p)):
        c1=p.iloc[i-2]; c2=p.iloc[i-1]; c3=p.iloc[i]
        if not (c2['high']<=c1['high'] and c2['low']>=c1['low']): continue
        if abs(c3['close']-c3['open']) < 0.3*atr: continue
        c1d = 1 if c1['close']>c1['open'] else -1
        c3d = 1 if c3['close']>c3['open'] else -1
        if c1d != c3d: continue
        d = 'long' if c3d > 0 else 'short'
        pi = candles.index.get_loc(p.index[i]); e = c3['close']
        b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
        pnl = (ex-e) if d == 'long' else (e-ex)
        t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b}); break
S['L'] = t

# ── M: Failed IB break Tokyo → reverse ──
print("  FAILIB..."); t = []
for day in trading_days:
    p = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC')) & (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(p) < 18: continue
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    ib_high = p.iloc[:12]['high'].max()
    ib_low = p.iloc[:12]['low'].min()
    for i in range(12, len(p)):
        r = p.iloc[i]
        # Break UP puis retour sous IB high = failed break → short
        if r['high'] > ib_high and r['close'] < ib_high:
            pi = candles.index.get_loc(p.index[i]); e = r['close']
            b, ex = sim_trail(candles, pi, e, 'short', SL, atr, 24, ACT, TRAIL)
            pnl = (e-ex)-get_sp(day)
            t.append({'date':day,'dir':'short','sl_atr':SL,'pnl_oz':pnl,'atr':atr,'ei':pi,'xi':pi+b}); break
        # Break DOWN puis retour au-dessus IB low = failed break → long
        if r['low'] < ib_low and r['close'] > ib_low:
            pi = candles.index.get_loc(p.index[i]); e = r['close']
            b, ex = sim_trail(candles, pi, e, 'long', SL, atr, 24, ACT, TRAIL)
            pnl = (ex-e)-get_sp(day)
            t.append({'date':day,'dir':'long','sl_atr':SL,'pnl_oz':pnl,'atr':atr,'ei':pi,'xi':pi+b}); break
S['M'] = t

# ── N: NY1st wick<50% (filtre qualite) ──
print("  NY1st_wick..."); t = []
for day in trading_days:
    p = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC')) & (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,21,30,tz='UTC'))]
    if len(p) < 6: continue
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    first = p.iloc[0]; body = abs(first['close'] - first['open']); rng = first['high'] - first['low']
    if rng == 0 or body < 0.3*atr: continue
    wick = (rng - body) / body
    if wick >= 0.5: continue  # trop de meche
    d = 'long' if first['close'] > first['open'] else 'short'
    if len(p) < 2: continue
    pi = candles.index.get_loc(p.index[1]); e = p.iloc[1]['open']
    b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
    pnl = (ex-e) if d == 'long' else (e-ex)
    t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b})
S['N'] = t

# Legende
LEGEND = {
    'A': 'IB_tok_1h_UP', 'B': 'D2_tok_5h_body', 'C': 'FADE_tok_lon',
    'D': 'GAP_tok_lon', 'E': 'KZ_lon_fade', 'F': '2BAR_tok_rev',
    'G': 'NY1st_candle', 'H': 'TOKEND_3b', 'I': 'FADENY_1h',
    'J': 'LON1st_candle', 'K': 'TOK1st_candle', 'L': '3BAR_tok',
    'M': 'FAILIB_tok', 'N': 'NY1st_wick50'
}

# Stats
print("\n" + "=" * 80)
print("STATS INDIVIDUELLES ({} strats)".format(len(S)))
print("=" * 80)
for sn in sorted(S.keys()):
    t = S[sn]
    if len(t) < 10: print("  {:8s}: n={} --".format(sn, len(t))); continue
    df = pd.DataFrame(t)
    gp = df[df['pnl_oz']>0]['pnl_oz'].sum(); gl = abs(df[df['pnl_oz']<0]['pnl_oz'].sum())+0.001
    wr = (df['pnl_oz']>0).mean()*100
    ns = (df['dir']=='short').sum(); nl = (df['dir']=='long').sum()
    mid = len(df)//2; f1 = df.iloc[:mid]['pnl_oz'].mean(); f2 = df.iloc[mid:]['pnl_oz'].mean()
    ok = "OK" if f1>0 and f2>0 else "!!"
    print("  {:8s}: n={:4d} ({:3d}L {:3d}S) WR={:.0f}% PF={:.2f} {:.1f}t/j [{:+.2f}|{:+.2f}] {}".format(
        sn, len(df), nl, ns, wr, gp/gl, len(df)/n_td, f1, f2, ok))

# Combinaisons (max 8 strats pour pas exploser)
print("\n" + "=" * 80)
print("COMBINAISONS (risk 0.4%, max 8 strats)")
print("=" * 80)

all_n = sorted(S.keys())
results = []

for size in range(2, len(all_n)+1):
    for combo in combinations(all_n, size):
        combined = []
        for sn in combo:
            for t in S[sn]: combined.append({**t, 'strat': sn})
        if len(combined) < 50: continue
        cdf = pd.DataFrame(combined).sort_values('ei').reset_index(drop=True)
        al = []; acc = []
        for _, t in cdf.iterrows():
            al = [(ei, d) for ei, d in al if ei >= t['ei']]
            if not any(d != t['dir'] for _, d in al):
                acc.append(t.to_dict()); al.append((t['xi'], t['dir']))
        df = pd.DataFrame(acc)
        if len(df) < 50: continue
        capital = 10000.0; recs = []
        for _, t in df.iterrows():
            pnl = t['pnl_oz'] * (capital*0.004)/(t['sl_atr']*t['atr'])
            capital += pnl
            recs.append({'capital':capital,'pnl':pnl,'date':t['date'],
                         'month':str(t['date'].year)+"-"+str(t['date'].month).zfill(2)})
        eq = pd.DataFrame(recs)
        pk = eq['capital'].cummax()
        mdd = ((eq['capital']-pk)/pk).min()*100
        ret = (capital-10000)/100
        wins = eq[eq['pnl']>0]
        gp = wins['pnl'].sum() if len(wins)>0 else 0
        gl = abs(eq[eq['pnl']<0]['pnl'].sum())+0.01
        mp = eq.groupby('month')['pnl'].sum()
        mid = len(eq)//2
        p1 = eq.iloc[:mid]['pnl'].sum(); p2 = eq.iloc[mid:]['pnl'].sum()
        has_s = any(t['dir']=='short' for t in acc)
        has_l = any(t['dir']=='long' for t in acc)
        t1 = eq.iloc[:len(eq)//3]['pnl'].sum()
        t2 = eq.iloc[len(eq)//3:2*len(eq)//3]['pnl'].sum()
        t3 = eq.iloc[2*len(eq)//3:]['pnl'].sum()
        results.append({
            'combo':'+'.join(combo),'ns':len(combo),'n':len(df),'tpd':len(df)/n_td,
            'ret':ret,'mdd':mdd,'cal':ret/abs(mdd) if mdd<0 else 0,
            'pf':gp/gl,'wr':len(wins)/len(eq)*100,
            'split':p1>0 and p2>0,'tiers':sum(1 for x in [t1,t2,t3] if x>0),
            'both':has_s and has_l,'pm':(mp>0).sum(),'tm':len(mp),
        })

rdf = pd.DataFrame(results)
ok = rdf[(rdf['split']) & (rdf['tiers']==3)]

def show(title, sub, col, n=15):
    print("\n  " + title)
    print("  {:45s} {:>5s} {:>4s} {:>7s} {:>6s} {:>5s} {:>5s} {:>4s} {:>5s}".format(
        "Combo","trad","t/j","Rend%","DD%","Cal","PF","WR%","M+"))
    for _, r in sub.sort_values(col, ascending=False).head(n).iterrows():
        d = "L+S" if r['both'] else "L"
        print("  {:45s} {:5d} {:4.1f} {:+6.1f}% {:+5.1f}% {:5.1f} {:.2f} {:3.0f}% {:2.0f}/{:.0f} {}".format(
            r['combo'][:45], r['n'], r['tpd'], r['ret'], r['mdd'], r['cal'], r['pf'], r['wr'], r['pm'], r['tm'], d))

print("\n  LEGENDE:")
for k in sorted(LEGEND.keys()):
    print("    {} = {}".format(k, LEGEND[k]))

show("TOP 15 RENDEMENT (split OK, tiers 3/3)", ok, 'ret', 15)
show("TOP 15 CALMAR (split OK, tiers 3/3, DD>-6%)", ok[ok['mdd']>-6], 'cal', 15)
show("TOP 15 CALMAR (split OK, tiers 3/3, DD>-10%)", ok[ok['mdd']>-10], 'cal', 15)
show("TOP 15 PF (split OK, tiers 3/3, n>=300)", ok[ok['n']>=300], 'pf', 15)
show("TOP 15 DIVERSIFIES (L+S, split OK, tiers 3/3, DD>-6%)", ok[(ok['both'])&(ok['mdd']>-6)], 'cal', 15)

conn.close()
print("\n" + "=" * 80)
