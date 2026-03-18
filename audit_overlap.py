"""
Audit : combien de strats entrent au MEME moment ?
Si 5 strats entrent long a 8h00, c'est UN SEUL trade x5 le risque.
"""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
from collections import Counter, defaultdict
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
SL, ACT, TRAIL = 0.75, 0.5, 0.3

# Collecter TOUS les trades avec leur ei (candle index d'entree)
all_trades = []

for day in trading_days:
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue

    def add(sn, d, e, pi):
        b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
        pnl = (ex-e) if d=='long' else (e-ex)
        all_trades.append({'day':day, 'strat':sn, 'dir':d, 'ei':pi, 'xi':pi+b,
                           'entry':e, 'exit':ex, 'pnl_oz':pnl-get_sp(day),
                           'time':candles.iloc[pi]['ts_dt']})

    tok = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    lon = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))]
    ny = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,21,30,tz='UTC'))]

    # A
    if len(tok)>=18:
        lvl=tok.iloc[:12]['high'].max()
        for i in range(12,len(tok)):
            if tok.iloc[i]['close']>lvl:
                add('A','long',tok.iloc[i]['close'],candles.index.get_loc(tok.index[i])); break
    # C
    if len(tok)>=10:
        m=(tok.iloc[-1]['close']-tok.iloc[0]['open'])/atr
        if abs(m)>=1.0:
            l2=candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
            if len(l2)>=6: add('C','short' if m>0 else 'long',l2.iloc[0]['open'],candles.index.get_loc(l2.index[0]))
    # D
    tc=candles[candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC')]
    if len(tc)>=5:
        l2=candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
        if len(l2)>=6:
            gap=(l2.iloc[0]['open']-tc.iloc[-1]['close'])/atr
            if abs(gap)>=0.5: add('D','long' if gap>0 else 'short',l2.iloc[0]['open'],candles.index.get_loc(l2.index[0]))
    # E
    kz=candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,10,0,tz='UTC'))]
    if len(kz)>=20:
        m=(kz.iloc[-1]['close']-kz.iloc[0]['open'])/atr
        if abs(m)>=0.5:
            post=candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,10,0,tz='UTC')]
            if len(post)>=6: add('E','short' if m>0 else 'long',post.iloc[0]['open'],candles.index.get_loc(post.index[0]))
    # F
    if len(tok)>=8:
        for i in range(1,len(tok)):
            b1b=tok.iloc[i-1]['close']-tok.iloc[i-1]['open'];b2b=tok.iloc[i]['close']-tok.iloc[i]['open']
            if abs(b1b)<0.5*atr or abs(b2b)<0.5*atr: continue
            if b1b*b2b>=0 or abs(b2b)<=abs(b1b): continue
            add('F','long' if b2b>0 else 'short',tok.iloc[i]['close'],candles.index.get_loc(tok.index[i])); break
    # G
    if len(ny)>=6:
        body=ny.iloc[0]['close']-ny.iloc[0]['open']
        if abs(body)>=0.3*atr and len(ny)>=2:
            add('G','long' if body>0 else 'short',ny.iloc[1]['open'],candles.index.get_loc(ny.index[1]))
    # H
    if len(tok)>=9:
        l3=tok.iloc[-3:]; m=(l3.iloc[-1]['close']-l3.iloc[0]['open'])/atr
        if abs(m)>=1.0:
            l2=candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
            if len(l2)>=6: add('H','long' if m>0 else 'short',l2.iloc[0]['open'],candles.index.get_loc(l2.index[0]))
    # I
    ny1=candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,15,30,tz='UTC'))]
    if len(ny1)>=10:
        m=(ny1.iloc[-1]['close']-ny1.iloc[0]['open'])/atr
        if abs(m)>=1.0:
            post=candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,15,30,tz='UTC')]
            if len(post)>=6: add('I','short' if m>0 else 'long',post.iloc[0]['open'],candles.index.get_loc(post.index[0]))
    # J
    if len(lon)>=6:
        body=lon.iloc[0]['close']-lon.iloc[0]['open']
        if abs(body)>=0.3*atr and len(lon)>=2:
            add('J','long' if body>0 else 'short',lon.iloc[1]['open'],candles.index.get_loc(lon.index[1]))
    # O
    if len(tok)>=6:
        for i in range(len(tok)):
            body=tok.iloc[i]['close']-tok.iloc[i]['open']
            if abs(body)>=1.0*atr:
                add('O','long' if body>0 else 'short',tok.iloc[i]['close'],candles.index.get_loc(tok.index[i])); break
    # P
    if len(ny)>=12:
        oh=ny.iloc[:6]['high'].max(); ol=ny.iloc[:6]['low'].min()
        for i in range(6,len(ny)):
            r=ny.iloc[i]
            if r['close']>oh: add('P','long',r['close'],candles.index.get_loc(ny.index[i])); break
            elif r['close']<ol: add('P','short',r['close'],candles.index.get_loc(ny.index[i])); break
    # Q
    if len(lon)>=6:
        for i in range(1,len(lon)):
            pb=lon.iloc[i-1];cb=lon.iloc[i]
            if pb['close']<pb['open'] and cb['close']>cb['open'] and cb['open']<=pb['close'] and cb['close']>=pb['open'] and abs(cb['close']-cb['open'])>=0.3*atr:
                add('Q','long',cb['close'],candles.index.get_loc(lon.index[i])); break
            if pb['close']>pb['open'] and cb['close']<cb['open'] and cb['open']>=pb['close'] and cb['close']<=pb['open'] and abs(cb['close']-cb['open'])>=0.3*atr:
                add('Q','short',cb['close'],candles.index.get_loc(lon.index[i])); break
    # R
    if len(tok)>=6:
        for i in range(2,len(tok)):
            c1=tok.iloc[i-2];c2=tok.iloc[i-1];c3=tok.iloc[i]
            b1=c1['close']-c1['open'];b2=c2['close']-c2['open'];b3=c3['close']-c3['open']
            if b1*b2>0 and b2*b3>0 and min(abs(b1),abs(b2),abs(b3))>0.1*atr and abs(b1+b2+b3)>=0.5*atr:
                add('R','long' if b3>0 else 'short',c3['close'],candles.index.get_loc(tok.index[i])); break
    # S
    if len(lon)>=6:
        for i in range(2,len(lon)):
            c1=lon.iloc[i-2];c2=lon.iloc[i-1];c3=lon.iloc[i]
            b1=c1['close']-c1['open'];b2=c2['close']-c2['open'];b3=c3['close']-c3['open']
            if b1*b2>0 and b2*b3>0 and min(abs(b1),abs(b2),abs(b3))>0.1*atr and abs(b1+b2+b3)>=0.5*atr:
                add('S','short' if b3>0 else 'long',c3['close'],candles.index.get_loc(lon.index[i])); break
    # V
    if len(tok)>=12:
        for i in range(6,len(tok)):
            last6=tok.iloc[i-6:i]; n_bull=(last6['close']>last6['open']).sum()
            if n_bull>=5:
                add('V','long',tok.iloc[i]['open'],candles.index.get_loc(tok.index[i])); break
            elif n_bull<=1:
                add('V','short',tok.iloc[i]['open'],candles.index.get_loc(tok.index[i])); break
    # Z
    daily_data={}
    for dk in trading_days:
        dc=candles[candles['date']==dk]
        if len(dc)>=10: daily_data[dk]={'dir':1 if dc.iloc[-1]['close']>dc.iloc[0]['open'] else -1}
    di=trading_days.index(day) if day in trading_days else -1
    if di>=3:
        dirs=[]
        for k in range(3):
            dk=trading_days[di-3+k]
            if dk in daily_data: dirs.append(daily_data[dk]['dir'])
        if len(dirs)==3 and len(set(dirs))==1:
            l2=candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
            if len(l2)>=6: add('Z','short' if dirs[0]>0 else 'long',l2.iloc[0]['open'],candles.index.get_loc(l2.index[0]))
    # AA
    if len(lon)>=6:
        for i in range(len(lon)):
            r=lon.iloc[i]; rng=r['high']-r['low']
            if rng<0.3*atr or abs(r['close']-r['open'])<0.2*atr: continue
            pir=(r['close']-r['low'])/rng
            if pir>=0.9: add('AA','long',r['close'],candles.index.get_loc(lon.index[i])); break
            if pir<=0.1: add('AA','short',r['close'],candles.index.get_loc(lon.index[i])); break
    # AC
    if len(tok)>=6:
        for i in range(3,len(tok)):
            prev3_h=tok.iloc[i-3:i]['high'].max(); prev3_l=tok.iloc[i-3:i]['low'].min()
            r=tok.iloc[i]; body=abs(r['close']-r['open'])
            if r['high']>=prev3_h and r['low']<=prev3_l and body>=0.5*atr:
                add('AC','long' if r['close']>r['open'] else 'short',r['close'],candles.index.get_loc(tok.index[i])); break

conn.close()

df = pd.DataFrame(all_trades)
print(f"Total trades: {len(df)}")
print(f"Jours de trading: {len(trading_days)}")
print(f"Trades/jour moyen: {len(df)/len(trading_days):.1f}")

# ══════ ANALYSE OVERLAP ══════
print("\n" + "="*80)
print("OVERLAP : trades qui entrent a la MEME bougie (meme ei)")
print("="*80)

# Grouper par (day, ei, dir) = meme bougie, meme direction
groups = df.groupby(['day','ei','dir'])
overlap_counts = Counter()
overlap_details = defaultdict(list)
same_entry_total = 0

for (day, ei, dir_), group in groups:
    n = len(group)
    if n > 1:
        strats = sorted(group['strat'].tolist())
        key = '+'.join(strats)
        overlap_counts[n] += 1
        overlap_details[key] += [day]
        same_entry_total += n

print(f"\n  Trades au total: {len(df)}")
print(f"  Trades sur une bougie partagee: {same_entry_total} ({same_entry_total/len(df)*100:.0f}%)")
print(f"\n  Distribution du nombre de strats par bougie d'entree:")
for n_strats in sorted(overlap_counts.keys()):
    print(f"    {n_strats} strats en meme temps: {overlap_counts[n_strats]} occurrences")

print(f"\n  Groupes de strats qui entrent ensemble le plus souvent:")
for key, days in sorted(overlap_details.items(), key=lambda x: -len(x[1]))[:15]:
    print(f"    {key:40s}: {len(days)} jours")

# ══════ ENTREES IDENTIQUES (meme ei ET meme entry price) ══════
print("\n" + "="*80)
print("ENTREES IDENTIQUES (meme bougie, meme prix, meme direction)")
print("="*80)
groups2 = df.groupby(['day','ei','dir','entry'])
identical = 0
for (day, ei, dir_, entry), group in groups2:
    if len(group) > 1:
        identical += len(group)
        if identical <= 20:  # montrer les premiers
            strats = sorted(group['strat'].tolist())
            print(f"  {day} ei={ei} {dir_:5s} entry={entry:.2f}: {'+'.join(strats)}")

print(f"\n  Trades avec entree identique: {identical} ({identical/len(df)*100:.0f}%)")

# ══════ RISQUE REEL ══════
print("\n" + "="*80)
print("RISQUE REEL — max trades simultanes par jour")
print("="*80)
daily_max = {}
for day in trading_days:
    day_trades = df[df['day']==day]
    if len(day_trades) == 0: continue
    # Pour chaque bougie, compter combien de positions sont ouvertes
    max_open = 0
    for _, t in day_trades.iterrows():
        # Positions ouvertes a cette bougie = trades dont ei <= cette bougie et xi > cette bougie
        open_at = len(day_trades[(day_trades['ei']<=t['ei']) & (day_trades['xi']>t['ei'])])
        if open_at > max_open: max_open = open_at
    daily_max[day] = max_open

max_counts = Counter(daily_max.values())
print(f"  Distribution du max positions ouvertes simultanment:")
for n in sorted(max_counts.keys()):
    print(f"    {n} positions: {max_counts[n]} jours")

max_ever = max(daily_max.values()) if daily_max else 0
print(f"\n  MAX positions simultanées: {max_ever}")
print(f"  Avec risk 1% par trade = {max_ever}% de risque reel max")

# ══════ C et D : meme entree ? ══════
print("\n" + "="*80)
print("DETAIL : C et D entrent-ils toujours au meme prix ?")
print("="*80)
c_trades = df[df['strat']=='C']
d_trades = df[df['strat']=='D']
cd_same = 0; cd_diff_dir = 0; cd_total = 0
for day in trading_days:
    ct = c_trades[c_trades['day']==day]
    dt = d_trades[d_trades['day']==day]
    if len(ct)==1 and len(dt)==1:
        cd_total += 1
        if ct.iloc[0]['ei'] == dt.iloc[0]['ei']:
            cd_same += 1
            if ct.iloc[0]['dir'] != dt.iloc[0]['dir']:
                cd_diff_dir += 1

print(f"  Jours ou C et D triggent tous les deux: {cd_total}")
print(f"  Dont meme bougie d'entree (ei identique): {cd_same} ({cd_same/max(cd_total,1)*100:.0f}%)")
print(f"  Dont meme bougie mais direction opposee: {cd_diff_dir}")

# Meme chose pour C, D, H, J, Z (tous a London open)
print("\n" + "="*80)
print("STRATS QUI ENTRENT A LONDON OPEN (8h00)")
print("="*80)
london_open_strats = ['C','D','H','J','Z']
for day in trading_days:
    day_df = df[df['day']==day]
    lon_open = day_df[day_df['strat'].isin(london_open_strats)]
    if len(lon_open) > 2:
        strats = sorted(lon_open['strat'].tolist())
        dirs = lon_open['dir'].unique()
        entries = lon_open['entry'].unique()
        same_entry = len(entries) == 1
        print(f"  {day}: {'+'.join(strats)} dir={list(dirs)} entry={'MEME' if same_entry else 'DIFF'} ({entries})")
        if len(lon_open) >= 20: break  # limiter l'output

print("\n" + "="*80)
