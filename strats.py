"""
Module commun: strategies et exit.
11 strats, noms par session.
Config: TRAIL SL=1.0 ACT=0.5 TRAIL=0.75, pas de timeout, trailing sur CLOSE.
"""
import pandas as pd

SL, ACT, TRAIL = 1.0, 0.5, 0.75

STRATS = [
    'TOK_2BAR','TOK_BIG','TOK_FADE',
    'LON_PIN','LON_GAP','LON_KZ','LON_TOKEND','LON_PREV',
    'NY_GAP','NY_LONEND','NY_LONMOM',
]

STRAT_NAMES = {
    'TOK_2BAR':'2BAR reversal Tokyo','TOK_BIG':'Big candle Tokyo >1ATR','TOK_FADE':'Fade prev day Tokyo',
    'LON_PIN':'Pin bar London','LON_GAP':'GAP Tokyo->London','LON_KZ':'KZ London fade',
    'LON_TOKEND':'TOKEND 3b->London','LON_PREV':'Prev day continuation London',
    'NY_GAP':'GAP London->NY','NY_LONEND':'LONEND 3b->NY','NY_LONMOM':'LONEND 0.5ATR->NY',
}

STRAT_SESSION = {
    'TOK_2BAR':'Tokyo','TOK_BIG':'Tokyo','TOK_FADE':'Tokyo',
    'LON_PIN':'London','LON_GAP':'London','LON_KZ':'London','LON_TOKEND':'London','LON_PREV':'London',
    'NY_GAP':'New York','NY_LONEND':'New York','NY_LONMOM':'New York',
}

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

def detect_all(candles, ci, row, ct, today, hour, atr, trig, tv, tok, lon, prev_day_data, add):
    """Detecte les signaux pour les 11 strats."""
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
