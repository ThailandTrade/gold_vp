"""
Audit replay — simule le live bougie par bougie sur les 10 derniers jours
et compare CHAQUE signal avec le backtest.
C'est le test definitif: est-ce que le live prend les memes trades ?
"""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
from dotenv import load_dotenv; load_dotenv()
from phase1_poc_calculator import get_conn, compute_atr, get_trading_days
from phase3_analyze import load_candles_5m

SLIPPAGE = 0.10
SL, ACT, TRAIL = 0.75, 0.5, 0.3

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

daily_data = {}
for day in trading_days:
    dc = candles[candles['date'] == day]
    if len(dc) >= 10: daily_data[day] = {'dir': 1 if dc.iloc[-1]['close'] > dc.iloc[0]['open'] else -1}

STRATS_ALL = ['A','C','D','E','F','G','H','I','J','O','P','Q','R','S','V','Z','AA','AC']

# ══════════════════════════════════════════════════════════════
# METHODE 1: BACKTEST (reference)
# ══════════════════════════════════════════════════════════════
def get_backtest_signals(day, atr):
    """Retourne la liste des signaux backtest pour un jour donne."""
    signals = []
    tok = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    lon = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))]
    ny = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,21,30,tz='UTC'))]

    # A
    if len(tok)>=18:
        lvl=tok.iloc[:12]['high'].max()
        for i in range(12,len(tok)):
            if tok.iloc[i]['close']>lvl:
                signals.append({'strat':'A','dir':'long','time':tok.iloc[i]['ts_dt'],'entry':tok.iloc[i]['close']}); break
    # C
    if len(tok)>=10:
        m=(tok.iloc[-1]['close']-tok.iloc[0]['open'])/atr
        if abs(m)>=1.0:
            l2=candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
            if len(l2)>=6: signals.append({'strat':'C','dir':'short' if m>0 else 'long','time':l2.iloc[0]['ts_dt'],'entry':l2.iloc[0]['open']})
    # D
    tc=candles[candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC')]
    if len(tc)>=5:
        l2=candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
        if len(l2)>=6:
            gap=(l2.iloc[0]['open']-tc.iloc[-1]['close'])/atr
            if abs(gap)>=0.5: signals.append({'strat':'D','dir':'long' if gap>0 else 'short','time':l2.iloc[0]['ts_dt'],'entry':l2.iloc[0]['open']})
    # E
    kz=candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,10,0,tz='UTC'))]
    if len(kz)>=20:
        m=(kz.iloc[-1]['close']-kz.iloc[0]['open'])/atr
        if abs(m)>=0.5:
            post=candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,10,0,tz='UTC')]
            if len(post)>=6: signals.append({'strat':'E','dir':'short' if m>0 else 'long','time':post.iloc[0]['ts_dt'],'entry':post.iloc[0]['open']})
    # F
    if len(tok)>=2:
        for i in range(1,len(tok)):
            b1b=tok.iloc[i-1]['close']-tok.iloc[i-1]['open'];b2b=tok.iloc[i]['close']-tok.iloc[i]['open']
            if abs(b1b)<0.5*atr or abs(b2b)<0.5*atr: continue
            if b1b*b2b>=0 or abs(b2b)<=abs(b1b): continue
            signals.append({'strat':'F','dir':'long' if b2b>0 else 'short','time':tok.iloc[i]['ts_dt'],'entry':tok.iloc[i]['close']}); break
    # G
    if len(ny)>=6:
        body=ny.iloc[0]['close']-ny.iloc[0]['open']
        if abs(body)>=0.3*atr and len(ny)>=2:
            signals.append({'strat':'G','dir':'long' if body>0 else 'short','time':ny.iloc[1]['ts_dt'],'entry':ny.iloc[1]['open']})
    # H
    if len(tok)>=9:
        l3=tok.iloc[-3:]; m=(l3.iloc[-1]['close']-l3.iloc[0]['open'])/atr
        if abs(m)>=1.0:
            l2=candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
            if len(l2)>=6: signals.append({'strat':'H','dir':'long' if m>0 else 'short','time':l2.iloc[0]['ts_dt'],'entry':l2.iloc[0]['open']})
    # I
    ny1=candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,15,30,tz='UTC'))]
    if len(ny1)>=10:
        m=(ny1.iloc[-1]['close']-ny1.iloc[0]['open'])/atr
        if abs(m)>=1.0:
            post=candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,15,30,tz='UTC')]
            if len(post)>=6: signals.append({'strat':'I','dir':'short' if m>0 else 'long','time':post.iloc[0]['ts_dt'],'entry':post.iloc[0]['open']})
    # J
    if len(lon)>=6:
        body=lon.iloc[0]['close']-lon.iloc[0]['open']
        if abs(body)>=0.3*atr and len(lon)>=2:
            signals.append({'strat':'J','dir':'long' if body>0 else 'short','time':lon.iloc[1]['ts_dt'],'entry':lon.iloc[1]['open']})
    # O
    if len(tok)>=1:
        for i in range(len(tok)):
            body=tok.iloc[i]['close']-tok.iloc[i]['open']
            if abs(body)>=1.0*atr:
                signals.append({'strat':'O','dir':'long' if body>0 else 'short','time':tok.iloc[i]['ts_dt'],'entry':tok.iloc[i]['close']}); break
    # P
    if len(ny)>=7:
        oh=ny.iloc[:6]['high'].max(); ol=ny.iloc[:6]['low'].min()
        for i in range(6,len(ny)):
            r=ny.iloc[i]
            if r['close']>oh: signals.append({'strat':'P','dir':'long','time':r['ts_dt'],'entry':r['close']}); break
            elif r['close']<ol: signals.append({'strat':'P','dir':'short','time':r['ts_dt'],'entry':r['close']}); break
    # Q
    if len(lon)>=2:
        for i in range(1,len(lon)):
            pb=lon.iloc[i-1];cb=lon.iloc[i]; hit=False
            if pb['close']<pb['open'] and cb['close']>cb['open'] and cb['open']<=pb['close'] and cb['close']>=pb['open'] and abs(cb['close']-cb['open'])>=0.3*atr:
                signals.append({'strat':'Q','dir':'long','time':cb['ts_dt'],'entry':cb['close']}); hit=True
            if not hit and pb['close']>pb['open'] and cb['close']<cb['open'] and cb['open']>=pb['close'] and cb['close']<=pb['open'] and abs(cb['close']-cb['open'])>=0.3*atr:
                signals.append({'strat':'Q','dir':'short','time':cb['ts_dt'],'entry':cb['close']}); hit=True
            if hit: break
    # R
    if len(tok)>=3:
        for i in range(2,len(tok)):
            c1=tok.iloc[i-2];c2=tok.iloc[i-1];c3=tok.iloc[i]
            b1=c1['close']-c1['open'];b2=c2['close']-c2['open'];b3=c3['close']-c3['open']
            if b1*b2>0 and b2*b3>0 and min(abs(b1),abs(b2),abs(b3))>0.1*atr and abs(b1+b2+b3)>=0.5*atr:
                signals.append({'strat':'R','dir':'long' if b3>0 else 'short','time':c3['ts_dt'],'entry':c3['close']}); break
    # S
    if len(lon)>=3:
        for i in range(2,len(lon)):
            c1=lon.iloc[i-2];c2=lon.iloc[i-1];c3=lon.iloc[i]
            b1=c1['close']-c1['open'];b2=c2['close']-c2['open'];b3=c3['close']-c3['open']
            if b1*b2>0 and b2*b3>0 and min(abs(b1),abs(b2),abs(b3))>0.1*atr and abs(b1+b2+b3)>=0.5*atr:
                signals.append({'strat':'S','dir':'short' if b3>0 else 'long','time':c3['ts_dt'],'entry':c3['close']}); break
    # V
    if len(tok)>=12:
        for i in range(6,len(tok)):
            last6=tok.iloc[i-6:i]; n_bull=(last6['close']>last6['open']).sum()
            if n_bull>=5: signals.append({'strat':'V','dir':'long','time':tok.iloc[i]['ts_dt'],'entry':tok.iloc[i]['open']}); break
            elif n_bull<=1: signals.append({'strat':'V','dir':'short','time':tok.iloc[i]['ts_dt'],'entry':tok.iloc[i]['open']}); break
    # Z
    di=trading_days.index(day) if day in trading_days else -1
    if di>=3:
        dirs=[]
        for k in range(3):
            dk=trading_days[di-3+k]
            if dk in daily_data: dirs.append(daily_data[dk]['dir'])
        if len(dirs)==3 and len(set(dirs))==1:
            l2=candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
            if len(l2)>=6: signals.append({'strat':'Z','dir':'short' if dirs[0]>0 else 'long','time':l2.iloc[0]['ts_dt'],'entry':l2.iloc[0]['open']})
    # AA
    if len(lon)>=1:
        for i in range(len(lon)):
            r=lon.iloc[i]; rng=r['high']-r['low']
            if rng<0.3*atr or abs(r['close']-r['open'])<0.2*atr: continue
            pir=(r['close']-r['low'])/rng
            if pir>=0.9: signals.append({'strat':'AA','dir':'long','time':r['ts_dt'],'entry':r['close']}); break
            if pir<=0.1: signals.append({'strat':'AA','dir':'short','time':r['ts_dt'],'entry':r['close']}); break
    # AC
    if len(tok)>=4:
        for i in range(3,len(tok)):
            prev3_h=tok.iloc[i-3:i]['high'].max(); prev3_l=tok.iloc[i-3:i]['low'].min()
            r=tok.iloc[i]; body=abs(r['close']-r['open'])
            if r['high']>=prev3_h and r['low']<=prev3_l and body>=0.5*atr:
                signals.append({'strat':'AC','dir':'long' if r['close']>r['open'] else 'short','time':r['ts_dt'],'entry':r['close']}); break

    return signals

# ══════════════════════════════════════════════════════════════
# METHODE 2: REPLAY LIVE (simule le live bougie par bougie)
# ══════════════════════════════════════════════════════════════
def replay_live_signals(day, atr):
    """Simule le live en iterant bougie par bougie et retourne les signaux."""
    signals = []
    trig = {}
    ibs = {}

    # Toutes les bougies du jour + contexte
    day_start = pd.Timestamp(day.year, day.month, day.day, 0, 0, tz='UTC')
    day_end = pd.Timestamp(day.year, day.month, day.day, 21, 30, tz='UTC')
    # Contexte: bougies precedentes (comme 1500 bougies)
    all_before = candles[candles['ts_dt'] < day_end]
    day_candles = candles[(candles['ts_dt'] >= day_start) & (candles['ts_dt'] < day_end)]

    for idx in range(len(day_candles)):
        # Le live voit toutes les bougies jusqu'a celle-ci
        current = day_candles.iloc[idx]
        candle_time = current['ts_dt']
        hour = candle_time.hour + candle_time.minute / 60.0
        today = candle_time.date()

        # Simuler get_recent_candles: toutes les bougies jusqu'a celle-ci
        visible = candles[candles['ts_dt'] <= candle_time].tail(1500)

        # ── Meme logique que detect_signals dans le live ──

        # A
        if 'A_done' not in ibs and hour >= 1.0:
            s = pd.Timestamp(today.year,today.month,today.day,0,0,tz='UTC')
            tok_all = visible[(visible['ts_dt']>=s) & (visible['ts_dt']<pd.Timestamp(today.year,today.month,today.day,6,0,tz='UTC'))]
            ib = visible[(visible['ts_dt']>=s) & (visible['ts_dt']<s+pd.Timedelta(hours=1))]
            if len(ib) >= 12 and len(tok_all) >= 18: ibs['A_high'] = float(ib['high'].max()); ibs['A_done'] = True
        if 'A_high' in ibs and 'A_trig' not in ibs and 1.0 <= hour < 6.0:
            if visible.iloc[-1]['close'] > ibs['A_high']:
                signals.append({'strat':'A','dir':'long','time':candle_time,'entry':visible.iloc[-1]['close']}); ibs['A_trig'] = True

        # C
        if 8.0 <= hour < 8.1:
            k = str(today)+'_C'
            if k not in trig:
                tok = visible[(visible['ts_dt']>=pd.Timestamp(today.year,today.month,today.day,0,0,tz='UTC')) & (visible['ts_dt']<pd.Timestamp(today.year,today.month,today.day,6,0,tz='UTC'))]
                if len(tok) >= 10:
                    m = (tok.iloc[-1]['close'] - tok.iloc[0]['open']) / atr
                    if abs(m) >= 1.0:
                        signals.append({'strat':'C','dir':'short' if m>0 else 'long','time':candle_time,'entry':visible.iloc[-1]['open']}); trig[k] = True

        # D
        if 8.0 <= hour < 8.1:
            k = str(today)+'_D'
            if k not in trig:
                tc = visible[visible['ts_dt']<pd.Timestamp(today.year,today.month,today.day,6,0,tz='UTC')]
                if len(tc) >= 5:
                    gap = (visible.iloc[-1]['open'] - tc.iloc[-1]['close']) / atr
                    if abs(gap) >= 0.5:
                        signals.append({'strat':'D','dir':'long' if gap>0 else 'short','time':candle_time,'entry':visible.iloc[-1]['open']}); trig[k] = True

        # E
        if 10.0 <= hour < 10.1:
            k = str(today)+'_E'
            if k not in trig:
                kz = visible[(visible['ts_dt']>=pd.Timestamp(today.year,today.month,today.day,8,0,tz='UTC')) & (visible['ts_dt']<pd.Timestamp(today.year,today.month,today.day,10,0,tz='UTC'))]
                if len(kz) >= 20:
                    m = (kz.iloc[-1]['close'] - kz.iloc[0]['open']) / atr
                    if abs(m) >= 0.5:
                        signals.append({'strat':'E','dir':'short' if m>0 else 'long','time':candle_time,'entry':visible.iloc[-1]['open']}); trig[k] = True

        # F
        if 0.0 <= hour < 6.0:
            k = str(today)+'_F'
            if k not in trig:
                tok_f = visible[(visible['ts_dt']>=pd.Timestamp(today.year,today.month,today.day,0,0,tz='UTC')) & (visible['ts_dt']<pd.Timestamp(today.year,today.month,today.day,6,0,tz='UTC'))]
                if len(tok_f) >= 8:
                    b1 = tok_f.iloc[-2]; b2 = tok_f.iloc[-1]
                    b1b = b1['close']-b1['open']; b2b = b2['close']-b2['open']
                    if abs(b1b)>=0.5*atr and abs(b2b)>=0.5*atr and b1b*b2b<0 and abs(b2b)>abs(b1b):
                        signals.append({'strat':'F','dir':'long' if b2b>0 else 'short','time':candle_time,'entry':b2['close']}); trig[k] = True

        # G
        if 14.5 <= hour < 14.6:
            k = str(today)+'_G'
            if k not in trig:
                first = visible.iloc[-1]; body = first['close'] - first['open']
                if abs(body) >= 0.3 * atr:
                    signals.append({'strat':'G','dir':'long' if body>0 else 'short','time':candle_time,'entry':first['close']}); trig[k] = True

        # H
        if 8.0 <= hour < 8.1:
            k = str(today)+'_H'
            if k not in trig:
                tok = visible[(visible['ts_dt']>=pd.Timestamp(today.year,today.month,today.day,0,0,tz='UTC')) & (visible['ts_dt']<pd.Timestamp(today.year,today.month,today.day,6,0,tz='UTC'))]
                if len(tok) >= 9:
                    last3 = tok.iloc[-3:]
                    m = (last3.iloc[-1]['close'] - last3.iloc[0]['open']) / atr
                    if abs(m) >= 1.0:
                        signals.append({'strat':'H','dir':'long' if m>0 else 'short','time':candle_time,'entry':visible.iloc[-1]['open']}); trig[k] = True

        # I
        if 15.5 <= hour < 15.6:
            k = str(today)+'_I'
            if k not in trig:
                ny1 = visible[(visible['ts_dt']>=pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC')) & (visible['ts_dt']<pd.Timestamp(today.year,today.month,today.day,15,30,tz='UTC'))]
                if len(ny1) >= 10:
                    m = (ny1.iloc[-1]['close'] - ny1.iloc[0]['open']) / atr
                    if abs(m) >= 1.0:
                        signals.append({'strat':'I','dir':'short' if m>0 else 'long','time':candle_time,'entry':visible.iloc[-1]['open']}); trig[k] = True

        # J
        if 8.0 <= hour < 8.1:
            k = str(today)+'_J'
            if k not in trig:
                first = visible.iloc[-1]; body = first['close'] - first['open']
                if abs(body) >= 0.3 * atr:
                    signals.append({'strat':'J','dir':'long' if body>0 else 'short','time':candle_time,'entry':first['close']}); trig[k] = True

        # O
        if 0.0 <= hour < 6.0:
            k = str(today)+'_O'
            if k not in trig:
                tok = visible[(visible['ts_dt']>=pd.Timestamp(today.year,today.month,today.day,0,0,tz='UTC')) & (visible['ts_dt']<pd.Timestamp(today.year,today.month,today.day,6,0,tz='UTC'))]
                if len(tok) >= 6:
                    r = visible.iloc[-1]; body = r['close'] - r['open']
                    if abs(body) >= 1.0 * atr:
                        signals.append({'strat':'O','dir':'long' if body>0 else 'short','time':candle_time,'entry':r['close']}); trig[k] = True

        # P
        if 15.0 <= hour < 21.5:
            k = str(today)+'_P'
            if k not in trig:
                if 'P_high' not in ibs:
                    orb = visible[(visible['ts_dt']>=pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC')) & (visible['ts_dt']<pd.Timestamp(today.year,today.month,today.day,15,0,tz='UTC'))]
                    if len(orb) >= 6:
                        ibs['P_high'] = float(orb['high'].max()); ibs['P_low'] = float(orb['low'].min())
                if 'P_high' in ibs:
                    r = visible.iloc[-1]
                    if r['close'] > ibs['P_high']:
                        signals.append({'strat':'P','dir':'long','time':candle_time,'entry':r['close']}); trig[k] = True
                    elif r['close'] < ibs['P_low']:
                        signals.append({'strat':'P','dir':'short','time':candle_time,'entry':r['close']}); trig[k] = True

        # Q
        if 8.0 <= hour < 14.5:
            k = str(today)+'_Q'
            if k not in trig:
                lon = visible[(visible['ts_dt']>=pd.Timestamp(today.year,today.month,today.day,8,0,tz='UTC')) & (visible['ts_dt']<pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC'))]
                if len(lon) >= 6:
                    prev_b = lon.iloc[-2]; cur_b = lon.iloc[-1]
                    if (prev_b['close']<prev_b['open'] and cur_b['close']>cur_b['open'] and cur_b['open']<=prev_b['close'] and cur_b['close']>=prev_b['open'] and abs(cur_b['close']-cur_b['open'])>=0.3*atr):
                        signals.append({'strat':'Q','dir':'long','time':candle_time,'entry':cur_b['close']}); trig[k] = True
                    elif (prev_b['close']>prev_b['open'] and cur_b['close']<cur_b['open'] and cur_b['open']>=prev_b['close'] and cur_b['close']<=prev_b['open'] and abs(cur_b['close']-cur_b['open'])>=0.3*atr):
                        signals.append({'strat':'Q','dir':'short','time':candle_time,'entry':cur_b['close']}); trig[k] = True

        # R
        if 0.0 <= hour < 6.0:
            k = str(today)+'_R'
            if k not in trig:
                tok = visible[(visible['ts_dt']>=pd.Timestamp(today.year,today.month,today.day,0,0,tz='UTC')) & (visible['ts_dt']<pd.Timestamp(today.year,today.month,today.day,6,0,tz='UTC'))]
                if len(tok) >= 6:
                    c1=tok.iloc[-3];c2=tok.iloc[-2];c3=tok.iloc[-1]
                    b1=c1['close']-c1['open'];b2=c2['close']-c2['open'];b3=c3['close']-c3['open']
                    if b1*b2>0 and b2*b3>0 and min(abs(b1),abs(b2),abs(b3))>0.1*atr and abs(b1+b2+b3)>=0.5*atr:
                        signals.append({'strat':'R','dir':'long' if b3>0 else 'short','time':candle_time,'entry':c3['close']}); trig[k] = True

        # S
        if 8.0 <= hour < 14.5:
            k = str(today)+'_S'
            if k not in trig:
                lon = visible[(visible['ts_dt']>=pd.Timestamp(today.year,today.month,today.day,8,0,tz='UTC')) & (visible['ts_dt']<pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC'))]
                if len(lon) >= 6:
                    c1=lon.iloc[-3];c2=lon.iloc[-2];c3=lon.iloc[-1]
                    b1=c1['close']-c1['open'];b2=c2['close']-c2['open'];b3=c3['close']-c3['open']
                    if b1*b2>0 and b2*b3>0 and min(abs(b1),abs(b2),abs(b3))>0.1*atr and abs(b1+b2+b3)>=0.5*atr:
                        signals.append({'strat':'S','dir':'short' if b3>0 else 'long','time':candle_time,'entry':c3['close']}); trig[k] = True

        # V
        if 0.0 <= hour < 6.0:
            k = str(today)+'_V'
            if k not in trig:
                tok = visible[(visible['ts_dt']>=pd.Timestamp(today.year,today.month,today.day,0,0,tz='UTC')) & (visible['ts_dt']<pd.Timestamp(today.year,today.month,today.day,6,0,tz='UTC'))]
                if len(tok) >= 7:
                    last6 = tok.iloc[-6:]
                    n_bull = (last6['close'] > last6['open']).sum()
                    if n_bull >= 5:
                        signals.append({'strat':'V','dir':'long','time':candle_time,'entry':tok.iloc[-1]['open']}); trig[k] = True
                    elif n_bull <= 1:
                        signals.append({'strat':'V','dir':'short','time':candle_time,'entry':tok.iloc[-1]['open']}); trig[k] = True

        # Z
        if 8.0 <= hour < 8.1:
            k = str(today)+'_Z'
            if k not in trig:
                prev_days = []
                for c_date in sorted(set(visible['date'].unique()), reverse=True):
                    if c_date < today:
                        prev_days.append(c_date)
                        if len(prev_days) == 3: break
                if len(prev_days) == 3:
                    dirs = []
                    for pd_z in prev_days:
                        dc = visible[visible['date'] == pd_z]
                        if len(dc) >= 10:
                            dirs.append(1 if dc.iloc[-1]['close'] > dc.iloc[0]['open'] else -1)
                    if len(dirs) == 3 and len(set(dirs)) == 1:
                        signals.append({'strat':'Z','dir':'short' if dirs[0] > 0 else 'long','time':candle_time,'entry':visible.iloc[-1]['open']}); trig[k] = True

        # AA
        if 8.0 <= hour < 14.5:
            k = str(today)+'_AA'
            if k not in trig:
                lon = visible[(visible['ts_dt']>=pd.Timestamp(today.year,today.month,today.day,8,0,tz='UTC')) & (visible['ts_dt']<pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC'))]
                if len(lon) >= 6:
                    r = lon.iloc[-1]; rng = r['high'] - r['low']
                    if rng >= 0.3*atr and abs(r['close']-r['open']) >= 0.2*atr:
                        pir = (r['close'] - r['low']) / rng
                        if pir >= 0.9:
                            signals.append({'strat':'AA','dir':'long','time':candle_time,'entry':r['close']}); trig[k] = True
                        elif pir <= 0.1:
                            signals.append({'strat':'AA','dir':'short','time':candle_time,'entry':r['close']}); trig[k] = True

        # AC
        if 0.0 <= hour < 6.0:
            k = str(today)+'_AC'
            if k not in trig:
                tok = visible[(visible['ts_dt']>=pd.Timestamp(today.year,today.month,today.day,0,0,tz='UTC')) & (visible['ts_dt']<pd.Timestamp(today.year,today.month,today.day,6,0,tz='UTC'))]
                if len(tok) >= 6 and len(tok) >= 4:
                    r = tok.iloc[-1]
                    prev3_h = tok.iloc[-4:-1]['high'].max()
                    prev3_l = tok.iloc[-4:-1]['low'].min()
                    body = abs(r['close'] - r['open'])
                    if r['high'] >= prev3_h and r['low'] <= prev3_l and body >= 0.5*atr:
                        d = 'long' if r['close'] > r['open'] else 'short'
                        signals.append({'strat':'AC','dir':d,'time':candle_time,'entry':r['close']}); trig[k] = True

    return signals

# ══════════════════════════════════════════════════════════════
# COMPARAISON
# ══════════════════════════════════════════════════════════════
print("="*100)
print("REPLAY AUDIT — 10 derniers jours, backtest vs live bougie par bougie")
print("="*100)

total_bt = 0; total_live = 0; matches = 0; mismatches = 0; extra_live = 0; missing_live = 0
mismatch_details = []

for day in trading_days[-10:]:
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue

    bt_signals = get_backtest_signals(day, atr)
    live_signals = replay_live_signals(day, atr)

    bt_set = {(s['strat'], s['dir']) for s in bt_signals}
    live_set = {(s['strat'], s['dir']) for s in live_signals}

    total_bt += len(bt_set)
    total_live += len(live_set)

    # Signaux dans les deux
    common = bt_set & live_set
    matches += len(common)

    # Dans backtest mais pas dans live
    only_bt = bt_set - live_set
    missing_live += len(only_bt)

    # Dans live mais pas dans backtest
    only_live = live_set - bt_set
    extra_live += len(only_live)

    if only_bt or only_live:
        mismatches += 1
        for s, d in only_bt:
            bt_s = [x for x in bt_signals if x['strat']==s and x['dir']==d][0]
            mismatch_details.append(f"  {day} MANQUE  {s:3s} {d:5s} backtest:{bt_s['time'].strftime('%H:%M')} entry={bt_s['entry']:.2f}")
        for s, d in only_live:
            live_s = [x for x in live_signals if x['strat']==s and x['dir']==d][0]
            mismatch_details.append(f"  {day} EXTRA   {s:3s} {d:5s} live:{live_s['time'].strftime('%H:%M')} entry={live_s['entry']:.2f}")

    day_ok = "OK" if not only_bt and not only_live else "DIFF"
    print(f"  {day}: BT={len(bt_set):2d} signals, Live={len(live_set):2d} signals, Match={len(common):2d} [{day_ok}]")

print(f"\n{'='*100}")
print(f"RESUME:")
print(f"  Signaux backtest:  {total_bt}")
print(f"  Signaux live:      {total_live}")
print(f"  Matches:           {matches}")
print(f"  Manquants live:    {missing_live}")
print(f"  Extra live:        {extra_live}")
print(f"  Jours avec diff:   {mismatches}/10")

if mismatch_details:
    print(f"\nDETAIL DES DIVERGENCES:")
    for d in mismatch_details:
        print(d)

pct = matches / total_bt * 100 if total_bt > 0 else 0
print(f"\n  TAUX DE MATCH: {pct:.1f}%")
print(f"{'='*100}")

conn.close()
