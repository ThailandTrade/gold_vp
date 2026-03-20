"""
Exploration v2 — nouvelles strategies toutes sessions.
Config: SL=1.0 ACT=0.5 TRAIL=0.75, pas de timeout, trailing sur CLOSE.
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
    tok = tv[tv['ts_dt']<te]
    lon = tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<ns)]
    ny = tv[tv['ts_dt']>=ns]

    def add(sn, d, e):
        b, ex = sim_exit(candles, ci, e, d, atr)
        pnl = (ex-e) if d=='long' else (e-ex)
        S.setdefault(sn,[]).append({'date':today,'dir':d,'pnl_oz':pnl-get_sp(today)})

    # ═══════════════════════════════════════════
    # TOKYO (0h-6h)
    # ═══════════════════════════════════════════

    # T1: IB 1h breakout UP (break du high 0h-1h apres 1h)
    if 'T1_done' not in trig and hour >= 1.0 and hour < 6.0:
        ib = tv[(tv['ts_dt']>=ds)&(tv['ts_dt']<ds+pd.Timedelta(hours=1))]
        if len(ib) >= 12:
            trig['T1_done'] = True; trig['T1_h'] = float(ib['high'].max()); trig['T1_l'] = float(ib['low'].min())
    if 'T1_h' in trig and 'T1' not in trig and 1.0 <= hour < 6.0:
        if row['close'] > trig['T1_h']: add('T1','long',row['close']); trig['T1']=True
        elif row['close'] < trig['T1_l']: add('T1','short',row['close']); trig['T1']=True

    # T2: IB 2h breakout (break du high/low 0h-2h apres 2h)
    if 'T2_done' not in trig and hour >= 2.0 and hour < 6.0:
        ib = tv[(tv['ts_dt']>=ds)&(tv['ts_dt']<ds+pd.Timedelta(hours=2))]
        if len(ib) >= 24:
            trig['T2_done'] = True; trig['T2_h'] = float(ib['high'].max()); trig['T2_l'] = float(ib['low'].min())
    if 'T2_h' in trig and 'T2' not in trig and 2.0 <= hour < 6.0:
        if row['close'] > trig['T2_h']: add('T2','long',row['close']); trig['T2']=True
        elif row['close'] < trig['T2_l']: add('T2','short',row['close']); trig['T2']=True

    # T3: First candle Tokyo > 0.5 ATR continuation
    if 0.0<=hour<0.1 and 'T3' not in trig:
        body = row['close'] - row['open']
        if abs(body) >= 0.5*atr:
            add('T3','long' if body>0 else 'short',row['close']); trig['T3']=True

    # T4: First candle Tokyo > 0.3 ATR continuation
    if 0.0<=hour<0.1 and 'T4' not in trig:
        body = row['close'] - row['open']
        if abs(body) >= 0.3*atr:
            add('T4','long' if body>0 else 'short',row['close']); trig['T4']=True

    # T5: Narrow range squeeze (range < 0.2 ATR) then big candle (> 0.5 ATR)
    if 0.0<=hour<6.0 and 'T5' not in trig and len(tok)>=2:
        prev_c = tok.iloc[-2]; cur_c = tok.iloc[-1]
        prev_rng = prev_c['high'] - prev_c['low']
        cur_body = cur_c['close'] - cur_c['open']
        if prev_rng < 0.2*atr and abs(cur_body) >= 0.5*atr:
            add('T5','long' if cur_body>0 else 'short',cur_c['close']); trig['T5']=True

    # T6: 3 consecutive same-direction candles Tokyo > 0.5 ATR total
    if 0.0<=hour<6.0 and 'T6' not in trig and len(tok)>=3:
        c1=tok.iloc[-3];c2=tok.iloc[-2];c3=tok.iloc[-1]
        b1=c1['close']-c1['open'];b2=c2['close']-c2['open'];b3=c3['close']-c3['open']
        if b1*b2>0 and b2*b3>0 and min(abs(b1),abs(b2),abs(b3))>0.05*atr and abs(b1+b2+b3)>=0.5*atr:
            add('T6','long' if b3>0 else 'short',c3['close']); trig['T6']=True

    # T7: Hammer/shooting star Tokyo (wick > 2x body, body > 0.1 ATR)
    if 0.0<=hour<6.0 and 'T7' not in trig:
        body = abs(row['close'] - row['open'])
        rng = row['high'] - row['low']
        if body >= 0.1*atr and rng >= 0.3*atr:
            upper_wick = row['high'] - max(row['open'], row['close'])
            lower_wick = min(row['open'], row['close']) - row['low']
            if lower_wick > 2*body and upper_wick < body:  # hammer
                add('T7','long',row['close']); trig['T7']=True
            elif upper_wick > 2*body and lower_wick < body:  # shooting star
                add('T7','short',row['close']); trig['T7']=True

    # T8: Gap from previous day close > 0.5 ATR at first candle
    if 0.0<=hour<0.1 and 'T8' not in trig and prev_day_data:
        gap = (row['open'] - prev_day_data['close']) / atr
        if abs(gap) >= 0.5:
            add('T8','long' if gap>0 else 'short',row['open']); trig['T8']=True

    # T9: Tokyo range < 0.5 ATR after 3h → breakout (squeeze)
    if 3.0<=hour<6.0 and 'T9' not in trig:
        tok3 = tv[(tv['ts_dt']>=ds)&(tv['ts_dt']<ds+pd.Timedelta(hours=3))]
        if len(tok3) >= 36 and 'T9_done' not in trig:
            rng = float(tok3['high'].max()) - float(tok3['low'].min())
            if rng < 0.5*atr:
                trig['T9_done'] = True; trig['T9_h'] = float(tok3['high'].max()); trig['T9_l'] = float(tok3['low'].min())
        if 'T9_h' in trig and 'T9' not in trig:
            if row['close'] > trig['T9_h']: add('T9','long',row['close']); trig['T9']=True
            elif row['close'] < trig['T9_l']: add('T9','short',row['close']); trig['T9']=True

    # T10: Fade previous day direction at Tokyo open
    if 0.0<=hour<0.1 and 'T10' not in trig and prev_day_data:
        prev_dir = prev_day_data['close'] - prev_day_data['open']
        if abs(prev_dir) >= 1.0*atr:
            add('T10','short' if prev_dir>0 else 'long',row['open']); trig['T10']=True

    # ═══════════════════════════════════════════
    # LONDON (8h-14h30)
    # ═══════════════════════════════════════════

    # L1: London IB 30min breakout (8h-8h30 range, break after)
    if 8.5<=hour<14.5 and 'L1' not in trig:
        if 'L1_done' not in trig:
            ib = tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<ls+pd.Timedelta(minutes=30))]
            if len(ib) >= 6:
                trig['L1_done'] = True; trig['L1_h'] = float(ib['high'].max()); trig['L1_l'] = float(ib['low'].min())
        if 'L1_h' in trig:
            if row['close'] > trig['L1_h']: add('L1','long',row['close']); trig['L1']=True
            elif row['close'] < trig['L1_l']: add('L1','short',row['close']); trig['L1']=True

    # L2: London IB 1h breakout (8h-9h range, break after)
    if 9.0<=hour<14.5 and 'L2' not in trig:
        if 'L2_done' not in trig:
            ib = tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<ls+pd.Timedelta(hours=1))]
            if len(ib) >= 12:
                trig['L2_done'] = True; trig['L2_h'] = float(ib['high'].max()); trig['L2_l'] = float(ib['low'].min())
        if 'L2_h' in trig:
            if row['close'] > trig['L2_h']: add('L2','long',row['close']); trig['L2']=True
            elif row['close'] < trig['L2_l']: add('L2','short',row['close']); trig['L2']=True

    # L3: Tokyo range breakout at London open
    if 8.0<=hour<14.5 and 'L3' not in trig:
        if 'L3_done' not in trig and len(tok) >= 60:
            trig['L3_done'] = True; trig['L3_h'] = float(tok['high'].max()); trig['L3_l'] = float(tok['low'].min())
        if 'L3_h' in trig:
            if row['close'] > trig['L3_h']: add('L3','long',row['close']); trig['L3']=True
            elif row['close'] < trig['L3_l']: add('L3','short',row['close']); trig['L3']=True

    # L4: First London candle > 0.5 ATR continuation
    if 8.0<=hour<8.1 and 'L4' not in trig:
        body = row['close'] - row['open']
        if abs(body) >= 0.5*atr:
            add('L4','long' if body>0 else 'short',row['close']); trig['L4']=True

    # L5: First London candle > 0.3 ATR continuation
    if 8.0<=hour<8.1 and 'L5' not in trig:
        body = row['close'] - row['open']
        if abs(body) >= 0.3*atr:
            add('L5','long' if body>0 else 'short',row['close']); trig['L5']=True

    # L6: Fade first 30min London move > 0.5 ATR
    if 8.5<=hour<8.6 and 'L6' not in trig:
        l30 = tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<ls+pd.Timedelta(minutes=30))]
        if len(l30) >= 6:
            m = (l30.iloc[-1]['close'] - l30.iloc[0]['open']) / atr
            if abs(m) >= 0.5:
                add('L6','short' if m>0 else 'long',row['close']); trig['L6']=True

    # L7: Continuation first 30min London move > 0.5 ATR
    if 8.5<=hour<8.6 and 'L7' not in trig:
        l30 = tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<ls+pd.Timedelta(minutes=30))]
        if len(l30) >= 6:
            m = (l30.iloc[-1]['close'] - l30.iloc[0]['open']) / atr
            if abs(m) >= 0.5:
                add('L7','long' if m>0 else 'short',row['close']); trig['L7']=True

    # L8: 2BAR reversal London
    if 8.0<=hour<14.5 and 'L8' not in trig and len(lon)>=2:
        b1=lon.iloc[-2];b2=lon.iloc[-1];b1b=b1['close']-b1['open'];b2b=b2['close']-b2['open']
        if abs(b1b)>=0.5*atr and abs(b2b)>=0.5*atr and b1b*b2b<0 and abs(b2b)>abs(b1b):
            add('L8','long' if b2b>0 else 'short',b2['close']); trig['L8']=True

    # L9: Hammer/shooting star London
    if 8.0<=hour<14.5 and 'L9' not in trig:
        body = abs(row['close'] - row['open'])
        rng = row['high'] - row['low']
        if body >= 0.1*atr and rng >= 0.3*atr:
            upper_wick = row['high'] - max(row['open'], row['close'])
            lower_wick = min(row['open'], row['close']) - row['low']
            if lower_wick > 2*body and upper_wick < body:
                add('L9','long',row['close']); trig['L9']=True
            elif upper_wick > 2*body and lower_wick < body:
                add('L9','short',row['close']); trig['L9']=True

    # L10: Fade Tokyo move > 0.5 ATR at London (lower threshold than C)
    if 8.0<=hour<8.1 and 'L10' not in trig and len(tok)>=10:
        m = (tok.iloc[-1]['close'] - tok.iloc[0]['open']) / atr
        if abs(m) >= 0.5:
            add('L10','short' if m>0 else 'long',row['open']); trig['L10']=True

    # L11: Narrow range Tokyo (< 0.5 ATR) → London breakout
    if 8.0<=hour<14.5 and 'L11' not in trig:
        if 'L11_done' not in trig and len(tok) >= 60:
            tok_rng = float(tok['high'].max()) - float(tok['low'].min())
            if tok_rng < 0.5*atr:
                trig['L11_done'] = True; trig['L11_h'] = float(tok['high'].max()); trig['L11_l'] = float(tok['low'].min())
        if 'L11_h' in trig:
            if row['close'] > trig['L11_h']: add('L11','long',row['close']); trig['L11']=True
            elif row['close'] < trig['L11_l']: add('L11','short',row['close']); trig['L11']=True

    # L12: Outside bar London (englobing 3 previous)
    if 8.0<=hour<14.5 and 'L12' not in trig and len(lon)>=4:
        prev3_h=lon.iloc[-4:-1]['high'].max();prev3_l=lon.iloc[-4:-1]['low'].min()
        body=abs(row['close']-row['open'])
        if row['high']>=prev3_h and row['low']<=prev3_l and body>=0.5*atr:
            add('L12','long' if row['close']>row['open'] else 'short',row['close']); trig['L12']=True

    # ═══════════════════════════════════════════
    # NEW YORK (14h30-21h)
    # ═══════════════════════════════════════════

    # N1: Daily range breakout at NY (break du high/low du jour)
    if 14.5<=hour<21.0 and 'N1' not in trig:
        if 'N1_done' not in trig and len(tv) >= 100:
            trig['N1_done'] = True; trig['N1_h'] = float(tv['high'].max()); trig['N1_l'] = float(tv['low'].min())
        if 'N1_h' in trig:
            if row['close'] > trig['N1_h']: add('N1','long',row['close']); trig['N1']=True
            elif row['close'] < trig['N1_l']: add('N1','short',row['close']); trig['N1']=True

    # N2: NY IB 15min breakout
    if 14.75<=hour<21.0 and 'N2' not in trig:
        if 'N2_done' not in trig:
            ib = tv[(tv['ts_dt']>=ns)&(tv['ts_dt']<ns+pd.Timedelta(minutes=15))]
            if len(ib) >= 3:
                trig['N2_done'] = True; trig['N2_h'] = float(ib['high'].max()); trig['N2_l'] = float(ib['low'].min())
        if 'N2_h' in trig:
            if row['close'] > trig['N2_h']: add('N2','long',row['close']); trig['N2']=True
            elif row['close'] < trig['N2_l']: add('N2','short',row['close']); trig['N2']=True

    # N3: Fade daily move > 2 ATR at NY
    if 15.0<=hour<21.0 and 'N3' not in trig and len(tv) > 0:
        day_move = (row['close'] - tv.iloc[0]['open']) / atr
        if day_move >= 2.0: add('N3','short',row['close']); trig['N3']=True
        elif day_move <= -2.0: add('N3','long',row['close']); trig['N3']=True

    # N4: Continuation daily move > 2 ATR at NY
    if 15.0<=hour<21.0 and 'N4' not in trig and len(tv) > 0:
        day_move = (row['close'] - tv.iloc[0]['open']) / atr
        if day_move >= 2.0: add('N4','long',row['close']); trig['N4']=True
        elif day_move <= -2.0: add('N4','short',row['close']); trig['N4']=True

    # N5: First NY candle > 0.5 ATR continuation
    if 14.5<=hour<14.6 and 'N5' not in trig:
        body = row['close'] - row['open']
        if abs(body) >= 0.5*atr:
            add('N5','long' if body>0 else 'short',row['close']); trig['N5']=True

    # N6: 2BAR reversal NY
    if 14.5<=hour<21.0 and 'N6' not in trig and len(ny)>=2:
        b1=ny.iloc[-2];b2=ny.iloc[-1];b1b=b1['close']-b1['open'];b2b=b2['close']-b2['open']
        if abs(b1b)>=0.5*atr and abs(b2b)>=0.5*atr and b1b*b2b<0 and abs(b2b)>abs(b1b):
            add('N6','long' if b2b>0 else 'short',b2['close']); trig['N6']=True

    # N7: Hammer/shooting star NY
    if 14.5<=hour<21.0 and 'N7' not in trig:
        body = abs(row['close'] - row['open'])
        rng = row['high'] - row['low']
        if body >= 0.1*atr and rng >= 0.3*atr:
            upper_wick = row['high'] - max(row['open'], row['close'])
            lower_wick = min(row['open'], row['close']) - row['low']
            if lower_wick > 2*body and upper_wick < body:
                add('N7','long',row['close']); trig['N7']=True
            elif upper_wick > 2*body and lower_wick < body:
                add('N7','short',row['close']); trig['N7']=True

    # N8: Big candle NY > 1 ATR continuation
    if 14.5<=hour<21.0 and 'N8' not in trig:
        body = row['close'] - row['open']
        if abs(body) >= 1.0*atr:
            add('N8','long' if body>0 else 'short',row['close']); trig['N8']=True

    # N9: Fade London KZ (8h-10h move) at NY open
    if 14.5<=hour<14.6 and 'N9' not in trig:
        kz = tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<pd.Timestamp(today.year,today.month,today.day,10,0,tz='UTC'))]
        if len(kz) >= 20:
            m = (kz.iloc[-1]['close'] - kz.iloc[0]['open']) / atr
            if abs(m) >= 1.0:
                add('N9','short' if m>0 else 'long',row['open']); trig['N9']=True

    # N10: London high/low break at NY
    if 14.5<=hour<21.0 and 'N10' not in trig:
        if 'N10_done' not in trig and len(lon) >= 60:
            trig['N10_done'] = True; trig['N10_h'] = float(lon['high'].max()); trig['N10_l'] = float(lon['low'].min())
        if 'N10_h' in trig:
            if row['close'] > trig['N10_h']: add('N10','long',row['close']); trig['N10']=True
            elif row['close'] < trig['N10_l']: add('N10','short',row['close']); trig['N10']=True

    # ═══════════════════════════════════════════
    # CROSS-SESSION
    # ═══════════════════════════════════════════

    # X1: Previous day bullish > 1ATR → continuation London
    if 8.0<=hour<8.1 and 'X1' not in trig and prev_day_data:
        prev_body = (prev_day_data['close'] - prev_day_data['open']) / atr
        if abs(prev_body) >= 1.0:
            add('X1','long' if prev_body>0 else 'short',row['open']); trig['X1']=True

    # X2: Previous day range > 2 ATR → fade at London
    if 8.0<=hour<8.1 and 'X2' not in trig and prev_day_data:
        prev_rng = (prev_day_data['high'] - prev_day_data['low']) / atr
        prev_body = prev_day_data['close'] - prev_day_data['open']
        if prev_rng >= 2.0:
            add('X2','short' if prev_body>0 else 'long',row['open']); trig['X2']=True

    # X3: Narrow Tokyo (< 0.5 ATR) + first London candle direction
    if 8.0<=hour<8.1 and 'X3' not in trig and len(tok) >= 60:
        tok_rng = float(tok['high'].max()) - float(tok['low'].min())
        body = row['close'] - row['open']
        if tok_rng < 0.5*atr and abs(body) >= 0.2*atr:
            add('X3','long' if body>0 else 'short',row['close']); trig['X3']=True

    # X4: Previous day continuation at Tokyo open (gap + direction)
    if 0.0<=hour<0.1 and 'X4' not in trig and prev_day_data:
        prev_body = (prev_day_data['close'] - prev_day_data['open']) / atr
        if abs(prev_body) >= 0.5:
            add('X4','long' if prev_body>0 else 'short',row['open']); trig['X4']=True

print(f"Done. {len(S)} strats.", flush=True)

# ── RESULTATS ──
print("\n" + "="*120)
print("EXPLORATION V2 — Config SL=1.0 ACT=0.5 TRAIL=0.75, pas de timeout")
print("="*120)
print(f"{'Strat':>5s} {'Sess':>5s} {'n':>5s} {'WR':>5s} {'PF':>6s} {'Avg':>8s} {'Total':>8s} {'[1st|2nd]':>18s} {'Split':>6s} {'Tiers':>5s}")
print("-"*120)

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
    sess = "TOK" if sn.startswith('T') else "LON" if sn.startswith('L') else "NY" if sn.startswith('N') else "X"
    marker = " <--" if pf > 1.2 and split else ""
    print(f"{sn:>5s} {sess:>5s} {n:5d} {wr:4.0f}% {pf:6.2f} {np.mean(pnls):+8.3f} {sum(pnls):+8.1f} [{f1:+7.3f}|{f2:+7.3f}] {split_str:>6s} {tiers:4d}/3{marker}")
    if pf > 1.2 and split:
        good.append(sn)

print(f"\n  Retenues (PF>1.2 + split OK): {', '.join(good) if good else 'aucune'}")
print()
