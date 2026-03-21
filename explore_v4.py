"""
Exploration v4 — Multi-angle:
1. Patterns daily (previous day) appliques en intraday
2. Filtres jour de la semaine
3. Patterns intra-session avances
4. Volatilite regime
5. Combinaisons multi-signal
"""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
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
def prev_day(day):
    for di, d in enumerate(trading_days):
        if d >= day: return trading_days[di-1] if di > 0 else None
    return None
def get_sp(day):
    return 2 * monthly_spread.get(str(day.year)+"-"+str(day.month).zfill(2), avg_sp)

# Build daily bars
daily = candles.groupby('date').agg(
    open=('open','first'), high=('high','max'), low=('low','min'), close=('close','last'),
    n=('close','count')
).reset_index()
daily['range'] = daily['high'] - daily['low']
daily['body'] = daily['close'] - daily['open']
daily['abs_body'] = abs(daily['body'])
daily_dict = {row['date']: row for _, row in daily.iterrows()}

print("Collecte...", flush=True)
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
                                 'range': float(yc['high'].max() - yc['low'].min()),
                                 'body': float(yc.iloc[-1]['close'] - yc.iloc[0]['open']),
                                 'weekday': prev_d.weekday()}
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
    wd = today.weekday()  # 0=lun, 4=ven

    def add(sn, d, e):
        b, ex = sim_exit(candles, ci, e, d, atr)
        pnl = (ex-e) if d=='long' else (e-ex)
        S.setdefault(sn,[]).append({'date':today,'dir':d,'pnl_oz':pnl-get_sp(today)})

    # ═══════════════════════════════════════════════════════════
    # BLOC 1: PATTERNS DAILY
    # ═══════════════════════════════════════════════════════════

    if prev_day_data:
        pb = prev_day_data['body']
        pr = prev_day_data['range']

        # D1: Previous day doji (body < 20% range) → breakout Tokyo
        if 0.0<=hour<6.0 and 'D1' not in trig:
            if pr > 0 and abs(pb) < 0.2 * pr and pr >= 0.5*atr:
                body = row['close'] - row['open']
                if abs(body) >= 0.5*atr:
                    add('D1','long' if body>0 else 'short',row['close']); trig['D1']=True

        # D2: Previous day hammer → long at London
        if 8.0<=hour<8.1 and 'D2' not in trig:
            if pr >= 0.5*atr:
                upper = prev_day_data['high'] - max(prev_day_data['open'], prev_day_data['close'])
                lower = min(prev_day_data['open'], prev_day_data['close']) - prev_day_data['low']
                if lower > 2*abs(pb) and upper < abs(pb) and abs(pb) > 0:
                    add('D2','long',row['open']); trig['D2']=True
                elif upper > 2*abs(pb) and lower < abs(pb) and abs(pb) > 0:
                    add('D2','short',row['open']); trig['D2']=True

        # D3: Previous day narrow range (< 0.5 ATR) → breakout London
        if 8.0<=hour<14.5 and 'D3' not in trig:
            if pr < 0.5*atr:
                if row['close'] > prev_day_data['high']:
                    add('D3','long',row['close']); trig['D3']=True
                elif row['close'] < prev_day_data['low']:
                    add('D3','short',row['close']); trig['D3']=True

        # D4: Previous day wide range (> 2 ATR) → fade at London
        if 8.0<=hour<8.1 and 'D4' not in trig:
            if pr >= 2.0*atr:
                add('D4','short' if pb>0 else 'long',row['open']); trig['D4']=True

        # D5: 2 jours consecutifs meme direction > 0.5 ATR → continuation London
        if 8.0<=hour<8.1 and 'D5' not in trig and prev2_day_data:
            if abs(pb) >= 0.5*atr and abs(prev2_day_data['body']) >= 0.5*atr:
                if pb > 0 and prev2_day_data['body'] > 0:
                    add('D5','long',row['open']); trig['D5']=True
                elif pb < 0 and prev2_day_data['body'] < 0:
                    add('D5','short',row['open']); trig['D5']=True

        # D6: 2 jours consecutifs direction opposee → fade London (inside day logic)
        if 8.0<=hour<8.1 and 'D6' not in trig and prev2_day_data:
            if abs(pb) >= 0.5*atr and abs(prev2_day_data['body']) >= 0.5*atr:
                if pb > 0 and prev2_day_data['body'] < 0:
                    add('D6','long',row['open']); trig['D6']=True
                elif pb < 0 and prev2_day_data['body'] > 0:
                    add('D6','short',row['open']); trig['D6']=True

        # D7: Previous day close near high (top 10%) → continuation Tokyo
        if 0.0<=hour<0.1 and 'D7' not in trig:
            if pr > 0:
                pos_close = (prev_day_data['close'] - prev_day_data['low']) / pr
                if pos_close >= 0.9:
                    add('D7','long',row['open']); trig['D7']=True
                elif pos_close <= 0.1:
                    add('D7','short',row['open']); trig['D7']=True

        # D8: Previous day inside day (high < prev2 high, low > prev2 low) → breakout
        if 8.0<=hour<14.5 and 'D8' not in trig and prev2_day_data:
            if prev_day_data['high'] < prev2_day_data['high'] and prev_day_data['low'] > prev2_day_data['low']:
                if row['close'] > prev_day_data['high']:
                    add('D8','long',row['close']); trig['D8']=True
                elif row['close'] < prev_day_data['low']:
                    add('D8','short',row['close']); trig['D8']=True

    # ═══════════════════════════════════════════════════════════
    # BLOC 2: JOUR DE LA SEMAINE
    # ═══════════════════════════════════════════════════════════

    # W1: Lundi continuation du vendredi
    if wd == 0 and 0.0<=hour<0.1 and 'W1' not in trig and prev_day_data:
        if prev_day_data.get('weekday') == 4 and abs(prev_day_data['body']) >= 0.5*atr:
            add('W1','long' if prev_day_data['body']>0 else 'short',row['open']); trig['W1']=True

    # W2: Vendredi fade (les gros moves du vendredi se retracent souvent)
    if wd == 4 and 14.5<=hour<14.6 and 'W2' not in trig and len(tv) > 50:
        day_move = (row['close'] - tv.iloc[0]['open']) / atr
        if abs(day_move) >= 1.5:
            add('W2','short' if day_move>0 else 'long',row['close']); trig['W2']=True

    # ═══════════════════════════════════════════════════════════
    # BLOC 3: PATTERNS INTRA-SESSION AVANCES
    # ═══════════════════════════════════════════════════════════

    # S1: Tokyo range breakout apres 4h de consolidation (range < ATR)
    if 4.0<=hour<6.0 and 'S1' not in trig:
        tok4 = tv[(tv['ts_dt']>=ds)&(tv['ts_dt']<ds+pd.Timedelta(hours=4))]
        if len(tok4) >= 48:
            rng4 = float(tok4['high'].max()) - float(tok4['low'].min())
            if rng4 < 1.0*atr:
                if 'S1_h' not in trig:
                    trig['S1_h'] = float(tok4['high'].max()); trig['S1_l'] = float(tok4['low'].min())
                if row['close'] > trig['S1_h']: add('S1','long',row['close']); trig['S1']=True
                elif row['close'] < trig['S1_l']: add('S1','short',row['close']); trig['S1']=True

    # S2: London first 30min range breakout
    if 8.5<=hour<14.5 and 'S2' not in trig:
        if 'S2_d' not in trig:
            l30 = tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<ls+pd.Timedelta(minutes=30))]
            if len(l30) >= 6:
                trig['S2_d']=True; trig['S2_h']=float(l30['high'].max()); trig['S2_l']=float(l30['low'].min())
        if 'S2_h' in trig:
            if row['close'] > trig['S2_h']: add('S2','long',row['close']); trig['S2']=True
            elif row['close'] < trig['S2_l']: add('S2','short',row['close']); trig['S2']=True

    # S3: London 2h momentum (8h-10h) continuation (pas fade)
    if 10.0<=hour<10.1 and 'S3' not in trig:
        kz = tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<pd.Timestamp(today.year,today.month,today.day,10,0,tz='UTC'))]
        if len(kz) >= 20:
            m = (kz.iloc[-1]['close'] - kz.iloc[0]['open']) / atr
            if abs(m) >= 0.5:
                add('S3','long' if m>0 else 'short',row['open']); trig['S3']=True

    # S4: NY first 15min range breakout
    if 14.75<=hour<21.0 and 'S4' not in trig:
        if 'S4_d' not in trig:
            ny15 = tv[(tv['ts_dt']>=ns)&(tv['ts_dt']<ns+pd.Timedelta(minutes=15))]
            if len(ny15) >= 3:
                trig['S4_d']=True; trig['S4_h']=float(ny15['high'].max()); trig['S4_l']=float(ny15['low'].min())
        if 'S4_h' in trig:
            if row['close'] > trig['S4_h']: add('S4','long',row['close']); trig['S4']=True
            elif row['close'] < trig['S4_l']: add('S4','short',row['close']); trig['S4']=True

    # S5: Whole-day range breakout a NY (break du high/low de la journee)
    if 14.5<=hour<21.0 and 'S5' not in trig and len(tv) >= 100:
        if 'S5_d' not in trig:
            pre_ny = tv[tv['ts_dt']<ns]
            if len(pre_ny) >= 100:
                trig['S5_d']=True; trig['S5_h']=float(pre_ny['high'].max()); trig['S5_l']=float(pre_ny['low'].min())
        if 'S5_h' in trig:
            if row['close'] > trig['S5_h']: add('S5','long',row['close']); trig['S5']=True
            elif row['close'] < trig['S5_l']: add('S5','short',row['close']); trig['S5']=True

    # S6: Gap Tokyo-London > 1.0 ATR (seuil plus haut que LON_GAP)
    if 8.0<=hour<8.1 and 'S6' not in trig and len(tok)>=5:
        tc = candles[(candles['ts_dt']<te)&(candles['ts_dt']<=ct)]
        if len(tc) >= 5:
            gap = (row['open']-tc.iloc[-1]['close'])/atr
            if abs(gap) >= 1.0: add('S6','long' if gap>0 else 'short',row['open']); trig['S6']=True

    # S7: London momentum 8h-12h (4h move) continuation a NY
    if 14.5<=hour<14.6 and 'S7' not in trig:
        l4h = tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<pd.Timestamp(today.year,today.month,today.day,12,0,tz='UTC'))]
        if len(l4h) >= 40:
            m = (l4h.iloc[-1]['close'] - l4h.iloc[0]['open']) / atr
            if abs(m) >= 1.0:
                add('S7','long' if m>0 else 'short',row['open']); trig['S7']=True

    # S8: Tokyo-London combined move > 1.5 ATR → continuation NY
    if 14.5<=hour<14.6 and 'S8' not in trig and len(tv) >= 100:
        day_move = (tv.iloc[-1]['close'] - tv.iloc[0]['open']) / atr
        if abs(day_move) >= 1.5:
            add('S8','long' if day_move>0 else 'short',row['open']); trig['S8']=True

    # S9: Tokyo-London combined move > 1.5 ATR → FADE NY
    if 14.5<=hour<14.6 and 'S9' not in trig and len(tv) >= 100:
        day_move = (tv.iloc[-1]['close'] - tv.iloc[0]['open']) / atr
        if abs(day_move) >= 1.5:
            add('S9','short' if day_move>0 else 'long',row['open']); trig['S9']=True

    # ═══════════════════════════════════════════════════════════
    # BLOC 4: VOLATILITE REGIME
    # ═══════════════════════════════════════════════════════════

    # V1: Low vol day (ATR < median ATR) → big candle Tokyo has more edge
    if 0.0<=hour<6.0 and 'V1' not in trig and prev_day_data:
        if atr < 3.0:  # faible volatilite
            body = row['close'] - row['open']
            if abs(body) >= 0.8*atr:
                add('V1','long' if body>0 else 'short',row['close']); trig['V1']=True

    # V2: High vol day (ATR > 5) → 2BAR reversal
    if 0.0<=hour<6.0 and 'V2' not in trig and len(tok)>=2:
        if atr >= 5.0:
            b1=tok.iloc[-2];b2=tok.iloc[-1];b1b=b1['close']-b1['open'];b2b=b2['close']-b2['open']
            if abs(b1b)>=0.3*atr and abs(b2b)>=0.3*atr and b1b*b2b<0 and abs(b2b)>abs(b1b):
                add('V2','long' if b2b>0 else 'short',b2['close']); trig['V2']=True

    # ═══════════════════════════════════════════════════════════
    # BLOC 5: MULTI-SIGNAL CONFIRMATIONS
    # ═══════════════════════════════════════════════════════════

    # M1: LON_GAP + LON_TOKEND same direction (double confirmation)
    if 8.0<=hour<8.1 and 'M1' not in trig and len(tok)>=9:
        tc = candles[(candles['ts_dt']<te)&(candles['ts_dt']<=ct)]
        if len(tc) >= 5:
            gap = (row['open']-tc.iloc[-1]['close'])/atr
            l3=tok.iloc[-3:]; m=(l3.iloc[-1]['close']-l3.iloc[0]['open'])/atr
            if abs(gap)>=0.5 and abs(m)>=1.0:
                gap_dir = 'long' if gap>0 else 'short'
                mom_dir = 'long' if m>0 else 'short'
                if gap_dir == mom_dir:
                    add('M1',gap_dir,row['open']); trig['M1']=True

    # M2: LON_PREV + LON_GAP same direction
    if 8.0<=hour<8.1 and 'M2' not in trig and prev_day_data:
        tc = candles[(candles['ts_dt']<te)&(candles['ts_dt']<=ct)]
        if len(tc) >= 5:
            gap = (row['open']-tc.iloc[-1]['close'])/atr
            prev_body = prev_day_data['body']/atr
            if abs(gap)>=0.5 and abs(prev_body)>=1.0:
                gap_dir = 'long' if gap>0 else 'short'
                prev_dir = 'long' if prev_body>0 else 'short'
                if gap_dir == prev_dir:
                    add('M2',gap_dir,row['open']); trig['M2']=True

    # M3: Big candle + in direction of day trend
    if 0.0<=hour<21.0 and 'M3' not in trig and len(tv)>=20:
        body = row['close'] - row['open']
        day_dir = tv.iloc[-1]['close'] - tv.iloc[0]['open']
        if abs(body) >= 1.0*atr and body * day_dir > 0:
            add('M3','long' if body>0 else 'short',row['close']); trig['M3']=True

print(f"Done. {len(S)} strats.", flush=True)

# ── RESULTATS ──
print("\n" + "="*130)
print("EXPLORATION V4 — Multi-angle (daily, jour, intra-session, vol, confirmations)")
print("="*130)
print(f"{'Strat':>8s} {'Bloc':>6s} {'n':>5s} {'WR':>5s} {'PF':>6s} {'Avg':>8s} {'Total':>8s} {'[1st|2nd]':>18s} {'Split':>6s} {'Tiers':>5s}")
print("-"*130)

blocs = {'D':'Daily','W':'Weekday','S':'Session','V':'VolReg','M':'Multi'}
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
    split_str = "OK" if split else "!!"
    bloc = blocs.get(sn[0], '?')
    marker = " <--" if pf > 1.5 and split else " *" if pf > 1.2 and split else ""
    print(f"{sn:>8s} {bloc:>6s} {n:5d} {wr:4.0f}% {pf:6.2f} {np.mean(pnls):+8.3f} {sum(pnls):+8.1f} [{f1:+7.3f}|{f2:+7.3f}] {split_str:>6s} {tiers:4d}/3{marker}")
    if pf > 1.2 and split:
        good.append(sn)

print(f"\n  Retenues (PF>1.2 + split OK): {', '.join(good) if good else 'aucune'}")
print()
