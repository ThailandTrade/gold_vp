"""
Module commun: toutes les strategies et exit.
Config: TRAIL SL=1.0 ACT=0.5 TRAIL=0.75, pas de timeout, trailing sur CLOSE.
Le portfolio actif est defini dans config_icmarkets.py ou config_ftmo.py.
"""
import pandas as pd

SL, ACT, TRAIL = 1.0, 0.5, 0.75

ALL_STRATS = [
    'TOK_2BAR','TOK_BIG','TOK_FADE','TOK_PREVEXT',
    'LON_PIN','LON_GAP','LON_BIGGAP','LON_KZ','LON_TOKEND','LON_PREV',
    'NY_GAP','NY_LONEND','NY_LONMOM','NY_DAYMOM',
    'D8',
]
# Default portfolio (ICMarkets)
STRATS = ALL_STRATS

STRAT_NAMES = {
    'TOK_2BAR':'2BAR reversal Tokyo','TOK_BIG':'Big candle Tokyo >1ATR',
    'TOK_FADE':'Fade prev day Tokyo','TOK_PREVEXT':'Prev day close extreme->Tokyo',
    'LON_PIN':'Pin bar London','LON_GAP':'GAP Tokyo->London',
    'LON_BIGGAP':'GAP Tokyo->London >1ATR','LON_KZ':'KZ London fade',
    'LON_TOKEND':'TOKEND 3b->London','LON_PREV':'Prev day continuation London',
    'NY_GAP':'GAP London->NY','NY_LONEND':'LONEND 3b->NY',
    'NY_LONMOM':'LONEND 0.5ATR->NY','NY_DAYMOM':'Day move >1.5ATR->NY',
    'D8':'Inside day breakout London',
}

STRAT_SESSION = {
    'TOK_2BAR':'Tokyo','TOK_BIG':'Tokyo','TOK_FADE':'Tokyo','TOK_PREVEXT':'Tokyo',
    'LON_PIN':'London','LON_GAP':'London','LON_BIGGAP':'London','LON_KZ':'London',
    'LON_TOKEND':'London','LON_PREV':'London',
    'NY_GAP':'New York','NY_LONEND':'New York','NY_LONMOM':'New York','NY_DAYMOM':'New York',
    'D8':'London',
}

def sim_exit(cdf, pos, entry, d, atr, check_entry_candle=False):
    """Exit avec config globale (SL, ACT, TRAIL)."""
    return sim_exit_custom(cdf, pos, entry, d, atr, 'TRAIL', SL, ACT, TRAIL, check_entry_candle)

def sim_exit_custom(cdf, pos, entry, d, atr, exit_type, p1, p2, p3, check_entry_candle=False):
    """Exit avec config custom.
    TRAIL: p1=sl, p2=act, p3=trail
    TPSL:  p1=sl, p2=tp, p3=unused
    """
    sl_val = p1
    stop = entry + sl_val*atr if d == 'short' else entry - sl_val*atr
    start = 0 if check_entry_candle else 1

    if exit_type == 'TPSL':
        target = entry + p2*atr if d == 'long' else entry - p2*atr
        for j in range(start, len(cdf)-pos):
            b = cdf.iloc[pos+j]
            if j == 0:
                if d == 'long' and b['low'] <= stop: return 0, stop
                if d == 'short' and b['high'] >= stop: return 0, stop
                continue
            if d == 'long':
                if b['low'] <= stop: return j, stop
                if b['close'] >= target: return j, b['close']
            else:
                if b['high'] >= stop: return j, stop
                if b['close'] <= target: return j, b['close']
        n = min(288, len(cdf)-pos-1)
        if n > 0: return n, cdf.iloc[pos+n]['close']
        return 1, entry
    else:  # TRAIL
        best = entry; ta = False; act_val = p2; trail_val = p3
        for j in range(start, len(cdf)-pos):
            b = cdf.iloc[pos+j]
            if j == 0:
                if d == 'long' and b['low'] <= stop: return 0, stop
                if d == 'short' and b['high'] >= stop: return 0, stop
                continue
            if d == 'long':
                if b['low'] <= stop: return j, stop
                if b['close'] > best: best = b['close']
                if not ta and (best-entry) >= act_val*atr: ta = True
                if ta: stop = max(stop, best - trail_val*atr)
                if b['close'] < stop: return j, b['close']
            else:
                if b['high'] >= stop: return j, stop
                if b['close'] < best: best = b['close']
                if not ta and (entry-best) >= act_val*atr: ta = True
                if ta: stop = min(stop, best + trail_val*atr)
                if b['close'] > stop: return j, b['close']
        return 1, entry

def detect_all(candles, ci, row, ct, today, hour, atr, trig, tv, tok, lon, prev_day_data, add, prev2_day_data=None):
    """Detecte les signaux pour toutes les strats."""
    ds = pd.Timestamp(today.year,today.month,today.day,0,0,tz='UTC')
    te = pd.Timestamp(today.year,today.month,today.day,6,0,tz='UTC')
    ls = pd.Timestamp(today.year,today.month,today.day,8,0,tz='UTC')
    ns = pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC')

    # ── TOKYO ──
    if 0.0<=hour<6.0 and 'TOK_2BAR' not in trig and len(tok)>=2:
        b1=tok.iloc[-2];b2=tok.iloc[-1];b1b=b1['close']-b1['open'];b2b=b2['close']-b2['open']
        if abs(b1b)>=0.5*atr and abs(b2b)>=0.5*atr and b1b*b2b<0 and abs(b2b)>abs(b1b):
            add('TOK_2BAR','long' if b2b>0 else 'short',b2['close']); trig['TOK_2BAR']=True
    if 0.0<=hour<6.0 and 'TOK_BIG' not in trig:
        body=row['close']-row['open']
        if abs(body)>=1.0*atr: add('TOK_BIG','long' if body>0 else 'short',row['close']); trig['TOK_BIG']=True
    if 0.0<=hour<0.1 and 'TOK_FADE' not in trig and prev_day_data:
        prev_dir = prev_day_data['close'] - prev_day_data['open']
        if abs(prev_dir) >= 1.0*atr:
            add('TOK_FADE','short' if prev_dir>0 else 'long',row['open']); trig['TOK_FADE']=True
    # TOK_PREVEXT: prev day close near extreme (top/bottom 10%) → continuation Tokyo
    if 0.0<=hour<0.1 and 'TOK_PREVEXT' not in trig and prev_day_data:
        pr = prev_day_data.get('range', prev_day_data['high']-prev_day_data['low'])
        if pr > 0:
            pos_close = (prev_day_data['close'] - prev_day_data['low']) / pr
            if pos_close >= 0.9: add('TOK_PREVEXT','long',row['open']); trig['TOK_PREVEXT']=True
            elif pos_close <= 0.1: add('TOK_PREVEXT','short',row['open']); trig['TOK_PREVEXT']=True

    # ── LONDON ──
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
    # LON_BIGGAP: GAP Tokyo→London > 1.0 ATR (seuil strict)
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
        prev_body = (prev_day_data['close'] - prev_day_data['open']) / atr
        if abs(prev_body) >= 1.0:
            add('LON_PREV','long' if prev_body>0 else 'short',row['open']); trig['LON_PREV']=True

    # ── NY ──
    if 14.5<=hour<14.6 and 'NY_GAP' not in trig and len(lon)>=5:
        gap=(row['open']-lon.iloc[-1]['close'])/atr
        if abs(gap)>=0.5: add('NY_GAP','long' if gap>0 else 'short',row['open']); trig['NY_GAP']=True
    if 14.5<=hour<14.6 and 'NY_LONEND' not in trig and len(lon)>=9:
        l3=lon.iloc[-3:]; m=(l3.iloc[-1]['close']-l3.iloc[0]['open'])/atr
        if abs(m)>=1.0: add('NY_LONEND','long' if m>0 else 'short',row['open']); trig['NY_LONEND']=True
    if 14.5<=hour<14.6 and 'NY_LONMOM' not in trig and len(lon)>=9:
        l3=lon.iloc[-3:]; m=(l3.iloc[-1]['close']-l3.iloc[0]['open'])/atr
        if abs(m)>=0.5: add('NY_LONMOM','long' if m>0 else 'short',row['open']); trig['NY_LONMOM']=True
    # NY_DAYMOM: Tokyo+London combined move >1.5ATR → continuation NY
    if 14.5<=hour<14.6 and 'NY_DAYMOM' not in trig and len(tv)>=100:
        day_move=(row['open']-tv.iloc[0]['open'])/atr  # open, pas close (la bougie n'est pas fermee)
        if abs(day_move)>=1.5: add('NY_DAYMOM','long' if day_move>0 else 'short',row['open']); trig['NY_DAYMOM']=True

    # ── DAILY PATTERNS ──
    # D8: Previous inside day → breakout London
    if 8.0<=hour<14.5 and 'D8' not in trig and prev_day_data and prev2_day_data:
        if prev_day_data['high']<prev2_day_data['high'] and prev_day_data['low']>prev2_day_data['low']:
            if row['close']>prev_day_data['high']: add('D8','long',row['close']); trig['D8']=True
            elif row['close']<prev_day_data['low']: add('D8','short',row['close']); trig['D8']=True
