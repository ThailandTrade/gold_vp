"""
Strategies pour indices (NAS100, SP500, DAX, etc.)
Sessions US-centric: Pre-market, NY open, NY close.
Toutes basees sur bougies 5min fermees.
"""
import pandas as pd
import numpy as np

ALL_STRATS_IDX = [
    # Opening / Gap
    'IDX_ORB15',        # Opening range breakout (first 15min)
    'IDX_ORB30',        # Opening range breakout (first 30min)
    'IDX_GAP_FILL',     # Overnight gap fill trade
    'IDX_GAP_CONT',     # Gap continuation (big gap same direction)
    # Momentum
    'IDX_NY_MOM',       # First hour NY momentum continuation
    'IDX_LATE_REV',     # Late day reversal (after 19:00 UTC)
    'IDX_TREND_DAY',    # Trend day detection (IB breakout)
    # Mean reversion
    'IDX_VWAP_BOUNCE',  # VWAP mean reversion bounce
    'IDX_BB_REV',       # Bollinger band reversal (touch + reject)
    'IDX_RSI_REV',      # RSI extreme reversal
    # Breakout
    'IDX_PREV_HL',      # Previous day high/low breakout
    'IDX_NR4',          # Narrow range 4 breakout
    'IDX_KC_BRK',       # Keltner channel breakout
    # Pattern
    'IDX_ENGULF',       # Engulfing pattern
    'IDX_3SOLDIERS',    # Three soldiers/crows
    'IDX_CONSEC_REV',   # Consecutive candles exhaustion reversal
]

STRAT_NAMES_IDX = {
    'IDX_ORB15': 'Opening range breakout 15min',
    'IDX_ORB30': 'Opening range breakout 30min',
    'IDX_GAP_FILL': 'Overnight gap fill',
    'IDX_GAP_CONT': 'Gap continuation',
    'IDX_NY_MOM': 'NY first hour momentum',
    'IDX_LATE_REV': 'Late day reversal',
    'IDX_TREND_DAY': 'Trend day (IB breakout)',
    'IDX_VWAP_BOUNCE': 'VWAP mean reversion',
    'IDX_BB_REV': 'Bollinger band reversal',
    'IDX_RSI_REV': 'RSI extreme reversal',
    'IDX_PREV_HL': 'Previous day H/L breakout',
    'IDX_NR4': 'Narrow range 4 breakout',
    'IDX_KC_BRK': 'Keltner channel breakout',
    'IDX_ENGULF': 'Engulfing pattern',
    'IDX_3SOLDIERS': 'Three soldiers/crows',
    'IDX_CONSEC_REV': 'Consecutive exhaustion reversal',
}

STRAT_SESSION_IDX = {s: 'US' for s in ALL_STRATS_IDX}
STRAT_SESSION_IDX['IDX_LATE_REV'] = 'US Late'

# US session times (UTC): NY open 14:30, NY close 21:00
# Pre-market: ~12:00-14:30 UTC (futures)
# Regular hours: 14:30-21:00 UTC

def compute_indicators_idx(candles):
    """Indicateurs pour indices."""
    c = candles
    # Body
    c['body'] = c['close'] - c['open']
    c['abs_body'] = c['body'].abs()
    c['candle_range'] = c['high'] - c['low']
    # EMA
    c['ema9'] = c['close'].ewm(span=9, adjust=False).mean()
    c['ema20'] = c['close'].ewm(span=20, adjust=False).mean()
    c['ema50'] = c['close'].ewm(span=50, adjust=False).mean()
    # ATR 14
    tr = np.maximum(c['high']-c['low'], np.maximum(abs(c['high']-c['close'].shift(1)), abs(c['low']-c['close'].shift(1))))
    c['atr14'] = tr.ewm(span=14, adjust=False).mean()
    # RSI 14
    delta = c['close'].diff()
    gain = delta.clip(lower=0); loss = (-delta).clip(lower=0)
    ag = gain.ewm(alpha=1.0/14, min_periods=14, adjust=False).mean()
    al = loss.ewm(alpha=1.0/14, min_periods=14, adjust=False).mean()
    c['rsi14'] = 100 - 100/(1+ag/(al+1e-10))
    # MACD (12,26,9)
    ef = c['close'].ewm(span=12, adjust=False).mean()
    es = c['close'].ewm(span=26, adjust=False).mean()
    c['macd'] = ef - es
    c['macd_sig'] = c['macd'].ewm(span=9, adjust=False).mean()
    c['macd_hist'] = c['macd'] - c['macd_sig']
    # Bollinger Bands 20,2
    c['bb_mid'] = c['close'].rolling(20).mean()
    c['bb_std'] = c['close'].rolling(20).std()
    c['bb_up'] = c['bb_mid'] + 2.0 * c['bb_std']
    c['bb_lo'] = c['bb_mid'] - 2.0 * c['bb_std']
    # Keltner Channels
    c['kc_up'] = c['ema20'] + 1.5 * c['atr14']
    c['kc_lo'] = c['ema20'] - 1.5 * c['atr14']
    # Donchian 10
    c['dc10_h'] = c['high'].rolling(10).max()
    c['dc10_l'] = c['low'].rolling(10).min()
    # VWAP proxy (cumulative on day — reset daily)
    # We approximate with rolling 60-bar (5h) mean weighted by range
    c['vwap'] = c['close'].rolling(60).mean()
    # Wicks
    c['upper_wick'] = c['high'] - c[['open','close']].max(axis=1)
    c['lower_wick'] = c[['open','close']].min(axis=1) - c['low']
    return c


def detect_all_idx(candles, ci, row, ct, today, hour, atr, trig, tv, prev_day_data, add):
    """Detecte les signaux pour toutes les strats indices."""
    if ci < 10: return
    prev = candles.iloc[ci-1]

    # Session boundaries (UTC)
    ds = pd.Timestamp(today.year,today.month,today.day,0,0,tz='UTC')
    ny_open = pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC')
    ny_close = pd.Timestamp(today.year,today.month,today.day,21,0,tz='UTC')

    # Pre-NY candles for ORB / gap
    pre_ny = candles[(candles['ts_dt']>=ds)&(candles['ts_dt']<ny_open)]
    ny_candles = candles[(candles['ts_dt']>=ny_open)&(candles['ts_dt']<=ct)]

    # ── OPENING RANGE BREAKOUT 15min ──
    if 14.75 <= hour < 21.0 and 'IDX_ORB15' not in trig and len(ny_candles) >= 3:
        orb = ny_candles.iloc[:3]  # first 15min (3 x 5min candles)
        orb_h = orb['high'].max(); orb_l = orb['low'].min()
        if row['close'] > orb_h and row['close'] > row['open'] and abs(row['body']) >= 0.2*atr:
            add('IDX_ORB15','long',row['close']); trig['IDX_ORB15']=True
        elif row['close'] < orb_l and row['close'] < row['open'] and abs(row['body']) >= 0.2*atr:
            add('IDX_ORB15','short',row['close']); trig['IDX_ORB15']=True

    # ── OPENING RANGE BREAKOUT 30min ──
    if 15.0 <= hour < 21.0 and 'IDX_ORB30' not in trig and len(ny_candles) >= 6:
        orb = ny_candles.iloc[:6]  # first 30min
        orb_h = orb['high'].max(); orb_l = orb['low'].min()
        if row['close'] > orb_h and row['close'] > row['open'] and abs(row['body']) >= 0.2*atr:
            add('IDX_ORB30','long',row['close']); trig['IDX_ORB30']=True
        elif row['close'] < orb_l and row['close'] < row['open'] and abs(row['body']) >= 0.2*atr:
            add('IDX_ORB30','short',row['close']); trig['IDX_ORB30']=True

    # ── GAP FILL ──
    if 14.5 <= hour < 15.0 and 'IDX_GAP_FILL' not in trig and prev_day_data:
        prev_close = prev_day_data['close']
        gap = (row['close'] - prev_close) / atr if atr > 0 else 0
        # Gap up → fade short (expecting fill)
        if gap >= 0.3:
            add('IDX_GAP_FILL','short',row['close']); trig['IDX_GAP_FILL']=True
        elif gap <= -0.3:
            add('IDX_GAP_FILL','long',row['close']); trig['IDX_GAP_FILL']=True

    # ── GAP CONTINUATION ──
    if 14.5 <= hour < 15.0 and 'IDX_GAP_CONT' not in trig and prev_day_data:
        prev_close = prev_day_data['close']
        gap = (row['close'] - prev_close) / atr if atr > 0 else 0
        # Big gap → continuation
        if gap >= 1.0:
            add('IDX_GAP_CONT','long',row['close']); trig['IDX_GAP_CONT']=True
        elif gap <= -1.0:
            add('IDX_GAP_CONT','short',row['close']); trig['IDX_GAP_CONT']=True

    # ── NY FIRST HOUR MOMENTUM ──
    if 15.5 <= hour < 15.6 and 'IDX_NY_MOM' not in trig and len(ny_candles) >= 12:
        first_hour = ny_candles.iloc[:12]
        move = (first_hour.iloc[-1]['close'] - first_hour.iloc[0]['open']) / atr if atr > 0 else 0
        if abs(move) >= 0.5:
            add('IDX_NY_MOM','long' if move > 0 else 'short',row['close']); trig['IDX_NY_MOM']=True

    # ── LATE DAY REVERSAL ──
    if 19.0 <= hour < 20.5 and 'IDX_LATE_REV' not in trig and len(ny_candles) >= 50:
        day_move = (ny_candles.iloc[-1]['close'] - ny_candles.iloc[0]['open']) / atr if atr > 0 else 0
        if day_move > 0.5 and row['close'] < row['open'] and abs(row['body']) >= 0.3*atr:
            add('IDX_LATE_REV','short',row['close']); trig['IDX_LATE_REV']=True
        elif day_move < -0.5 and row['close'] > row['open'] and abs(row['body']) >= 0.3*atr:
            add('IDX_LATE_REV','long',row['close']); trig['IDX_LATE_REV']=True

    # ── TREND DAY (Initial Balance breakout) ──
    if 15.5 <= hour < 21.0 and 'IDX_TREND_DAY' not in trig and len(ny_candles) >= 12:
        ib = ny_candles.iloc[:12]  # first hour = initial balance
        ib_h = ib['high'].max(); ib_l = ib['low'].min()
        ib_range = ib_h - ib_l
        if ib_range >= 0.3*atr:
            if row['close'] > ib_h and row['close'] > row['open']:
                add('IDX_TREND_DAY','long',row['close']); trig['IDX_TREND_DAY']=True
            elif row['close'] < ib_l and row['close'] < row['open']:
                add('IDX_TREND_DAY','short',row['close']); trig['IDX_TREND_DAY']=True

    # ── VWAP BOUNCE ──
    if 14.5 <= hour < 21.0 and 'IDX_VWAP_BOUNCE' not in trig and 'vwap' in row.index and pd.notna(row.get('vwap')):
        vwap = row['vwap']
        # Price touches VWAP from above and bounces
        if prev['low'] <= vwap and row['close'] > vwap and row['close'] > row['open'] and abs(row['body']) >= 0.2*atr:
            add('IDX_VWAP_BOUNCE','long',row['close']); trig['IDX_VWAP_BOUNCE']=True
        elif prev['high'] >= vwap and row['close'] < vwap and row['close'] < row['open'] and abs(row['body']) >= 0.2*atr:
            add('IDX_VWAP_BOUNCE','short',row['close']); trig['IDX_VWAP_BOUNCE']=True

    # ── BOLLINGER BAND REVERSAL ──
    if 'IDX_BB_REV' not in trig and 'bb_up' in row.index and pd.notna(row.get('bb_up')):
        if prev['high'] >= prev.get('bb_up',99999) and row['close'] < row.get('bb_up',99999) and row['close'] < row['open']:
            add('IDX_BB_REV','short',row['close']); trig['IDX_BB_REV']=True
        elif prev['low'] <= prev.get('bb_lo',0) and row['close'] > row.get('bb_lo',0) and row['close'] > row['open']:
            add('IDX_BB_REV','long',row['close']); trig['IDX_BB_REV']=True

    # ── RSI EXTREME REVERSAL ──
    if 'IDX_RSI_REV' not in trig and 'rsi14' in row.index and pd.notna(row.get('rsi14')):
        if prev['rsi14'] < 25 and row['rsi14'] >= 25 and row['close'] > row['open']:
            add('IDX_RSI_REV','long',row['close']); trig['IDX_RSI_REV']=True
        elif prev['rsi14'] > 75 and row['rsi14'] <= 75 and row['close'] < row['open']:
            add('IDX_RSI_REV','short',row['close']); trig['IDX_RSI_REV']=True

    # ── PREVIOUS DAY HIGH/LOW BREAKOUT ──
    if 14.5 <= hour < 21.0 and 'IDX_PREV_HL' not in trig and prev_day_data:
        if row['close'] > prev_day_data['high'] and row['close'] > row['open'] and abs(row['body']) >= 0.2*atr:
            add('IDX_PREV_HL','long',row['close']); trig['IDX_PREV_HL']=True
        elif row['close'] < prev_day_data['low'] and row['close'] < row['open'] and abs(row['body']) >= 0.2*atr:
            add('IDX_PREV_HL','short',row['close']); trig['IDX_PREV_HL']=True

    # ── NR4 (Narrow Range 4) ──
    if 'IDX_NR4' not in trig and ci >= 5:
        ranges = [candles.iloc[ci-j]['candle_range'] for j in range(4)]
        if row['candle_range'] == min(ranges) and row['candle_range'] > 0 and abs(row['body']) >= 0.1*atr:
            add('IDX_NR4','long' if row['body'] > 0 else 'short',row['close']); trig['IDX_NR4']=True

    # ── KELTNER CHANNEL BREAKOUT ──
    if 'IDX_KC_BRK' not in trig and 'kc_up' in row.index and pd.notna(row.get('kc_up')):
        if row['close'] > row['kc_up'] and prev['close'] <= prev.get('kc_up', 99999):
            add('IDX_KC_BRK','long',row['close']); trig['IDX_KC_BRK']=True
        elif row['close'] < row['kc_lo'] and prev['close'] >= prev.get('kc_lo', 0):
            add('IDX_KC_BRK','short',row['close']); trig['IDX_KC_BRK']=True

    # ── ENGULFING ──
    if 'IDX_ENGULF' not in trig:
        pb = prev['close'] - prev['open']
        cb = row['close'] - row['open']
        if pb < 0 and cb > 0 and row['close'] > prev['open'] and row['open'] < prev['close'] and abs(cb) >= 0.3*atr:
            add('IDX_ENGULF','long',row['close']); trig['IDX_ENGULF']=True
        elif pb > 0 and cb < 0 and row['close'] < prev['open'] and row['open'] > prev['close'] and abs(cb) >= 0.3*atr:
            add('IDX_ENGULF','short',row['close']); trig['IDX_ENGULF']=True

    # ── THREE SOLDIERS / CROWS ──
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

    # ── CONSECUTIVE REVERSAL ──
    if 'IDX_CONSEC_REV' not in trig and ci >= 6:
        last5 = candles.iloc[ci-5:ci]
        all_bull = all(last5.iloc[j]['close'] > last5.iloc[j]['open'] for j in range(5))
        all_bear = all(last5.iloc[j]['close'] < last5.iloc[j]['open'] for j in range(5))
        total_rng = last5['high'].max() - last5['low'].min()
        if all_bull and total_rng >= 1.0*atr and row['close'] < row['open'] and abs(row['body']) >= 0.2*atr:
            add('IDX_CONSEC_REV','short',row['close']); trig['IDX_CONSEC_REV']=True
        elif all_bear and total_rng >= 1.0*atr and row['close'] > row['open'] and abs(row['body']) >= 0.2*atr:
            add('IDX_CONSEC_REV','long',row['close']); trig['IDX_CONSEC_REV']=True
