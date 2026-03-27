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
    'ALL_ADX_FAST','TOK_WILLR',
    # Candlestick patterns
    'ALL_ENGULF','ALL_HAMMER','ALL_DOJI_REV','ALL_MSTAR',
    'ALL_INSIDE_BRK','ALL_BB_SQUEEZE',
    'ALL_RSI_EXTREME','ALL_MACD_HIST','ALL_VOL_SPIKE',
    'LON_ASIAN_BRK',
    # Index/crypto strats (US session)
    'IDX_ORB15','IDX_ORB30','IDX_GAP_FILL','IDX_GAP_CONT',
    'IDX_NY_MOM','IDX_LATE_REV','IDX_TREND_DAY',
    'IDX_VWAP_BOUNCE','IDX_BB_REV','IDX_RSI_REV',
    'IDX_PREV_HL','IDX_NR4','IDX_KC_BRK',
    'IDX_ENGULF','IDX_3SOLDIERS','IDX_CONSEC_REV',
    'TOK_NR4','LON_DC10_MOM',
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
    'ALL_ADX_FAST':'ADX fast DI cross + EMA21',
    'TOK_WILLR':'Williams %R Tokyo reversal',
    'ALL_ENGULF':'Bullish/bearish engulfing',
    'ALL_HAMMER':'Hammer / shooting star',
    'ALL_DOJI_REV':'Doji after trend reversal',
    'ALL_MSTAR':'Morning star / evening star',
    'LON_ASIAN_BRK':'Asian range breakout London',
    'ALL_INSIDE_BRK':'Inside bar breakout',
    'ALL_BB_SQUEEZE':'Bollinger squeeze breakout',
    'ALL_RSI_EXTREME':'RSI extreme reversal',
    'ALL_MACD_HIST':'MACD histogram reversal',
    'ALL_VOL_SPIKE':'Volume spike with direction',
    'IDX_ORB15':'Opening range breakout 15min',
    'IDX_ORB30':'Opening range breakout 30min',
    'IDX_GAP_FILL':'Overnight gap fill',
    'IDX_GAP_CONT':'Gap continuation',
    'IDX_NY_MOM':'NY first hour momentum',
    'IDX_LATE_REV':'Late day reversal',
    'IDX_TREND_DAY':'Trend day (IB breakout)',
    'IDX_VWAP_BOUNCE':'VWAP mean reversion',
    'IDX_BB_REV':'Bollinger band reversal',
    'IDX_RSI_REV':'RSI extreme reversal (index)',
    'IDX_PREV_HL':'Previous day H/L breakout',
    'IDX_NR4':'Narrow range 4 breakout (index)',
    'IDX_KC_BRK':'Keltner channel breakout (index)',
    'IDX_ENGULF':'Engulfing pattern (index)',
    'IDX_3SOLDIERS':'Three soldiers/crows (index)',
    'IDX_CONSEC_REV':'Consecutive exhaustion reversal (index)',
    'TOK_NR4':'Narrow range 4 Tokyo',
    'LON_DC10_MOM':'Donchian 10 + momentum London',
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
    'ALL_ADX_FAST':'All',
    'TOK_WILLR':'Tokyo',
    'PO3_SWEEP':'London',
    'ALL_ENGULF':'All','ALL_HAMMER':'All','ALL_DOJI_REV':'All','ALL_MSTAR':'All',
    'LON_ASIAN_BRK':'London',
    'ALL_INSIDE_BRK':'All','ALL_BB_SQUEEZE':'All',
    'ALL_RSI_EXTREME':'All','ALL_MACD_HIST':'All','ALL_VOL_SPIKE':'All',
    'IDX_ORB15':'US','IDX_ORB30':'US','IDX_GAP_FILL':'US','IDX_GAP_CONT':'US',
    'IDX_NY_MOM':'US','IDX_LATE_REV':'US Late','IDX_TREND_DAY':'US',
    'IDX_VWAP_BOUNCE':'US','IDX_BB_REV':'All','IDX_RSI_REV':'All',
    'IDX_PREV_HL':'US','IDX_NR4':'All','IDX_KC_BRK':'All',
    'IDX_ENGULF':'All','IDX_3SOLDIERS':'All','IDX_CONSEC_REV':'All',
    'TOK_NR4':'Tokyo','LON_DC10_MOM':'London',
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
    # ADX fast (7-period)
    pdm = c['high'].diff().clip(lower=0); mdm = (-c['low'].diff()).clip(lower=0)
    mask = pdm > mdm; pdm2 = pdm.where(mask, 0); mdm2 = mdm.where(~mask, 0)
    atr_f = tr.ewm(span=7, adjust=False).mean()
    c['pdi_f'] = 100 * pdm2.ewm(span=7, adjust=False).mean() / (atr_f + 1e-10)
    c['mdi_f'] = 100 * mdm2.ewm(span=7, adjust=False).mean() / (atr_f + 1e-10)
    dx_f = 100 * abs(c['pdi_f'] - c['mdi_f']) / (c['pdi_f'] + c['mdi_f'] + 1e-10)
    c['adx_f'] = dx_f.ewm(span=7, adjust=False).mean()
    # EMA 21
    c['ema21'] = c['close'].ewm(span=21, adjust=False).mean()
    # Williams %R 14
    hh14 = c['high'].rolling(14).max(); ll14 = c['low'].rolling(14).min()
    c['wr14'] = -100 * (hh14 - c['close']) / (hh14 - ll14 + 1e-10)
    # Donchian Channel 10
    c['dc10_h'] = c['high'].rolling(10).max()
    c['dc10_l'] = c['low'].rolling(10).min()
    # Body / abs_body
    c['body'] = c['close'] - c['open']
    c['abs_body'] = c['body'].abs()
    # Bollinger Bands 20,2 (for BB_SQUEEZE)
    c['bb_mid'] = c['close'].rolling(20).mean()
    c['bb_std'] = c['close'].rolling(20).std()
    c['bb_up'] = c['bb_mid'] + 2.0 * c['bb_std']
    c['bb_lo'] = c['bb_mid'] - 2.0 * c['bb_std']
    c['bb_width'] = (c['bb_up'] - c['bb_lo']) / (c['bb_mid'] + 1e-10)
    c['bb_width_min20'] = c['bb_width'].rolling(20).min()
    # MACD histogram (for MACD_HIST)
    c['macd_hist'] = c['macd_med'] - c['macd_med_sig']
    # Volume average (for VOL_SPIKE)
    if 'tick_volume' in c.columns:
        c['vol_avg'] = c['tick_volume'].rolling(20).mean()
    elif 'volume' in c.columns:
        c['vol_avg'] = c['volume'].rolling(20).mean()
    # Upper/lower wick ratios (for HAMMER)
    c['upper_wick'] = c['high'] - c[['open','close']].max(axis=1)
    c['lower_wick'] = c[['open','close']].min(axis=1) - c['low']
    c['candle_range'] = c['high'] - c['low']
    # VWAP proxy (rolling 60-bar mean)
    c['vwap'] = c['close'].rolling(60).mean()
    # EMA 9, 50 (for indices)
    if 'ema9' not in c.columns:
        c['ema9'] = c['close'].ewm(span=9, adjust=False).mean()
    if 'ema50' not in c.columns:
        c['ema50'] = c['close'].ewm(span=50, adjust=False).mean()
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

    # ALL_ADX_FAST: ADX fast DI cross + EMA21 filter
    if 'ALL_ADX_FAST' not in trig and 'adx_f' in row.index and pd.notna(row.get('adx_f')) and pd.notna(row.get('ema21')):
        if row['adx_f'] > 25 and row['pdi_f'] > row['mdi_f'] and row['close'] > row['ema21'] and not (prev['pdi_f'] > prev['mdi_f']):
            add('ALL_ADX_FAST','long',row['close']); trig['ALL_ADX_FAST']=True
        elif row['adx_f'] > 25 and row['mdi_f'] > row['pdi_f'] and row['close'] < row['ema21'] and not (prev['mdi_f'] > prev['pdi_f']):
            add('ALL_ADX_FAST','short',row['close']); trig['ALL_ADX_FAST']=True

    # TOK_WILLR: Williams %R Tokyo reversal
    if 0.0 <= hour < 6.0 and 'TOK_WILLR' not in trig and 'wr14' in row.index and pd.notna(row.get('wr14')):
        if prev['wr14'] < -80 and row['wr14'] >= -80:
            add('TOK_WILLR','long',row['close']); trig['TOK_WILLR']=True
        elif prev['wr14'] > -20 and row['wr14'] <= -20:
            add('TOK_WILLR','short',row['close']); trig['TOK_WILLR']=True

    # ── NEW STRATS ──

    # ALL_ENGULF: Bullish/bearish engulfing
    if 'ALL_ENGULF' not in trig and ci >= 1:
        pb = prev['body'] if 'body' in prev.index else prev['close'] - prev['open']
        cb = row['close'] - row['open']
        if pb < 0 and cb > 0 and row['close'] > prev['open'] and row['open'] < prev['close'] and abs(cb) >= 0.3*atr:
            add('ALL_ENGULF','long',row['close']); trig['ALL_ENGULF']=True
        elif pb > 0 and cb < 0 and row['close'] < prev['open'] and row['open'] > prev['close'] and abs(cb) >= 0.3*atr:
            add('ALL_ENGULF','short',row['close']); trig['ALL_ENGULF']=True

    # ALL_HAMMER: Hammer (long lower wick) / Shooting star (long upper wick)
    if 'ALL_HAMMER' not in trig and 'candle_range' in row.index:
        rng = row['candle_range']
        if rng >= 0.3*atr:
            lw = row['lower_wick']; uw = row['upper_wick']; ab = abs(row['close'] - row['open'])
            # Hammer: lower wick > 2x body, small upper wick, after down move
            if lw >= 2*ab and uw < 0.3*rng and ci >= 5:
                last5 = candles.iloc[ci-5:ci]
                if last5.iloc[-1]['close'] < last5.iloc[0]['open']:
                    add('ALL_HAMMER','long',row['close']); trig['ALL_HAMMER']=True
            # Shooting star: upper wick > 2x body, small lower wick, after up move
            elif uw >= 2*ab and lw < 0.3*rng and ci >= 5:
                last5 = candles.iloc[ci-5:ci]
                if last5.iloc[-1]['close'] > last5.iloc[0]['open']:
                    add('ALL_HAMMER','short',row['close']); trig['ALL_HAMMER']=True

    # ALL_DOJI_REV: Doji (tiny body) after trend → reversal
    if 'ALL_DOJI_REV' not in trig and ci >= 5:
        rng = row['high'] - row['low']
        ab = abs(row['close'] - row['open'])
        if rng >= 0.2*atr and ab < 0.1*rng:  # doji: body < 10% of range
            last5 = candles.iloc[ci-5:ci]
            move = last5.iloc[-1]['close'] - last5.iloc[0]['open']
            if move > 0.5*atr:  # was going up → reverse short
                add('ALL_DOJI_REV','short',row['close']); trig['ALL_DOJI_REV']=True
            elif move < -0.5*atr:  # was going down → reverse long
                add('ALL_DOJI_REV','long',row['close']); trig['ALL_DOJI_REV']=True

    # ALL_MSTAR: Morning star (3-bar bullish reversal) / Evening star (bearish)
    if 'ALL_MSTAR' not in trig and ci >= 3:
        b1 = candles.iloc[ci-2]; b2 = candles.iloc[ci-1]; b3 = row
        b1b = b1['close'] - b1['open']; b2b = b2['close'] - b2['open']; b3b = b3['close'] - b3['open']
        b2_range = b2['high'] - b2['low']
        # Morning star: big bear, small body (star), big bull
        if (b1b < -0.3*atr and abs(b2b) < 0.15*atr and b2_range < 0.5*atr
            and b3b > 0.3*atr and b3['close'] > (b1['open']+b1['close'])/2):
            add('ALL_MSTAR','long',row['close']); trig['ALL_MSTAR']=True
        # Evening star: big bull, small body (star), big bear
        elif (b1b > 0.3*atr and abs(b2b) < 0.15*atr and b2_range < 0.5*atr
              and b3b < -0.3*atr and b3['close'] < (b1['open']+b1['close'])/2):
            add('ALL_MSTAR','short',row['close']); trig['ALL_MSTAR']=True

    # LON_ASIAN_BRK: Asian range breakout at London open
    if 8.0 <= hour < 10.0 and 'LON_ASIAN_BRK' not in trig:
        asian = candles[(candles['ts_dt']>=ds)&(candles['ts_dt']<te)]
        if len(asian) >= 20:
            ah = asian['high'].max(); al_ = asian['low'].min()
            ar = ah - al_
            if ar >= 0.3*atr:  # meaningful range
                if row['close'] > ah and row['close'] > row['open']:
                    add('LON_ASIAN_BRK','long',row['close']); trig['LON_ASIAN_BRK']=True
                elif row['close'] < al_ and row['close'] < row['open']:
                    add('LON_ASIAN_BRK','short',row['close']); trig['LON_ASIAN_BRK']=True

    # ALL_INSIDE_BRK: Inside bar breakout (prev bar contains current)
    if 'ALL_INSIDE_BRK' not in trig and ci >= 2:
        p2 = candles.iloc[ci-1]
        # prev bar is inside bar (contained by bar before it)
        p3 = candles.iloc[ci-2]
        if p2['high'] < p3['high'] and p2['low'] > p3['low']:
            # current bar breaks out
            if row['close'] > p2['high'] and abs(row['close']-row['open']) >= 0.2*atr:
                add('ALL_INSIDE_BRK','long',row['close']); trig['ALL_INSIDE_BRK']=True
            elif row['close'] < p2['low'] and abs(row['close']-row['open']) >= 0.2*atr:
                add('ALL_INSIDE_BRK','short',row['close']); trig['ALL_INSIDE_BRK']=True

    # ALL_BB_SQUEEZE: Bollinger squeeze (width at 20-bar min) then breakout
    if 'ALL_BB_SQUEEZE' not in trig and 'bb_width' in row.index and pd.notna(row.get('bb_width_min20')):
        if prev.get('bb_width', 999) <= prev.get('bb_width_min20', 0) * 1.05:  # prev was squeezed
            if row['close'] > row.get('bb_up', 999):
                add('ALL_BB_SQUEEZE','long',row['close']); trig['ALL_BB_SQUEEZE']=True
            elif row['close'] < row.get('bb_lo', 0):
                add('ALL_BB_SQUEEZE','short',row['close']); trig['ALL_BB_SQUEEZE']=True

    # ALL_RSI_EXTREME: RSI < 25 reversal or > 75 reversal
    if 'ALL_RSI_EXTREME' not in trig and 'rsi14' in row.index and pd.notna(row.get('rsi14')):
        if prev['rsi14'] < 25 and row['rsi14'] >= 25 and row['close'] > row['open']:
            add('ALL_RSI_EXTREME','long',row['close']); trig['ALL_RSI_EXTREME']=True
        elif prev['rsi14'] > 75 and row['rsi14'] <= 75 and row['close'] < row['open']:
            add('ALL_RSI_EXTREME','short',row['close']); trig['ALL_RSI_EXTREME']=True

    # ALL_MACD_HIST: MACD histogram reversal (direction change)
    if 'ALL_MACD_HIST' not in trig and 'macd_hist' in row.index and pd.notna(row.get('macd_hist')) and ci >= 3:
        h1 = candles.iloc[ci-2].get('macd_hist', 0)
        h2 = prev.get('macd_hist', 0)
        h3 = row['macd_hist']
        if pd.notna(h1) and pd.notna(h2):
            # Histogram was declining, now rising → bullish
            if h1 > h2 and h2 < h3 and h3 < 0 and row['close'] > row['open']:
                add('ALL_MACD_HIST','long',row['close']); trig['ALL_MACD_HIST']=True
            # Histogram was rising, now declining → bearish
            elif h1 < h2 and h2 > h3 and h3 > 0 and row['close'] < row['open']:
                add('ALL_MACD_HIST','short',row['close']); trig['ALL_MACD_HIST']=True

    # ALL_VOL_SPIKE: Volume spike > 2x average with directional candle
    if 'ALL_VOL_SPIKE' not in trig and 'vol_avg' in row.index and pd.notna(row.get('vol_avg')):
        vol_col = 'tick_volume' if 'tick_volume' in row.index else 'volume' if 'volume' in row.index else None
        if vol_col and row.get(vol_col, 0) > 2 * row['vol_avg'] and row['vol_avg'] > 0:
            cb = row['close'] - row['open']
            if cb > 0 and abs(cb) >= 0.3*atr:
                add('ALL_VOL_SPIKE','long',row['close']); trig['ALL_VOL_SPIKE']=True
            elif cb < 0 and abs(cb) >= 0.3*atr:
                add('ALL_VOL_SPIKE','short',row['close']); trig['ALL_VOL_SPIKE']=True

    # TOK_NR4: Narrow range 4 during Tokyo session
    if 0.0 <= hour < 6.0 and 'TOK_NR4' not in trig and ci >= 5 and 'candle_range' in row.index:
        ranges = [candles.iloc[ci-j]['candle_range'] for j in range(4)]
        if row['candle_range'] == min(ranges) and row['candle_range'] > 0 and abs(row['body']) >= 0.1*atr:
            add('TOK_NR4','long' if row['body'] > 0 else 'short',row['close']); trig['TOK_NR4']=True

    # LON_DC10_MOM: Donchian 10 breakout + momentum during London
    if 8.0 <= hour < 14.5 and 'LON_DC10_MOM' not in trig and 'dc10_h' in row.index and pd.notna(prev.get('dc10_h')):
        mom = row['close'] / candles.iloc[ci-10]['close'] * 100 - 100 if ci >= 10 else 0
        if row['close'] > prev['dc10_h'] and mom > 0:
            add('LON_DC10_MOM','long',row['close']); trig['LON_DC10_MOM']=True
        elif row['close'] < prev['dc10_l'] and mom < 0:
            add('LON_DC10_MOM','short',row['close']); trig['LON_DC10_MOM']=True

    # ── INDEX / CRYPTO STRATS (US session: 14:30-21:00 UTC) ──
    ny_open = pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC')
    ny_candles = tv[tv['ts_dt']>=ny_open]

    # IDX_ORB15: Opening range breakout 15min
    if 14.75 <= hour < 21.0 and 'IDX_ORB15' not in trig and len(ny_candles) >= 3:
        orb = ny_candles.iloc[:3]
        orb_h = orb['high'].max(); orb_l = orb['low'].min()
        if row['close'] > orb_h and row['close'] > row['open'] and abs(row['body']) >= 0.2*atr:
            add('IDX_ORB15','long',row['close']); trig['IDX_ORB15']=True
        elif row['close'] < orb_l and row['close'] < row['open'] and abs(row['body']) >= 0.2*atr:
            add('IDX_ORB15','short',row['close']); trig['IDX_ORB15']=True

    # IDX_ORB30: Opening range breakout 30min
    if 15.0 <= hour < 21.0 and 'IDX_ORB30' not in trig and len(ny_candles) >= 6:
        orb = ny_candles.iloc[:6]
        orb_h = orb['high'].max(); orb_l = orb['low'].min()
        if row['close'] > orb_h and row['close'] > row['open'] and abs(row['body']) >= 0.2*atr:
            add('IDX_ORB30','long',row['close']); trig['IDX_ORB30']=True
        elif row['close'] < orb_l and row['close'] < row['open'] and abs(row['body']) >= 0.2*atr:
            add('IDX_ORB30','short',row['close']); trig['IDX_ORB30']=True

    # IDX_GAP_FILL: Overnight gap fade
    if 14.5 <= hour < 15.0 and 'IDX_GAP_FILL' not in trig and prev_day_data:
        gap = (row['close'] - prev_day_data['close']) / atr if atr > 0 else 0
        if gap >= 0.3: add('IDX_GAP_FILL','short',row['close']); trig['IDX_GAP_FILL']=True
        elif gap <= -0.3: add('IDX_GAP_FILL','long',row['close']); trig['IDX_GAP_FILL']=True

    # IDX_GAP_CONT: Big gap continuation
    if 14.5 <= hour < 15.0 and 'IDX_GAP_CONT' not in trig and prev_day_data:
        gap = (row['close'] - prev_day_data['close']) / atr if atr > 0 else 0
        if gap >= 1.0: add('IDX_GAP_CONT','long',row['close']); trig['IDX_GAP_CONT']=True
        elif gap <= -1.0: add('IDX_GAP_CONT','short',row['close']); trig['IDX_GAP_CONT']=True

    # IDX_NY_MOM: First hour NY momentum
    if 15.5 <= hour < 15.6 and 'IDX_NY_MOM' not in trig and len(ny_candles) >= 12:
        first_hour = ny_candles.iloc[:12]
        move = (first_hour.iloc[-1]['close'] - first_hour.iloc[0]['open']) / atr if atr > 0 else 0
        if abs(move) >= 0.5:
            add('IDX_NY_MOM','long' if move > 0 else 'short',row['close']); trig['IDX_NY_MOM']=True

    # IDX_LATE_REV: Late day reversal
    if 19.0 <= hour < 20.5 and 'IDX_LATE_REV' not in trig and len(ny_candles) >= 50:
        day_move = (ny_candles.iloc[-1]['close'] - ny_candles.iloc[0]['open']) / atr if atr > 0 else 0
        if day_move > 0.5 and row['close'] < row['open'] and abs(row['body']) >= 0.3*atr:
            add('IDX_LATE_REV','short',row['close']); trig['IDX_LATE_REV']=True
        elif day_move < -0.5 and row['close'] > row['open'] and abs(row['body']) >= 0.3*atr:
            add('IDX_LATE_REV','long',row['close']); trig['IDX_LATE_REV']=True

    # IDX_TREND_DAY: Initial balance breakout
    if 15.5 <= hour < 21.0 and 'IDX_TREND_DAY' not in trig and len(ny_candles) >= 12:
        ib = ny_candles.iloc[:12]
        ib_h = ib['high'].max(); ib_l = ib['low'].min()
        if ib_h - ib_l >= 0.3*atr:
            if row['close'] > ib_h and row['close'] > row['open']:
                add('IDX_TREND_DAY','long',row['close']); trig['IDX_TREND_DAY']=True
            elif row['close'] < ib_l and row['close'] < row['open']:
                add('IDX_TREND_DAY','short',row['close']); trig['IDX_TREND_DAY']=True

    # IDX_VWAP_BOUNCE
    if 14.5 <= hour < 21.0 and 'IDX_VWAP_BOUNCE' not in trig and 'vwap' in row.index and pd.notna(row.get('vwap')):
        vwap = row['vwap']
        if prev['low'] <= vwap and row['close'] > vwap and row['close'] > row['open'] and abs(row['body']) >= 0.2*atr:
            add('IDX_VWAP_BOUNCE','long',row['close']); trig['IDX_VWAP_BOUNCE']=True
        elif prev['high'] >= vwap and row['close'] < vwap and row['close'] < row['open'] and abs(row['body']) >= 0.2*atr:
            add('IDX_VWAP_BOUNCE','short',row['close']); trig['IDX_VWAP_BOUNCE']=True

    # IDX_BB_REV: Bollinger band reversal
    if 'IDX_BB_REV' not in trig and 'bb_up' in row.index and pd.notna(row.get('bb_up')):
        if prev['high'] >= prev.get('bb_up',99999) and row['close'] < row.get('bb_up',99999) and row['close'] < row['open']:
            add('IDX_BB_REV','short',row['close']); trig['IDX_BB_REV']=True
        elif prev['low'] <= prev.get('bb_lo',0) and row['close'] > row.get('bb_lo',0) and row['close'] > row['open']:
            add('IDX_BB_REV','long',row['close']); trig['IDX_BB_REV']=True

    # IDX_RSI_REV
    if 'IDX_RSI_REV' not in trig and 'rsi14' in row.index and pd.notna(row.get('rsi14')):
        if prev['rsi14'] < 25 and row['rsi14'] >= 25 and row['close'] > row['open']:
            add('IDX_RSI_REV','long',row['close']); trig['IDX_RSI_REV']=True
        elif prev['rsi14'] > 75 and row['rsi14'] <= 75 and row['close'] < row['open']:
            add('IDX_RSI_REV','short',row['close']); trig['IDX_RSI_REV']=True

    # IDX_PREV_HL: Previous day high/low breakout
    if 14.5 <= hour < 21.0 and 'IDX_PREV_HL' not in trig and prev_day_data:
        if row['close'] > prev_day_data['high'] and row['close'] > row['open'] and abs(row['body']) >= 0.2*atr:
            add('IDX_PREV_HL','long',row['close']); trig['IDX_PREV_HL']=True
        elif row['close'] < prev_day_data['low'] and row['close'] < row['open'] and abs(row['body']) >= 0.2*atr:
            add('IDX_PREV_HL','short',row['close']); trig['IDX_PREV_HL']=True

    # IDX_NR4
    if 'IDX_NR4' not in trig and ci >= 5 and 'candle_range' in row.index:
        ranges = [candles.iloc[ci-j]['candle_range'] for j in range(4)]
        if row['candle_range'] == min(ranges) and row['candle_range'] > 0 and abs(row['body']) >= 0.1*atr:
            add('IDX_NR4','long' if row['body'] > 0 else 'short',row['close']); trig['IDX_NR4']=True

    # IDX_KC_BRK
    if 'IDX_KC_BRK' not in trig and 'kc_up' in row.index and pd.notna(row.get('kc_up')):
        if row['close'] > row['kc_up'] and prev['close'] <= prev.get('kc_up',99999):
            add('IDX_KC_BRK','long',row['close']); trig['IDX_KC_BRK']=True
        elif row['close'] < row['kc_lo'] and prev['close'] >= prev.get('kc_lo',0):
            add('IDX_KC_BRK','short',row['close']); trig['IDX_KC_BRK']=True

    # IDX_ENGULF
    if 'IDX_ENGULF' not in trig:
        pb = prev['close'] - prev['open']; cb = row['close'] - row['open']
        if pb < 0 and cb > 0 and row['close'] > prev['open'] and row['open'] < prev['close'] and abs(cb) >= 0.3*atr:
            add('IDX_ENGULF','long',row['close']); trig['IDX_ENGULF']=True
        elif pb > 0 and cb < 0 and row['close'] < prev['open'] and row['open'] > prev['close'] and abs(cb) >= 0.3*atr:
            add('IDX_ENGULF','short',row['close']); trig['IDX_ENGULF']=True

    # IDX_3SOLDIERS
    if 'IDX_3SOLDIERS' not in trig and ci >= 3:
        b1 = candles.iloc[ci-2]; b2 = candles.iloc[ci-1]; b3 = row
        if (b1['close']>b1['open'] and b2['close']>b2['open'] and b3['close']>b3['open'] and
            b2['close']>b1['close'] and b3['close']>b2['close'] and
            min(abs(b1['close']-b1['open']),abs(b2['close']-b2['open']),abs(b3['close']-b3['open']))>=0.2*atr):
            add('IDX_3SOLDIERS','long',row['close']); trig['IDX_3SOLDIERS']=True
        elif (b1['close']<b1['open'] and b2['close']<b2['open'] and b3['close']<b3['open'] and
              b2['close']<b1['close'] and b3['close']<b2['close'] and
              min(abs(b1['close']-b1['open']),abs(b2['close']-b2['open']),abs(b3['close']-b3['open']))>=0.2*atr):
            add('IDX_3SOLDIERS','short',row['close']); trig['IDX_3SOLDIERS']=True

    # IDX_CONSEC_REV
    if 'IDX_CONSEC_REV' not in trig and ci >= 6:
        last5 = candles.iloc[ci-5:ci]
        all_bull = all(last5.iloc[j]['close'] > last5.iloc[j]['open'] for j in range(5))
        all_bear = all(last5.iloc[j]['close'] < last5.iloc[j]['open'] for j in range(5))
        total_rng = last5['high'].max() - last5['low'].min()
        if all_bull and total_rng >= 1.0*atr and row['close'] < row['open'] and abs(row['body']) >= 0.2*atr:
            add('IDX_CONSEC_REV','short',row['close']); trig['IDX_CONSEC_REV']=True
        elif all_bear and total_rng >= 1.0*atr and row['close'] > row['open'] and abs(row['body']) >= 0.2*atr:
            add('IDX_CONSEC_REV','long',row['close']); trig['IDX_CONSEC_REV']=True
