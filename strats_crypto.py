"""
Strategies dediees crypto 15min perpetual futures (Hyperliquid/Binance).
Zero dependance sur strats.py — pipeline MT5 intact.

Regles look-ahead STRICTES (cf LOOK_AHEAD_CHECKLIST.md):
- Toutes les conditions utilisent des bougies FERMEES (prev = c.iloc[ci-1] ou plus loin)
- Entry price = row['close'] (bougie fermee) — PAS de strats open
- ATR du jour = ATR de la VEILLE (passe via parametre)
- 1 trigger max par strat par jour (dict trig)
- Indicateurs forward-only (ewm, rolling.strict lookback)
- Pas de biais directionnel : chaque strat teste LONG ET SHORT

Nomenclature: toutes les strats sont prefixees CRYPTO_ pour eviter collision
avec strats.py (MT5 65 strats deja existantes).
"""
import numpy as np
import pandas as pd


# ═══════════════════════════════════════════════════════════════════════
#  INDICATEURS
# ═══════════════════════════════════════════════════════════════════════

def _wma(s, n):
    """Weighted moving average (pour HMA)."""
    w = np.arange(1, n+1, dtype=float)
    return s.rolling(n).apply(lambda x: np.dot(x, w)/w.sum(), raw=True)


def _supertrend(c, period=10, mult=3.0):
    """SuperTrend indicator — retourne (st_dir, st_val).
    Forward-only, boucle ligne par ligne avec data <= i."""
    tr = np.maximum(
        c['high'] - c['low'],
        np.maximum(abs(c['high'] - c['close'].shift(1)), abs(c['low'] - c['close'].shift(1)))
    )
    atr = tr.ewm(span=period, adjust=False).mean()
    mid = (c['high'] + c['low']) / 2
    up = mid - mult * atr
    dn = mid + mult * atr
    n = len(c)
    st_dir = np.zeros(n); st_val = np.zeros(n)
    for i in range(1, n):
        if c.iloc[i]['close'] > dn.iloc[i-1]:
            st_dir[i] = 1
            st_val[i] = max(up.iloc[i], st_val[i-1]) if st_dir[i-1] == 1 else up.iloc[i]
        elif c.iloc[i]['close'] < up.iloc[i-1]:
            st_dir[i] = -1
            st_val[i] = min(dn.iloc[i], st_val[i-1]) if st_dir[i-1] == -1 else dn.iloc[i]
        else:
            st_dir[i] = st_dir[i-1]
            st_val[i] = max(up.iloc[i], st_val[i-1]) if st_dir[i] == 1 else min(dn.iloc[i], st_val[i-1])
    return st_dir, st_val


def _psar(c, af_step=0.02, af_max=0.2):
    """Parabolic SAR — forward-only."""
    n = len(c)
    psar = np.zeros(n); direction = np.zeros(n)
    if n < 2: return psar, direction
    direction[0] = 1
    psar[0] = c.iloc[0]['low']
    ep = c.iloc[0]['high']
    af = af_step
    for i in range(1, n):
        prev_psar = psar[i-1]
        if direction[i-1] == 1:
            psar[i] = prev_psar + af * (ep - prev_psar)
            if c.iloc[i]['low'] < psar[i]:
                direction[i] = -1
                psar[i] = ep
                ep = c.iloc[i]['low']
                af = af_step
            else:
                direction[i] = 1
                if c.iloc[i]['high'] > ep:
                    ep = c.iloc[i]['high']
                    af = min(af + af_step, af_max)
        else:
            psar[i] = prev_psar + af * (ep - prev_psar)
            if c.iloc[i]['high'] > psar[i]:
                direction[i] = 1
                psar[i] = ep
                ep = c.iloc[i]['high']
                af = af_step
            else:
                direction[i] = -1
                if c.iloc[i]['low'] < ep:
                    ep = c.iloc[i]['low']
                    af = min(af + af_step, af_max)
    return psar, direction


def _heikin_ashi(c):
    """Heikin Ashi — forward-only sequential."""
    n = len(c)
    ha_close = np.zeros(n); ha_open = np.zeros(n); ha_high = np.zeros(n); ha_low = np.zeros(n)
    if n == 0: return ha_open, ha_high, ha_low, ha_close
    ha_close[0] = (c.iloc[0]['open'] + c.iloc[0]['high'] + c.iloc[0]['low'] + c.iloc[0]['close']) / 4
    ha_open[0] = (c.iloc[0]['open'] + c.iloc[0]['close']) / 2
    ha_high[0] = c.iloc[0]['high']; ha_low[0] = c.iloc[0]['low']
    for i in range(1, n):
        ha_close[i] = (c.iloc[i]['open'] + c.iloc[i]['high'] + c.iloc[i]['low'] + c.iloc[i]['close']) / 4
        ha_open[i] = (ha_open[i-1] + ha_close[i-1]) / 2
        ha_high[i] = max(c.iloc[i]['high'], ha_open[i], ha_close[i])
        ha_low[i] = min(c.iloc[i]['low'], ha_open[i], ha_close[i])
    return ha_open, ha_high, ha_low, ha_close


def compute_indicators_crypto(candles):
    """
    Pre-calcule tous les indicateurs necessaires aux strats crypto 15m.
    Forward-only, zero look-ahead.
    """
    c = candles.copy()

    # ─── Basiques ───
    c['body'] = c['close'] - c['open']
    c['abs_body'] = c['body'].abs()
    c['range'] = c['high'] - c['low']
    c['mid'] = (c['high'] + c['low']) / 2
    c['upper_wick'] = c['high'] - c[['open', 'close']].max(axis=1)
    c['lower_wick'] = c[['open', 'close']].min(axis=1) - c['low']

    # ─── EMA ───
    for p in [9, 13, 21, 50, 55, 100, 200]:
        c[f'ema{p}'] = c['close'].ewm(span=p, adjust=False).mean()

    # ─── ATR ───
    tr = np.maximum(
        c['high'] - c['low'],
        np.maximum(abs(c['high'] - c['close'].shift(1)), abs(c['low'] - c['close'].shift(1)))
    )
    c['tr'] = tr
    c['atr14'] = tr.ewm(span=14, adjust=False).mean()
    c['atr20'] = tr.rolling(20).mean()

    # ─── RSI ───
    delta = c['close'].diff()
    gain = delta.clip(lower=0); loss = (-delta).clip(lower=0)
    ag = gain.ewm(alpha=1.0/14, min_periods=14, adjust=False).mean()
    al = loss.ewm(alpha=1.0/14, min_periods=14, adjust=False).mean()
    c['rsi14'] = 100 - 100 / (1 + ag / (al + 1e-10))

    # ─── Stochastic RSI ───
    rsi_min = c['rsi14'].rolling(14).min()
    rsi_max = c['rsi14'].rolling(14).max()
    c['stochrsi'] = 100 * (c['rsi14'] - rsi_min) / (rsi_max - rsi_min + 1e-10)

    # ─── MACD ───
    ef = c['close'].ewm(span=12, adjust=False).mean()
    es = c['close'].ewm(span=26, adjust=False).mean()
    c['macd'] = ef - es
    c['macd_sig'] = c['macd'].ewm(span=9, adjust=False).mean()
    c['macd_hist'] = c['macd'] - c['macd_sig']

    # ─── ADX ───
    pdm = c['high'].diff().clip(lower=0)
    mdm = (-c['low'].diff()).clip(lower=0)
    mask = pdm > mdm
    pdm2 = pdm.where(mask, 0); mdm2 = mdm.where(~mask, 0)
    atr14 = c['atr14']
    c['pdi'] = 100 * pdm2.ewm(span=14, adjust=False).mean() / (atr14 + 1e-10)
    c['mdi'] = 100 * mdm2.ewm(span=14, adjust=False).mean() / (atr14 + 1e-10)
    dx = 100 * abs(c['pdi'] - c['mdi']) / (c['pdi'] + c['mdi'] + 1e-10)
    c['adx'] = dx.ewm(span=14, adjust=False).mean()

    # ─── Donchian Channels ───
    for p in [20, 50]:
        c[f'dc{p}_h'] = c['high'].rolling(p).max()
        c[f'dc{p}_l'] = c['low'].rolling(p).min()
        c[f'dc{p}_m'] = (c[f'dc{p}_h'] + c[f'dc{p}_l']) / 2

    # ─── Keltner Channels (EMA20 +/- 2*ATR) ───
    c['kc_mid'] = c['close'].ewm(span=20, adjust=False).mean()
    c['kc_up'] = c['kc_mid'] + 2.0 * c['atr14']
    c['kc_lo'] = c['kc_mid'] - 2.0 * c['atr14']

    # ─── Bollinger Bands (20, 2) ───
    c['bb_mid'] = c['close'].rolling(20).mean()
    c['bb_std'] = c['close'].rolling(20).std()
    c['bb_up'] = c['bb_mid'] + 2.0 * c['bb_std']
    c['bb_lo'] = c['bb_mid'] - 2.0 * c['bb_std']
    c['bb_width'] = (c['bb_up'] - c['bb_lo']) / (c['bb_mid'] + 1e-10)

    # ─── BB/KC Squeeze flag (BB inside KC) ───
    c['in_squeeze'] = (c['bb_up'] < c['kc_up']) & (c['bb_lo'] > c['kc_lo'])

    # ─── SuperTrend ───
    st_dir, st_val = _supertrend(c, period=10, mult=3.0)
    c['st_dir'] = st_dir
    c['st_val'] = st_val

    # ─── Parabolic SAR ───
    psar, psar_dir = _psar(c)
    c['psar'] = psar
    c['psar_dir'] = psar_dir

    # ─── Ichimoku (Tenkan 9, Kijun 26, Senkou A/B 52) ───
    c['tenkan'] = (c['high'].rolling(9).max() + c['low'].rolling(9).min()) / 2
    c['kijun'] = (c['high'].rolling(26).max() + c['low'].rolling(26).min()) / 2
    c['senkou_a'] = ((c['tenkan'] + c['kijun']) / 2).shift(26)
    c['senkou_b'] = ((c['high'].rolling(52).max() + c['low'].rolling(52).min()) / 2).shift(26)

    # ─── HMA ───
    c['hma9'] = _wma(2 * _wma(c['close'], 4) - _wma(c['close'], 9), 3)
    c['hma21'] = _wma(2 * _wma(c['close'], 10) - _wma(c['close'], 21), 4)
    c['hma50'] = _wma(2 * _wma(c['close'], 25) - _wma(c['close'], 50), 7)

    # ─── Heikin Ashi ───
    ha_o, ha_h, ha_l, ha_c = _heikin_ashi(c)
    c['ha_open'] = ha_o
    c['ha_high'] = ha_h
    c['ha_low'] = ha_l
    c['ha_close'] = ha_c

    # ─── Rate of Change ───
    c['roc10'] = c['close'] / c['close'].shift(10) * 100 - 100
    c['roc20'] = c['close'] / c['close'].shift(20) * 100 - 100

    # ─── Volume ───
    if 'volume' in c.columns:
        c['vol_ma20'] = c['volume'].rolling(20).mean()
        c['vol_ma50'] = c['volume'].rolling(50).mean()
    else:
        c['vol_ma20'] = 0
        c['vol_ma50'] = 0

    # ─── NR7 (Narrowest Range 7) ───
    c['range_min7'] = c['range'].rolling(7).min()

    # ─── VWAP daily cumulatif ───
    c['vwap_day'] = _daily_vwap(c)

    # ─── Williams %R ───
    hh14 = c['high'].rolling(14).max()
    ll14 = c['low'].rolling(14).min()
    c['wr14'] = -100 * (hh14 - c['close']) / (hh14 - ll14 + 1e-10)

    return c


def _daily_vwap(c):
    """VWAP remis a zero chaque jour UTC. Cumulatif bar par bar, zero look-ahead."""
    if 'volume' not in c.columns:
        # Fallback: utilisation du close comme proxy (pour crypto sans volume)
        return c['close'].rolling(20).mean()
    vwap = np.zeros(len(c))
    cur_date = None
    cum_pv = 0.0
    cum_v = 0.0
    for i in range(len(c)):
        d = c.iloc[i]['date']
        if d != cur_date:
            cur_date = d
            cum_pv = 0.0
            cum_v = 0.0
        tp = (c.iloc[i]['high'] + c.iloc[i]['low'] + c.iloc[i]['close']) / 3
        v = c.iloc[i]['volume'] if 'volume' in c.columns else 1.0
        cum_pv += tp * v
        cum_v += v
        vwap[i] = cum_pv / cum_v if cum_v > 0 else tp
    return vwap


# ═══════════════════════════════════════════════════════════════════════
#  DETECT ALL CRYPTO
# ═══════════════════════════════════════════════════════════════════════

def detect_all_crypto(c, ci, row, prev, ct, today, hour, atr, trig, prev_day_data, add, prev2_day_data=None):
    """
    Detecte les signaux des strategies crypto 15m pour la bougie fermee ci.

    Args:
        c: DataFrame avec indicateurs precalcules
        ci: index de la bougie courante (fermee)
        row: c.iloc[ci]
        prev: c.iloc[ci-1]
        ct: timestamp de row
        today: date.today()
        hour: float hour (ct.hour + ct.minute/60)
        atr: ATR de la veille (pour sizing cote optimizer)
        trig: dict des strats deja declenchees aujourd'hui
        prev_day_data: OHLC du jour precedent
        add: callback add(strat_name, direction, entry_price)
        prev2_day_data: OHLC avant-veille (pas utilise crypto)
    """
    # Besoin d'au moins 200 bars pour tous les indicateurs
    if ci < 200:
        return

    # ═══ 1. CRYPTO_DONCHIAN_20 — Break Donchian 20 bars ═══
    if 'CRYPTO_DONCHIAN_20' not in trig:
        if not (pd.isna(prev['dc20_h']) or pd.isna(prev['dc20_l'])):
            # Entry sur close qui casse le precedent Donchian (prev pour eviter look-ahead)
            if row['close'] > prev['dc20_h']:
                add('CRYPTO_DONCHIAN_20', 'long', row['close'])
                trig['CRYPTO_DONCHIAN_20'] = True
            elif row['close'] < prev['dc20_l']:
                add('CRYPTO_DONCHIAN_20', 'short', row['close'])
                trig['CRYPTO_DONCHIAN_20'] = True

    # ═══ 2. CRYPTO_DONCHIAN_50 — Break Donchian 50 bars ═══
    if 'CRYPTO_DONCHIAN_50' not in trig:
        if not (pd.isna(prev['dc50_h']) or pd.isna(prev['dc50_l'])):
            if row['close'] > prev['dc50_h']:
                add('CRYPTO_DONCHIAN_50', 'long', row['close'])
                trig['CRYPTO_DONCHIAN_50'] = True
            elif row['close'] < prev['dc50_l']:
                add('CRYPTO_DONCHIAN_50', 'short', row['close'])
                trig['CRYPTO_DONCHIAN_50'] = True

    # ═══ 3. CRYPTO_KELTNER_MOMO — Break Keltner + ROC ═══
    if 'CRYPTO_KELTNER_MOMO' not in trig:
        if not (pd.isna(row['kc_up']) or pd.isna(row['kc_lo']) or pd.isna(row['roc10'])):
            # Break upper + momentum positif
            if row['close'] > row['kc_up'] and row['roc10'] > 0 and prev['close'] <= prev['kc_up']:
                add('CRYPTO_KELTNER_MOMO', 'long', row['close'])
                trig['CRYPTO_KELTNER_MOMO'] = True
            elif row['close'] < row['kc_lo'] and row['roc10'] < 0 and prev['close'] >= prev['kc_lo']:
                add('CRYPTO_KELTNER_MOMO', 'short', row['close'])
                trig['CRYPTO_KELTNER_MOMO'] = True

    # ═══ 4. CRYPTO_SUPERTREND_FLIP — SuperTrend flip + ADX ═══
    if 'CRYPTO_SUPERTREND_FLIP' not in trig:
        if not pd.isna(row['adx']) and row['adx'] > 25:
            # Flip detecte sur prev (transition fermee)
            if prev['st_dir'] == -1 and row['st_dir'] == 1:
                add('CRYPTO_SUPERTREND_FLIP', 'long', row['close'])
                trig['CRYPTO_SUPERTREND_FLIP'] = True
            elif prev['st_dir'] == 1 and row['st_dir'] == -1:
                add('CRYPTO_SUPERTREND_FLIP', 'short', row['close'])
                trig['CRYPTO_SUPERTREND_FLIP'] = True

    # ═══ 5. CRYPTO_ICHIMOKU_CROSS — Kumo break + Tenkan/Kijun cross ═══
    if 'CRYPTO_ICHIMOKU_CROSS' not in trig:
        if not (pd.isna(row['senkou_a']) or pd.isna(row['senkou_b']) or
                pd.isna(row['tenkan']) or pd.isna(row['kijun'])):
            kumo_up = max(row['senkou_a'], row['senkou_b'])
            kumo_lo = min(row['senkou_a'], row['senkou_b'])
            # Long: close au-dessus du kumo + tenkan>kijun avec cross recent
            if (row['close'] > kumo_up and row['tenkan'] > row['kijun']
                and prev['tenkan'] <= prev['kijun']):
                add('CRYPTO_ICHIMOKU_CROSS', 'long', row['close'])
                trig['CRYPTO_ICHIMOKU_CROSS'] = True
            elif (row['close'] < kumo_lo and row['tenkan'] < row['kijun']
                  and prev['tenkan'] >= prev['kijun']):
                add('CRYPTO_ICHIMOKU_CROSS', 'short', row['close'])
                trig['CRYPTO_ICHIMOKU_CROSS'] = True

    # ═══ 6. CRYPTO_HMA_TRIPLE — HMA9×HMA21 + HMA50 meme direction ═══
    if 'CRYPTO_HMA_TRIPLE' not in trig:
        if not (pd.isna(row['hma9']) or pd.isna(row['hma21']) or pd.isna(row['hma50'])):
            # Cross detecte sur prev (on utilise row et prev)
            if (prev['hma9'] <= prev['hma21'] and row['hma9'] > row['hma21']
                and row['close'] > row['hma50']):
                add('CRYPTO_HMA_TRIPLE', 'long', row['close'])
                trig['CRYPTO_HMA_TRIPLE'] = True
            elif (prev['hma9'] >= prev['hma21'] and row['hma9'] < row['hma21']
                  and row['close'] < row['hma50']):
                add('CRYPTO_HMA_TRIPLE', 'short', row['close'])
                trig['CRYPTO_HMA_TRIPLE'] = True

    # ═══ 7. CRYPTO_EMA_21_55_ADX — EMA cross + ADX>25 ═══
    if 'CRYPTO_EMA_21_55_ADX' not in trig:
        if not (pd.isna(row['ema21']) or pd.isna(row['ema55']) or pd.isna(row['adx'])):
            if row['adx'] > 25:
                if prev['ema21'] <= prev['ema55'] and row['ema21'] > row['ema55']:
                    add('CRYPTO_EMA_21_55_ADX', 'long', row['close'])
                    trig['CRYPTO_EMA_21_55_ADX'] = True
                elif prev['ema21'] >= prev['ema55'] and row['ema21'] < row['ema55']:
                    add('CRYPTO_EMA_21_55_ADX', 'short', row['close'])
                    trig['CRYPTO_EMA_21_55_ADX'] = True

    # ═══ 8. CRYPTO_PSAR_EMA200 — PSAR flip dans le sens EMA200 ═══
    if 'CRYPTO_PSAR_EMA200' not in trig:
        if not pd.isna(row['ema200']):
            # PSAR flip detection (prev direction != current)
            if prev['psar_dir'] == -1 and row['psar_dir'] == 1 and row['close'] > row['ema200']:
                add('CRYPTO_PSAR_EMA200', 'long', row['close'])
                trig['CRYPTO_PSAR_EMA200'] = True
            elif prev['psar_dir'] == 1 and row['psar_dir'] == -1 and row['close'] < row['ema200']:
                add('CRYPTO_PSAR_EMA200', 'short', row['close'])
                trig['CRYPTO_PSAR_EMA200'] = True

    # ═══ 9. CRYPTO_HA_TREND — 3 bougies HA meme couleur sans meche opposee ═══
    if 'CRYPTO_HA_TREND' not in trig and ci >= 3:
        # On regarde les 3 dernieres bougies HA FERMEES: ci-2, ci-1, ci
        ha_o = c['ha_open'].values
        ha_c = c['ha_close'].values
        ha_h = c['ha_high'].values
        ha_l = c['ha_low'].values
        # Haussier: 3 vertes sans meche basse (lower wick = 0)
        bull = (ha_c[ci] > ha_o[ci] and ha_c[ci-1] > ha_o[ci-1] and ha_c[ci-2] > ha_o[ci-2]
                and ha_l[ci] >= ha_o[ci] and ha_l[ci-1] >= ha_o[ci-1])
        # Baissier: 3 rouges sans meche haute
        bear = (ha_c[ci] < ha_o[ci] and ha_c[ci-1] < ha_o[ci-1] and ha_c[ci-2] < ha_o[ci-2]
                and ha_h[ci] <= ha_o[ci] and ha_h[ci-1] <= ha_o[ci-1])
        if bull:
            add('CRYPTO_HA_TREND', 'long', row['close'])
            trig['CRYPTO_HA_TREND'] = True
        elif bear:
            add('CRYPTO_HA_TREND', 'short', row['close'])
            trig['CRYPTO_HA_TREND'] = True

    # ═══ 10. CRYPTO_MACD_ZERO — MACD cross zero + trend EMA200 ═══
    if 'CRYPTO_MACD_ZERO' not in trig:
        if not (pd.isna(row['macd']) or pd.isna(row['ema200'])):
            if prev['macd'] <= 0 and row['macd'] > 0 and row['close'] > row['ema200']:
                add('CRYPTO_MACD_ZERO', 'long', row['close'])
                trig['CRYPTO_MACD_ZERO'] = True
            elif prev['macd'] >= 0 and row['macd'] < 0 and row['close'] < row['ema200']:
                add('CRYPTO_MACD_ZERO', 'short', row['close'])
                trig['CRYPTO_MACD_ZERO'] = True
