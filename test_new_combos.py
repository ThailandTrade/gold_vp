"""
Test combos: portfolio existant (renomme) + 4 nouvelles strats.

Renommage par session:
  TOKYO:  TOK_2BAR (F), TOK_BIG (O), TOK_IB (T1), TOK_3BAR (T6), TOK_FADE (T10)
  LONDON: LON_PIN (AA), LON_GAP (D), LON_KZ (E), LON_TOKEND (H), LON_PREV (X1)
  NY:     NY_GAP (NY6), NY_LONEND (NY16), NY_LONMOM (NY17)
"""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
from itertools import combinations
from dotenv import load_dotenv; load_dotenv()
from phase1_poc_calculator import get_conn, compute_atr, get_trading_days
from phase3_analyze import load_candles_5m

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
n_td = len(set(candles['date'].unique()))

SL, ACT, TRAIL = 1.0, 0.5, 0.75
def sim_exit(cdf, pos, entry, d, atr):
    best = entry; stop = entry + SL*atr if d == 'short' else entry - SL*atr; ta = False
    for j in range(1, len(cdf)-pos):
        b = cdf.iloc[pos+j]
        if d == 'long':
            if b['low'] <= stop: return j, stop
            if b['close'] > best: best = b['close']
            if not ta and (best-entry) >= ACT*atr: ta = True
            if ta: stop = max(stop, best - TRAIL*atr)
            if b['close'] < stop: return j, b['close']
        else:
            if b['high'] >= stop: return j, stop
            if b['close'] < best: best = b['close']
            if not ta and (entry-best) >= ACT*atr: ta = True
            if ta: stop = min(stop, best + TRAIL*atr)
            if b['close'] > stop: return j, b['close']
    return 1, entry

print("Collecte...", flush=True)
S = {}
prev_d = None; trig = {}; day_atr = None; prev_day_data = None
for ci in range(len(candles)):
    row = candles.iloc[ci]; ct = row['ts_dt']; today = ct.date()
    hour = ct.hour + ct.minute / 60.0
    if today != prev_d:
        if prev_d:
            yc = candles[candles['date']==prev_d]
            if len(yc) > 0:
                prev_day_data = {'open': float(yc.iloc[0]['open']), 'close': float(yc.iloc[-1]['close']),
                                 'high': float(yc['high'].max()), 'low': float(yc['low'].min())}
        prev_d = today; trig = {}
        pd_ = prev_day(today); day_atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    atr = day_atr
    if atr == 0 or atr is None: continue
    ds = pd.Timestamp(today.year,today.month,today.day,0,0,tz='UTC')
    te = pd.Timestamp(today.year,today.month,today.day,6,0,tz='UTC')
    ls = pd.Timestamp(today.year,today.month,today.day,8,0,tz='UTC')
    ns = pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC')
    tv = candles[(candles['ts_dt']>=ds)&(candles['ts_dt']<=ct)]
    tok = tv[tv['ts_dt']<te]; lon = tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<ns)]
    def add(sn, d, e):
        b, ex = sim_exit(candles, ci, e, d, atr)
        pnl = (ex-e) if d=='long' else (e-ex)
        S.setdefault(sn,[]).append({'date':today,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(today),'atr':atr,'ei':ci,'xi':ci+b})

    # ── TOKYO ──
    # TOK_2BAR: Two-bar reversal (ex F)
    if 0.0<=hour<6.0 and 'TOK_2BAR' not in trig and len(tok)>=2:
        b1=tok.iloc[-2];b2=tok.iloc[-1];b1b=b1['close']-b1['open'];b2b=b2['close']-b2['open']
        if abs(b1b)>=0.5*atr and abs(b2b)>=0.5*atr and b1b*b2b<0 and abs(b2b)>abs(b1b):
            add('TOK_2BAR','long' if b2b>0 else 'short',b2['close']); trig['TOK_2BAR']=True
    # TOK_BIG: Big candle >1ATR (ex O)
    if 0.0<=hour<6.0 and 'TOK_BIG' not in trig:
        body=row['close']-row['open']
        if abs(body)>=1.0*atr: add('TOK_BIG','long' if body>0 else 'short',row['close']); trig['TOK_BIG']=True
    # TOK_IB: IB 1h breakout (new T1)
    if 'TOK_IB_d' not in trig and hour >= 1.0 and hour < 6.0:
        ib = tv[(tv['ts_dt']>=ds)&(tv['ts_dt']<ds+pd.Timedelta(hours=1))]
        if len(ib) >= 12:
            trig['TOK_IB_d'] = True; trig['TOK_IB_h'] = float(ib['high'].max()); trig['TOK_IB_l'] = float(ib['low'].min())
    if 'TOK_IB_h' in trig and 'TOK_IB' not in trig and 1.0 <= hour < 6.0:
        if row['close'] > trig['TOK_IB_h']: add('TOK_IB','long',row['close']); trig['TOK_IB']=True
        elif row['close'] < trig['TOK_IB_l']: add('TOK_IB','short',row['close']); trig['TOK_IB']=True
    # TOK_3BAR: 3 consecutive candles same dir (new T6)
    if 0.0<=hour<6.0 and 'TOK_3BAR' not in trig and len(tok)>=3:
        c1=tok.iloc[-3];c2=tok.iloc[-2];c3=tok.iloc[-1]
        b1=c1['close']-c1['open'];b2=c2['close']-c2['open'];b3=c3['close']-c3['open']
        if b1*b2>0 and b2*b3>0 and min(abs(b1),abs(b2),abs(b3))>0.05*atr and abs(b1+b2+b3)>=0.5*atr:
            add('TOK_3BAR','long' if b3>0 else 'short',c3['close']); trig['TOK_3BAR']=True
    # TOK_FADE: Fade previous day >1ATR (new T10)
    if 0.0<=hour<0.1 and 'TOK_FADE' not in trig and prev_day_data:
        prev_dir = prev_day_data['close'] - prev_day_data['open']
        if abs(prev_dir) >= 1.0*atr:
            add('TOK_FADE','short' if prev_dir>0 else 'long',row['open']); trig['TOK_FADE']=True

    # ── LONDON ──
    # LON_PIN: Pin bar (ex AA)
    if 8.0<=hour<14.5 and 'LON_PIN' not in trig:
        rng=row['high']-row['low']
        if rng>=0.3*atr and abs(row['close']-row['open'])>=0.2*atr:
            pir=(row['close']-row['low'])/rng
            if pir>=0.9: add('LON_PIN','long',row['close']); trig['LON_PIN']=True
            elif pir<=0.1: add('LON_PIN','short',row['close']); trig['LON_PIN']=True
    # LON_GAP: Gap Tokyo→London >0.5ATR (ex D)
    if 8.0<=hour<8.1 and 'LON_GAP' not in trig:
        tc=candles[(candles['ts_dt']<te)&(candles['ts_dt']<=ct)]
        if len(tc)>=5:
            gap=(row['open']-tc.iloc[-1]['close'])/atr
            if abs(gap)>=0.5: add('LON_GAP','long' if gap>0 else 'short',row['open']); trig['LON_GAP']=True
    # LON_KZ: Kill Zone fade 8h-10h (ex E)
    if 10.0<=hour<10.1 and 'LON_KZ' not in trig:
        kz=tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<pd.Timestamp(today.year,today.month,today.day,10,0,tz='UTC'))]
        if len(kz)>=20:
            m=(kz.iloc[-1]['close']-kz.iloc[0]['open'])/atr
            if abs(m)>=0.5: add('LON_KZ','short' if m>0 else 'long',row['open']); trig['LON_KZ']=True
    # LON_TOKEND: 3 last Tokyo candles >1ATR continuation (ex H)
    if 8.0<=hour<8.1 and 'LON_TOKEND' not in trig and len(tok)>=9:
        l3=tok.iloc[-3:]; m=(l3.iloc[-1]['close']-l3.iloc[0]['open'])/atr
        if abs(m)>=1.0: add('LON_TOKEND','long' if m>0 else 'short',row['open']); trig['LON_TOKEND']=True
    # LON_PREV: Previous day continuation >1ATR (new X1)
    if 8.0<=hour<8.1 and 'LON_PREV' not in trig and prev_day_data:
        prev_body = (prev_day_data['close'] - prev_day_data['open']) / atr
        if abs(prev_body) >= 1.0:
            add('LON_PREV','long' if prev_body>0 else 'short',row['open']); trig['LON_PREV']=True

    # ── NY ──
    # NY_GAP: Gap London→NY >0.5ATR (ex NY6)
    if 14.5<=hour<14.6 and 'NY_GAP' not in trig and len(lon)>=5:
        gap=(row['open']-lon.iloc[-1]['close'])/atr
        if abs(gap)>=0.5: add('NY_GAP','long' if gap>0 else 'short',row['open']); trig['NY_GAP']=True
    # NY_LONEND: 3 last London candles >1ATR continuation (ex NY16)
    if 14.5<=hour<14.6 and 'NY_LONEND' not in trig and len(lon)>=9:
        l3=lon.iloc[-3:]; m=(l3.iloc[-1]['close']-l3.iloc[0]['open'])/atr
        if abs(m)>=1.0: add('NY_LONEND','long' if m>0 else 'short',row['open']); trig['NY_LONEND']=True
    # NY_LONMOM: 3 last London candles >0.5ATR continuation (ex NY17)
    if 14.5<=hour<14.6 and 'NY_LONMOM' not in trig and len(lon)>=9:
        l3=lon.iloc[-3:]; m=(l3.iloc[-1]['close']-l3.iloc[0]['open'])/atr
        if abs(m)>=0.5: add('NY_LONMOM','long' if m>0 else 'short',row['open']); trig['NY_LONMOM']=True

print("Done.", flush=True)

# Stats individuelles
print("\n" + "="*100)
print("STATS INDIVIDUELLES")
print("="*100)
base = ['TOK_2BAR','TOK_BIG','LON_PIN','LON_GAP','LON_KZ','LON_TOKEND','NY_GAP','NY_LONEND','NY_LONMOM']
new = ['TOK_IB','TOK_3BAR','TOK_FADE','LON_PREV']

for sn in base + new:
    t = S.get(sn, [])
    if len(t) < 10: continue
    pnls = [x['pnl_oz'] for x in t]
    n = len(pnls)
    gp = sum(p for p in pnls if p>0); gl = abs(sum(p for p in pnls if p<0))+0.001
    wr = sum(1 for p in pnls if p>0)/n*100
    pf = gp/gl
    mid = n//2; f1 = np.mean(pnls[:mid]); f2 = np.mean(pnls[mid:])
    tag = "BASE" if sn in base else "NEW "
    split = "OK" if f1>0 and f2>0 else "!!"
    print(f"  {tag} {sn:12s} n={n:4d} WR={wr:.0f}% PF={pf:.2f} [{f1:+.3f}|{f2:+.3f}] {split}")

# Build arrays
strat_arrays = {}
for sn in S:
    rows = []
    for t in S[sn]:
        di = 1 if t['dir'] == 'long' else -1
        mo = str(t['date'].year)+"-"+str(t['date'].month).zfill(2)
        rows.append((t['ei'], t['xi'], di, t['pnl_oz'], t['sl_atr'], t['atr'], mo, sn))
    strat_arrays[sn] = rows

def eval_combo(combo, capital=1000.0, risk=0.01):
    combined = []
    for sn in combo:
        if sn in strat_arrays: combined.extend(strat_arrays[sn])
    if len(combined) < 50: return None
    combined.sort(key=lambda x: (x[0], x[7]))
    active = []; accepted = []
    for ei, xi, di, pnl_oz, sl_atr, atr, mo, _sn in combined:
        active = [(axi, ad) for axi, ad in active if axi >= ei]
        if any(ad != di for _, ad in active): continue
        accepted.append((ei, xi, di, pnl_oz, sl_atr, atr, mo, _sn))
        active.append((xi, di))
    n = len(accepted)
    if n < 50: return None
    cap = capital; peak = cap; max_dd = 0; gp = 0; gl = 0; wins = 0; months = {}
    has_l = False; has_s = False; pnls = []
    for ei, xi, di, pnl_oz, sl_atr, atr, mo, _sn in accepted:
        pnl = pnl_oz * (cap * risk) / (sl_atr * atr)
        cap += pnl; pnls.append(pnl)
        if cap > peak: peak = cap
        dd = (cap - peak) / peak
        if dd < max_dd: max_dd = dd
        if pnl > 0: gp += pnl; wins += 1
        else: gl += abs(pnl)
        months[mo] = months.get(mo, 0.0) + pnl
        if di == 1: has_l = True
        else: has_s = True
    mdd = max_dd * 100; ret = (cap - capital) / capital * 100
    mid = n // 2; p1 = sum(pnls[:mid]); p2 = sum(pnls[mid:])
    t1 = sum(pnls[:n//3]); t2 = sum(pnls[n//3:2*n//3]); t3 = sum(pnls[2*n//3:])
    pm = sum(1 for v in months.values() if v > 0)
    return {
        'combo': '+'.join(combo), 'ns': len(combo), 'n': n, 'tpd': n / n_td,
        'ret': ret, 'mdd': mdd, 'cal': ret / abs(mdd) if mdd < 0 else 0,
        'pf': gp / (gl + 0.01), 'wr': wins / n * 100, 'capital': cap,
        'split': p1 > 0 and p2 > 0,
        'tiers': sum(1 for x in [t1, t2, t3] if x > 0),
        'both': has_s and has_l, 'pm': pm, 'tm': len(months),
    }

# Test combos
print("\n" + "="*130)
print("COMBOS: BASE + NOUVELLES STRATS")
print("="*130)

r = eval_combo(tuple(base))
print(f"\n  BASE (9 strats):")
print(f"  n={r['n']:.0f} PF={r['pf']:.2f} WR={r['wr']:.0f}% DD={r['mdd']:+.1f}% Cal={r['cal']:.1f} Rend={r['ret']:+.0f}% M+={r['pm']:.0f}/{r['tm']:.0f}")

print(f"\n  {'Ajout':15s} {'n':>5s} {'PF':>5s} {'WR':>4s} {'DD%':>7s} {'Cal':>8s} {'Rend%':>10s} {'M+':>5s} {'Split':>5s} {'T':>3s}")
print(f"  {'-'*100}")

# +1
for ny in new:
    combo = tuple(sorted(base + [ny]))
    r = eval_combo(combo)
    if r:
        sp = "OK" if r['split'] else "!!"
        print(f"  +{ny:14s} {r['n']:5.0f} {r['pf']:.2f} {r['wr']:3.0f}% {r['mdd']:+6.1f}% {r['cal']:8.1f} {r['ret']:+9.0f}% {r['pm']:.0f}/{r['tm']:.0f} {sp:>5s} {r['tiers']}/3")

# +2
print(f"\n  +2 nouvelles (top 6 Calmar, split OK):")
print(f"  {'Ajout':25s} {'n':>5s} {'PF':>5s} {'WR':>4s} {'DD%':>7s} {'Cal':>8s} {'Rend%':>10s} {'M+':>5s} {'T':>3s}")
print(f"  {'-'*100}")
res2 = []
for nc in combinations(new, 2):
    combo = tuple(sorted(base + list(nc)))
    r = eval_combo(combo)
    if r and r['split'] and r['both']: res2.append((nc, r))
res2.sort(key=lambda x: x[1]['cal'], reverse=True)
for nc, r in res2[:6]:
    print(f"  +{'+'.join(nc):24s} {r['n']:5.0f} {r['pf']:.2f} {r['wr']:3.0f}% {r['mdd']:+6.1f}% {r['cal']:8.1f} {r['ret']:+9.0f}% {r['pm']:.0f}/{r['tm']:.0f} {r['tiers']}/3")

# +3
print(f"\n  +3 nouvelles (top 4 Calmar, split OK):")
res3 = []
for nc in combinations(new, 3):
    combo = tuple(sorted(base + list(nc)))
    r = eval_combo(combo)
    if r and r['split'] and r['both']: res3.append((nc, r))
res3.sort(key=lambda x: x[1]['cal'], reverse=True)
for nc, r in res3[:4]:
    print(f"  +{'+'.join(nc):34s} {r['n']:5.0f} {r['pf']:.2f} {r['wr']:3.0f}% {r['mdd']:+6.1f}% {r['cal']:8.1f} {r['ret']:+9.0f}% {r['pm']:.0f}/{r['tm']:.0f} {r['tiers']}/3")

# +4 (all)
combo = tuple(sorted(base + new))
r = eval_combo(combo)
if r:
    sp = "OK" if r['split'] else "!!"
    print(f"\n  +ALL (13 strats):   {r['n']:5.0f} {r['pf']:.2f} {r['wr']:3.0f}% {r['mdd']:+6.1f}% {r['cal']:8.1f} {r['ret']:+9.0f}% {r['pm']:.0f}/{r['tm']:.0f} {sp} {r['tiers']}/3")

print()
