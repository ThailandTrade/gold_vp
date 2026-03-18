"""
Audit complet du portfolio v7 (18 strats) — tous les angles
1. Stabilite par tiers (3 periodes)
2. Stabilite par mois
3. PF par strat individuelle
4. Correlation entre strats (gagnent/perdent ensemble?)
5. Distribution des PnL (pas de outliers qui portent tout?)
6. Worst streaks (max pertes consecutives)
7. Performance par jour de la semaine
8. Performance par heure d'entree
9. Dependance au regime de marche (ATR haut/bas)
10. Robustesse parametrique (SL, ACT, TRAIL varies)
"""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
from collections import Counter
from dotenv import load_dotenv; load_dotenv()
from phase1_poc_calculator import get_conn, compute_atr, get_trading_days
from phase3_analyze import load_candles_5m

SLIPPAGE = 0.10
def sim_trail(cdf, pos, entry, d, sl, atr, mx, act, trail):
    best = entry; stop = entry + sl*atr if d == 'short' else entry - sl*atr; ta = False
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
SL, ACT, TRAIL = 0.75, 0.5, 0.3

# ══════ Collecter tous les trades ══════
print("Collecte des 18 strats...", flush=True)
S = {}

# Meme code que test_v10 pour toutes les strats
def collect_all():
    daily_data = {}
    for day in trading_days:
        dc = candles[candles['date'] == day]
        if len(dc) >= 10: daily_data[day] = {'dir': 1 if dc.iloc[-1]['close'] > dc.iloc[0]['open'] else -1}

    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        tok = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
        lon = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))]
        ny = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,21,30,tz='UTC'))]

        def add(sn, d, e, pi):
            b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
            pnl = (ex-e) if d=='long' else (e-ex)
            S.setdefault(sn, []).append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b,
                                         'hour':candles.iloc[pi]['ts_dt'].hour,'dow':day.weekday()})

        if len(tok)>=18:
            lvl=tok.iloc[:12]['high'].max()
            for i in range(12,len(tok)):
                if tok.iloc[i]['close']>lvl: add('A','long',tok.iloc[i]['close'],candles.index.get_loc(tok.index[i])); break
        if len(tok)>=10:
            m=(tok.iloc[-1]['close']-tok.iloc[0]['open'])/atr
            if abs(m)>=1.0:
                l2=candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
                if len(l2)>=6: add('C','short' if m>0 else 'long',l2.iloc[0]['open'],candles.index.get_loc(l2.index[0]))
        tc=candles[candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC')]
        if len(tc)>=5:
            l2=candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
            if len(l2)>=6:
                gap=(l2.iloc[0]['open']-tc.iloc[-1]['close'])/atr
                if abs(gap)>=0.5: add('D','long' if gap>0 else 'short',l2.iloc[0]['open'],candles.index.get_loc(l2.index[0]))
        kz=candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,10,0,tz='UTC'))]
        if len(kz)>=20:
            m=(kz.iloc[-1]['close']-kz.iloc[0]['open'])/atr
            if abs(m)>=0.5:
                post=candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,10,0,tz='UTC')]
                if len(post)>=6: add('E','short' if m>0 else 'long',post.iloc[0]['open'],candles.index.get_loc(post.index[0]))
        if len(tok)>=8:
            for i in range(1,len(tok)):
                b1b=tok.iloc[i-1]['close']-tok.iloc[i-1]['open'];b2b=tok.iloc[i]['close']-tok.iloc[i]['open']
                if abs(b1b)<0.5*atr or abs(b2b)<0.5*atr: continue
                if b1b*b2b>=0 or abs(b2b)<=abs(b1b): continue
                add('F','long' if b2b>0 else 'short',tok.iloc[i]['close'],candles.index.get_loc(tok.index[i])); break
        if len(ny)>=6:
            body=ny.iloc[0]['close']-ny.iloc[0]['open']
            if abs(body)>=0.3*atr and len(ny)>=2:
                add('G','long' if body>0 else 'short',ny.iloc[1]['open'],candles.index.get_loc(ny.index[1]))
        if len(tok)>=9:
            l3=tok.iloc[-3:]; m=(l3.iloc[-1]['close']-l3.iloc[0]['open'])/atr
            if abs(m)>=1.0:
                l2=candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
                if len(l2)>=6: add('H','long' if m>0 else 'short',l2.iloc[0]['open'],candles.index.get_loc(l2.index[0]))
        ny1=candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,15,30,tz='UTC'))]
        if len(ny1)>=10:
            m=(ny1.iloc[-1]['close']-ny1.iloc[0]['open'])/atr
            if abs(m)>=1.0:
                post=candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,15,30,tz='UTC')]
                if len(post)>=6: add('I','short' if m>0 else 'long',post.iloc[0]['open'],candles.index.get_loc(post.index[0]))
        if len(lon)>=6:
            body=lon.iloc[0]['close']-lon.iloc[0]['open']
            if abs(body)>=0.3*atr and len(lon)>=2:
                add('J','long' if body>0 else 'short',lon.iloc[1]['open'],candles.index.get_loc(lon.index[1]))
        if len(tok)>=6:
            for i in range(len(tok)):
                body=tok.iloc[i]['close']-tok.iloc[i]['open']
                if abs(body)>=1.0*atr:
                    add('O','long' if body>0 else 'short',tok.iloc[i]['close'],candles.index.get_loc(tok.index[i])); break
        if len(ny)>=12:
            oh=ny.iloc[:6]['high'].max(); ol=ny.iloc[:6]['low'].min()
            for i in range(6,len(ny)):
                r=ny.iloc[i]
                if r['close']>oh: add('P','long',r['close'],candles.index.get_loc(ny.index[i])); break
                elif r['close']<ol: add('P','short',r['close'],candles.index.get_loc(ny.index[i])); break
        if len(lon)>=6:
            for i in range(1,len(lon)):
                pb=lon.iloc[i-1];cb=lon.iloc[i]; hit=False
                if pb['close']<pb['open'] and cb['close']>cb['open'] and cb['open']<=pb['close'] and cb['close']>=pb['open'] and abs(cb['close']-cb['open'])>=0.3*atr:
                    add('Q','long',cb['close'],candles.index.get_loc(lon.index[i])); hit=True
                if not hit and pb['close']>pb['open'] and cb['close']<cb['open'] and cb['open']>=pb['close'] and cb['close']<=pb['open'] and abs(cb['close']-cb['open'])>=0.3*atr:
                    add('Q','short',cb['close'],candles.index.get_loc(lon.index[i])); hit=True
                if hit: break
        if len(tok)>=6:
            for i in range(2,len(tok)):
                c1=tok.iloc[i-2];c2=tok.iloc[i-1];c3=tok.iloc[i]
                b1=c1['close']-c1['open'];b2=c2['close']-c2['open'];b3=c3['close']-c3['open']
                if b1*b2>0 and b2*b3>0 and min(abs(b1),abs(b2),abs(b3))>0.1*atr and abs(b1+b2+b3)>=0.5*atr:
                    add('R','long' if b3>0 else 'short',c3['close'],candles.index.get_loc(tok.index[i])); break
        if len(lon)>=6:
            for i in range(2,len(lon)):
                c1=lon.iloc[i-2];c2=lon.iloc[i-1];c3=lon.iloc[i]
                b1=c1['close']-c1['open'];b2=c2['close']-c2['open'];b3=c3['close']-c3['open']
                if b1*b2>0 and b2*b3>0 and min(abs(b1),abs(b2),abs(b3))>0.1*atr and abs(b1+b2+b3)>=0.5*atr:
                    add('S','short' if b3>0 else 'long',c3['close'],candles.index.get_loc(lon.index[i])); break
        if len(tok)>=12:
            for i in range(6,len(tok)):
                last6=tok.iloc[i-6:i]; n_bull=(last6['close']>last6['open']).sum()
                if n_bull>=5:
                    add('V','long',tok.iloc[i]['open'],candles.index.get_loc(tok.index[i])); break
                elif n_bull<=1:
                    add('V','short',tok.iloc[i]['open'],candles.index.get_loc(tok.index[i])); break
        di = trading_days.index(day) if day in trading_days else -1
        if di>=3:
            dirs=[]
            for k in range(3):
                dk=trading_days[di-3+k]
                if dk in daily_data: dirs.append(daily_data[dk]['dir'])
            if len(dirs)==3 and len(set(dirs))==1:
                l2=candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
                if len(l2)>=6: add('Z','short' if dirs[0]>0 else 'long',l2.iloc[0]['open'],candles.index.get_loc(l2.index[0]))
        if len(lon)>=6:
            for i in range(len(lon)):
                r=lon.iloc[i]; rng=r['high']-r['low']
                if rng<0.3*atr or abs(r['close']-r['open'])<0.2*atr: continue
                pir=(r['close']-r['low'])/rng
                if pir>=0.9: add('AA','long',r['close'],candles.index.get_loc(lon.index[i])); break
                if pir<=0.1: add('AA','short',r['close'],candles.index.get_loc(lon.index[i])); break
        if len(tok)>=6:
            for i in range(3,len(tok)):
                prev3_h=tok.iloc[i-3:i]['high'].max(); prev3_l=tok.iloc[i-3:i]['low'].min()
                r=tok.iloc[i]; body=abs(r['close']-r['open'])
                if r['high']>=prev3_h and r['low']<=prev3_l and body>=0.5*atr:
                    add('AC','long' if r['close']>r['open'] else 'short',r['close'],candles.index.get_loc(tok.index[i])); break

collect_all()
conn.close()

# Construire le portfolio avec conflict resolution
strats = ['A','C','D','E','F','G','H','I','J','O','P','Q','R','S','V','Z','AA','AC']
combined = []
for sn in strats:
    for t in S.get(sn, []): combined.append({**t, 'strat': sn})
combined.sort(key=lambda x: (x['ei'], x['strat']))
al = []; acc = []
for t in combined:
    al = [(xi, d) for xi, d in al if xi >= t['ei']]
    if any(d != t['dir'] for _, d in al): continue
    acc.append(t); al.append((t['xi'], t['dir']))

df = pd.DataFrame(acc)
print(f"Trades apres conflict resolution: {len(df)}")

# ══════ 1. STABILITE PAR TIERS ══════
print("\n" + "="*80)
print("1. STABILITE PAR TIERS (3 periodes egales)")
print("="*80)
n = len(df); t1 = n//3; t2 = 2*n//3
for label, sub in [("Tiers 1", df.iloc[:t1]), ("Tiers 2", df.iloc[t1:t2]), ("Tiers 3", df.iloc[t2:])]:
    gp = sub[sub['pnl_oz']>0]['pnl_oz'].sum(); gl = abs(sub[sub['pnl_oz']<0]['pnl_oz'].sum())+0.001
    wr = (sub['pnl_oz']>0).mean()*100
    print(f"  {label}: n={len(sub):4d} WR={wr:.0f}% PF={gp/gl:.2f} avg={sub['pnl_oz'].mean():+.3f}")

# ══════ 2. STABILITE PAR MOIS ══════
print("\n" + "="*80)
print("2. STABILITE PAR MOIS")
print("="*80)
df['month'] = df['date'].apply(lambda d: str(d.year)+"-"+str(d.month).zfill(2))
print(f"  {'Mois':8s} {'n':>5s} {'WR':>5s} {'PF':>6s} {'Avg PnL':>10s} {'Sum PnL':>10s}")
for mo in sorted(df['month'].unique()):
    sub = df[df['month']==mo]
    gp = sub[sub['pnl_oz']>0]['pnl_oz'].sum(); gl = abs(sub[sub['pnl_oz']<0]['pnl_oz'].sum())+0.001
    wr = (sub['pnl_oz']>0).mean()*100
    print(f"  {mo:8s} {len(sub):5d} {wr:4.0f}% {gp/gl:6.2f} {sub['pnl_oz'].mean():+10.3f} {sub['pnl_oz'].sum():+10.2f}")

# ══════ 3. PF PAR STRAT ══════
print("\n" + "="*80)
print("3. PF PAR STRAT (apres conflict resolution)")
print("="*80)
print(f"  {'Strat':5s} {'n':>5s} {'WR':>5s} {'PF':>6s} {'Avg':>8s} {'L':>4s} {'S':>4s}")
for sn in sorted(df['strat'].unique()):
    sub = df[df['strat']==sn]
    gp = sub[sub['pnl_oz']>0]['pnl_oz'].sum(); gl = abs(sub[sub['pnl_oz']<0]['pnl_oz'].sum())+0.001
    wr = (sub['pnl_oz']>0).mean()*100
    nl = (sub['dir']=='long').sum(); ns = (sub['dir']=='short').sum()
    print(f"  {sn:5s} {len(sub):5d} {wr:4.0f}% {gp/gl:6.2f} {sub['pnl_oz'].mean():+8.3f} {nl:4d} {ns:4d}")

# ══════ 4. CORRELATION ══════
print("\n" + "="*80)
print("4. CORRELATION — strats qui gagnent/perdent ensemble")
print("="*80)
# Pour chaque jour, noter si chaque strat a gagne ou perdu
strat_daily = {}
for sn in strats:
    sn_trades = df[df['strat']==sn]
    strat_daily[sn] = {}
    for _, t in sn_trades.iterrows():
        strat_daily[sn][str(t['date'])] = 1 if t['pnl_oz'] > 0 else -1

# Matrice de correlation
strat_names = sorted(strat_daily.keys())
print(f"  Paires les plus correlees (gagnent/perdent le meme jour):")
corr_pairs = []
for i, s1 in enumerate(strat_names):
    for s2 in strat_names[i+1:]:
        common_days = set(strat_daily[s1].keys()) & set(strat_daily[s2].keys())
        if len(common_days) < 20: continue
        same = sum(1 for d in common_days if strat_daily[s1][d] == strat_daily[s2][d])
        corr = same / len(common_days)
        corr_pairs.append((s1, s2, corr, len(common_days)))

for s1, s2, corr, n in sorted(corr_pairs, key=lambda x: -x[2])[:10]:
    print(f"    {s1:3s}+{s2:3s}: {corr:.0%} meme resultat ({n} jours communs)")
print(f"\n  Paires les moins correlees:")
for s1, s2, corr, n in sorted(corr_pairs, key=lambda x: x[2])[:5]:
    print(f"    {s1:3s}+{s2:3s}: {corr:.0%} meme resultat ({n} jours communs)")

# ══════ 5. DISTRIBUTION DES PNL ══════
print("\n" + "="*80)
print("5. DISTRIBUTION DES PNL (en ATR)")
print("="*80)
df['pnl_atr'] = df['pnl_oz'] / df['atr']
print(f"  Moyenne: {df['pnl_atr'].mean():+.3f} ATR")
print(f"  Mediane: {df['pnl_atr'].median():+.3f} ATR")
print(f"  Std:     {df['pnl_atr'].std():.3f} ATR")
print(f"  Min:     {df['pnl_atr'].min():+.3f} ATR")
print(f"  Max:     {df['pnl_atr'].max():+.3f} ATR")
print(f"  Skew:    {df['pnl_atr'].skew():+.3f}")
percentiles = [1, 5, 10, 25, 50, 75, 90, 95, 99]
print(f"  Percentiles:")
for p in percentiles:
    print(f"    P{p:2d}: {df['pnl_atr'].quantile(p/100):+.3f} ATR")

# Top 10 gagnants / perdants
print(f"\n  Top 5 gagnants:")
for _, t in df.nlargest(5, 'pnl_atr').iterrows():
    print(f"    {t['strat']:3s} {t['date']} {t['dir']:5s} {t['pnl_atr']:+.3f} ATR")
print(f"  Top 5 perdants:")
for _, t in df.nsmallest(5, 'pnl_atr').iterrows():
    print(f"    {t['strat']:3s} {t['date']} {t['dir']:5s} {t['pnl_atr']:+.3f} ATR")

# ══════ 6. WORST STREAKS ══════
print("\n" + "="*80)
print("6. WORST STREAKS (pertes consecutives)")
print("="*80)
import itertools
losses = [t['pnl_oz'] < 0 for _, t in df.iterrows()]
max_loss_streak = max((sum(1 for _ in g) for k, g in itertools.groupby(losses) if k), default=0)
win_streak = max((sum(1 for _ in g) for k, g in itertools.groupby(losses) if not k), default=0)
print(f"  Max pertes consecutives: {max_loss_streak}")
print(f"  Max gains consecutifs:   {win_streak}")

# Worst drawdown streak (jours consecutifs negatifs)
daily_pnl = df.groupby('date')['pnl_oz'].sum()
daily_neg = [p < 0 for p in daily_pnl.values]
max_neg_days = max((sum(1 for _ in g) for k, g in itertools.groupby(daily_neg) if k), default=0)
print(f"  Max jours consecutifs negatifs: {max_neg_days}")

# ══════ 7. PAR JOUR DE LA SEMAINE ══════
print("\n" + "="*80)
print("7. PERFORMANCE PAR JOUR DE LA SEMAINE")
print("="*80)
dow_names = ['Lun','Mar','Mer','Jeu','Ven']
print(f"  {'Jour':5s} {'n':>5s} {'WR':>5s} {'PF':>6s} {'Avg':>8s}")
for dow in range(5):
    sub = df[df['dow']==dow]
    if len(sub) < 10: continue
    gp = sub[sub['pnl_oz']>0]['pnl_oz'].sum(); gl = abs(sub[sub['pnl_oz']<0]['pnl_oz'].sum())+0.001
    wr = (sub['pnl_oz']>0).mean()*100
    print(f"  {dow_names[dow]:5s} {len(sub):5d} {wr:4.0f}% {gp/gl:6.2f} {sub['pnl_oz'].mean():+8.3f}")

# ══════ 8. PAR HEURE D'ENTREE ══════
print("\n" + "="*80)
print("8. PERFORMANCE PAR HEURE D'ENTREE")
print("="*80)
print(f"  {'Heure':5s} {'n':>5s} {'WR':>5s} {'PF':>6s} {'Avg':>8s}")
for hour in sorted(df['hour'].unique()):
    sub = df[df['hour']==hour]
    if len(sub) < 10: continue
    gp = sub[sub['pnl_oz']>0]['pnl_oz'].sum(); gl = abs(sub[sub['pnl_oz']<0]['pnl_oz'].sum())+0.001
    wr = (sub['pnl_oz']>0).mean()*100
    print(f"  {hour:5d} {len(sub):5d} {wr:4.0f}% {gp/gl:6.2f} {sub['pnl_oz'].mean():+8.3f}")

# ══════ 9. REGIME ATR ══════
print("\n" + "="*80)
print("9. PERFORMANCE PAR REGIME ATR")
print("="*80)
atr_med = df['atr'].median()
for label, sub in [("ATR bas (<median)", df[df['atr']<atr_med]), ("ATR haut (>median)", df[df['atr']>=atr_med])]:
    gp = sub[sub['pnl_oz']>0]['pnl_oz'].sum(); gl = abs(sub[sub['pnl_oz']<0]['pnl_oz'].sum())+0.001
    wr = (sub['pnl_oz']>0).mean()*100
    print(f"  {label:25s}: n={len(sub):4d} WR={wr:.0f}% PF={gp/gl:.2f} avg={sub['pnl_oz'].mean():+.3f}")

# ══════ 10. ROBUSTESSE PARAMETRIQUE ══════
print("\n" + "="*80)
print("10. ROBUSTESSE PARAMETRIQUE — variation SL/ACT/TRAIL")
print("="*80)
# Recalculer le PF pour differents params (sur un echantillon)
sample_trades = combined[:500]  # premier 500 trades bruts pour vitesse
for sl_test, act_test, trail_test in [(0.5,0.5,0.3),(0.75,0.5,0.3),(1.0,0.5,0.3),(0.75,0.3,0.3),(0.75,0.7,0.3),(0.75,0.5,0.2),(0.75,0.5,0.4)]:
    gp = 0; gl = 0; n_test = 0
    for t in sample_trades:
        b, ex = sim_trail(candles, t['ei'], t['entry'] if 'entry' in t else candles.iloc[t['ei']]['close'],
                          t['dir'], sl_test, t['atr'], 24, act_test, trail_test)
        pnl_raw = (ex - (t['entry'] if 'entry' in t else candles.iloc[t['ei']]['close'])) if t['dir']=='long' else ((t['entry'] if 'entry' in t else candles.iloc[t['ei']]['close']) - ex)
        pnl = pnl_raw - get_sp(t['date'])
        if pnl > 0: gp += pnl
        else: gl += abs(pnl)
        n_test += 1
    pf = gp / (gl + 0.001)
    current = "  <<<" if sl_test==0.75 and act_test==0.5 and trail_test==0.3 else ""
    print(f"  SL={sl_test:.2f} ACT={act_test:.1f} TRAIL={trail_test:.1f}: PF={pf:.2f} (n={n_test}){current}")

# ══════ 11. EXIT REASONS ══════
print("\n" + "="*80)
print("11. RAISONS DE SORTIE")
print("="*80)
# Calculer combien sortent par stop vs timeout
# On peut inferer: bars_held < 24 = stop, bars_held >= 24 = timeout
# Mais on n'a pas bars_held dans nos donnees... recalculer
stop_trades = 0; timeout_trades = 0
for t in acc:
    bars = t['xi'] - t['ei']
    if bars >= 24: timeout_trades += 1
    else: stop_trades += 1
print(f"  Stop:    {stop_trades} ({stop_trades/len(acc)*100:.0f}%)")
print(f"  Timeout: {timeout_trades} ({timeout_trades/len(acc)*100:.0f}%)")

# PF par raison
stop_pnl = [t['pnl_oz'] for t in acc if (t['xi']-t['ei']) < 24]
timeout_pnl = [t['pnl_oz'] for t in acc if (t['xi']-t['ei']) >= 24]
if stop_pnl:
    gp=sum(p for p in stop_pnl if p>0); gl=abs(sum(p for p in stop_pnl if p<0))+0.001
    print(f"  Stop PF:    {gp/gl:.2f} (avg={np.mean(stop_pnl):+.3f})")
if timeout_pnl:
    gp=sum(p for p in timeout_pnl if p>0); gl=abs(sum(p for p in timeout_pnl if p<0))+0.001
    print(f"  Timeout PF: {gp/gl:.2f} (avg={np.mean(timeout_pnl):+.3f})")

# ══════ 12. LONG vs SHORT ══════
print("\n" + "="*80)
print("12. LONG vs SHORT")
print("="*80)
for d in ['long','short']:
    sub = df[df['dir']==d]
    gp = sub[sub['pnl_oz']>0]['pnl_oz'].sum(); gl = abs(sub[sub['pnl_oz']<0]['pnl_oz'].sum())+0.001
    wr = (sub['pnl_oz']>0).mean()*100
    print(f"  {d:5s}: n={len(sub):4d} WR={wr:.0f}% PF={gp/gl:.2f} avg={sub['pnl_oz'].mean():+.3f}")

print("\n" + "="*80)
print("FIN AUDIT COMPLET")
print("="*80)
