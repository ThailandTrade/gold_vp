"""
Strategies swing 4h — arsenal refondu (reflexion.md 2026-05-19).
Chaque strat a une these economique claire (trend / breakout / pullback / reversal / pattern).

Categories:
- A: Trend following (10) — A1..A10
- B: Breakout structurel (8) — B1..B8
- C: Pullback en tendance (5) — C1..C5
- D: Reversal sur niveau majeur (5) — D1..D5
- F: Patterns swing (4) — F1..F4

Total: 32 detecteurs single-instrument. Les categories E (cross-sectional, meta)
et G (overlays regime) sont implementees separement car elles operent au niveau portfolio,
pas au niveau (sym, bar).
"""
import numpy as np
import pandas as pd


STRAT_NAMES_SWING = {
    # A — Trend following
    'A1_DC20_BRK':       'Donchian 20-bar high/low breakout (5 jours 4h)',
    'A2_DC55_BRK':       'Donchian 55-bar high/low breakout (Turtle 14 jours)',
    'A3_EMA20_50_ADX':   'EMA 20/50 cross + ADX > 25 confirmation',
    'A4_EMA50_200_RT':   'Golden/Death cross EMA 50/200 + retest',
    'A5_TSMOM_3M':       'Time-series momentum signe(close - close_60_4h)',
    'A6_TSMOM_6M':       'Time-series momentum signe(close - close_120_4h)',
    'A7_MULTI_SPEED':    'Multi-speed trend TSMOM 1M+3M+6M pondere',
    'A8_TRIPLE_MA':      'Triple MA alignment EMA 8/21/55',
    'A9_LR_SLOPE_50':    'Linear regression slope 50-bar reversal',
    'A10_KAMA':          'Kaufman adaptive MA cross',
    # B — Breakout structurel
    'B1_WEEKLY_HL':      'Weekly high/low breakout',
    'B2_MONTHLY_HL':     'Monthly high/low breakout',
    'B3_NDAY_CONSO':     'N-day consolidation (range < 1 ATR) breakout',
    'B4_TRIANGLE':       'Triangle/wedge breakout (highs desc + lows asc)',
    'B5_BB_SQUEEZE_50':  'Bollinger 50-period squeeze (BB width 25p pct) breakout',
    'B6_KC_BRK_50':      'Keltner Channel 50/2 ATR breakout',
    'B7_FAILED_BRK':     'Failed breakout reversal (cassure + retour brutal)',
    'B8_ASIAN_RANGE':    'Asian session (12-16h UTC) range break in London/NY',
    # C — Pullback
    'C1_PULLBACK_EMA20': 'Pullback to EMA 20 in trend (EMA50>EMA200)',
    'C2_FIB_RETRACE':    'Fib 38/50/61 retracement entry',
    'C3_3BAR_PULLBACK':  '3-bar counter-trend pullback in ADX>30',
    'C4_RS_RETEST':      'Previous resistance->support (or inverse) retest',
    'C5_AVWAP_RECLAIM':  'Anchored VWAP (daily) reclaim',
    # D — Reversal sur niveau
    'D1_DOUBLE_TB':      'Double top/bottom (20+ bars)',
    'D2_TRIPLE_TB':      'Triple top/bottom',
    'D3_ENGULF_WHL':     'Engulfing au touch weekly H/L',
    'D4_PIN_LEVEL':      'Pin bar/hammer/SS sur niveau majeur (EMA200/Fib/RS)',
    'D5_RSI_DIV_LVL':    'RSI divergence + niveau majeur (R/S, BB extreme)',
    # F — Patterns swing
    'F1_FLAG_BRK':       'Flag/pennant breakout (impulse + consolidation)',
    'F2_CUP_HANDLE':     'Cup & Handle pattern',
    'F3_HEAD_SHOULDERS': 'Head & Shoulders / inverse H&S',
    'F4_SYM_TRIANGLE':   'Symmetrical triangle (convergence + breakout)',
}


# ═══════════════════════════════════════════════════════════════════════
#  INDICATORS — precalcul des indicateurs pour les strats swing
# ═══════════════════════════════════════════════════════════════════════
def compute_indicators_swing(c):
    """Precalcule les indicateurs swing 4h. Modifie c in place + retourne c."""
    # EMAs
    for p in [8, 13, 20, 21, 50, 55, 100, 200]:
        k = f'ema{p}'
        if k not in c.columns:
            c[k] = c['close'].ewm(span=p, adjust=False).mean()

    # ATR 14
    tr = np.maximum(c['high']-c['low'],
                    np.maximum(abs(c['high']-c['close'].shift(1)),
                               abs(c['low']-c['close'].shift(1))))
    if 'atr14' not in c.columns:
        c['atr14'] = tr.ewm(span=14, adjust=False).mean()

    # Donchian 10, 20, 55
    for p in [10, 20, 55]:
        c[f'dc{p}_h'] = c['high'].rolling(p).max()
        c[f'dc{p}_l'] = c['low'].rolling(p).min()

    # ADX (Wilder smoothed) 14
    if 'adx14' not in c.columns:
        pdm = c['high'].diff().clip(lower=0)
        mdm = (-c['low'].diff()).clip(lower=0)
        mask = pdm > mdm
        pdm2 = pdm.where(mask, 0); mdm2 = mdm.where(~mask, 0)
        atr_w = tr.ewm(alpha=1/14, adjust=False).mean()
        pdi = 100 * pdm2.ewm(alpha=1/14, adjust=False).mean() / (atr_w + 1e-10)
        mdi = 100 * mdm2.ewm(alpha=1/14, adjust=False).mean() / (atr_w + 1e-10)
        dx = 100 * abs(pdi - mdi) / (pdi + mdi + 1e-10)
        c['adx14'] = dx.ewm(alpha=1/14, adjust=False).mean()
        c['pdi14'] = pdi
        c['mdi14'] = mdi

    # RSI 14
    if 'rsi14' not in c.columns:
        d = c['close'].diff()
        gain = d.clip(lower=0); loss = (-d).clip(lower=0)
        ag = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
        al = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
        c['rsi14'] = 100 - 100/(1+ag/(al+1e-10))

    # Returns lookback (TSMOM)
    for n in [30, 60, 120]:
        c[f'ret_{n}'] = c['close'] / c['close'].shift(n) - 1

    # Linear regression slope 50
    if 'lr_slope_50' not in c.columns:
        def _lrs(x):
            n = len(x); xs = np.arange(n)
            denom = n*(xs**2).sum() - xs.sum()**2
            return (n*np.dot(xs,x) - xs.sum()*x.sum())/(denom+1e-10) if denom else 0
        c['lr_slope_50'] = c['close'].rolling(50).apply(_lrs, raw=True)

    # Bollinger 50 (squeeze)
    if 'bb50_width' not in c.columns:
        m = c['close'].rolling(50).mean()
        s = c['close'].rolling(50).std()
        c['bb50_up'] = m + 2*s
        c['bb50_lo'] = m - 2*s
        c['bb50_width'] = (c['bb50_up'] - c['bb50_lo']) / (m + 1e-10)
        c['bb50_width_q25'] = c['bb50_width'].rolling(200).quantile(0.25)

    # Keltner 50 (2 ATR)
    if 'kc50_up' not in c.columns:
        c['kc50_mid'] = c['close'].ewm(span=50, adjust=False).mean()
        c['kc50_up'] = c['kc50_mid'] + 2 * c['atr14']
        c['kc50_lo'] = c['kc50_mid'] - 2 * c['atr14']

    # KAMA (Kaufman Adaptive MA, period 10, fast 2, slow 30)
    if 'kama' not in c.columns:
        n_kama = 10
        change = abs(c['close'] - c['close'].shift(n_kama))
        vol = c['close'].diff().abs().rolling(n_kama).sum()
        er = change / (vol + 1e-10)
        fast_sc = 2/(2+1); slow_sc = 2/(30+1)
        sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2
        kama = pd.Series(index=c.index, dtype=float)
        kama.iloc[n_kama] = c['close'].iloc[n_kama]
        for i in range(n_kama+1, len(c)):
            prev = kama.iloc[i-1]
            kama.iloc[i] = prev + sc.iloc[i] * (c['close'].iloc[i] - prev) if not pd.isna(prev) else c['close'].iloc[i]
        c['kama'] = kama

    # Wicks
    if 'upper_wick' not in c.columns:
        c['upper_wick'] = c['high'] - c[['open','close']].max(axis=1)
        c['lower_wick'] = c[['open','close']].min(axis=1) - c['low']
        c['body_abs'] = (c['close'] - c['open']).abs()
        c['candle_range'] = c['high'] - c['low']

    # Anchored VWAP daily (reset chaque jour UTC)
    if 'avwap_daily' not in c.columns and 'date' in c.columns:
        pv = (c['close'] * c.get('volume', 1.0).fillna(1.0)) if 'volume' in c.columns else c['close']
        vol = c.get('volume', pd.Series(1.0, index=c.index)).fillna(1.0)
        # Reset cum chaque jour
        cum_pv = pv.groupby(c['date']).cumsum()
        cum_v = vol.groupby(c['date']).cumsum()
        c['avwap_daily'] = cum_pv / (cum_v + 1e-10)

    # Weekly H/L (rolling 30 bars 4h ≈ 5 jours)
    if 'wk_h' not in c.columns:
        c['wk_h'] = c['high'].rolling(30).max().shift(1)
        c['wk_l'] = c['low'].rolling(30).min().shift(1)

    # Monthly H/L (rolling 120 bars 4h ≈ 20 jours)
    if 'mo_h' not in c.columns:
        c['mo_h'] = c['high'].rolling(120).max().shift(1)
        c['mo_l'] = c['low'].rolling(120).min().shift(1)

    return c


# ═══════════════════════════════════════════════════════════════════════
#  DETECTORS — chaque fonction emet via add(sn, dir, entry_price)
# ═══════════════════════════════════════════════════════════════════════

def _safe(v):
    return v is not None and not (isinstance(v, float) and (np.isnan(v) or np.isinf(v)))


def detect_swing(candles, ci, add):
    """Dispatcher: detecte tous les signaux des 32 strats sur la bar ci.
    add(sn, dir, entry_price) avec dir='long' ou 'short'."""
    if ci < 200:
        return
    r = candles.iloc[ci]
    rp = candles.iloc[ci-1]
    c = candles
    close = r['close']

    # ── A1: Donchian 20-bar breakout ────────────────────────
    if _safe(rp.get('dc20_h')) and _safe(rp.get('dc20_l')):
        if close > rp['dc20_h']:
            add('A1_DC20_BRK', 'long', close)
        elif close < rp['dc20_l']:
            add('A1_DC20_BRK', 'short', close)

    # ── A2: Donchian 55-bar breakout (Turtle) ───────────────
    if _safe(rp.get('dc55_h')) and _safe(rp.get('dc55_l')):
        if close > rp['dc55_h']:
            add('A2_DC55_BRK', 'long', close)
        elif close < rp['dc55_l']:
            add('A2_DC55_BRK', 'short', close)

    # ── A3: EMA 20/50 cross + ADX>25 ────────────────────────
    if _safe(r.get('ema20')) and _safe(r.get('ema50')) and _safe(rp.get('ema20')) and _safe(rp.get('ema50')) and _safe(r.get('adx14')):
        if r['adx14'] > 25:
            if rp['ema20'] <= rp['ema50'] and r['ema20'] > r['ema50']:
                add('A3_EMA20_50_ADX', 'long', close)
            elif rp['ema20'] >= rp['ema50'] and r['ema20'] < r['ema50']:
                add('A3_EMA20_50_ADX', 'short', close)

    # ── A4: EMA 50/200 cross + retest ──────────────────────
    # Approximation: cross recent (dans 5 bars) ET prix dans 0.5 ATR de EMA50
    if _safe(r.get('ema50')) and _safe(r.get('ema200')) and _safe(r.get('atr14')):
        window = candles.iloc[max(0,ci-5):ci]
        if len(window) >= 5:
            had_golden = (window['ema50'].shift(1) <= window['ema200'].shift(1)).any() and (window['ema50'] > window['ema200']).any()
            had_death = (window['ema50'].shift(1) >= window['ema200'].shift(1)).any() and (window['ema50'] < window['ema200']).any()
            dist = abs(close - r['ema50'])
            if had_golden and r['ema50'] > r['ema200'] and dist < 0.5 * r['atr14'] and close > r['ema50']:
                add('A4_EMA50_200_RT', 'long', close)
            elif had_death and r['ema50'] < r['ema200'] and dist < 0.5 * r['atr14'] and close < r['ema50']:
                add('A4_EMA50_200_RT', 'short', close)

    # ── A5: TSMOM 3M (60 bars 4h ≈ 10 jours) ───────────────
    if _safe(r.get('ret_60')):
        if r['ret_60'] > 0.005 and (not _safe(rp.get('ret_60')) or rp['ret_60'] <= 0):
            add('A5_TSMOM_3M', 'long', close)
        elif r['ret_60'] < -0.005 and (not _safe(rp.get('ret_60')) or rp['ret_60'] >= 0):
            add('A5_TSMOM_3M', 'short', close)

    # ── A6: TSMOM 6M (120 bars) ─────────────────────────────
    if _safe(r.get('ret_120')):
        if r['ret_120'] > 0.01 and (not _safe(rp.get('ret_120')) or rp['ret_120'] <= 0):
            add('A6_TSMOM_6M', 'long', close)
        elif r['ret_120'] < -0.01 and (not _safe(rp.get('ret_120')) or rp['ret_120'] >= 0):
            add('A6_TSMOM_6M', 'short', close)

    # ── A7: Multi-speed TSMOM (combo 30/60/120) ─────────────
    if _safe(r.get('ret_30')) and _safe(r.get('ret_60')) and _safe(r.get('ret_120')):
        score = np.sign(r['ret_30']) + np.sign(r['ret_60']) + np.sign(r['ret_120'])
        rp_score = (np.sign(rp.get('ret_30',0)) + np.sign(rp.get('ret_60',0)) + np.sign(rp.get('ret_120',0))) if _safe(rp.get('ret_30')) else 0
        if score >= 3 and rp_score < 3:
            add('A7_MULTI_SPEED', 'long', close)
        elif score <= -3 and rp_score > -3:
            add('A7_MULTI_SPEED', 'short', close)

    # ── A8: Triple MA alignment 8/21/55 ─────────────────────
    if all(_safe(r.get(k)) for k in ['ema8','ema21','ema55']):
        ema8, ema21, ema55 = r['ema8'], r['ema21'], r['ema55']
        rp8, rp21, rp55 = rp.get('ema8'), rp.get('ema21'), rp.get('ema55')
        if _safe(rp8) and _safe(rp21) and _safe(rp55):
            curr_long = ema8 > ema21 > ema55 and close > ema8
            prev_long = rp8 > rp21 > rp55 and rp['close'] > rp8
            curr_short = ema8 < ema21 < ema55 and close < ema8
            prev_short = rp8 < rp21 < rp55 and rp['close'] < rp8
            if curr_long and not prev_long:
                add('A8_TRIPLE_MA', 'long', close)
            elif curr_short and not prev_short:
                add('A8_TRIPLE_MA', 'short', close)

    # ── A9: Linear regression slope 50 ──────────────────────
    if _safe(r.get('lr_slope_50')) and _safe(rp.get('lr_slope_50')):
        if r['lr_slope_50'] > 0 and rp['lr_slope_50'] <= 0:
            add('A9_LR_SLOPE_50', 'long', close)
        elif r['lr_slope_50'] < 0 and rp['lr_slope_50'] >= 0:
            add('A9_LR_SLOPE_50', 'short', close)

    # ── A10: KAMA cross ────────────────────────────────────
    if _safe(r.get('kama')) and _safe(rp.get('kama')):
        if rp['close'] <= rp['kama'] and close > r['kama']:
            add('A10_KAMA', 'long', close)
        elif rp['close'] >= rp['kama'] and close < r['kama']:
            add('A10_KAMA', 'short', close)

    # ── B1: Weekly H/L breakout ─────────────────────────────
    if _safe(r.get('wk_h')) and _safe(r.get('wk_l')):
        if close > r['wk_h']:
            add('B1_WEEKLY_HL', 'long', close)
        elif close < r['wk_l']:
            add('B1_WEEKLY_HL', 'short', close)

    # ── B2: Monthly H/L breakout ────────────────────────────
    if _safe(r.get('mo_h')) and _safe(r.get('mo_l')):
        if close > r['mo_h']:
            add('B2_MONTHLY_HL', 'long', close)
        elif close < r['mo_l']:
            add('B2_MONTHLY_HL', 'short', close)

    # ── B3: N-day consolidation breakout ────────────────────
    # Range 30 bars < 2 ATR, breakout des extremes
    window = candles.iloc[max(0,ci-30):ci]
    if len(window) >= 30 and _safe(r.get('atr14')):
        rng = window['high'].max() - window['low'].min()
        if rng < 2 * r['atr14']:
            if close > window['high'].max():
                add('B3_NDAY_CONSO', 'long', close)
            elif close < window['low'].min():
                add('B3_NDAY_CONSO', 'short', close)

    # ── B4: Triangle breakout (highs desc + lows asc) ───────
    # Approximation: regression sur highs et lows derniers 30 bars convergent
    if len(window) >= 30:
        n = len(window); xs = np.arange(n)
        denom = n*(xs**2).sum() - xs.sum()**2 + 1e-10
        slope_h = (n*np.dot(xs, window['high'].values) - xs.sum()*window['high'].sum())/denom
        slope_l = (n*np.dot(xs, window['low'].values) - xs.sum()*window['low'].sum())/denom
        if slope_h < 0 and slope_l > 0:  # convergence
            # last high projected ≈ recent close
            mid_proj_h = window['high'].iloc[-1] + slope_h
            mid_proj_l = window['low'].iloc[-1] + slope_l
            if close > mid_proj_h:
                add('B4_TRIANGLE', 'long', close)
            elif close < mid_proj_l:
                add('B4_TRIANGLE', 'short', close)

    # ── B5: BB Squeeze 50 ───────────────────────────────────
    if _safe(rp.get('bb50_width')) and _safe(rp.get('bb50_width_q25')) and _safe(r.get('bb50_up')) and _safe(r.get('bb50_lo')):
        if rp['bb50_width'] <= rp['bb50_width_q25']:
            if close > r['bb50_up']:
                add('B5_BB_SQUEEZE_50', 'long', close)
            elif close < r['bb50_lo']:
                add('B5_BB_SQUEEZE_50', 'short', close)

    # ── B6: Keltner 50 breakout ─────────────────────────────
    if _safe(rp.get('kc50_up')) and _safe(rp.get('kc50_lo')):
        if rp['close'] <= rp['kc50_up'] and close > r['kc50_up']:
            add('B6_KC_BRK_50', 'long', close)
        elif rp['close'] >= rp['kc50_lo'] and close < r['kc50_lo']:
            add('B6_KC_BRK_50', 'short', close)

    # ── B7: Failed breakout reversal ────────────────────────
    # Bar -1: cassure du wk_h. Bar 0: retour brutal sous wk_h
    if _safe(rp.get('wk_h')) and _safe(rp.get('wk_l')):
        if rp['high'] > rp['wk_h'] and close < rp['wk_h'] and close < rp['low']:
            add('B7_FAILED_BRK', 'short', close)
        elif rp['low'] < rp['wk_l'] and close > rp['wk_l'] and close > rp['high']:
            add('B7_FAILED_BRK', 'long', close)

    # ── B8: Asian range break ───────────────────────────────
    # Range Asian (bars 4h 0:00 et 4:00 UTC). Cassure en bars London (8h-12h) ou NY (12h-16h)
    ts = r.get('ts_dt')
    if ts is not None and hasattr(ts, 'hour'):
        if ts.hour in (8, 12, 16):
            # Recup les 2 bars asian (0h et 4h) du meme jour
            today = ts.date()
            same_day = candles[candles['date']==today] if 'date' in candles.columns else None
            if same_day is not None and len(same_day) >= 3:
                asian = same_day[same_day['ts_dt'].dt.hour.isin([0,4])]
                if len(asian) >= 1:
                    asian_h, asian_l = asian['high'].max(), asian['low'].min()
                    if close > asian_h:
                        add('B8_ASIAN_RANGE', 'long', close)
                    elif close < asian_l:
                        add('B8_ASIAN_RANGE', 'short', close)

    # ── C1: Pullback to EMA 20 in trend (EMA50>EMA200) ──────
    if all(_safe(r.get(k)) for k in ['ema20','ema50','ema200','atr14']):
        if r['ema50'] > r['ema200']:  # trend up
            # Pullback: low approach ema20 mais close au-dessus
            if rp['low'] < rp['ema20'] and close > r['ema20'] and r['lower_wick'] > r['body_abs']:
                add('C1_PULLBACK_EMA20', 'long', close)
        elif r['ema50'] < r['ema200']:  # trend down
            if rp['high'] > rp['ema20'] and close < r['ema20'] and r['upper_wick'] > r['body_abs']:
                add('C1_PULLBACK_EMA20', 'short', close)

    # ── C2: Fibonacci retracement ───────────────────────────
    # Swing detection 30 bars: high - low du segment
    if len(window) >= 30 and _safe(r.get('atr14')):
        swing_h = window['high'].max()
        swing_l = window['low'].min()
        swing_range = swing_h - swing_l
        if swing_range > 2 * r['atr14']:
            for lvl in [0.382, 0.5, 0.618]:
                # Retrace from top (long if swing was up)
                if window['high'].idxmax() > window['low'].idxmin():  # trend up
                    fib = swing_h - swing_range * lvl
                    if abs(close - fib) < 0.3 * r['atr14'] and close > r['open']:
                        add('C2_FIB_RETRACE', 'long', close)
                        break
                else:  # trend down
                    fib = swing_l + swing_range * lvl
                    if abs(close - fib) < 0.3 * r['atr14'] and close < r['open']:
                        add('C2_FIB_RETRACE', 'short', close)
                        break

    # ── C3: 3-bar counter-trend pullback (ADX>30) ───────────
    if _safe(r.get('adx14')) and r['adx14'] > 30 and ci >= 4:
        last3 = candles.iloc[ci-3:ci]
        if _safe(r.get('ema50')):
            if r['close'] > r['ema50']:  # trend up
                if (last3['close'] < last3['open']).all() and close > rp['high']:
                    add('C3_3BAR_PULLBACK', 'long', close)
            else:  # trend down
                if (last3['close'] > last3['open']).all() and close < rp['low']:
                    add('C3_3BAR_PULLBACK', 'short', close)

    # ── C4: Previous resistance->support retest ─────────────
    # Niveau casse il y a >5 bars, retest +/- 0.3 ATR avec rejet
    if _safe(r.get('atr14')) and ci >= 30:
        past = candles.iloc[ci-30:ci-5]
        if len(past) > 0:
            level_h = past['high'].max()
            level_l = past['low'].min()
            # cassure haute confirmee + retest
            if past['close'].iloc[-1] > level_h and abs(r['low']-level_h) < 0.3*r['atr14'] and close > level_h:
                add('C4_RS_RETEST', 'long', close)
            elif past['close'].iloc[-1] < level_l and abs(r['high']-level_l) < 0.3*r['atr14'] and close < level_l:
                add('C4_RS_RETEST', 'short', close)

    # ── C5: Anchored VWAP daily reclaim ─────────────────────
    if _safe(r.get('avwap_daily')) and _safe(rp.get('avwap_daily')):
        if rp['close'] < rp['avwap_daily'] and close > r['avwap_daily']:
            add('C5_AVWAP_RECLAIM', 'long', close)
        elif rp['close'] > rp['avwap_daily'] and close < r['avwap_daily']:
            add('C5_AVWAP_RECLAIM', 'short', close)

    # ── D1: Double top/bottom (20+ bars) ────────────────────
    if ci >= 30 and _safe(r.get('atr14')):
        seg = candles.iloc[ci-30:ci]
        peaks_idx = seg['high'].nlargest(2).index.tolist()
        troughs_idx = seg['low'].nsmallest(2).index.tolist()
        # Double top: 2 peaks proches en prix, separes par >=10 bars
        if len(peaks_idx) == 2:
            p1, p2 = sorted(peaks_idx)
            if p2 - p1 >= 10 and abs(seg.loc[p1,'high'] - seg.loc[p2,'high']) < 0.3 * r['atr14']:
                neckline = seg.loc[p1:p2,'low'].min()
                if close < neckline:
                    add('D1_DOUBLE_TB', 'short', close)
        if len(troughs_idx) == 2:
            t1, t2 = sorted(troughs_idx)
            if t2 - t1 >= 10 and abs(seg.loc[t1,'low'] - seg.loc[t2,'low']) < 0.3 * r['atr14']:
                neckline = seg.loc[t1:t2,'high'].max()
                if close > neckline:
                    add('D1_DOUBLE_TB', 'long', close)

    # ── D2: Triple top/bottom (50+ bars, 3 touches) ────────
    if ci >= 50 and _safe(r.get('atr14')):
        seg = candles.iloc[ci-50:ci]
        peaks = seg['high'].nlargest(3).index.tolist()
        troughs = seg['low'].nsmallest(3).index.tolist()
        if len(peaks) == 3 and max(peaks) - min(peaks) >= 20:
            spread = seg.loc[peaks,'high'].max() - seg.loc[peaks,'high'].min()
            if spread < 0.4 * r['atr14']:
                neck = seg['low'].min()
                if close < neck:
                    add('D2_TRIPLE_TB', 'short', close)
        if len(troughs) == 3 and max(troughs) - min(troughs) >= 20:
            spread = seg.loc[troughs,'low'].max() - seg.loc[troughs,'low'].min()
            if spread < 0.4 * r['atr14']:
                neck = seg['high'].max()
                if close > neck:
                    add('D2_TRIPLE_TB', 'long', close)

    # ── D3: Engulfing au touch weekly H/L ───────────────────
    if _safe(r.get('wk_h')) and _safe(r.get('wk_l')) and _safe(r.get('atr14')):
        bull_eng = (rp['close'] < rp['open'] and r['close'] > r['open']
                    and r['open'] < rp['close'] and r['close'] > rp['open'])
        bear_eng = (rp['close'] > rp['open'] and r['close'] < r['open']
                    and r['open'] > rp['close'] and r['close'] < rp['open'])
        if bull_eng and abs(r['low'] - r['wk_l']) < 0.5 * r['atr14']:
            add('D3_ENGULF_WHL', 'long', close)
        elif bear_eng and abs(r['high'] - r['wk_h']) < 0.5 * r['atr14']:
            add('D3_ENGULF_WHL', 'short', close)

    # ── D4: Pin bar sur niveau majeur (EMA200) ─────────────
    if _safe(r.get('ema200')) and _safe(r.get('atr14')) and r['candle_range'] > 0:
        pin_bull = r['lower_wick'] > 2 * r['body_abs'] and r['lower_wick'] > 0.5 * r['candle_range']
        pin_bear = r['upper_wick'] > 2 * r['body_abs'] and r['upper_wick'] > 0.5 * r['candle_range']
        dist = abs(close - r['ema200'])
        if pin_bull and dist < 0.5 * r['atr14']:
            add('D4_PIN_LEVEL', 'long', close)
        elif pin_bear and dist < 0.5 * r['atr14']:
            add('D4_PIN_LEVEL', 'short', close)

    # ── D5: RSI divergence + niveau majeur ─────────────────
    if ci >= 30 and _safe(r.get('rsi14')) and _safe(r.get('bb50_up')) and _safe(r.get('bb50_lo')):
        seg = candles.iloc[ci-30:ci+1]
        # Bullish div: lower low price, higher low RSI
        prev_low_idx = seg.iloc[:-1]['low'].idxmin()
        if seg.loc[prev_low_idx, 'rsi14'] < r['rsi14'] and r['low'] < seg.loc[prev_low_idx,'low']:
            if r['low'] <= r['bb50_lo']:
                add('D5_RSI_DIV_LVL', 'long', close)
        prev_high_idx = seg.iloc[:-1]['high'].idxmax()
        if seg.loc[prev_high_idx, 'rsi14'] > r['rsi14'] and r['high'] > seg.loc[prev_high_idx,'high']:
            if r['high'] >= r['bb50_up']:
                add('D5_RSI_DIV_LVL', 'short', close)

    # ── F1: Flag breakout (impulse + consolidation) ─────────
    if ci >= 20 and _safe(r.get('atr14')):
        impulse = candles.iloc[ci-20:ci-10]
        conso = candles.iloc[ci-10:ci]
        imp_move = impulse.iloc[-1]['close'] - impulse.iloc[0]['close']
        conso_range = conso['high'].max() - conso['low'].min()
        if abs(imp_move) > 3 * r['atr14'] and conso_range < 1.5 * r['atr14']:
            if imp_move > 0 and close > conso['high'].max():
                add('F1_FLAG_BRK', 'long', close)
            elif imp_move < 0 and close < conso['low'].min():
                add('F1_FLAG_BRK', 'short', close)

    # ── F2: Cup & Handle ────────────────────────────────────
    # Pattern U sur 40 bars + petite consolidation 10 bars
    if ci >= 50 and _safe(r.get('atr14')):
        cup = candles.iloc[ci-50:ci-10]
        handle = candles.iloc[ci-10:ci]
        if len(cup) >= 40:
            left_high = cup.iloc[:10]['high'].max()
            right_high = cup.iloc[-10:]['high'].max()
            cup_low = cup['low'].min()
            cup_depth = min(left_high, right_high) - cup_low
            handle_depth = handle.iloc[:-1]['high'].max() - handle.iloc[:-1]['low'].min()
            if (abs(left_high - right_high) < 0.5 * r['atr14']
                and cup_depth > 2 * r['atr14']
                and handle_depth < 0.4 * cup_depth
                and close > right_high):
                add('F2_CUP_HANDLE', 'long', close)

    # ── F3: Head & Shoulders ────────────────────────────────
    if ci >= 50 and _safe(r.get('atr14')):
        seg = candles.iloc[ci-50:ci]
        peaks = seg['high'].nlargest(3).index.tolist()
        if len(peaks) == 3:
            p_sorted = sorted(peaks)
            h_idx = max(peaks, key=lambda x: seg.loc[x,'high'])
            shoulders = [p for p in p_sorted if p != h_idx]
            if len(shoulders) == 2 and h_idx > shoulders[0] and h_idx < shoulders[1]:
                sh_l, sh_r = seg.loc[shoulders[0],'high'], seg.loc[shoulders[1],'high']
                head = seg.loc[h_idx,'high']
                if head > sh_l + r['atr14'] and head > sh_r + r['atr14'] and abs(sh_l - sh_r) < 0.5 * r['atr14']:
                    neckline = seg['low'].min()
                    if close < neckline:
                        add('F3_HEAD_SHOULDERS', 'short', close)
        troughs = seg['low'].nsmallest(3).index.tolist()
        if len(troughs) == 3:
            t_sorted = sorted(troughs)
            h_idx = min(troughs, key=lambda x: seg.loc[x,'low'])
            shoulders = [t for t in t_sorted if t != h_idx]
            if len(shoulders) == 2 and h_idx > shoulders[0] and h_idx < shoulders[1]:
                sh_l, sh_r = seg.loc[shoulders[0],'low'], seg.loc[shoulders[1],'low']
                head = seg.loc[h_idx,'low']
                if head < sh_l - r['atr14'] and head < sh_r - r['atr14'] and abs(sh_l - sh_r) < 0.5 * r['atr14']:
                    neckline = seg['high'].max()
                    if close > neckline:
                        add('F3_HEAD_SHOULDERS', 'long', close)

    # ── F4: Symmetrical triangle ───────────────────────────
    # Convergence highs desc + lows asc sur 30 bars (similaire B4 mais sym strict)
    if len(window) >= 30:
        n = len(window); xs = np.arange(n)
        denom = n*(xs**2).sum() - xs.sum()**2 + 1e-10
        slope_h = (n*np.dot(xs, window['high'].values) - xs.sum()*window['high'].sum())/denom
        slope_l = (n*np.dot(xs, window['low'].values) - xs.sum()*window['low'].sum())/denom
        # Sym strict: |slope_h| ~ |slope_l|
        if slope_h < 0 and slope_l > 0 and abs(slope_h + slope_l) < 0.5 * min(abs(slope_h), abs(slope_l)):
            proj_h = window['high'].iloc[-1] + slope_h
            proj_l = window['low'].iloc[-1] + slope_l
            if close > proj_h:
                add('F4_SYM_TRIANGLE', 'long', close)
            elif close < proj_l:
                add('F4_SYM_TRIANGLE', 'short', close)
