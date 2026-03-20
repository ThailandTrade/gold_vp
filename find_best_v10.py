"""
Optimisation v10 — trailing corrige (pas de re-check low/high vs nouveau stop).
Config UNIQUE: TRp SL=1.5 ACT=0.3 TRAIL=0.3 T12 (toutes strats).
15 strats, combos de 3 a 15.
$1000, risk 1%.
"""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import time, numpy as np, pandas as pd
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

# Config unique
SL, ACT, TRAIL, MX = 1.0, 0.5, 0.75, 12

def sim_exit(cdf, pos, entry, d, atr):
    """Trailing corrige: apres update du stop, on ne re-check PAS low/high
    (le low/high s'est produit PENDANT la bougie avec l'ANCIEN stop).
    On re-check seulement le CLOSE vs nouveau stop."""
    best = entry; stop = entry + SL*atr if d == 'short' else entry - SL*atr; ta = False
    for j in range(1, MX+1):
        if pos+j >= len(cdf): break
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
    if pos+MX < len(cdf): return MX, cdf.iloc[pos+MX]['close']
    return MX, entry

# ── COLLECTE BOUGIE PAR BOUGIE ──
print("Collecte bougie par bougie...", flush=True)
S = {}
prev_d = None; trig = {}; day_atr = None
for ci in range(len(candles)):
    if ci % 10000 == 0 and ci > 0: print(f"\r  {ci*100//len(candles)}%", end='', flush=True)
    row = candles.iloc[ci]; ct = row['ts_dt']; today = ct.date()
    hour = ct.hour + ct.minute / 60.0
    if today != prev_d:
        prev_d = today; trig = {}
        pd_ = prev_day(today); day_atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    atr = day_atr
    if atr == 0 or atr is None: continue
    ds = pd.Timestamp(today.year,today.month,today.day,0,0,tz='UTC')
    te = pd.Timestamp(today.year,today.month,today.day,6,0,tz='UTC')
    ls = pd.Timestamp(today.year,today.month,today.day,8,0,tz='UTC')
    le = pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC')
    ns = pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC')
    tv = candles[(candles['ts_dt']>=ds)&(candles['ts_dt']<=ct)]
    tok = tv[tv['ts_dt']<te]; lon = tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<le)]; ny = tv[tv['ts_dt']>=ns]

    def add(sn, d, e):
        b, ex = sim_exit(candles, ci, e, d, atr)
        pnl = (ex-e) if d=='long' else (e-ex)
        S.setdefault(sn,[]).append({'date':today,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(today),'atr':atr,'ei':ci,'xi':ci+b})

    # C: FADE_tok_lon — Tokyo move >1ATR, inverse a London open
    if 8.0<=hour<8.1 and 'C' not in trig and len(tok)>=10:
        m=(tok.iloc[-1]['close']-tok.iloc[0]['open'])/atr
        if abs(m)>=1.0: add('C','short' if m>0 else 'long',row['open']); trig['C']=True
    # D: GAP_tok_lon — Gap Tokyo close vs London open >0.5ATR
    if 8.0<=hour<8.1 and 'D' not in trig:
        tc=candles[(candles['ts_dt']<te)&(candles['ts_dt']<=ct)]
        if len(tc)>=5:
            gap=(row['open']-tc.iloc[-1]['close'])/atr
            if abs(gap)>=0.5: add('D','long' if gap>0 else 'short',row['open']); trig['D']=True
    # E: KZ_lon_fade — London KZ 8h-10h move >0.5ATR, fade a 10h
    if 10.0<=hour<10.1 and 'E' not in trig:
        kz=tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<pd.Timestamp(today.year,today.month,today.day,10,0,tz='UTC'))]
        if len(kz)>=20:
            m=(kz.iloc[-1]['close']-kz.iloc[0]['open'])/atr
            if abs(m)>=0.5: add('E','short' if m>0 else 'long',row['open']); trig['E']=True
    # F: 2BAR_tok_rev — Two-bar reversal Tokyo
    if 0.0<=hour<6.0 and 'F' not in trig and len(tok)>=2:
        b1=tok.iloc[-2];b2=tok.iloc[-1];b1b=b1['close']-b1['open'];b2b=b2['close']-b2['open']
        if abs(b1b)>=0.5*atr and abs(b2b)>=0.5*atr and b1b*b2b<0 and abs(b2b)>abs(b1b):
            add('F','long' if b2b>0 else 'short',b2['close']); trig['F']=True
    # G: NY1st_candle — 1ere bougie NY >0.3ATR
    if 14.5<=hour<14.6 and 'G' not in trig:
        body=row['close']-row['open']
        if abs(body)>=0.3*atr: add('G','long' if body>0 else 'short',row['close']); trig['G']=True
    # H: TOKEND_3b — 3 dernieres bougies Tokyo >1ATR, continuation London
    if 8.0<=hour<8.1 and 'H' not in trig and len(tok)>=9:
        l3=tok.iloc[-3:]; m=(l3.iloc[-1]['close']-l3.iloc[0]['open'])/atr
        if abs(m)>=1.0: add('H','long' if m>0 else 'short',row['open']); trig['H']=True
    # I: FADENY_1h — NY 1ere heure move >1ATR, inverse
    if 15.5<=hour<15.6 and 'I' not in trig:
        ny1=tv[(tv['ts_dt']>=ns)&(tv['ts_dt']<pd.Timestamp(today.year,today.month,today.day,15,30,tz='UTC'))]
        if len(ny1)>=10:
            m=(ny1.iloc[-1]['close']-ny1.iloc[0]['open'])/atr
            if abs(m)>=1.0: add('I','short' if m>0 else 'long',row['open']); trig['I']=True
    # O: BIG_tok_candle — Bougie Tokyo >1ATR, continuation
    if 0.0<=hour<6.0 and 'O' not in trig:
        body=row['close']-row['open']
        if abs(body)>=1.0*atr: add('O','long' if body>0 else 'short',row['close']); trig['O']=True
    # P: NY_ORB — NY Opening Range Breakout
    if 15.0<=hour<21.5 and 'P' not in trig:
        if 'P_h' not in trig:
            orb=tv[(tv['ts_dt']>=ns)&(tv['ts_dt']<pd.Timestamp(today.year,today.month,today.day,15,0,tz='UTC'))]
            if len(orb)>=6: trig['P_h']=float(orb['high'].max()); trig['P_l']=float(orb['low'].min())
        if 'P_h' in trig:
            if row['close']>trig['P_h']: add('P','long',row['close']); trig['P']=True
            elif row['close']<trig['P_l']: add('P','short',row['close']); trig['P']=True
    # Q: LON_engulf — London bullish/bearish engulfing
    if 8.0<=hour<14.5 and 'Q' not in trig and len(lon)>=2:
        pb=lon.iloc[-2];cb=lon.iloc[-1]
        if pb['close']<pb['open'] and cb['close']>cb['open'] and cb['open']<=pb['close'] and cb['close']>=pb['open'] and abs(cb['close']-cb['open'])>=0.3*atr:
            add('Q','long',cb['close']); trig['Q']=True
        elif pb['close']>pb['open'] and cb['close']<cb['open'] and cb['open']>=pb['close'] and cb['close']<=pb['open'] and abs(cb['close']-cb['open'])>=0.3*atr:
            add('Q','short',cb['close']); trig['Q']=True
    # R: TOK_3bar_mom — 3 bougies Tokyo meme sens >0.5ATR
    if 0.0<=hour<6.0 and 'R' not in trig and len(tok)>=3:
        c1=tok.iloc[-3];c2=tok.iloc[-2];c3=tok.iloc[-1];b1=c1['close']-c1['open'];b2=c2['close']-c2['open'];b3=c3['close']-c3['open']
        if b1*b2>0 and b2*b3>0 and min(abs(b1),abs(b2),abs(b3))>0.1*atr and abs(b1+b2+b3)>=0.5*atr:
            add('R','long' if b3>0 else 'short',c3['close']); trig['R']=True
    # S: LON_3bar_fade — 3 bougies London meme sens, fade
    if 8.0<=hour<14.5 and 'S' not in trig and len(lon)>=3:
        c1=lon.iloc[-3];c2=lon.iloc[-2];c3=lon.iloc[-1];b1=c1['close']-c1['open'];b2=c2['close']-c2['open'];b3=c3['close']-c3['open']
        if b1*b2>0 and b2*b3>0 and min(abs(b1),abs(b2),abs(b3))>0.1*atr and abs(b1+b2+b3)>=0.5*atr:
            add('S','short' if b3>0 else 'long',c3['close']); trig['S']=True
    # V: TOK_6bar_bias — 5/6 ou 1/6 bougies bullish Tokyo
    if 0.0<=hour<6.0 and 'V' not in trig and len(tok)>=7:
        last6=tok.iloc[-6:]; n_bull=(last6['close']>last6['open']).sum()
        if n_bull>=5: add('V','long',row['close']); trig['V']=True
        elif n_bull<=1: add('V','short',row['close']); trig['V']=True
    # AA: LON_pinbar — London pin bar (wick >70% range)
    if 8.0<=hour<14.5 and 'AA' not in trig:
        rng=row['high']-row['low']
        if rng>=0.3*atr and abs(row['close']-row['open'])>=0.2*atr:
            pir=(row['close']-row['low'])/rng
            if pir>=0.9: add('AA','long',row['close']); trig['AA']=True
            elif pir<=0.1: add('AA','short',row['close']); trig['AA']=True
    # AC: TOK_outside_bar — Outside bar Tokyo englobant 3 precedentes
    if 0.0<=hour<6.0 and 'AC' not in trig and len(tok)>=4:
        prev3_h=tok.iloc[-4:-1]['high'].max();prev3_l=tok.iloc[-4:-1]['low'].min()
        body=abs(row['close']-row['open'])
        if row['high']>=prev3_h and row['low']<=prev3_l and body>=0.5*atr:
            add('AC','long' if row['close']>row['open'] else 'short',row['close']); trig['AC']=True
    # NY6: GAP London close vs NY open >0.5ATR, continuation
    if 14.5<=hour<14.6 and 'NY6' not in trig and len(lon)>=5:
        gap=(row['open']-lon.iloc[-1]['close'])/atr
        if abs(gap)>=0.5: add('NY6','long' if gap>0 else 'short',row['open']); trig['NY6']=True
    # NY11: ORB NY 30min breakout
    if 15.0<=hour<21.0 and 'NY11' not in trig:
        if 'NY11_h' not in trig:
            orb=tv[(tv['ts_dt']>=ns)&(tv['ts_dt']<pd.Timestamp(today.year,today.month,today.day,15,0,tz='UTC'))]
            if len(orb)>=6: trig['NY11_h']=float(orb['high'].max()); trig['NY11_l']=float(orb['low'].min())
        if 'NY11_h' in trig:
            if row['close']>trig['NY11_h']: add('NY11','long',row['close']); trig['NY11']=True
            elif row['close']<trig['NY11_l']: add('NY11','short',row['close']); trig['NY11']=True
    # NY16: 3 dernieres bougies London >1ATR, continuation NY
    if 14.5<=hour<14.6 and 'NY16' not in trig and len(lon)>=9:
        l3=lon.iloc[-3:]; m=(l3.iloc[-1]['close']-l3.iloc[0]['open'])/atr
        if abs(m)>=1.0: add('NY16','long' if m>0 else 'short',row['open']); trig['NY16']=True
    # NY17: 3 dernieres bougies London >0.5ATR, continuation NY
    if 14.5<=hour<14.6 and 'NY17' not in trig and len(lon)>=9:
        l3=lon.iloc[-3:]; m=(l3.iloc[-1]['close']-l3.iloc[0]['open'])/atr
        if abs(m)>=0.5: add('NY17','long' if m>0 else 'short',row['open']); trig['NY17']=True
    # NY23: 3 soldiers/crows NY continuation
    if 14.5<=hour<21.0 and 'NY23' not in trig and len(ny)>=3:
        c1=ny.iloc[-3];c2=ny.iloc[-2];c3=ny.iloc[-1]
        b1n=c1['close']-c1['open'];b2n=c2['close']-c2['open'];b3n=c3['close']-c3['open']
        if b1n*b2n>0 and b2n*b3n>0 and min(abs(b1n),abs(b2n),abs(b3n))>0.1*atr and abs(b1n+b2n+b3n)>=0.5*atr:
            add('NY23','long' if b3n>0 else 'short',c3['close']); trig['NY23']=True
    # NY24: Outside bar NY
    if 14.5<=hour<21.0 and 'NY24' not in trig and len(ny)>=4:
        prev3_h_ny=ny.iloc[-4:-1]['high'].max();prev3_l_ny=ny.iloc[-4:-1]['low'].min()
        body_ny=abs(row['close']-row['open'])
        if row['high']>=prev3_h_ny and row['low']<=prev3_l_ny and body_ny>=0.5*atr:
            add('NY24','long' if row['close']>row['open'] else 'short',row['close']); trig['NY24']=True

print(f"\n  Done.", flush=True)

# Stats individuelles
print("\n" + "="*100)
print("STATS INDIVIDUELLES — Config unique TRp SL=1.5 ACT=0.3 TRAIL=0.3 T12 (trailing corrige)")
print("="*100)
for sn in sorted(S.keys()):
    t = S[sn]
    if len(t) < 10: continue
    pnls = [x['pnl_oz'] for x in t]
    gp = sum(p for p in pnls if p>0); gl = abs(sum(p for p in pnls if p<0))+0.001
    wr = sum(1 for p in pnls if p>0)/len(pnls)*100
    mid = len(pnls)//2
    f1 = np.mean(pnls[:mid]); f2 = np.mean(pnls[mid:])
    # Tiers
    n = len(pnls); t1s = sum(pnls[:n//3]); t2s = sum(pnls[n//3:2*n//3]); t3s = sum(pnls[2*n//3:])
    tiers = sum(1 for x in [t1s, t2s, t3s] if x > 0)
    split_ok = "OK" if f1>0 and f2>0 else "!!"
    print(f"  {sn:3s}: n={len(t):4d} WR={wr:.0f}% PF={gp/gl:.2f} Avg={np.mean(pnls):+.3f} [{f1:+.3f}|{f2:+.3f}] {split_ok} Tiers={tiers}/3")

# Combos
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

all_n = sorted(strat_arrays.keys())
n_strats = len(all_n)
total_combos = sum(1 for sz in range(3, n_strats+1) for _ in combinations(all_n, sz))
print(f"\n{'='*100}")
print(f"COMBINAISONS ({total_combos} combos, {n_strats} strats: {', '.join(all_n)}, taille 3-{n_strats})")
print(f"{'='*100}", flush=True)

results = []
done = 0; t0 = time.time()
for size in range(3, n_strats+1):
    for combo in combinations(all_n, size):
        done += 1
        if done % 2000 == 0:
            elapsed = time.time() - t0
            speed = done / elapsed if elapsed > 0 else 0
            eta = (total_combos - done) / speed if speed > 0 else 0
            pct = done * 100 // total_combos
            print(f"\r  {pct:3d}% ({done}/{total_combos}) ETA {eta:.0f}s   ", end='', flush=True)
        r = eval_combo(combo)
        if r is not None: results.append(r)

print(f"\n\n  {len(results)} combos valides", flush=True)

rdf = pd.DataFrame(results)
ok = rdf[(rdf['split']) & (rdf['tiers']==3) & (rdf['both'])]

def show(title, sub, col, n=20):
    print(f"\n  {title}")
    print(f"  {'Combo':55s} {'n':>5s} {'t/j':>4s} {'Capital':>12s} {'Rend%':>9s} {'DD%':>7s} {'Cal':>8s} {'PF':>5s} {'WR%':>4s} {'M+':>5s}")
    for _, r in sub.sort_values(col, ascending=False).head(n).iterrows():
        print(f"  {r['combo'][:55]:55s} {r['n']:5.0f} {r['tpd']:4.1f} {r['capital']:12,.0f}$ {r['ret']:+8.0f}% {r['mdd']:+6.1f}% {r['cal']:8.1f} {r['pf']:.2f} {r['wr']:3.0f}% {r['pm']:2.0f}/{r['tm']:.0f}")

# Toutes les combos qui passent les filtres, triees par Calmar
print(f"\n  {len(ok)} combos passent les filtres (split OK, tiers 3/3, L+S)")

show("TOP 50 CALMAR (split OK, tiers 3/3, L+S)", ok, 'cal', 50)
show("TOP 50 PF (split OK, tiers 3/3, L+S)", ok, 'pf', 50)
show("TOP 30 RENDEMENT (split OK, tiers 3/3, L+S, DD>-15%)", ok[ok['mdd']>-15], 'ret', 30)
show("TOP 30 RENDEMENT (split OK, tiers 3/3, L+S, DD>-10%)", ok[ok['mdd']>-10], 'ret', 30)

# Par taille de combo
print(f"\n{'='*100}")
print("MEILLEUR COMBO PAR TAILLE (Calmar, split OK, tiers 3/3, L+S)")
print(f"{'='*100}")
for sz in range(3, n_strats+1):
    sub = ok[ok['ns']==sz]
    if len(sub) == 0: continue
    best = sub.sort_values('cal', ascending=False).iloc[0]
    print(f"  {sz:2d} strats: {best['combo'][:55]:55s} n={best['n']:5.0f} PF={best['pf']:.2f} WR={best['wr']:.0f}% DD={best['mdd']:+.1f}% Cal={best['cal']:.1f} Rend={best['ret']:+.0f}% M+={best['pm']:.0f}/{best['tm']:.0f}")

# Frequence d'apparition de chaque strat dans le top 50 Calmar
top50 = ok.sort_values('cal', ascending=False).head(50)
print(f"\n{'='*100}")
print("FREQUENCE DES STRATS DANS LE TOP 50 CALMAR")
print(f"{'='*100}")
from collections import Counter
freq = Counter()
for _, r in top50.iterrows():
    for s in r['combo'].split('+'):
        freq[s] += 1
for s, c in freq.most_common():
    bar = '#' * c
    print(f"  {s:3s}: {c:2d}/50  {bar}")

print()
