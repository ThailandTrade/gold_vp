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

    # ═══ 11. CRYPTO_BBKC_SQUEEZE — BB inside KC 10+ bars puis release + momentum ═══
    if 'CRYPTO_BBKC_SQUEEZE' not in trig and ci >= 12:
        # Verif squeeze sur les 10 bougies precedentes (ci-10 a ci-1)
        # Release = row n'est plus in_squeeze + momentum direction
        was_squeezed = c['in_squeeze'].iloc[ci-10:ci].all()
        now_released = not row['in_squeeze'] and prev['in_squeeze']
        if was_squeezed and now_released and not pd.isna(row['macd']):
            if row['macd'] > 0 and row['close'] > prev['close']:
                add('CRYPTO_BBKC_SQUEEZE', 'long', row['close'])
                trig['CRYPTO_BBKC_SQUEEZE'] = True
            elif row['macd'] < 0 and row['close'] < prev['close']:
                add('CRYPTO_BBKC_SQUEEZE', 'short', row['close'])
                trig['CRYPTO_BBKC_SQUEEZE'] = True

    # ═══ 12. CRYPTO_ATR_SPIKE — Bougie avec range > 2x ATR20 ═══
    if 'CRYPTO_ATR_SPIKE' not in trig:
        if not pd.isna(row['atr20']) and row['atr20'] > 0:
            # Range de la bougie fermee > 2x ATR20
            if row['range'] > 2.0 * row['atr20']:
                body = row['close'] - row['open']
                # Suivre la direction de la bougie
                if body > 0.5 * row['range']:
                    add('CRYPTO_ATR_SPIKE', 'long', row['close'])
                    trig['CRYPTO_ATR_SPIKE'] = True
                elif body < -0.5 * row['range']:
                    add('CRYPTO_ATR_SPIKE', 'short', row['close'])
                    trig['CRYPTO_ATR_SPIKE'] = True

    # ═══ 13. CRYPTO_ORB_UTC — Opening Range Break 4 premieres bougies 00:00 UTC ═══
    # OR = high/low des 4 premieres bougies 15m (00:00-01:00 UTC)
    # Entry: break de l'OR apres 01:00 UTC pendant la journee
    if 'CRYPTO_ORB_UTC' not in trig and hour >= 1.0:
        # Recuperer les 4 premieres bougies du jour
        day_start_idx = ci
        for k in range(ci-1, max(ci-100, -1), -1):
            if c.iloc[k]['date'] != today:
                day_start_idx = k + 1
                break
            if k == 0:
                day_start_idx = 0
        # 4 premieres bougies (15m x 4 = 1h)
        if day_start_idx + 4 <= ci:
            or_candles = c.iloc[day_start_idx:day_start_idx+4]
            or_h = or_candles['high'].max()
            or_l = or_candles['low'].min()
            # Break sur row, mais PAS pendant l'OR elle-meme
            if ci > day_start_idx + 3:
                if row['close'] > or_h and prev['close'] <= or_h:
                    add('CRYPTO_ORB_UTC', 'long', row['close'])
                    trig['CRYPTO_ORB_UTC'] = True
                elif row['close'] < or_l and prev['close'] >= or_l:
                    add('CRYPTO_ORB_UTC', 'short', row['close'])
                    trig['CRYPTO_ORB_UTC'] = True

    # ═══ 14. CRYPTO_LONDON_OR — OR 08:00-09:00 UTC (session London) ═══
    if 'CRYPTO_LONDON_OR' not in trig and hour >= 9.0:
        # OR = high/low des bougies 8h-9h UTC du jour courant
        today_mask = c['date'] == today
        df_today = c[today_mask]
        lon_or = df_today[(df_today['ts_dt'].dt.hour == 8)]
        if len(lon_or) >= 3 and ci > lon_or.index[-1]:
            or_h = lon_or['high'].max()
            or_l = lon_or['low'].min()
            if row['close'] > or_h and prev['close'] <= or_h:
                add('CRYPTO_LONDON_OR', 'long', row['close'])
                trig['CRYPTO_LONDON_OR'] = True
            elif row['close'] < or_l and prev['close'] >= or_l:
                add('CRYPTO_LONDON_OR', 'short', row['close'])
                trig['CRYPTO_LONDON_OR'] = True

    # ═══ 15. CRYPTO_CONSO_VOL_BRK — Range 20 bars avec ATR declining + volume break ═══
    if 'CRYPTO_CONSO_VOL_BRK' not in trig and ci >= 40:
        # Range des 20 bougies precedentes (ci-20 a ci-1)
        window = c.iloc[ci-20:ci]
        range_h = window['high'].max()
        range_l = window['low'].min()
        range_size = range_h - range_l
        # ATR declinant: ATR actuel < ATR il y a 20 bars
        atr_now = row['atr14']
        atr_ago = c.iloc[ci-20]['atr14']
        declining = not pd.isna(atr_now) and not pd.isna(atr_ago) and atr_now < atr_ago
        # Volume break
        vol_ok = ('volume' in c.columns and not pd.isna(row['vol_ma20'])
                  and row['volume'] > 2.0 * row['vol_ma20'])
        if declining and vol_ok and range_size > 0:
            if row['close'] > range_h:
                add('CRYPTO_CONSO_VOL_BRK', 'long', row['close'])
                trig['CRYPTO_CONSO_VOL_BRK'] = True
            elif row['close'] < range_l:
                add('CRYPTO_CONSO_VOL_BRK', 'short', row['close'])
                trig['CRYPTO_CONSO_VOL_BRK'] = True

    # ═══ 16. CRYPTO_NR7 — Narrowest Range 7 bars break ═══
    if 'CRYPTO_NR7' not in trig:
        # prev est la bougie NR7 (plus petit range sur 7 dernieres bougies)
        if not pd.isna(prev['range_min7']) and prev['range'] == prev['range_min7']:
            # Break du high/low de la bougie NR7 par la bougie suivante (row)
            if row['close'] > prev['high']:
                add('CRYPTO_NR7', 'long', row['close'])
                trig['CRYPTO_NR7'] = True
            elif row['close'] < prev['low']:
                add('CRYPTO_NR7', 'short', row['close'])
                trig['CRYPTO_NR7'] = True

    # ═══ 17. CRYPTO_RSI_DEEP_DIV — RSI<20 + divergence haussiere (ou inverse) ═══
    if 'CRYPTO_RSI_DEEP_DIV' not in trig and ci >= 20:
        if not pd.isna(row['rsi14']):
            # Bullish divergence: prix fait un lower low, RSI fait un higher low, RSI<30 maintenant
            if row['rsi14'] < 25:
                # Cherche un creux precedent sur les 20 dernieres bougies
                window = c.iloc[ci-20:ci]
                low_idx = window['low'].idxmin()
                prev_low = window.loc[low_idx]
                if (low_idx < ci - 2 and row['low'] < prev_low['low']
                    and row['rsi14'] > prev_low['rsi14']):
                    add('CRYPTO_RSI_DEEP_DIV', 'long', row['close'])
                    trig['CRYPTO_RSI_DEEP_DIV'] = True
            elif row['rsi14'] > 75:
                window = c.iloc[ci-20:ci]
                high_idx = window['high'].idxmax()
                prev_high = window.loc[high_idx]
                if (high_idx < ci - 2 and row['high'] > prev_high['high']
                    and row['rsi14'] < prev_high['rsi14']):
                    add('CRYPTO_RSI_DEEP_DIV', 'short', row['close'])
                    trig['CRYPTO_RSI_DEEP_DIV'] = True

    # ═══ 18. CRYPTO_STOCH_RSI_EXTREME — StochRSI<5 ou >95 + reversal bar ═══
    if 'CRYPTO_STOCH_RSI_EXTREME' not in trig:
        if not (pd.isna(prev['stochrsi']) or pd.isna(row['stochrsi'])):
            # Oversold: prev<5, row>prev (reversal bar), close>open (bougie verte)
            if prev['stochrsi'] < 5 and row['stochrsi'] > prev['stochrsi'] and row['close'] > row['open']:
                add('CRYPTO_STOCH_RSI_EXTREME', 'long', row['close'])
                trig['CRYPTO_STOCH_RSI_EXTREME'] = True
            elif prev['stochrsi'] > 95 and row['stochrsi'] < prev['stochrsi'] and row['close'] < row['open']:
                add('CRYPTO_STOCH_RSI_EXTREME', 'short', row['close'])
                trig['CRYPTO_STOCH_RSI_EXTREME'] = True

    # ═══ 19. CRYPTO_BB_OUTLIER — Prix > 2.5 std outside BB + reversal ═══
    if 'CRYPTO_BB_OUTLIER' not in trig:
        if not (pd.isna(row['bb_mid']) or pd.isna(row['bb_std']) or row['bb_std'] == 0):
            z = (row['close'] - row['bb_mid']) / row['bb_std']
            prev_z = (prev['close'] - prev['bb_mid']) / (prev['bb_std'] + 1e-10) if not pd.isna(prev['bb_std']) else 0
            # Extreme oversold (z < -2.5) qui commence a remonter
            if prev_z < -2.5 and z > prev_z and row['close'] > row['open']:
                add('CRYPTO_BB_OUTLIER', 'long', row['close'])
                trig['CRYPTO_BB_OUTLIER'] = True
            elif prev_z > 2.5 and z < prev_z and row['close'] < row['open']:
                add('CRYPTO_BB_OUTLIER', 'short', row['close'])
                trig['CRYPTO_BB_OUTLIER'] = True

    # ═══ 20. CRYPTO_VWAP_RECLAIM — Clash puis reclaim VWAP avec volume ═══
    if 'CRYPTO_VWAP_RECLAIM' not in trig and ci >= 5:
        if not pd.isna(row['vwap_day']):
            # Long: prev close < VWAP, row close > VWAP (reclaim)
            vol_ok = True
            if 'volume' in c.columns and not pd.isna(row['vol_ma20']):
                vol_ok = row['volume'] > 1.5 * row['vol_ma20']
            if prev['close'] < prev['vwap_day'] and row['close'] > row['vwap_day'] and vol_ok:
                # Verif que le prix etait clairement sous le VWAP (au moins 2 bars)
                below_vwap = all(c.iloc[ci-k]['close'] < c.iloc[ci-k]['vwap_day'] for k in range(1, 4))
                if below_vwap:
                    add('CRYPTO_VWAP_RECLAIM', 'long', row['close'])
                    trig['CRYPTO_VWAP_RECLAIM'] = True
            elif prev['close'] > prev['vwap_day'] and row['close'] < row['vwap_day'] and vol_ok:
                above_vwap = all(c.iloc[ci-k]['close'] > c.iloc[ci-k]['vwap_day'] for k in range(1, 4))
                if above_vwap:
                    add('CRYPTO_VWAP_RECLAIM', 'short', row['close'])
                    trig['CRYPTO_VWAP_RECLAIM'] = True

    # ═══ 21. CRYPTO_AVWAP_BOUNCE — Bounce sur Anchored VWAP depuis dernier swing H/L ═══
    # Simplification: on utilise le VWAP daily comme anchored VWAP (depuis debut de journee)
    # Bounce = prix touche VWAP et repart dans le sens du trend intraday
    if 'CRYPTO_AVWAP_BOUNCE' not in trig and ci >= 10:
        if not pd.isna(row['vwap_day']) and not pd.isna(row['ema50']):
            # Bullish bounce: trend haussier (close>ema50), prix touche VWAP, bougie verte
            touched_vwap_from_above = (prev['low'] <= prev['vwap_day']
                                       and prev['close'] > prev['vwap_day']
                                       and row['close'] > row['open']
                                       and row['close'] > row['vwap_day'])
            if touched_vwap_from_above and row['close'] > row['ema50']:
                add('CRYPTO_AVWAP_BOUNCE', 'long', row['close'])
                trig['CRYPTO_AVWAP_BOUNCE'] = True
            touched_vwap_from_below = (prev['high'] >= prev['vwap_day']
                                       and prev['close'] < prev['vwap_day']
                                       and row['close'] < row['open']
                                       and row['close'] < row['vwap_day'])
            if touched_vwap_from_below and row['close'] < row['ema50']:
                add('CRYPTO_AVWAP_BOUNCE', 'short', row['close'])
                trig['CRYPTO_AVWAP_BOUNCE'] = True

    # ═══ 22. CRYPTO_BOS_FVG — Break of Structure + Fair Value Gap retest ═══
    # BOS: prix casse le dernier swing high/low
    # FVG: gap entre la bougie ci-2 high et ci high (pour long) — trou pas comble par ci-1
    # Entry: quand row retrace dans la FVG apres un BOS
    if 'CRYPTO_BOS_FVG' not in trig and ci >= 25:
        window = c.iloc[ci-20:ci]
        swing_h = window['high'].max()
        swing_l = window['low'].min()
        # BOS bullish sur la bougie ci-3 ou ci-2 (close > swing_h)
        for k in range(2, 6):
            if ci-k-2 < 0: break
            bos_bar = c.iloc[ci-k]
            # FVG Bullish: low de bar ci-k > high de bar ci-k-2 (gap de 3 bougies)
            b1 = c.iloc[ci-k-2]  # bougie avant le gap
            b2 = c.iloc[ci-k-1]  # bougie centrale (forte impulsion)
            b3 = bos_bar         # bougie apres le gap
            if b3['low'] > b1['high'] and b2['close'] > b2['open']:  # FVG bullish
                # BOS: b3 close > swing high recent
                recent_swing = c.iloc[max(0, ci-k-20):ci-k-2]['high'].max()
                if b3['close'] > recent_swing:
                    # Entry: row retrace dans la FVG (row low <= b3 low ou b1 high)
                    fvg_top = b3['low']
                    fvg_bot = b1['high']
                    if (row['low'] <= fvg_top and row['low'] >= fvg_bot
                        and row['close'] > row['open']):
                        add('CRYPTO_BOS_FVG', 'long', row['close'])
                        trig['CRYPTO_BOS_FVG'] = True
                        break
            # FVG Bearish
            if b3['high'] < b1['low'] and b2['close'] < b2['open']:
                recent_swing = c.iloc[max(0, ci-k-20):ci-k-2]['low'].min()
                if b3['close'] < recent_swing:
                    fvg_top = b1['low']
                    fvg_bot = b3['high']
                    if (row['high'] >= fvg_bot and row['high'] <= fvg_top
                        and row['close'] < row['open']):
                        add('CRYPTO_BOS_FVG', 'short', row['close'])
                        trig['CRYPTO_BOS_FVG'] = True
                        break

    # ═══ 23. CRYPTO_LIQ_SWEEP — Wick au-dessus/sous swing H/L puis close oppose ═══
    if 'CRYPTO_LIQ_SWEEP' not in trig and ci >= 20:
        window = c.iloc[ci-20:ci]
        swing_h = window['high'].max()
        swing_l = window['low'].min()
        # Bullish liq sweep: row wick low casse swing_l mais close > swing_l (sweep+reclaim)
        if row['low'] < swing_l and row['close'] > swing_l and row['close'] > row['open']:
            # Meche basse doit etre significative (au moins 0.5 ATR sous swing_l)
            if row['atr14'] > 0 and (swing_l - row['low']) >= 0.3 * row['atr14']:
                add('CRYPTO_LIQ_SWEEP', 'long', row['close'])
                trig['CRYPTO_LIQ_SWEEP'] = True
        # Bearish liq sweep
        elif row['high'] > swing_h and row['close'] < swing_h and row['close'] < row['open']:
            if row['atr14'] > 0 and (row['high'] - swing_h) >= 0.3 * row['atr14']:
                add('CRYPTO_LIQ_SWEEP', 'short', row['close'])
                trig['CRYPTO_LIQ_SWEEP'] = True

    # ═══ 24. CRYPTO_ORDER_BLOCK — Retest d'un Order Block (bougie avant impulsion) ═══
    # OB = derniere bougie opposee avant un move impulsif (>= 2 ATR en 3 bougies)
    if 'CRYPTO_ORDER_BLOCK' not in trig and ci >= 10:
        if row['atr14'] > 0:
            # Cherche un OB bullish dans les 10 dernieres bougies
            for k in range(3, 11):
                if ci-k < 0: break
                ob_bar = c.iloc[ci-k]
                # Impulsion apres OB: close (ci-k+3) - close (ci-k) > 2 ATR
                if ci-k+3 >= ci: continue
                impulse = c.iloc[ci-k+3]['close'] - ob_bar['close']
                # OB bullish: bougie rouge, suivie d'une impulsion haussiere
                if (ob_bar['close'] < ob_bar['open'] and impulse > 2.0 * row['atr14']
                    and row['low'] <= ob_bar['high'] and row['low'] >= ob_bar['low']
                    and row['close'] > row['open']):
                    add('CRYPTO_ORDER_BLOCK', 'long', row['close'])
                    trig['CRYPTO_ORDER_BLOCK'] = True
                    break
                # OB bearish
                if (ob_bar['close'] > ob_bar['open'] and impulse < -2.0 * row['atr14']
                    and row['high'] >= ob_bar['low'] and row['high'] <= ob_bar['high']
                    and row['close'] < row['open']):
                    add('CRYPTO_ORDER_BLOCK', 'short', row['close'])
                    trig['CRYPTO_ORDER_BLOCK'] = True
                    break

    # ═══ 25. CRYPTO_OTE_618 — Entry zone Fib 0.62-0.79 d'un leg impulsif ═══
    if 'CRYPTO_OTE_618' not in trig and ci >= 15:
        # Trouve le leg impulsif le plus recent (>= 3 ATR en < 10 bougies)
        for k in range(3, 15):
            if ci-k-3 < 0: break
            leg_start_idx = ci - k
            leg_end_idx = ci - 2
            if leg_end_idx <= leg_start_idx: continue
            leg = c.iloc[leg_start_idx:leg_end_idx+1]
            leg_h = leg['high'].max()
            leg_l = leg['low'].min()
            leg_range = leg_h - leg_l
            if row['atr14'] <= 0 or leg_range < 3.0 * row['atr14']: continue
            # Direction du leg: close final vs open debut
            leg_dir = leg.iloc[-1]['close'] - leg.iloc[0]['open']
            if leg_dir > 0:  # Leg haussier — cherche retracement
                fib_62 = leg_h - 0.62 * leg_range
                fib_79 = leg_h - 0.79 * leg_range
                if fib_79 <= row['low'] <= fib_62 and row['close'] > row['open']:
                    add('CRYPTO_OTE_618', 'long', row['close'])
                    trig['CRYPTO_OTE_618'] = True
                    break
            elif leg_dir < 0:  # Leg baissier
                fib_62 = leg_l + 0.62 * leg_range
                fib_79 = leg_l + 0.79 * leg_range
                if fib_62 <= row['high'] <= fib_79 and row['close'] < row['open']:
                    add('CRYPTO_OTE_618', 'short', row['close'])
                    trig['CRYPTO_OTE_618'] = True
                    break

    # ═══ 26. CRYPTO_HVN_REJECT — Reject sur High Volume Node (POC N dernieres bougies) ═══
    # Approximation HVN: cherche le prix le plus frequent sur les 96 bougies precedentes (~24h)
    if 'CRYPTO_HVN_REJECT' not in trig and ci >= 100:
        window = c.iloc[ci-96:ci]
        # HVN = prix median des closes (approximation rapide)
        hvn = window['close'].median()
        # Reject: row touche HVN avec meche mais ferme oppose
        tol = row['atr14'] * 0.3 if not pd.isna(row['atr14']) else 0
        if tol > 0:
            # Bullish reject: low touche HVN, close > HVN (rejet)
            if abs(row['low'] - hvn) < tol and row['close'] > hvn and row['close'] > row['open']:
                add('CRYPTO_HVN_REJECT', 'long', row['close'])
                trig['CRYPTO_HVN_REJECT'] = True
            # Bearish reject
            elif abs(row['high'] - hvn) < tol and row['close'] < hvn and row['close'] < row['open']:
                add('CRYPTO_HVN_REJECT', 'short', row['close'])
                trig['CRYPTO_HVN_REJECT'] = True

    # ═══ 27. CRYPTO_LVN_BRK — Break rapide Low Volume Node + volume spike ═══
    # LVN = zone peu tradee, identifiee comme gap de prix recent (quantile extreme)
    if 'CRYPTO_LVN_BRK' not in trig and ci >= 100:
        window = c.iloc[ci-96:ci]
        # LVN = zones pres du max/min du range peu visitees
        q25 = window['close'].quantile(0.05)
        q75 = window['close'].quantile(0.95)
        vol_ok = True
        if 'volume' in c.columns and not pd.isna(row['vol_ma20']):
            vol_ok = row['volume'] > 2.0 * row['vol_ma20']
        if vol_ok:
            # Break rapide au-dessus du q95 du range (LVN haussier)
            if prev['close'] <= q75 and row['close'] > q75:
                add('CRYPTO_LVN_BRK', 'long', row['close'])
                trig['CRYPTO_LVN_BRK'] = True
            elif prev['close'] >= q25 and row['close'] < q25:
                add('CRYPTO_LVN_BRK', 'short', row['close'])
                trig['CRYPTO_LVN_BRK'] = True

    # ═══ 28. CRYPTO_POC_MIGRATION — Suivre migration POC jour par jour ═══
    # Simplification: POC = median des closes de la journee precedente
    # Entry: prix se deplace du POC prev vers un nouveau niveau
    if 'CRYPTO_POC_MIGRATION' not in trig and prev_day_data is not None:
        prev_poc = (prev_day_data['high'] + prev_day_data['low']) / 2  # approximation
        if not pd.isna(row['atr14']) and row['atr14'] > 0:
            dist = (row['close'] - prev_poc) / row['atr14']
            # Migration significative (> 1 ATR) + EMA21 confirme trend
            if dist > 1.0 and not pd.isna(row['ema21']) and row['close'] > row['ema21'] and prev['close'] <= prev['ema21'] + row['atr14'] * 0.5:
                add('CRYPTO_POC_MIGRATION', 'long', row['close'])
                trig['CRYPTO_POC_MIGRATION'] = True
            elif dist < -1.0 and not pd.isna(row['ema21']) and row['close'] < row['ema21'] and prev['close'] >= prev['ema21'] - row['atr14'] * 0.5:
                add('CRYPTO_POC_MIGRATION', 'short', row['close'])
                trig['CRYPTO_POC_MIGRATION'] = True

    # ═══ 29. CRYPTO_VOL_SPIKE — Volume > 3x moyenne + body > 1.5 ATR ═══
    if 'CRYPTO_VOL_SPIKE' not in trig:
        if ('volume' in c.columns and not pd.isna(row['vol_ma50'])
            and not pd.isna(row['atr14']) and row['atr14'] > 0):
            vol_spike = row['volume'] > 3.0 * row['vol_ma50']
            body_big = abs(row['body']) > 1.5 * row['atr14']
            if vol_spike and body_big:
                if row['body'] > 0:
                    add('CRYPTO_VOL_SPIKE', 'long', row['close'])
                    trig['CRYPTO_VOL_SPIKE'] = True
                else:
                    add('CRYPTO_VOL_SPIKE', 'short', row['close'])
                    trig['CRYPTO_VOL_SPIKE'] = True

    # ═══ 30. CRYPTO_DOUBLE_BOT_TOP — Double bottom/top avec volume decroissant ═══
    # Cherche 2 creux/sommets similaires dans les 50 dernieres bougies
    if 'CRYPTO_DOUBLE_BOT_TOP' not in trig and ci >= 55:
        window = c.iloc[ci-50:ci]
        atr = row['atr14']
        if not pd.isna(atr) and atr > 0:
            tol = atr * 0.5
            # Double bottom: 2 lows proches + volume decroissant + breakout au-dessus du neckline
            lows = window['low'].values
            # Find local minima (simple)
            minima_idx = []
            for k in range(2, len(lows)-2):
                if lows[k] < lows[k-1] and lows[k] < lows[k+1] and lows[k] < lows[k-2] and lows[k] < lows[k+2]:
                    minima_idx.append(k)
            if len(minima_idx) >= 2:
                m1, m2 = minima_idx[-2], minima_idx[-1]
                if abs(lows[m1] - lows[m2]) < tol and m2 - m1 >= 5:
                    neckline = window.iloc[m1:m2+1]['high'].max()
                    # Break au-dessus du neckline avec row
                    if row['close'] > neckline and prev['close'] <= neckline:
                        add('CRYPTO_DOUBLE_BOT_TOP', 'long', row['close'])
                        trig['CRYPTO_DOUBLE_BOT_TOP'] = True
            # Double top
            highs = window['high'].values
            maxima_idx = []
            for k in range(2, len(highs)-2):
                if highs[k] > highs[k-1] and highs[k] > highs[k+1] and highs[k] > highs[k-2] and highs[k] > highs[k+2]:
                    maxima_idx.append(k)
            if 'CRYPTO_DOUBLE_BOT_TOP' not in trig and len(maxima_idx) >= 2:
                m1, m2 = maxima_idx[-2], maxima_idx[-1]
                if abs(highs[m1] - highs[m2]) < tol and m2 - m1 >= 5:
                    neckline = window.iloc[m1:m2+1]['low'].min()
                    if row['close'] < neckline and prev['close'] >= neckline:
                        add('CRYPTO_DOUBLE_BOT_TOP', 'short', row['close'])
                        trig['CRYPTO_DOUBLE_BOT_TOP'] = True

    # ═══ 31. CRYPTO_INV_HS — Inverse Head & Shoulders (et Head & Shoulders) ═══
    # Simplification: 3 lows avec le central plus bas, epaules similaires, neckline break
    if 'CRYPTO_INV_HS' not in trig and ci >= 60:
        window = c.iloc[ci-50:ci]
        atr = row['atr14']
        if not pd.isna(atr) and atr > 0:
            lows = window['low'].values
            tol = atr * 0.7
            # Trouve 3 minima distants
            minima_idx = []
            for k in range(3, len(lows)-3):
                if lows[k] < lows[k-1] and lows[k] < lows[k+1] and lows[k] < lows[k-3] and lows[k] < lows[k+3]:
                    minima_idx.append(k)
            if len(minima_idx) >= 3:
                ls, head, rs = minima_idx[-3], minima_idx[-2], minima_idx[-1]
                # Head plus bas que les 2 epaules, epaules similaires
                if (lows[head] < lows[ls] - tol and lows[head] < lows[rs] - tol
                    and abs(lows[ls] - lows[rs]) < tol):
                    neckline = max(window.iloc[ls:head+1]['high'].max(),
                                   window.iloc[head:rs+1]['high'].max())
                    if row['close'] > neckline and prev['close'] <= neckline:
                        add('CRYPTO_INV_HS', 'long', row['close'])
                        trig['CRYPTO_INV_HS'] = True
            # Head & Shoulders (inverse logic for shorts)
            highs = window['high'].values
            maxima_idx = []
            for k in range(3, len(highs)-3):
                if highs[k] > highs[k-1] and highs[k] > highs[k+1] and highs[k] > highs[k-3] and highs[k] > highs[k+3]:
                    maxima_idx.append(k)
            if 'CRYPTO_INV_HS' not in trig and len(maxima_idx) >= 3:
                ls, head, rs = maxima_idx[-3], maxima_idx[-2], maxima_idx[-1]
                if (highs[head] > highs[ls] + tol and highs[head] > highs[rs] + tol
                    and abs(highs[ls] - highs[rs]) < tol):
                    neckline = min(window.iloc[ls:head+1]['low'].min(),
                                   window.iloc[head:rs+1]['low'].min())
                    if row['close'] < neckline and prev['close'] >= neckline:
                        add('CRYPTO_INV_HS', 'short', row['close'])
                        trig['CRYPTO_INV_HS'] = True

    # ═══ 32. CRYPTO_WYCKOFF_SPRING — Drop sous range puis reclaim rapide ═══
    if 'CRYPTO_WYCKOFF_SPRING' not in trig and ci >= 40:
        window = c.iloc[ci-30:ci-1]  # range ne inclut pas les 2 dernieres bars
        range_l = window['low'].min()
        range_h = window['high'].max()
        atr = row['atr14']
        if not pd.isna(atr) and atr > 0:
            # Spring bullish: prev a casse le range_l, row reclaim au-dessus
            if prev['low'] < range_l - 0.1 * atr and row['close'] > range_l and row['close'] > row['open']:
                # Range doit etre assez large (> 3 ATR)
                if range_h - range_l > 3.0 * atr:
                    add('CRYPTO_WYCKOFF_SPRING', 'long', row['close'])
                    trig['CRYPTO_WYCKOFF_SPRING'] = True
            # Upthrust (spring inverse) bearish
            elif prev['high'] > range_h + 0.1 * atr and row['close'] < range_h and row['close'] < row['open']:
                if range_h - range_l > 3.0 * atr:
                    add('CRYPTO_WYCKOFF_SPRING', 'short', row['close'])
                    trig['CRYPTO_WYCKOFF_SPRING'] = True

    # ═══ 33. CRYPTO_HTF_BIAS — Trend 4h (16 bars 15m) + pullback EMA21 15m ═══
    # HTF trend: slope EMA200 sur les 16 derniers bars (equiv 4h trend)
    if 'CRYPTO_HTF_BIAS' not in trig and ci >= 220:
        if not (pd.isna(row['ema21']) or pd.isna(row['ema200'])):
            ema200_now = row['ema200']
            ema200_ago = c.iloc[ci-16]['ema200']  # 16 bars = 4h
            trend_up = ema200_now > ema200_ago and row['close'] > row['ema200']
            trend_dn = ema200_now < ema200_ago and row['close'] < row['ema200']
            # Pullback vers EMA21: prev touche EMA21, row rebondit
            tol = row['atr14'] * 0.3 if not pd.isna(row['atr14']) else 0
            if trend_up and tol > 0:
                touched = abs(prev['low'] - prev['ema21']) < tol or prev['low'] < prev['ema21']
                bouncing = row['close'] > row['ema21'] and row['close'] > row['open']
                if touched and bouncing:
                    add('CRYPTO_HTF_BIAS', 'long', row['close'])
                    trig['CRYPTO_HTF_BIAS'] = True
            elif trend_dn and tol > 0:
                touched = abs(prev['high'] - prev['ema21']) < tol or prev['high'] > prev['ema21']
                bouncing = row['close'] < row['ema21'] and row['close'] < row['open']
                if touched and bouncing:
                    add('CRYPTO_HTF_BIAS', 'short', row['close'])
                    trig['CRYPTO_HTF_BIAS'] = True

    # ═══ 34. CRYPTO_WEEKLY_PIVOT — Reaction aux pivots weekly confirmee 15m ═══
    # Pivots weekly: calcul sur OHLC de la semaine precedente (approx 7 jours)
    # Simplification: on utilise prev_day_data comme proxy (pivot daily)
    if 'CRYPTO_WEEKLY_PIVOT' not in trig and prev_day_data is not None:
        pp = (prev_day_data['high'] + prev_day_data['low'] + prev_day_data['close']) / 3
        r1 = 2 * pp - prev_day_data['low']
        s1 = 2 * pp - prev_day_data['high']
        atr = row['atr14']
        tol = atr * 0.3 if not pd.isna(atr) else 0
        if tol > 0:
            # Bounce sur S1 (long)
            if abs(prev['low'] - s1) < tol and row['close'] > s1 and row['close'] > row['open']:
                add('CRYPTO_WEEKLY_PIVOT', 'long', row['close'])
                trig['CRYPTO_WEEKLY_PIVOT'] = True
            # Rejet sur R1 (short)
            elif abs(prev['high'] - r1) < tol and row['close'] < r1 and row['close'] < row['open']:
                add('CRYPTO_WEEKLY_PIVOT', 'short', row['close'])
                trig['CRYPTO_WEEKLY_PIVOT'] = True

    # ═══ 35. CRYPTO_FUNDING_EXTREME — Funding rate extreme (PROXY via RSI+volume) ═══
    # Pas de data funding rate en backtest — on utilise un proxy:
    # "Overheated long" = RSI > 75 + volume haut + bougie rouge = correction a venir
    if 'CRYPTO_FUNDING_EXTREME' not in trig:
        if not pd.isna(prev['rsi14']) and 'volume' in c.columns and not pd.isna(prev['vol_ma20']):
            vol_high = prev['volume'] > 1.5 * prev['vol_ma20']
            # Overheated longs: RSI>75 + vol haut + row qui commence a baisser
            if prev['rsi14'] > 75 and vol_high and row['close'] < row['open'] and row['close'] < prev['close']:
                add('CRYPTO_FUNDING_EXTREME', 'short', row['close'])
                trig['CRYPTO_FUNDING_EXTREME'] = True
            elif prev['rsi14'] < 25 and vol_high and row['close'] > row['open'] and row['close'] > prev['close']:
                add('CRYPTO_FUNDING_EXTREME', 'long', row['close'])
                trig['CRYPTO_FUNDING_EXTREME'] = True
