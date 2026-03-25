"""
Module commun: toutes les strategies, exit et indicateurs.
Le portfolio actif est defini dans config_icm.py / config_ftmo.py / config_5ers.py.
"""
import pandas as pd
import numpy as np

ALL_STRATS = [
    # Price Action
    'TOK_2BAR','TOK_BIG','TOK_FADE','TOK_PREVEXT',
    'LON_PIN','LON_GAP','LON_BIGGAP','LON_KZ','LON_TOKEND','LON_PREV',
    'NY_GAP','NY_LONEND','NY_LONMOM','NY_DAYMOM',
    'D8',
    # Indicators
    'ALL_MACD_RSI','ALL_FVG_BULL','ALL_CONSEC_REV','ALL_FIB_618',
    'ALL_3SOLDIERS','ALL_PSAR_EMA','PO3_SWEEP','ALL_KC_BRK','ALL_DC10',
]

STRAT_NAMES = {
    'TOK_2BAR':'2BAR reversal Tokyo','TOK_BIG':'Big candle Tokyo >1ATR',
    'TOK_FADE':'Fade prev day Tokyo','TOK_PREVEXT':'Prev day close extreme->Tokyo',
    'LON_PIN':'Pin bar London','LON_GAP':'GAP Tokyo->London',
    'LON_BIGGAP':'GAP Tokyo->London >1ATR','LON_KZ':'KZ London fade',
    'LON_TOKEND':'TOKEND 3b->London','LON_PREV':'Prev day continuation London',
    'NY_GAP':'GAP London->NY','NY_LONEND':'LONEND 3b->NY',
    'NY_LONMOM':'LONEND 0.5ATR->NY','NY_DAYMOM':'Day move >1.5ATR->NY',
    'D8':'Inside day breakout London',
    'ALL_MACD_RSI':'MACD med cross + RSI>50',
    'ALL_FVG_BULL':'Fair Value Gap bullish',
    'ALL_CONSEC_REV':'5-bar exhaustion reversal',
    'ALL_FIB_618':'Fib 0.618 retracement bounce',
    'ALL_3SOLDIERS':'Three soldiers/crows pattern',
    'ALL_PSAR_EMA':'Parabolic SAR flip + EMA20',
    'PO3_SWEEP':'PO3 Asian sweep reversal',
    'ALL_KC_BRK':'Keltner Channel breakout',
    'ALL_DC10':'Donchian 10 breakout',
}

STRAT_SESSION = {
    'TOK_2BAR':'Tokyo','TOK_BIG':'Tokyo','TOK_FADE':'Tokyo','TOK_PREVEXT':'Tokyo',
    'LON_PIN':'London','LON_GAP':'London','LON_BIGGAP':'London','LON_KZ':'London',
    'LON_TOKEND':'London','LON_PREV':'London',
    'NY_GAP':'New York','NY_LONEND':'New York','NY_LONMOM':'New York','NY_DAYMOM':'New York',
    'D8':'London',
    'ALL_MACD_RSI':'All','ALL_FVG_BULL':'All','ALL_CONSEC_REV':'All',
    'ALL_FIB_618':'All','ALL_3SOLDIERS':'All','ALL_PSAR_EMA':'All',
    'ALL_KC_BRK':'All',
    'ALL_DC10':'All',
    'PO3_SWEEP':'London',
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
                # SL first (conservative: si les deux touchent sur la meme bougie, SL gagne)
                if b['low'] <= stop: return j, stop
                if b['high'] >= target: return j, target  # TP sur HIGH, exit au TARGET
            else:
                if b['high'] >= stop: return j, stop
                if b['low'] <= target: return j, target  # TP sur LOW, exit au TARGET
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

def compute_indicators(candles):
    """Precalcule les indicateurs necessaires pour les strats indicator.
    IMPORTANT: doit reproduire EXACTEMENT les calculs de find_combo_greedy.py.
    """
    c = candles
    # MACD med (8,17,9)
    ef = c['close'].ewm(span=8, adjust=False).mean()
    es = c['close'].ewm(span=17, adjust=False).mean()
    c['macd_med'] = ef - es
    c['macd_med_sig'] = c['macd_med'].ewm(span=9, adjust=False).mean()
    # RSI 14
    delta = c['close'].diff()
    gain = delta.clip(lower=0); loss = (-delta).clip(lower=0)
    ag = gain.ewm(alpha=1.0/14, min_periods=14, adjust=False).mean()
    al = loss.ewm(alpha=1.0/14, min_periods=14, adjust=False).mean()
    c['rsi14'] = 100 - 100/(1+ag/(al+1e-10))
    # EMA 20
    c['ema20'] = c['close'].ewm(span=20, adjust=False).mean()
    # ATR14 (pour supertrend)
    tr = np.maximum(c['high']-c['low'], np.maximum(abs(c['high']-c['close'].shift(1)), abs(c['low']-c['close'].shift(1))))
    c['atr14'] = tr.ewm(span=14, adjust=False).mean()
    # SUPERTREND comme proxy PSAR (identique a find_combo_greedy.py ligne 112-120)
    c['mid'] = (c['high'] + c['low']) / 2
    up2 = c['mid'] - 2.0 * c['atr14']
    dn2 = c['mid'] + 2.0 * c['atr14']
    n = len(c)
    st_dir = np.zeros(n); st_val = np.zeros(n)
    for i in range(1, n):
        if c.iloc[i]['close'] > dn2.iloc[i-1]:
            st_dir[i] = 1; st_val[i] = up2.iloc[i]
        elif c.iloc[i]['close'] < up2.iloc[i-1]:
            st_dir[i] = -1; st_val[i] = dn2.iloc[i]
        else:
            st_dir[i] = st_dir[i-1]
            st_val[i] = max(up2.iloc[i], st_val[i-1]) if st_dir[i] == 1 else min(dn2.iloc[i], st_val[i-1])
    c['psar_dir'] = st_dir
    # Keltner Channels (EMA20 +/- 1.5*ATR14)
    c['kc_up'] = c['ema20'] + 1.5 * c['atr14']
    c['kc_lo'] = c['ema20'] - 1.5 * c['atr14']
    # Donchian Channel 10
    c['dc10_h'] = c['high'].rolling(10).max()
    c['dc10_l'] = c['low'].rolling(10).min()
    # Body / abs_body
    c['body'] = c['close'] - c['open']
    c['abs_body'] = c['body'].abs()
    return c

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

    # ── INDICATOR STRATS ──
    prev = candles.iloc[ci-1] if ci >= 1 else row

    # ALL_MACD_RSI: MACD med cross + RSI confirmation
    if 'ALL_MACD_RSI' not in trig and 'macd_med' in row.index and pd.notna(row.get('macd_med')) and pd.notna(row.get('rsi14')):
        if prev.get('macd_med',0)<prev.get('macd_med_sig',0) and row['macd_med']>row['macd_med_sig'] and row['rsi14']>50:
            add('ALL_MACD_RSI','long',row['close']); trig['ALL_MACD_RSI']=True
        elif prev.get('macd_med',0)>prev.get('macd_med_sig',0) and row['macd_med']<row['macd_med_sig'] and row['rsi14']<50:
            add('ALL_MACD_RSI','short',row['close']); trig['ALL_MACD_RSI']=True

    # ALL_FVG_BULL: Fair Value Gap (candle 3 bars ago high < current low)
    if 'ALL_FVG_BULL' not in trig and ci >= 3:
        prev3 = candles.iloc[ci-3]
        body = row['close'] - row['open']
        if prev3['high'] < row['low'] and row['close'] > row['open'] and abs(body) >= 0.3*atr:
            add('ALL_FVG_BULL','long',row['close']); trig['ALL_FVG_BULL']=True

    # ALL_CONSEC_REV: 5 consecutive same-dir candles then reversal
    if 'ALL_CONSEC_REV' not in trig and ci >= 6:
        last5 = candles.iloc[ci-5:ci]
        all_bull = all(last5.iloc[j]['close'] > last5.iloc[j]['open'] for j in range(5))
        all_bear = all(last5.iloc[j]['close'] < last5.iloc[j]['open'] for j in range(5))
        total_rng = last5['high'].max() - last5['low'].min()
        abs_body = abs(row['close'] - row['open'])
        if all_bull and total_rng >= 1.5*atr and row['close'] < row['open'] and abs_body >= 0.3*atr:
            add('ALL_CONSEC_REV','short',row['close']); trig['ALL_CONSEC_REV']=True
        elif all_bear and total_rng >= 1.5*atr and row['close'] > row['open'] and abs_body >= 0.3*atr:
            add('ALL_CONSEC_REV','long',row['close']); trig['ALL_CONSEC_REV']=True

    # ALL_FIB_618: Fibonacci 0.618 retracement from 30-bar swing
    # IMPORTANT: LONG ONLY (identique a find_combo_greedy.py, short jamais teste)
    if 'ALL_FIB_618' not in trig and ci >= 30:
        last30 = candles.iloc[ci-30:ci]
        swing_h = last30['high'].max(); swing_l = last30['low'].min()
        swing_rng = swing_h - swing_l
        if swing_rng >= 2.0*atr:
            fib_618 = swing_h - 0.618 * swing_rng
            if row['close'] > swing_h - 0.3*swing_rng and prev['low'] <= fib_618 and row['close'] > fib_618 and row['close'] > row['open']:
                add('ALL_FIB_618','long',row['close']); trig['ALL_FIB_618']=True

    # ALL_3SOLDIERS: Three white soldiers / three black crows
    # IMPORTANT: conditions identiques a find_combo_greedy.py (pas d'overlap/wick check)
    if 'ALL_3SOLDIERS' not in trig and ci >= 3:
        b1 = candles.iloc[ci-2]; b2 = candles.iloc[ci-1]; b3 = row
        if (b1['close']>b1['open'] and b2['close']>b2['open'] and b3['close']>b3['open'] and
            b2['close']>b1['close'] and b3['close']>b2['close'] and
            min(abs(b1['close']-b1['open']),abs(b2['close']-b2['open']),abs(b3['close']-b3['open']))>=0.3*atr):
            add('ALL_3SOLDIERS','long',row['close']); trig['ALL_3SOLDIERS']=True
        if (b1['close']<b1['open'] and b2['close']<b2['open'] and b3['close']<b3['open'] and
            b2['close']<b1['close'] and b3['close']<b2['close'] and
            min(abs(b1['close']-b1['open']),abs(b2['close']-b2['open']),abs(b3['close']-b3['open']))>=0.3*atr):
            add('ALL_3SOLDIERS','short',row['close']); trig['ALL_3SOLDIERS']=True

    # ALL_PSAR_EMA: Parabolic SAR flip + EMA20 filter
    if 'ALL_PSAR_EMA' not in trig and 'psar_dir' in row.index and 'ema20' in row.index and pd.notna(row.get('ema20')):
        if prev.get('psar_dir',-1)==-1 and row['psar_dir']==1 and row['close']>row['ema20']:
            add('ALL_PSAR_EMA','long',row['close']); trig['ALL_PSAR_EMA']=True
        elif prev.get('psar_dir',1)==1 and row['psar_dir']==-1 and row['close']<row['ema20']:
            add('ALL_PSAR_EMA','short',row['close']); trig['ALL_PSAR_EMA']=True

    # PO3_SWEEP: Asian session sweep reversal at London open (7h-9h)
    if 7.0<=hour<9.0 and 'PO3_SWEEP' not in trig:
        asian = candles[(candles['ts_dt']>=ds)&(candles['ts_dt']<te)]
        if len(asian) >= 50:
            asian_h = asian['high'].max(); asian_l = asian['low'].min()
            if row['low'] < asian_l and row['close'] > asian_l and row['close'] > row['open']:
                add('PO3_SWEEP','long',row['close']); trig['PO3_SWEEP']=True
            elif row['high'] > asian_h and row['close'] < asian_h and row['close'] < row['open']:
                add('PO3_SWEEP','short',row['close']); trig['PO3_SWEEP']=True

    # ALL_KC_BRK: Keltner Channel breakout (close crosses KC band)
    if 'ALL_KC_BRK' not in trig and 'kc_up' in row.index and pd.notna(row.get('kc_up')):
        if row['close'] > row['kc_up'] and prev['close'] <= prev['kc_up']:
            add('ALL_KC_BRK','long',row['close']); trig['ALL_KC_BRK']=True
        elif row['close'] < row['kc_lo'] and prev['close'] >= prev['kc_lo']:
            add('ALL_KC_BRK','short',row['close']); trig['ALL_KC_BRK']=True

    # ALL_DC10: Donchian 10 breakout (close breaks prev high/low)
    if 'ALL_DC10' not in trig and 'dc10_h' in row.index and pd.notna(prev.get('dc10_h')):
        if row['close'] > prev['dc10_h']:
            add('ALL_DC10','long',row['close']); trig['ALL_DC10']=True
        elif row['close'] < prev['dc10_l']:
            add('ALL_DC10','short',row['close']); trig['ALL_DC10']=True
