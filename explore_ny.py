"""
Exploration exhaustive de strategies pour la session New York (14h30-21h UTC).
Meme infrastructure que les strats existantes, config unique SL=1.0 ACT=0.5 TRAIL=0.75 MX=12.
Trailing sur CLOSE.
"""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
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

SL, ACT, TRAIL, MX = 1.0, 0.5, 0.75, 12

def sim_exit(cdf, pos, entry, d, atr):
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

print("Collecte...", flush=True)
S = {}
prev_d = None; trig = {}; day_atr = None
for ci in range(len(candles)):
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
    ns = pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC')
    tv = candles[(candles['ts_dt']>=ds)&(candles['ts_dt']<=ct)]
    tok = tv[tv['ts_dt']<te]
    lon = tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<ns)]
    ny = tv[tv['ts_dt']>=ns]

    def add(sn, d, e):
        b, ex = sim_exit(candles, ci, e, d, atr)
        pnl = (ex-e) if d=='long' else (e-ex)
        S.setdefault(sn,[]).append({'date':today,'dir':d,'pnl_oz':pnl-get_sp(today),'atr':atr,'ei':ci,'xi':ci+b})

    # ═══════════════════════════════════════════════════════════
    # STRATEGIES NY — toutes entre 14h30 et 21h00 UTC
    # ═══════════════════════════════════════════════════════════

    # NY1: 1ere bougie NY > 0.3 ATR, continuation
    if 14.5<=hour<14.6 and 'NY1' not in trig:
        body = row['close'] - row['open']
        if abs(body) >= 0.3*atr:
            add('NY1','long' if body>0 else 'short',row['close']); trig['NY1']=True

    # NY2: 1ere bougie NY > 0.5 ATR, continuation (filtre plus strict)
    if 14.5<=hour<14.6 and 'NY2' not in trig:
        body = row['close'] - row['open']
        if abs(body) >= 0.5*atr:
            add('NY2','long' if body>0 else 'short',row['close']); trig['NY2']=True

    # NY3: 1ere bougie NY > 1.0 ATR, continuation (gros move)
    if 14.5<=hour<14.6 and 'NY3' not in trig:
        body = row['close'] - row['open']
        if abs(body) >= 1.0*atr:
            add('NY3','long' if body>0 else 'short',row['close']); trig['NY3']=True

    # NY4: FADE London move >1ATR a NY open (comme C mais London->NY)
    if 14.5<=hour<14.6 and 'NY4' not in trig and len(lon)>=10:
        m = (lon.iloc[-1]['close'] - lon.iloc[0]['open']) / atr
        if abs(m) >= 1.0:
            add('NY4','short' if m>0 else 'long',row['open']); trig['NY4']=True

    # NY5: FADE London move >0.5ATR a NY open
    if 14.5<=hour<14.6 and 'NY5' not in trig and len(lon)>=10:
        m = (lon.iloc[-1]['close'] - lon.iloc[0]['open']) / atr
        if abs(m) >= 0.5:
            add('NY5','short' if m>0 else 'long',row['open']); trig['NY5']=True

    # NY6: GAP London close vs NY open > 0.5 ATR (comme D mais London->NY)
    if 14.5<=hour<14.6 and 'NY6' not in trig and len(lon)>=5:
        gap = (row['open'] - lon.iloc[-1]['close']) / atr
        if abs(gap) >= 0.5:
            add('NY6','long' if gap>0 else 'short',row['open']); trig['NY6']=True

    # NY7: FADE NY 1ere heure >1ATR (strat I originale)
    if 15.5<=hour<15.6 and 'NY7' not in trig:
        ny1h = tv[(tv['ts_dt']>=ns)&(tv['ts_dt']<pd.Timestamp(today.year,today.month,today.day,15,30,tz='UTC'))]
        if len(ny1h)>=10:
            m = (ny1h.iloc[-1]['close'] - ny1h.iloc[0]['open']) / atr
            if abs(m) >= 1.0:
                add('NY7','short' if m>0 else 'long',row['open']); trig['NY7']=True

    # NY8: FADE NY 1ere heure >0.5ATR
    if 15.5<=hour<15.6 and 'NY8' not in trig:
        ny1h = tv[(tv['ts_dt']>=ns)&(tv['ts_dt']<pd.Timestamp(today.year,today.month,today.day,15,30,tz='UTC'))]
        if len(ny1h)>=10:
            m = (ny1h.iloc[-1]['close'] - ny1h.iloc[0]['open']) / atr
            if abs(m) >= 0.5:
                add('NY8','short' if m>0 else 'long',row['open']); trig['NY8']=True

    # NY9: Continuation NY 1ere heure >1ATR (inverse de NY7)
    if 15.5<=hour<15.6 and 'NY9' not in trig:
        ny1h = tv[(tv['ts_dt']>=ns)&(tv['ts_dt']<pd.Timestamp(today.year,today.month,today.day,15,30,tz='UTC'))]
        if len(ny1h)>=10:
            m = (ny1h.iloc[-1]['close'] - ny1h.iloc[0]['open']) / atr
            if abs(m) >= 1.0:
                add('NY9','long' if m>0 else 'short',row['open']); trig['NY9']=True

    # NY10: Continuation NY 1ere heure >0.5ATR
    if 15.5<=hour<15.6 and 'NY10' not in trig:
        ny1h = tv[(tv['ts_dt']>=ns)&(tv['ts_dt']<pd.Timestamp(today.year,today.month,today.day,15,30,tz='UTC'))]
        if len(ny1h)>=10:
            m = (ny1h.iloc[-1]['close'] - ny1h.iloc[0]['open']) / atr
            if abs(m) >= 0.5:
                add('NY10','long' if m>0 else 'short',row['open']); trig['NY10']=True

    # NY11: ORB NY 30min breakout (14:30-15:00, break apres 15h)
    if 15.0<=hour<21.0 and 'NY11' not in trig:
        if 'NY11_h' not in trig:
            orb = tv[(tv['ts_dt']>=ns)&(tv['ts_dt']<pd.Timestamp(today.year,today.month,today.day,15,0,tz='UTC'))]
            if len(orb)>=6: trig['NY11_h']=float(orb['high'].max()); trig['NY11_l']=float(orb['low'].min())
        if 'NY11_h' in trig:
            if row['close']>trig['NY11_h']: add('NY11','long',row['close']); trig['NY11']=True
            elif row['close']<trig['NY11_l']: add('NY11','short',row['close']); trig['NY11']=True

    # NY12: ORB NY 1h breakout (14:30-15:30, break apres 15h30)
    if 15.5<=hour<21.0 and 'NY12' not in trig:
        if 'NY12_h' not in trig:
            orb = tv[(tv['ts_dt']>=ns)&(tv['ts_dt']<pd.Timestamp(today.year,today.month,today.day,15,30,tz='UTC'))]
            if len(orb)>=12: trig['NY12_h']=float(orb['high'].max()); trig['NY12_l']=float(orb['low'].min())
        if 'NY12_h' in trig:
            if row['close']>trig['NY12_h']: add('NY12','long',row['close']); trig['NY12']=True
            elif row['close']<trig['NY12_l']: add('NY12','short',row['close']); trig['NY12']=True

    # NY13: Big candle NY >1ATR, continuation (comme O pour Tokyo)
    if 14.5<=hour<21.0 and 'NY13' not in trig:
        body = row['close'] - row['open']
        if abs(body) >= 1.0*atr:
            add('NY13','long' if body>0 else 'short',row['close']); trig['NY13']=True

    # NY14: 2BAR reversal NY (comme F pour Tokyo)
    if 14.5<=hour<21.0 and 'NY14' not in trig and len(ny)>=2:
        b1=ny.iloc[-2];b2=ny.iloc[-1];b1b=b1['close']-b1['open'];b2b=b2['close']-b2['open']
        if abs(b1b)>=0.5*atr and abs(b2b)>=0.5*atr and b1b*b2b<0 and abs(b2b)>abs(b1b):
            add('NY14','long' if b2b>0 else 'short',b2['close']); trig['NY14']=True

    # NY15: Pin bar NY (comme AA pour London)
    if 14.5<=hour<21.0 and 'NY15' not in trig:
        rng=row['high']-row['low']
        if rng>=0.3*atr and abs(row['close']-row['open'])>=0.2*atr:
            pir=(row['close']-row['low'])/rng
            if pir>=0.9: add('NY15','long',row['close']); trig['NY15']=True
            elif pir<=0.1: add('NY15','short',row['close']); trig['NY15']=True

    # NY16: 3 dernieres bougies London >1ATR, continuation NY (comme H pour Tokyo->London)
    if 14.5<=hour<14.6 and 'NY16' not in trig and len(lon)>=9:
        l3=lon.iloc[-3:]; m=(l3.iloc[-1]['close']-l3.iloc[0]['open'])/atr
        if abs(m)>=1.0: add('NY16','long' if m>0 else 'short',row['open']); trig['NY16']=True

    # NY17: 3 dernieres bougies London >0.5ATR, continuation NY
    if 14.5<=hour<14.6 and 'NY17' not in trig and len(lon)>=9:
        l3=lon.iloc[-3:]; m=(l3.iloc[-1]['close']-l3.iloc[0]['open'])/atr
        if abs(m)>=0.5: add('NY17','long' if m>0 else 'short',row['open']); trig['NY17']=True

    # NY18: Engulfing NY
    if 14.5<=hour<21.0 and 'NY18' not in trig and len(ny)>=2:
        pb=ny.iloc[-2];cb=ny.iloc[-1]
        if pb['close']<pb['open'] and cb['close']>cb['open'] and cb['open']<=pb['close'] and cb['close']>=pb['open'] and abs(cb['close']-cb['open'])>=0.3*atr:
            add('NY18','long',cb['close']); trig['NY18']=True
        elif pb['close']>pb['open'] and cb['close']<cb['open'] and cb['open']>=pb['close'] and cb['close']<=pb['open'] and abs(cb['close']-cb['open'])>=0.3*atr:
            add('NY18','short',cb['close']); trig['NY18']=True

    # NY19: 6 bar bias NY (comme V pour Tokyo) — 5/6 bullish ou 1/6
    if 14.5<=hour<21.0 and 'NY19' not in trig and len(ny)>=7:
        last6=ny.iloc[-6:]; n_bull=(last6['close']>last6['open']).sum()
        if n_bull>=5: add('NY19','long',row['close']); trig['NY19']=True
        elif n_bull<=1: add('NY19','short',row['close']); trig['NY19']=True

    # NY20: London range breakout a NY (break du high/low London)
    if 14.5<=hour<21.0 and 'NY20' not in trig:
        if 'NY20_h' not in trig and len(lon)>=20:
            trig['NY20_h']=float(lon['high'].max()); trig['NY20_l']=float(lon['low'].min())
        if 'NY20_h' in trig:
            if row['close']>trig['NY20_h']: add('NY20','long',row['close']); trig['NY20']=True
            elif row['close']<trig['NY20_l']: add('NY20','short',row['close']); trig['NY20']=True

    # NY21: Fade day move >2ATR (prix a monte/baisse >2ATR depuis open, fade)
    if 15.0<=hour<21.0 and 'NY21' not in trig:
        day_open = tv.iloc[0]['open'] if len(tv)>0 else None
        if day_open:
            day_move = (row['close'] - day_open) / atr
            if day_move >= 2.0: add('NY21','short',row['close']); trig['NY21']=True
            elif day_move <= -2.0: add('NY21','long',row['close']); trig['NY21']=True

    # NY22: Continuation day move >2ATR
    if 15.0<=hour<21.0 and 'NY22' not in trig:
        day_open = tv.iloc[0]['open'] if len(tv)>0 else None
        if day_open:
            day_move = (row['close'] - day_open) / atr
            if day_move >= 2.0: add('NY22','long',row['close']); trig['NY22']=True
            elif day_move <= -2.0: add('NY22','short',row['close']); trig['NY22']=True

    # NY23: 3 soldiers/crows NY continuation
    if 14.5<=hour<21.0 and 'NY23' not in trig and len(ny)>=3:
        c1=ny.iloc[-3];c2=ny.iloc[-2];c3=ny.iloc[-1]
        b1=c1['close']-c1['open'];b2=c2['close']-c2['open'];b3=c3['close']-c3['open']
        if b1*b2>0 and b2*b3>0 and min(abs(b1),abs(b2),abs(b3))>0.1*atr and abs(b1+b2+b3)>=0.5*atr:
            add('NY23','long' if b3>0 else 'short',c3['close']); trig['NY23']=True

    # NY24: Outside bar NY (couvre range 3 precedentes)
    if 14.5<=hour<21.0 and 'NY24' not in trig and len(ny)>=4:
        prev3_h=ny.iloc[-4:-1]['high'].max();prev3_l=ny.iloc[-4:-1]['low'].min()
        body=abs(row['close']-row['open'])
        if row['high']>=prev3_h and row['low']<=prev3_l and body>=0.5*atr:
            add('NY24','long' if row['close']>row['open'] else 'short',row['close']); trig['NY24']=True

    # NY25: London KZ fade a NY (London 8h-10h move, fade a 14h30)
    if 14.5<=hour<14.6 and 'NY25' not in trig:
        kz = tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<pd.Timestamp(today.year,today.month,today.day,10,0,tz='UTC'))]
        if len(kz)>=20:
            m = (kz.iloc[-1]['close'] - kz.iloc[0]['open']) / atr
            if abs(m) >= 0.5:
                add('NY25','short' if m>0 else 'long',row['open']); trig['NY25']=True

print(f"Done. {len(S)} strats testees.", flush=True)

# ── RESULTATS ──
print("\n" + "="*110)
print("STRATEGIES NY — Config unique SL=1.0 ACT=0.5 TRAIL=0.75 MX=12 (trailing sur CLOSE)")
print("="*110)
print(f"{'Strat':>6s} {'n':>5s} {'WR':>5s} {'PF':>6s} {'Avg':>8s} {'Total':>8s} {'[1st|2nd]':>18s} {'Split':>6s} {'Tiers':>5s} {'L':>4s} {'S':>4s}")
print("-"*110)

good = []
for sn in sorted(S.keys()):
    t = S[sn]
    if len(t) < 20: continue
    pnls = [x['pnl_oz'] for x in t]
    n = len(pnls)
    gp = sum(p for p in pnls if p>0); gl = abs(sum(p for p in pnls if p<0))+0.001
    wr = sum(1 for p in pnls if p>0)/n*100
    pf = gp/gl
    mid = n//2; f1 = np.mean(pnls[:mid]); f2 = np.mean(pnls[mid:])
    t1 = sum(pnls[:n//3]); t2 = sum(pnls[n//3:2*n//3]); t3 = sum(pnls[2*n//3:])
    tiers = sum(1 for x in [t1, t2, t3] if x > 0)
    split = f1 > 0 and f2 > 0
    nl = sum(1 for x in t if x['dir']=='long'); ns_ = sum(1 for x in t if x['dir']=='short')
    split_str = "OK" if split else "!!"
    marker = " <--" if pf > 1.2 and split else ""
    print(f"{sn:>6s} {n:5d} {wr:4.0f}% {pf:6.2f} {np.mean(pnls):+8.3f} {sum(pnls):+8.1f} [{f1:+7.3f}|{f2:+7.3f}] {split_str:>6s} {tiers:4d}/3 {nl:4d} {ns_:4d}{marker}")
    if pf > 1.2 and split:
        good.append(sn)

if good:
    print(f"\n  Strats retenues (PF>1.2 + split OK): {', '.join(good)}")
else:
    print(f"\n  Aucune strat avec PF>1.2 et split OK")

# Detail des bonnes strats
for sn in good:
    t = S[sn]
    pnls = [x['pnl_oz'] for x in t]
    print(f"\n  --- {sn} ---")
    # Par direction
    longs = [x for x in t if x['dir']=='long']
    shorts = [x for x in t if x['dir']=='short']
    for label, sub in [('LONG', longs), ('SHORT', shorts)]:
        if not sub: continue
        sp = [x['pnl_oz'] for x in sub]
        gp = sum(p for p in sp if p>0); gl = abs(sum(p for p in sp if p<0))+0.001
        wr = sum(1 for p in sp if p>0)/len(sp)*100
        print(f"    {label}: n={len(sub)} WR={wr:.0f}% PF={gp/gl:.2f} Avg={np.mean(sp):+.3f}")
    # Par mois
    months = {}
    for x in t:
        mo = str(x['date'].year)+"-"+str(x['date'].month).zfill(2)
        months.setdefault(mo, []).append(x['pnl_oz'])
    print(f"    Mois: ", end='')
    for mo in sorted(months.keys()):
        mp = sum(months[mo])
        marker = "+" if mp > 0 else "-"
        print(f"{mo}({marker}{abs(mp):.0f}) ", end='')
    print()

print()
