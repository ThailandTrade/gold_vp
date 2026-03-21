"""
Retest complet sur donnees FTMO — toutes les strats jamais testees.
Config: SL=1.0 ACT=0.5 TRAIL=0.75, pas de timeout, trailing sur CLOSE.
"""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
from itertools import combinations
from dotenv import load_dotenv; load_dotenv()
from phase1_poc_calculator import get_conn, compute_atr, get_trading_days
from phase3_analyze import load_candles_5m
from strats import SL, ACT, TRAIL, sim_exit

conn = get_conn()
candles = load_candles_5m(conn)
daily_atr, global_atr = compute_atr(conn)
trading_days = get_trading_days(conn)
cur = conn.cursor()
cur.execute("""SELECT DATE_TRUNC('month', time), AVG(ask-bid) FROM market_ticks_xauusd WHERE ask>bid AND ask-bid<10 GROUP BY 1""")
monthly_spread = {r[0].strftime("%Y-%m"): float(r[1]) for r in cur.fetchall()}
cur.close(); conn.close()
avg_sp = np.mean(list(monthly_spread.values()))
n_td = len(set(candles['date'].unique()))
def prev_day(day):
    for di, d in enumerate(trading_days):
        if d >= day: return trading_days[di-1] if di > 0 else None
    return None
def get_sp(day):
    return 2 * monthly_spread.get(str(day.year)+"-"+str(day.month).zfill(2), avg_sp)

print("Collecte de TOUTES les strats...", flush=True)
S = {}
prev_d = None; trig = {}; day_atr = None; prev_day_data = None; prev2_day_data = None
for ci in range(len(candles)):
    row = candles.iloc[ci]; ct = row['ts_dt']; today = ct.date()
    hour = ct.hour + ct.minute / 60.0
    if today != prev_d:
        if prev_d:
            yc = candles[candles['date']==prev_d]
            if len(yc) > 0:
                prev2_day_data = prev_day_data
                prev_day_data = {'open': float(yc.iloc[0]['open']), 'close': float(yc.iloc[-1]['close']),
                                 'high': float(yc['high'].max()), 'low': float(yc['low'].min()),
                                 'range': float(yc['high'].max()-yc['low'].min()),
                                 'body': float(yc.iloc[-1]['close']-yc.iloc[0]['open'])}
        prev_d = today; trig = {}
        pd_ = prev_day(today); day_atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    atr = day_atr
    if atr == 0 or atr is None: continue
    ds = pd.Timestamp(today.year,today.month,today.day,0,0,tz='UTC')
    te = pd.Timestamp(today.year,today.month,today.day,6,0,tz='UTC')
    ls = pd.Timestamp(today.year,today.month,today.day,8,0,tz='UTC')
    ns = pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC')
    tv = candles[(candles['ts_dt']>=ds)&(candles['ts_dt']<=ct)]
    tok = tv[tv['ts_dt']<te]; lon = tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<ns)]; ny = tv[tv['ts_dt']>=ns]

    def add(sn, d, e):
        b, ex = sim_exit(candles, ci, e, d, atr)
        pnl = (ex-e) if d=='long' else (e-ex)
        S.setdefault(sn,[]).append({'date':today,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(today),'atr':atr,'ei':ci,'xi':ci+b})

    # ═══════════════════════════════════════════════════
    # TOKYO (0h-6h)
    # ═══════════════════════════════════════════════════
    if 0.0<=hour<6.0 and 'TOK_2BAR' not in trig and len(tok)>=2:
        b1=tok.iloc[-2];b2=tok.iloc[-1];b1b=b1['close']-b1['open'];b2b=b2['close']-b2['open']
        if abs(b1b)>=0.5*atr and abs(b2b)>=0.5*atr and b1b*b2b<0 and abs(b2b)>abs(b1b):
            add('TOK_2BAR','long' if b2b>0 else 'short',b2['close']); trig['TOK_2BAR']=True
    if 0.0<=hour<6.0 and 'TOK_BIG' not in trig:
        body=row['close']-row['open']
        if abs(body)>=1.0*atr: add('TOK_BIG','long' if body>0 else 'short',row['close']); trig['TOK_BIG']=True
    if 0.0<=hour<0.1 and 'TOK_FADE' not in trig and prev_day_data:
        prev_dir = prev_day_data['body']
        if abs(prev_dir) >= 1.0*atr:
            add('TOK_FADE','short' if prev_dir>0 else 'long',row['open']); trig['TOK_FADE']=True
    if 0.0<=hour<0.1 and 'TOK_PREVEXT' not in trig and prev_day_data and prev_day_data['range']>0:
        pos_close = (prev_day_data['close'] - prev_day_data['low']) / prev_day_data['range']
        if pos_close >= 0.9: add('TOK_PREVEXT','long',row['open']); trig['TOK_PREVEXT']=True
        elif pos_close <= 0.1: add('TOK_PREVEXT','short',row['open']); trig['TOK_PREVEXT']=True
    # TOK_IB: IB 1h breakout
    if 'TOK_IB_d' not in trig and hour >= 1.0 and hour < 6.0:
        ib = tv[(tv['ts_dt']>=ds)&(tv['ts_dt']<ds+pd.Timedelta(hours=1))]
        if len(ib) >= 12:
            trig['TOK_IB_d']=True; trig['TOK_IB_h']=float(ib['high'].max()); trig['TOK_IB_l']=float(ib['low'].min())
    if 'TOK_IB_h' in trig and 'TOK_IB' not in trig and 1.0<=hour<6.0:
        if row['close'] > trig['TOK_IB_h']: add('TOK_IB','long',row['close']); trig['TOK_IB']=True
        elif row['close'] < trig['TOK_IB_l']: add('TOK_IB','short',row['close']); trig['TOK_IB']=True
    # TOK_3BAR: 3 consecutive same dir
    if 0.0<=hour<6.0 and 'TOK_3BAR' not in trig and len(tok)>=3:
        c1=tok.iloc[-3];c2=tok.iloc[-2];c3=tok.iloc[-1]
        b1=c1['close']-c1['open'];b2=c2['close']-c2['open'];b3=c3['close']-c3['open']
        if b1*b2>0 and b2*b3>0 and min(abs(b1),abs(b2),abs(b3))>0.05*atr and abs(b1+b2+b3)>=0.5*atr:
            add('TOK_3BAR','long' if b3>0 else 'short',c3['close']); trig['TOK_3BAR']=True
    # TOK_6BAR: 5/6 or 1/6 bullish (ex V)
    if 0.0<=hour<6.0 and 'TOK_6BAR' not in trig and len(tok)>=7:
        last6=tok.iloc[-6:]; n_bull=(last6['close']>last6['open']).sum()
        if n_bull>=5: add('TOK_6BAR','long',row['close']); trig['TOK_6BAR']=True
        elif n_bull<=1: add('TOK_6BAR','short',row['close']); trig['TOK_6BAR']=True
    # TOK_OUTSIDE: outside bar Tokyo (ex AC)
    if 0.0<=hour<6.0 and 'TOK_OUTSIDE' not in trig and len(tok)>=4:
        prev3_h=tok.iloc[-4:-1]['high'].max();prev3_l=tok.iloc[-4:-1]['low'].min()
        body=abs(row['close']-row['open'])
        if row['high']>=prev3_h and row['low']<=prev3_l and body>=0.5*atr:
            add('TOK_OUTSIDE','long' if row['close']>row['open'] else 'short',row['close']); trig['TOK_OUTSIDE']=True

    # ═══════════════════════════════════════════════════
    # LONDON (8h-14h30)
    # ═══════════════════════════════════════════════════
    if 8.0<=hour<14.5 and 'LON_PIN' not in trig:
        rng=row['high']-row['low']
        if rng>=0.3*atr and abs(row['close']-row['open'])>=0.2*atr:
            pir=(row['close']-row['low'])/rng
            if pir>=0.9: add('LON_PIN','long',row['close']); trig['LON_PIN']=True
            elif pir<=0.1: add('LON_PIN','short',row['close']); trig['LON_PIN']=True
    if 8.0<=hour<8.1 and 'LON_GAP' not in trig:
        tc=candles[(candles['ts_dt']<te)&(candles['ts_dt']<=ct)]
        if len(tc)>=5:
            gap=(row['open']-tc.iloc[-1]['close'])/atr
            if abs(gap)>=0.5: add('LON_GAP','long' if gap>0 else 'short',row['open']); trig['LON_GAP']=True
    if 8.0<=hour<8.1 and 'LON_BIGGAP' not in trig:
        tc=candles[(candles['ts_dt']<te)&(candles['ts_dt']<=ct)]
        if len(tc)>=5:
            gap=(row['open']-tc.iloc[-1]['close'])/atr
            if abs(gap)>=1.0: add('LON_BIGGAP','long' if gap>0 else 'short',row['open']); trig['LON_BIGGAP']=True
    if 10.0<=hour<10.1 and 'LON_KZ' not in trig:
        kz=tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<pd.Timestamp(today.year,today.month,today.day,10,0,tz='UTC'))]
        if len(kz)>=20:
            m=(kz.iloc[-1]['close']-kz.iloc[0]['open'])/atr
            if abs(m)>=0.5: add('LON_KZ','short' if m>0 else 'long',row['open']); trig['LON_KZ']=True
    if 8.0<=hour<8.1 and 'LON_TOKEND' not in trig and len(tok)>=9:
        l3=tok.iloc[-3:]; m=(l3.iloc[-1]['close']-l3.iloc[0]['open'])/atr
        if abs(m)>=1.0: add('LON_TOKEND','long' if m>0 else 'short',row['open']); trig['LON_TOKEND']=True
    if 8.0<=hour<8.1 and 'LON_PREV' not in trig and prev_day_data:
        prev_body = prev_day_data['body']/atr
        if abs(prev_body) >= 1.0:
            add('LON_PREV','long' if prev_body>0 else 'short',row['open']); trig['LON_PREV']=True
    # LON_FADE: Fade Tokyo move >1ATR at London (ex C)
    if 8.0<=hour<8.1 and 'LON_FADE' not in trig and len(tok)>=10:
        m=(tok.iloc[-1]['close']-tok.iloc[0]['open'])/atr
        if abs(m)>=1.0: add('LON_FADE','short' if m>0 else 'long',row['open']); trig['LON_FADE']=True
    # LON_KZ_CONT: KZ continuation (inverse of fade)
    if 10.0<=hour<10.1 and 'LON_KZ_CONT' not in trig:
        kz=tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<pd.Timestamp(today.year,today.month,today.day,10,0,tz='UTC'))]
        if len(kz)>=20:
            m=(kz.iloc[-1]['close']-kz.iloc[0]['open'])/atr
            if abs(m)>=0.5: add('LON_KZ_CONT','long' if m>0 else 'short',row['open']); trig['LON_KZ_CONT']=True
    # LON_2BAR: 2BAR reversal London (ex L8)
    if 8.0<=hour<14.5 and 'LON_2BAR' not in trig and len(lon)>=2:
        b1=lon.iloc[-2];b2=lon.iloc[-1];b1b=b1['close']-b1['open'];b2b=b2['close']-b2['open']
        if abs(b1b)>=0.5*atr and abs(b2b)>=0.5*atr and b1b*b2b<0 and abs(b2b)>abs(b1b):
            add('LON_2BAR','long' if b2b>0 else 'short',b2['close']); trig['LON_2BAR']=True
    # LON_ENGULF: engulfing London (ex Q)
    if 8.0<=hour<14.5 and 'LON_ENGULF' not in trig and len(lon)>=2:
        pb=lon.iloc[-2];cb=lon.iloc[-1]
        if pb['close']<pb['open'] and cb['close']>cb['open'] and cb['open']<=pb['close'] and cb['close']>=pb['open'] and abs(cb['close']-cb['open'])>=0.3*atr:
            add('LON_ENGULF','long',cb['close']); trig['LON_ENGULF']=True
        elif pb['close']>pb['open'] and cb['close']<cb['open'] and cb['open']>=pb['close'] and cb['close']<=pb['open'] and abs(cb['close']-cb['open'])>=0.3*atr:
            add('LON_ENGULF','short',cb['close']); trig['LON_ENGULF']=True
    # LON_3BAR: 3 soldiers/crows London (ex S)
    if 8.0<=hour<14.5 and 'LON_3BAR' not in trig and len(lon)>=3:
        c1=lon.iloc[-3];c2=lon.iloc[-2];c3=lon.iloc[-1];b1=c1['close']-c1['open'];b2=c2['close']-c2['open'];b3=c3['close']-c3['open']
        if b1*b2>0 and b2*b3>0 and min(abs(b1),abs(b2),abs(b3))>0.1*atr and abs(b1+b2+b3)>=0.5*atr:
            add('LON_3BAR','short' if b3>0 else 'long',c3['close']); trig['LON_3BAR']=True

    # ═══════════════════════════════════════════════════
    # NY (14h30-21h)
    # ═══════════════════════════════════════════════════
    if 14.5<=hour<14.6 and 'NY_GAP' not in trig and len(lon)>=5:
        gap=(row['open']-lon.iloc[-1]['close'])/atr
        if abs(gap)>=0.5: add('NY_GAP','long' if gap>0 else 'short',row['open']); trig['NY_GAP']=True
    if 14.5<=hour<14.6 and 'NY_LONEND' not in trig and len(lon)>=9:
        l3=lon.iloc[-3:]; m=(l3.iloc[-1]['close']-l3.iloc[0]['open'])/atr
        if abs(m)>=1.0: add('NY_LONEND','long' if m>0 else 'short',row['open']); trig['NY_LONEND']=True
    if 14.5<=hour<14.6 and 'NY_LONMOM' not in trig and len(lon)>=9:
        l3=lon.iloc[-3:]; m=(l3.iloc[-1]['close']-l3.iloc[0]['open'])/atr
        if abs(m)>=0.5: add('NY_LONMOM','long' if m>0 else 'short',row['open']); trig['NY_LONMOM']=True
    if 14.5<=hour<14.6 and 'NY_DAYMOM' not in trig and len(tv)>=100:
        day_move=(tv.iloc[-1]['close']-tv.iloc[0]['open'])/atr
        if abs(day_move)>=1.5: add('NY_DAYMOM','long' if day_move>0 else 'short',row['open']); trig['NY_DAYMOM']=True
    # NY_FADE1H: fade NY 1ere heure >1ATR (ex I/NY7)
    if 15.5<=hour<15.6 and 'NY_FADE1H' not in trig:
        ny1h=tv[(tv['ts_dt']>=ns)&(tv['ts_dt']<pd.Timestamp(today.year,today.month,today.day,15,30,tz='UTC'))]
        if len(ny1h)>=10:
            m=(ny1h.iloc[-1]['close']-ny1h.iloc[0]['open'])/atr
            if abs(m)>=1.0: add('NY_FADE1H','short' if m>0 else 'long',row['open']); trig['NY_FADE1H']=True
    # NY_CONT1H: continuation NY 1ere heure >1ATR
    if 15.5<=hour<15.6 and 'NY_CONT1H' not in trig:
        ny1h=tv[(tv['ts_dt']>=ns)&(tv['ts_dt']<pd.Timestamp(today.year,today.month,today.day,15,30,tz='UTC'))]
        if len(ny1h)>=10:
            m=(ny1h.iloc[-1]['close']-ny1h.iloc[0]['open'])/atr
            if abs(m)>=1.0: add('NY_CONT1H','long' if m>0 else 'short',row['open']); trig['NY_CONT1H']=True
    # NY_ORB30: ORB NY 30min
    if 15.0<=hour<21.0 and 'NY_ORB30' not in trig:
        if 'NY_ORB30_d' not in trig:
            orb=tv[(tv['ts_dt']>=ns)&(tv['ts_dt']<pd.Timestamp(today.year,today.month,today.day,15,0,tz='UTC'))]
            if len(orb)>=6: trig['NY_ORB30_d']=True; trig['NY_ORB30_h']=float(orb['high'].max()); trig['NY_ORB30_l']=float(orb['low'].min())
        if 'NY_ORB30_h' in trig:
            if row['close']>trig['NY_ORB30_h']: add('NY_ORB30','long',row['close']); trig['NY_ORB30']=True
            elif row['close']<trig['NY_ORB30_l']: add('NY_ORB30','short',row['close']); trig['NY_ORB30']=True
    # NY_1ST: 1ere bougie NY > 0.3 ATR (ex G/NY1)
    if 14.5<=hour<14.6 and 'NY_1ST' not in trig:
        body=row['close']-row['open']
        if abs(body)>=0.3*atr: add('NY_1ST','long' if body>0 else 'short',row['close']); trig['NY_1ST']=True
    # NY_BIG: big candle NY >1ATR
    if 14.5<=hour<21.0 and 'NY_BIG' not in trig:
        body=row['close']-row['open']
        if abs(body)>=1.0*atr: add('NY_BIG','long' if body>0 else 'short',row['close']); trig['NY_BIG']=True
    # NY_2BAR: 2BAR reversal NY
    if 14.5<=hour<21.0 and 'NY_2BAR' not in trig and len(ny)>=2:
        b1=ny.iloc[-2];b2=ny.iloc[-1];b1b=b1['close']-b1['open'];b2b=b2['close']-b2['open']
        if abs(b1b)>=0.5*atr and abs(b2b)>=0.5*atr and b1b*b2b<0 and abs(b2b)>abs(b1b):
            add('NY_2BAR','long' if b2b>0 else 'short',b2['close']); trig['NY_2BAR']=True
    # NY_LONMOM4H: London 4h momentum >1ATR → continuation NY (ex S7)
    if 14.5<=hour<14.6 and 'NY_LONMOM4H' not in trig:
        l4h=tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<pd.Timestamp(today.year,today.month,today.day,12,0,tz='UTC'))]
        if len(l4h)>=40:
            m=(l4h.iloc[-1]['close']-l4h.iloc[0]['open'])/atr
            if abs(m)>=1.0: add('NY_LONMOM4H','long' if m>0 else 'short',row['open']); trig['NY_LONMOM4H']=True
    # NY_DAYFADE: Fade daily move >1.5ATR
    if 14.5<=hour<14.6 and 'NY_DAYFADE' not in trig and len(tv)>=100:
        day_move=(tv.iloc[-1]['close']-tv.iloc[0]['open'])/atr
        if abs(day_move)>=1.5: add('NY_DAYFADE','short' if day_move>0 else 'long',row['open']); trig['NY_DAYFADE']=True

    # ═══════════════════════════════════════════════════
    # DAILY PATTERNS
    # ═══════════════════════════════════════════════════
    if prev_day_data:
        pb = prev_day_data['body']; pr = prev_day_data['range']
        # D5: 2 jours consecutifs meme direction
        if 8.0<=hour<8.1 and 'D5' not in trig and prev2_day_data:
            if abs(pb)>=0.5*atr and abs(prev2_day_data['body'])>=0.5*atr:
                if pb>0 and prev2_day_data['body']>0: add('D5','long',row['open']); trig['D5']=True
                elif pb<0 and prev2_day_data['body']<0: add('D5','short',row['open']); trig['D5']=True
        # D6: 2 jours consecutifs opposees
        if 8.0<=hour<8.1 and 'D6' not in trig and prev2_day_data:
            if abs(pb)>=0.5*atr and abs(prev2_day_data['body'])>=0.5*atr:
                if pb>0 and prev2_day_data['body']<0: add('D6','long',row['open']); trig['D6']=True
                elif pb<0 and prev2_day_data['body']>0: add('D6','short',row['open']); trig['D6']=True
        # D4: Prev day wide range >2ATR → fade London
        if 8.0<=hour<8.1 and 'D4' not in trig:
            if pr>=2.0*atr: add('D4','short' if pb>0 else 'long',row['open']); trig['D4']=True
        # D8: Inside day → breakout London
        if 8.0<=hour<14.5 and 'D8' not in trig and prev2_day_data:
            if prev_day_data['high']<prev2_day_data['high'] and prev_day_data['low']>prev2_day_data['low']:
                if row['close']>prev_day_data['high']: add('D8','long',row['close']); trig['D8']=True
                elif row['close']<prev_day_data['low']: add('D8','short',row['close']); trig['D8']=True
        # X4: Prev day >0.5ATR continuation Tokyo
        if 0.0<=hour<0.1 and 'X4' not in trig:
            if abs(pb)>=0.5*atr: add('X4','long' if pb>0 else 'short',row['open']); trig['X4']=True

print(f"Done. {len(S)} strats.", flush=True)

# ── STATS INDIVIDUELLES ──
print("\n" + "="*120)
print("TOUTES LES STRATS — Donnees FTMO")
print("="*120)
print(f"{'Strat':>14s} {'n':>5s} {'WR':>5s} {'PF':>6s} {'Avg':>8s} {'[1st|2nd]':>18s} {'Split':>6s} {'Tiers':>5s}")
print("-"*120)

good = []
for sn in sorted(S.keys()):
    t = S[sn]
    if len(t) < 15: continue
    pnls = [x['pnl_oz'] for x in t]
    n = len(pnls)
    gp = sum(p for p in pnls if p>0); gl = abs(sum(p for p in pnls if p<0))+0.001
    wr = sum(1 for p in pnls if p>0)/n*100
    pf = gp/gl
    mid = n//2; f1 = np.mean(pnls[:mid]); f2 = np.mean(pnls[mid:])
    t1 = sum(pnls[:n//3]); t2 = sum(pnls[n//3:2*n//3]); t3 = sum(pnls[2*n//3:])
    tiers = sum(1 for x in [t1, t2, t3] if x > 0)
    split = f1 > 0 and f2 > 0
    split_str = "OK" if split else "!!"
    marker = " <--" if pf > 1.2 and split else ""
    print(f"{sn:>14s} {n:5d} {wr:4.0f}% {pf:6.2f} {np.mean(pnls):+8.3f} [{f1:+7.3f}|{f2:+7.3f}] {split_str:>6s} {tiers:4d}/3{marker}")
    if pf > 1.2 and split:
        good.append(sn)

print(f"\n  Retenues (PF>1.2 + split OK): {', '.join(good)}")

# ── COMBOS ──
if len(good) >= 3:
    strat_arrays = {}
    for sn in good:
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
        t1s = sum(pnls[:n//3]); t2s = sum(pnls[n//3:2*n//3]); t3s = sum(pnls[2*n//3:])
        pm = sum(1 for v in months.values() if v > 0)
        return {
            'combo': '+'.join(combo), 'ns': len(combo), 'n': n, 'tpd': n / n_td,
            'ret': ret, 'mdd': mdd, 'cal': ret / abs(mdd) if mdd < 0 else 0,
            'pf': gp / (gl + 0.01), 'wr': wins / n * 100, 'capital': cap,
            'split': p1 > 0 and p2 > 0,
            'tiers': sum(1 for x in [t1s, t2s, t3s] if x > 0),
            'both': has_s and has_l, 'pm': pm, 'tm': len(months),
        }

    print(f"\n{'='*130}")
    print(f"MEILLEUR COMBO PAR TAILLE (Calmar, split OK, tiers>=2, L+S)")
    print(f"{'='*130}")
    for sz in range(3, min(len(good)+1, 16)):
        best = None
        for combo in combinations(good, sz):
            r = eval_combo(combo)
            if r and r['split'] and r['tiers']>=2 and r['both']:
                if best is None or r['cal'] > best['cal']:
                    best = r
        if best:
            print(f"  {sz:2d} strats: {best['combo'][:70]:70s} n={best['n']:5.0f} PF={best['pf']:.2f} WR={best['wr']:.0f}% DD={best['mdd']:+.1f}% Cal={best['cal']:.1f} Rend={best['ret']:+.0f}% M+={best['pm']:.0f}/{best['tm']:.0f}")

    # Top 20 Calmar
    print(f"\n  TOP 20 CALMAR (split OK, L+S):")
    print(f"  {'Combo':60s} {'n':>5s} {'PF':>5s} {'WR':>4s} {'DD%':>7s} {'Cal':>8s} {'Rend%':>10s} {'M+':>5s} {'T':>3s}")
    results = []
    for sz in range(3, min(len(good)+1, 12)):
        for combo in combinations(good, sz):
            r = eval_combo(combo)
            if r and r['split'] and r['tiers']>=2 and r['both']:
                results.append(r)
    results.sort(key=lambda x: x['cal'], reverse=True)
    for r in results[:20]:
        print(f"  {r['combo'][:60]:60s} {r['n']:5.0f} {r['pf']:.2f} {r['wr']:3.0f}% {r['mdd']:+6.1f}% {r['cal']:8.1f} {r['ret']:+9.0f}% {r['pm']:.0f}/{r['tm']:.0f} {r['tiers']}/3")

print()
