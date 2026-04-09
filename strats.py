"""
Module commun: toutes les strategies, exit et indicateurs.
Le portfolio actif est defini dans config_icm.py / config_ftmo.py / config_5ers.py.
"""
import pandas as pd
import numpy as np

# Strats retirees definitivement (open strats + jamais safe sur aucun instrument)
REMOVED_STRATS = frozenset({
    # Open strats (timing non reproductible en live)
    'TOK_FADE', 'TOK_PREVEXT', 'LON_GAP', 'LON_BIGGAP', 'LON_KZ',
    'LON_TOKEND', 'LON_PREV', 'NY_GAP', 'NY_LONEND', 'NY_LONMOM', 'NY_DAYMOM',
    # Jamais safe sur aucun instrument/TF
    'ALL_AO_SAUCER', 'ALL_BB_SQUEEZE', 'ALL_EMA_TREND_PB', 'ALL_HMA_DIR',
    'ALL_MACD_MED_SIG', 'ALL_STOCH_CROSS', 'ALL_VOL_SPIKE',
    'IDX_GAP_FILL', 'IDX_ORB15', 'LON_PIN', 'TOK_MACD_MED',
})

_ALL_STRATS_RAW = [
    # Price Action
    'TOK_2BAR','TOK_BIG','TOK_FADE','TOK_PREVEXT',
    'LON_PIN','LON_GAP','LON_BIGGAP','LON_KZ','LON_TOKEND','LON_PREV',
    'NY_GAP','NY_LONEND','NY_LONMOM','NY_DAYMOM',
    'D8',
    # Indicators (original)
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
    # Indicator strats (from optimize_all v6)
    'ALL_RSI_50','ALL_RSI_DIV','ALL_FISHER_9','ALL_DPO_14',
    'ALL_AO_SAUCER','ALL_HMA_CROSS','ALL_HMA_DIR','ALL_DC10_EMA',
    'ALL_CMO_14_ZERO','ALL_ICHI_TK','ALL_MACD_ADX',
    'ALL_MACD_STD_SIG','ALL_MACD_FAST_ZERO',
    'ALL_BB_TIGHT','ALL_CCI_14_ZERO','ALL_CCI_20_ZERO',
    'ALL_MTF_BRK','ALL_NR4','ALL_PIVOT_BOUNCE','ALL_PIVOT_BRK',
    'ALL_EMA_513','ALL_EMA_821','ALL_EMA_921','ALL_EMA_TREND_PB',
    'ALL_WILLR_14','ALL_MOM_10','ALL_MOM_14','ALL_DC50',
    'TOK_FISHER','TOK_MACD_MED',
    'LON_DC10','NY_HMA_CROSS',
    'ALL_CMO_9','ALL_CMO_14','ALL_MACD_FAST_SIG','ALL_MACD_MED_SIG','ALL_WILLR_7',
    # New strats v7
    'ALL_STOCH_CROSS','ALL_STOCH_OB','ALL_TRIX','ALL_SUPERTREND',
    'ALL_ROC_ZERO','ALL_ELDER_BULL','ALL_ELDER_BEAR',
    'ALL_AROON_CROSS','ALL_STOCH_RSI','ALL_CCI_100',
    'ALL_KB_SQUEEZE','ALL_LR_BREAK','ALL_ADX_RSI50',
    'ALL_MACD_DIV','ALL_STOCH_PIVOT',
    'TOK_STOCH','TOK_TRIX','LON_STOCH','NY_ELDER',
]
ALL_STRATS = [s for s in _ALL_STRATS_RAW if s not in REMOVED_STRATS]

# Index unique par strat pour magic numbers (ne jamais changer l'ordre, ajouter en fin)
# IMPORTANT: utilise _ALL_STRATS_RAW pour garder les index stables (meme si strat retiree)
STRAT_ID = {s: i for i, s in enumerate(_ALL_STRATS_RAW)}

# Symboles connus et leur offset (ne jamais changer, ajouter en fin)
SYMBOL_ID = {
    'XAUUSD': 0, 'JPN225': 1, 'DAX40': 2, 'NAS100': 3, 'SP500': 4, 'UK100': 5,
    'BTCUSD': 6, 'GER40.cash': 7, 'UK100.cash': 8, 'US100.cash': 9,
    'US500.cash': 10, 'US30.cash': 11, 'JP225.cash': 12,
}

MAGIC_BASES = {'icm': 240000, 'ftmo': 250000, '5ers': 260000}

def make_magic(broker, symbol, strat):
    """Magic = broker_base + symbol_id * 200 + strat_id. Garanti unique."""
    return MAGIC_BASES[broker] + SYMBOL_ID[symbol] * 200 + STRAT_ID[strat]

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
    'ALL_RSI_50':'RSI 50 cross',
    'ALL_RSI_DIV':'RSI divergence',
    'ALL_FISHER_9':'Fisher transform 9 cross',
    'ALL_DPO_14':'DPO 14 zero cross',
    'ALL_AO_SAUCER':'Awesome Oscillator saucer',
    'ALL_HMA_CROSS':'HMA 9/21 cross',
    'ALL_HMA_DIR':'HMA 21 direction change',
    'ALL_DC10_EMA':'Donchian 10 + EMA21 filter',
    'ALL_CMO_14_ZERO':'CMO 14 zero cross',
    'ALL_ICHI_TK':'Ichimoku TK cross above cloud',
    'ALL_MACD_ADX':'MACD std cross + ADX>25',
    'ALL_MACD_STD_SIG':'MACD std signal cross',
    'ALL_MACD_FAST_ZERO':'MACD fast zero cross',
    'ALL_BB_TIGHT':'Tight Bollinger breakout',
    'ALL_CCI_14_ZERO':'CCI 14 zero cross',
    'ALL_CCI_20_ZERO':'CCI 20 zero cross',
    'ALL_MTF_BRK':'Multi-timeframe 1H breakout',
    'ALL_NR4':'Narrow range 4 breakout',
    'ALL_PIVOT_BOUNCE':'Daily pivot bounce',
    'ALL_PIVOT_BRK':'Daily pivot breakout',
    'ALL_EMA_513':'EMA 5/13 cross',
    'ALL_EMA_821':'EMA 8/21 cross',
    'ALL_EMA_921':'EMA 9/21 cross',
    'ALL_EMA_TREND_PB':'EMA trend pullback',
    'ALL_WILLR_14':'Williams %R 14 reversal',
    'ALL_MOM_10':'Momentum 10 zero cross',
    'ALL_MOM_14':'Momentum 14 zero cross',
    'ALL_DC50':'Donchian 50 breakout',
    'TOK_FISHER':'Fisher transform Tokyo',
    'TOK_MACD_MED':'MACD med cross Tokyo',
    'LON_DC10':'Donchian 10 London',
    'NY_HMA_CROSS':'HMA 9/21 cross NY',
    'ALL_CMO_9':'CMO 9 reversal (-50/+50)',
    'ALL_CMO_14':'CMO 14 reversal (-50/+50)',
    'ALL_MACD_FAST_SIG':'MACD fast signal cross',
    'ALL_MACD_MED_SIG':'MACD med signal cross',
    'ALL_WILLR_7':'Williams %R 7 reversal',
    'ALL_STOCH_CROSS':'Stochastic K/D cross',
    'ALL_STOCH_OB':'Stochastic overbought/oversold reversal',
    'ALL_TRIX':'TRIX signal cross',
    'ALL_SUPERTREND':'Supertrend direction change',
    'ALL_ROC_ZERO':'Rate of Change zero cross',
    'ALL_ELDER_BULL':'Elder Ray bull power reversal',
    'ALL_ELDER_BEAR':'Elder Ray bear power reversal',
    'ALL_AROON_CROSS':'Aroon up/down cross',
    'ALL_STOCH_RSI':'Stochastic RSI cross',
    'ALL_CCI_100':'CCI 100 extreme reversal',
    'ALL_KB_SQUEEZE':'Keltner-Bollinger squeeze breakout',
    'ALL_LR_BREAK':'Linear regression slope reversal',
    'ALL_ADX_RSI50':'ADX trend + RSI 50 cross',
    'ALL_MACD_DIV':'MACD divergence',
    'ALL_STOCH_PIVOT':'Stochastic + pivot bounce',
    'TOK_STOCH':'Stochastic reversal Tokyo',
    'TOK_TRIX':'TRIX cross Tokyo',
    'LON_STOCH':'Stochastic reversal London',
    'NY_ELDER':'Elder Ray reversal NY',
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
    'ALL_RSI_50':'All','ALL_RSI_DIV':'All','ALL_FISHER_9':'All','ALL_DPO_14':'All',
    'ALL_AO_SAUCER':'All','ALL_HMA_CROSS':'All','ALL_HMA_DIR':'All','ALL_DC10_EMA':'All',
    'ALL_CMO_14_ZERO':'All','ALL_ICHI_TK':'All','ALL_MACD_ADX':'All',
    'ALL_MACD_STD_SIG':'All','ALL_MACD_FAST_ZERO':'All',
    'ALL_BB_TIGHT':'All','ALL_CCI_14_ZERO':'All','ALL_CCI_20_ZERO':'All',
    'ALL_MTF_BRK':'All','ALL_NR4':'All','ALL_PIVOT_BOUNCE':'All','ALL_PIVOT_BRK':'All',
    'ALL_EMA_513':'All','ALL_EMA_821':'All','ALL_EMA_921':'All','ALL_EMA_TREND_PB':'All',
    'ALL_WILLR_14':'All','ALL_MOM_10':'All','ALL_MOM_14':'All','ALL_DC50':'All',
    'TOK_FISHER':'Tokyo','TOK_MACD_MED':'Tokyo',
    'LON_DC10':'London','NY_HMA_CROSS':'New York',
    'ALL_CMO_9':'All','ALL_CMO_14':'All',
    'ALL_MACD_FAST_SIG':'All','ALL_MACD_MED_SIG':'All','ALL_WILLR_7':'All',
    'ALL_STOCH_CROSS':'All','ALL_STOCH_OB':'All','ALL_TRIX':'All','ALL_SUPERTREND':'All',
    'ALL_ROC_ZERO':'All','ALL_ELDER_BULL':'All','ALL_ELDER_BEAR':'All',
    'ALL_AROON_CROSS':'All','ALL_STOCH_RSI':'All','ALL_CCI_100':'All',
    'ALL_KB_SQUEEZE':'All','ALL_LR_BREAK':'All','ALL_ADX_RSI50':'All',
    'ALL_MACD_DIV':'All','ALL_STOCH_PIVOT':'All',
    'TOK_STOCH':'Tokyo','TOK_TRIX':'Tokyo','LON_STOCH':'London','NY_ELDER':'New York',
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
        n = min(288, len(cdf)-pos-1)
        if n > 0: return n, cdf.iloc[pos+n]['close']
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
    # Extra EMAs
    for p in [5, 8, 9, 13, 50, 100, 200]:
        k = f'ema{p}'
        if k not in c.columns:
            c[k] = c['close'].ewm(span=p, adjust=False).mean()
    # MACD std (12,26,9) and fast (5,13,1)
    for fast,slow,sig,name in [(12,26,9,'std'),(5,13,1,'fast')]:
        mk = f'macd_{name}'
        if mk not in c.columns:
            ef = c['close'].ewm(span=fast, adjust=False).mean()
            es = c['close'].ewm(span=slow, adjust=False).mean()
            c[mk] = ef - es
            c[f'{mk}_sig'] = c[mk].ewm(span=max(sig,2), adjust=False).mean()
    # HMA (Hull Moving Average)
    def _wma(s, n):
        w = np.arange(1, n+1, dtype=float)
        return s.rolling(n).apply(lambda x: np.dot(x, w)/w.sum(), raw=True)
    if 'hma9' not in c.columns:
        c['hma9'] = _wma(2*_wma(c['close'],4)-_wma(c['close'],9), 3)
    if 'hma21' not in c.columns:
        c['hma21'] = _wma(2*_wma(c['close'],10)-_wma(c['close'],21), 4)
    # CCI 14, 20
    for p in [14, 20]:
        k = f'cci{p}'
        if k not in c.columns:
            tp = (c['high']+c['low']+c['close'])/3
            sm = tp.rolling(p).mean()
            mad = tp.rolling(p).apply(lambda x: np.mean(np.abs(x-np.mean(x))), raw=True)
            c[k] = (tp-sm)/(0.015*mad+1e-10)
    # CMO 9, 14
    for p in [9, 14]:
        k = f'cmo{p}'
        if k not in c.columns:
            delta_c = c['close'].diff()
            su = delta_c.clip(lower=0).rolling(p).sum()
            sd = (-delta_c.clip(upper=0)).rolling(p).sum()
            c[k] = 100*(su-sd)/(su+sd+1e-10)
    # Momentum 10, 14
    for p in [10, 14]:
        k = f'mom{p}'
        if k not in c.columns:
            c[k] = c['close']/c['close'].shift(p)*100 - 100
    # DPO 14
    if 'dpo14' not in c.columns:
        c['dpo14'] = c['close'] - c['close'].rolling(14).mean().shift(8)
    # Fisher Transform 9
    if 'fisher9' not in c.columns:
        hh = c['high'].rolling(9).max(); ll = c['low'].rolling(9).min()
        val = 2*((c['close']-ll)/(hh-ll+1e-10)-0.5)
        val = val.clip(-0.999, 0.999)
        c['fisher9'] = (0.5*np.log((1+val)/(1-val+1e-10))).ewm(span=3, adjust=False).mean()
        c['fisher9_sig'] = c['fisher9'].shift(1)
    # Awesome Oscillator
    if 'ao' not in c.columns:
        mid = (c['high']+c['low'])/2
        c['ao'] = mid.rolling(5).mean() - mid.rolling(34).mean()
    # Ichimoku (short periods for 5m)
    if 'i_t' not in c.columns:
        c['i_t'] = (c['high'].rolling(6).max()+c['low'].rolling(6).min())/2
        c['i_k'] = (c['high'].rolling(13).max()+c['low'].rolling(13).min())/2
        c['i_sa'] = ((c['i_t']+c['i_k'])/2).shift(13)
        c['i_sb'] = ((c['high'].rolling(26).max()+c['low'].rolling(26).min())/2).shift(13)
    # Tight Bollinger Bands (10, 1.5)
    if 'bb_t_up' not in c.columns:
        bb_t_mid = c['close'].rolling(10).mean()
        bb_t_std = c['close'].rolling(10).std()
        c['bb_t_up'] = bb_t_mid + 1.5*bb_t_std
        c['bb_t_lo'] = bb_t_mid - 1.5*bb_t_std
    # ADX slow (14-period)
    if 'adx_s' not in c.columns:
        tr_ = np.maximum(c['high']-c['low'], np.maximum(abs(c['high']-c['close'].shift(1)), abs(c['low']-c['close'].shift(1))))
        pdm = c['high'].diff().clip(lower=0); mdm = (-c['low'].diff()).clip(lower=0)
        mask = pdm > mdm; pdm2 = pdm.where(mask, 0); mdm2 = mdm.where(~mask, 0)
        atr_s = tr_.ewm(span=14, adjust=False).mean()
        c['pdi_s'] = 100*pdm2.ewm(span=14, adjust=False).mean()/(atr_s+1e-10)
        c['mdi_s'] = 100*mdm2.ewm(span=14, adjust=False).mean()/(atr_s+1e-10)
        dx_s = 100*abs(c['pdi_s']-c['mdi_s'])/(c['pdi_s']+c['mdi_s']+1e-10)
        c['adx_s'] = dx_s.ewm(span=14, adjust=False).mean()
    # Multi-timeframe 1H high/low
    if 'high_1h' not in c.columns:
        c['high_1h'] = c['high'].rolling(12).max()
        c['low_1h'] = c['low'].rolling(12).min()
    # Donchian 50
    if 'dc50_h' not in c.columns:
        c['dc50_h'] = c['high'].rolling(50).max()
        c['dc50_l'] = c['low'].rolling(50).min()
    # Williams %R 7
    if 'wr7' not in c.columns:
        hh7 = c['high'].rolling(7).max(); ll7 = c['low'].rolling(7).min()
        c['wr7'] = -100*(hh7-c['close'])/(hh7-ll7+1e-10)
    # Daily pivot (prev day H+L+C /3)
    if 'pivot' not in c.columns and 'date' in c.columns:
        dates = c['date'].unique()
        c['prev_h_d'] = np.nan; c['prev_l_d'] = np.nan; c['prev_c_d'] = np.nan
        for i in range(1, len(dates)):
            prev_dc = c[c['date']==dates[i-1]]
            today_mask = c['date']==dates[i]
            c.loc[today_mask,'prev_h_d'] = prev_dc['high'].max()
            c.loc[today_mask,'prev_l_d'] = prev_dc['low'].min()
            c.loc[today_mask,'prev_c_d'] = prev_dc.iloc[-1]['close']
        c['pivot'] = (c['prev_h_d']+c['prev_l_d']+c['prev_c_d'])/3
    # range (for ALL_NR4)
    if 'range' not in c.columns:
        c['range'] = c['high'] - c['low']
    # Stochastic (14,3,3)
    if 'stoch_k' not in c.columns:
        hh14 = c['high'].rolling(14).max(); ll14 = c['low'].rolling(14).min()
        c['stoch_k'] = 100 * (c['close'] - ll14) / (hh14 - ll14 + 1e-10)
        c['stoch_k'] = c['stoch_k'].rolling(3).mean()  # %K smoothed
        c['stoch_d'] = c['stoch_k'].rolling(3).mean()   # %D
    # TRIX (15-period triple smoothed EMA)
    if 'trix' not in c.columns:
        e1 = c['close'].ewm(span=15, adjust=False).mean()
        e2 = e1.ewm(span=15, adjust=False).mean()
        e3 = e2.ewm(span=15, adjust=False).mean()
        c['trix'] = e3.pct_change() * 10000  # in basis points
        c['trix_sig'] = c['trix'].ewm(span=9, adjust=False).mean()
    # Supertrend direct signal (direction change)
    if 'st_dir' not in c.columns:
        c['st_dir'] = st_dir if 'st_dir' in dir() else c.get('psar_dir', 0)
    # ROC (Rate of Change 10)
    if 'roc10' not in c.columns:
        c['roc10'] = (c['close'] / c['close'].shift(10) - 1) * 100
    # Elder Ray (bull/bear power)
    if 'bull_power' not in c.columns:
        ema13_er = c['close'].ewm(span=13, adjust=False).mean()
        c['bull_power'] = c['high'] - ema13_er
        c['bear_power'] = c['low'] - ema13_er
    # Aroon (25-period)
    if 'aroon_up' not in c.columns:
        p = 25
        c['aroon_up'] = c['high'].rolling(p+1).apply(lambda x: x.argmax() / p * 100, raw=True)
        c['aroon_dn'] = c['low'].rolling(p+1).apply(lambda x: x.argmin() / p * 100, raw=True)
    # Stochastic RSI
    if 'stoch_rsi' not in c.columns and 'rsi14' in c.columns:
        rsi_min = c['rsi14'].rolling(14).min(); rsi_max = c['rsi14'].rolling(14).max()
        c['stoch_rsi'] = (c['rsi14'] - rsi_min) / (rsi_max - rsi_min + 1e-10)
        c['stoch_rsi_k'] = c['stoch_rsi'].rolling(3).mean()
        c['stoch_rsi_d'] = c['stoch_rsi_k'].rolling(3).mean()
    # CCI extreme flag (for CCI > 100 reversal)
    # (cci14 and cci20 already computed)
    # Keltner + Bollinger squeeze (BB inside KC)
    if 'kb_squeeze' not in c.columns and 'bb_up' in c.columns and 'kc_up' in c.columns:
        c['kb_squeeze'] = ((c['bb_up'] < c['kc_up']) & (c['bb_lo'] > c['kc_lo'])).astype(int)
    # Linear regression slope (20-period)
    if 'lr_slope' not in c.columns:
        def _lr_slope(x):
            n = len(x); xs = np.arange(n)
            return (n * np.dot(xs, x) - xs.sum() * x.sum()) / (n * (xs**2).sum() - xs.sum()**2 + 1e-10)
        c['lr_slope'] = c['close'].rolling(20).apply(_lr_slope, raw=True)
    return c

def detect_all(candles, ci, row, ct, today, hour, atr, trig, tv, tok, lon, prev_day_data, add, prev2_day_data=None):
    """Detecte les signaux pour toutes les strats."""
    # Wrapper add qui filtre les strats retirees
    _orig_add = add
    def add(sn, d, e):
        if sn not in REMOVED_STRATS: _orig_add(sn, d, e)
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

    # ── INDICATOR STRATS V6 (from optimize_all.py) ──

    # ALL_RSI_50: RSI 50 cross
    if 'ALL_RSI_50' not in trig and 'rsi14' in row.index and pd.notna(row.get('rsi14')):
        if prev['rsi14']<50 and row['rsi14']>=50: add('ALL_RSI_50','long',row['close']); trig['ALL_RSI_50']=True
        elif prev['rsi14']>50 and row['rsi14']<=50: add('ALL_RSI_50','short',row['close']); trig['ALL_RSI_50']=True

    # ALL_RSI_DIV: RSI divergence (new low + higher RSI = bullish, etc.)
    if 'ALL_RSI_DIV' not in trig and ci >= 10 and 'rsi14' in row.index and pd.notna(row.get('rsi14')):
        l10 = candles.iloc[ci-9:ci+1]
        if row['low']<l10.iloc[:-1]['low'].min() and row['rsi14']>l10.iloc[:-1]['rsi14'].min() and row['close']>row['open']:
            add('ALL_RSI_DIV','long',row['close']); trig['ALL_RSI_DIV']=True
        if row['high']>l10.iloc[:-1]['high'].max() and row['rsi14']<l10.iloc[:-1]['rsi14'].max() and row['close']<row['open']:
            add('ALL_RSI_DIV','short',row['close']); trig['ALL_RSI_DIV']=True

    # ALL_FISHER_9: Fisher transform signal cross
    if 'ALL_FISHER_9' not in trig and 'fisher9' in row.index and pd.notna(row.get('fisher9')):
        if prev['fisher9']<prev['fisher9_sig'] and row['fisher9']>row['fisher9_sig']: add('ALL_FISHER_9','long',row['close']); trig['ALL_FISHER_9']=True
        elif prev['fisher9']>prev['fisher9_sig'] and row['fisher9']<row['fisher9_sig']: add('ALL_FISHER_9','short',row['close']); trig['ALL_FISHER_9']=True

    # ALL_DPO_14: DPO zero cross
    if 'ALL_DPO_14' not in trig and 'dpo14' in row.index and pd.notna(row.get('dpo14')):
        if prev['dpo14']<0 and row['dpo14']>=0: add('ALL_DPO_14','long',row['close']); trig['ALL_DPO_14']=True
        elif prev['dpo14']>0 and row['dpo14']<=0: add('ALL_DPO_14','short',row['close']); trig['ALL_DPO_14']=True

    # ALL_AO_SAUCER: Awesome Oscillator saucer
    if 'ALL_AO_SAUCER' not in trig and ci >= 4 and 'ao' in row.index and pd.notna(row.get('ao')):
        a = [candles.iloc[ci-j]['ao'] for j in range(3,-1,-1)]
        if all(pd.notna(x) for x in a):
            if a[0]>0 and a[1]<a[0] and a[2]<a[1] and a[3]>a[2] and a[3]>0: add('ALL_AO_SAUCER','long',row['close']); trig['ALL_AO_SAUCER']=True
            elif a[0]<0 and a[1]>a[0] and a[2]>a[1] and a[3]<a[2] and a[3]<0: add('ALL_AO_SAUCER','short',row['close']); trig['ALL_AO_SAUCER']=True

    # ALL_HMA_CROSS: HMA 9/21 cross
    if 'ALL_HMA_CROSS' not in trig and 'hma9' in row.index and pd.notna(row.get('hma9')) and pd.notna(row.get('hma21')):
        if prev['hma9']<prev['hma21'] and row['hma9']>row['hma21']: add('ALL_HMA_CROSS','long',row['close']); trig['ALL_HMA_CROSS']=True
        elif prev['hma9']>prev['hma21'] and row['hma9']<row['hma21']: add('ALL_HMA_CROSS','short',row['close']); trig['ALL_HMA_CROSS']=True

    # ALL_HMA_DIR: HMA21 direction change
    if 'ALL_HMA_DIR' not in trig and ci >= 2 and 'hma21' in row.index and pd.notna(row.get('hma21')):
        if candles.iloc[ci-2]['hma21']>prev['hma21'] and prev['hma21']<row['hma21']: add('ALL_HMA_DIR','long',row['close']); trig['ALL_HMA_DIR']=True
        elif candles.iloc[ci-2]['hma21']<prev['hma21'] and prev['hma21']>row['hma21']: add('ALL_HMA_DIR','short',row['close']); trig['ALL_HMA_DIR']=True

    # ALL_DC10_EMA: Donchian 10 + EMA21 filter
    if 'ALL_DC10_EMA' not in trig and 'dc10_h' in row.index and pd.notna(prev.get('dc10_h')) and pd.notna(row.get('ema21')):
        if row['close']>prev['dc10_h'] and row['close']>row['ema21']: add('ALL_DC10_EMA','long',row['close']); trig['ALL_DC10_EMA']=True
        elif row['close']<prev['dc10_l'] and row['close']<row['ema21']: add('ALL_DC10_EMA','short',row['close']); trig['ALL_DC10_EMA']=True

    # ALL_CMO_14_ZERO: CMO 14 zero cross
    if 'ALL_CMO_14_ZERO' not in trig and 'cmo14' in row.index and pd.notna(row.get('cmo14')):
        if prev['cmo14']<0 and row['cmo14']>=0: add('ALL_CMO_14_ZERO','long',row['close']); trig['ALL_CMO_14_ZERO']=True
        elif prev['cmo14']>0 and row['cmo14']<=0: add('ALL_CMO_14_ZERO','short',row['close']); trig['ALL_CMO_14_ZERO']=True

    # ALL_ICHI_TK: Ichimoku TK cross above/below cloud
    if 'ALL_ICHI_TK' not in trig and 'i_t' in row.index and pd.notna(row.get('i_t')):
        if prev['i_t']<prev['i_k'] and row['i_t']>row['i_k'] and pd.notna(row.get('i_sa')) and row['close']>max(row['i_sa'],row['i_sb']):
            add('ALL_ICHI_TK','long',row['close']); trig['ALL_ICHI_TK']=True
        elif prev['i_t']>prev['i_k'] and row['i_t']<row['i_k'] and pd.notna(row.get('i_sa')) and row['close']<min(row['i_sa'],row['i_sb']):
            add('ALL_ICHI_TK','short',row['close']); trig['ALL_ICHI_TK']=True

    # ALL_MACD_ADX: MACD std cross + ADX>25
    if 'ALL_MACD_ADX' not in trig and 'macd_std' in row.index and pd.notna(row.get('macd_std')) and pd.notna(row.get('adx_s')):
        if row['adx_s']>25 and prev['macd_std']<prev['macd_std_sig'] and row['macd_std']>row['macd_std_sig']: add('ALL_MACD_ADX','long',row['close']); trig['ALL_MACD_ADX']=True
        elif row['adx_s']>25 and prev['macd_std']>prev['macd_std_sig'] and row['macd_std']<row['macd_std_sig']: add('ALL_MACD_ADX','short',row['close']); trig['ALL_MACD_ADX']=True

    # ALL_MACD_STD_SIG: MACD std signal cross
    if 'ALL_MACD_STD_SIG' not in trig and 'macd_std' in row.index and pd.notna(row.get('macd_std')):
        if prev['macd_std']<prev['macd_std_sig'] and row['macd_std']>row['macd_std_sig']: add('ALL_MACD_STD_SIG','long',row['close']); trig['ALL_MACD_STD_SIG']=True
        elif prev['macd_std']>prev['macd_std_sig'] and row['macd_std']<row['macd_std_sig']: add('ALL_MACD_STD_SIG','short',row['close']); trig['ALL_MACD_STD_SIG']=True

    # ALL_MACD_FAST_ZERO: MACD fast zero cross
    if 'ALL_MACD_FAST_ZERO' not in trig and 'macd_fast' in row.index and pd.notna(row.get('macd_fast')):
        if prev['macd_fast']<0 and row['macd_fast']>=0: add('ALL_MACD_FAST_ZERO','long',row['close']); trig['ALL_MACD_FAST_ZERO']=True
        elif prev['macd_fast']>0 and row['macd_fast']<=0: add('ALL_MACD_FAST_ZERO','short',row['close']); trig['ALL_MACD_FAST_ZERO']=True

    # ALL_BB_TIGHT: Tight Bollinger breakout
    if 'ALL_BB_TIGHT' not in trig and 'bb_t_up' in row.index and pd.notna(row.get('bb_t_up')):
        if row['close']>row['bb_t_up'] and prev['close']<=prev['bb_t_up']: add('ALL_BB_TIGHT','long',row['close']); trig['ALL_BB_TIGHT']=True
        elif row['close']<row['bb_t_lo'] and prev['close']>=prev['bb_t_lo']: add('ALL_BB_TIGHT','short',row['close']); trig['ALL_BB_TIGHT']=True

    # ALL_CCI_14_ZERO: CCI14 zero cross
    if 'ALL_CCI_14_ZERO' not in trig and 'cci14' in row.index and pd.notna(row.get('cci14')):
        if prev['cci14']<0 and row['cci14']>=0: add('ALL_CCI_14_ZERO','long',row['close']); trig['ALL_CCI_14_ZERO']=True
        elif prev['cci14']>0 and row['cci14']<=0: add('ALL_CCI_14_ZERO','short',row['close']); trig['ALL_CCI_14_ZERO']=True

    # ALL_CCI_20_ZERO: CCI20 zero cross
    if 'ALL_CCI_20_ZERO' not in trig and 'cci20' in row.index and pd.notna(row.get('cci20')):
        if prev['cci20']<0 and row['cci20']>=0: add('ALL_CCI_20_ZERO','long',row['close']); trig['ALL_CCI_20_ZERO']=True
        elif prev['cci20']>0 and row['cci20']<=0: add('ALL_CCI_20_ZERO','short',row['close']); trig['ALL_CCI_20_ZERO']=True

    # ALL_MTF_BRK: Multi-timeframe 1H breakout
    if 'ALL_MTF_BRK' not in trig and 'high_1h' in row.index and pd.notna(row.get('high_1h')) and ci >= 2:
        if row['close']>prev['high_1h'] and prev['close']<=candles.iloc[ci-2]['high_1h']: add('ALL_MTF_BRK','long',row['close']); trig['ALL_MTF_BRK']=True
        elif row['close']<prev['low_1h'] and prev['close']>=candles.iloc[ci-2]['low_1h']: add('ALL_MTF_BRK','short',row['close']); trig['ALL_MTF_BRK']=True

    # ALL_NR4: Narrow range 4 breakout
    if 'ALL_NR4' not in trig and ci >= 5:
        r_col = 'range' if 'range' in row.index else 'candle_range'
        if r_col in row.index:
            ranges = [candles.iloc[ci-j][r_col] for j in range(4)]
            if row[r_col]==min(ranges) and row[r_col]>0 and abs(row.get('body', row['close']-row['open']))>=0.1*atr:
                add('ALL_NR4','long' if (row.get('body', row['close']-row['open']))>0 else 'short',row['close']); trig['ALL_NR4']=True

    # ALL_PIVOT_BOUNCE: Daily pivot bounce
    if 'ALL_PIVOT_BOUNCE' not in trig and 'pivot' in row.index and pd.notna(row.get('pivot')):
        if prev['low']<=row['pivot']*1.001 and row['close']>row['pivot'] and row['close']>row['open']:
            add('ALL_PIVOT_BOUNCE','long',row['close']); trig['ALL_PIVOT_BOUNCE']=True
        elif prev['high']>=row['pivot']*0.999 and row['close']<row['pivot'] and row['close']<row['open']:
            add('ALL_PIVOT_BOUNCE','short',row['close']); trig['ALL_PIVOT_BOUNCE']=True

    # ALL_PIVOT_BRK: Daily pivot breakout
    if 'ALL_PIVOT_BRK' not in trig and 'pivot' in row.index and pd.notna(row.get('pivot')):
        ab = abs(row.get('body', row['close']-row['open']))
        if prev['close']<row['pivot'] and row['close']>row['pivot'] and ab>=0.2*atr: add('ALL_PIVOT_BRK','long',row['close']); trig['ALL_PIVOT_BRK']=True
        elif prev['close']>row['pivot'] and row['close']<row['pivot'] and ab>=0.2*atr: add('ALL_PIVOT_BRK','short',row['close']); trig['ALL_PIVOT_BRK']=True

    # ALL_EMA_513: EMA5 cross EMA13
    if 'ALL_EMA_513' not in trig and 'ema5' in row.index and pd.notna(row.get('ema5')) and pd.notna(row.get('ema13')):
        if prev['ema5']<prev['ema13'] and row['ema5']>row['ema13']: add('ALL_EMA_513','long',row['close']); trig['ALL_EMA_513']=True
        elif prev['ema5']>prev['ema13'] and row['ema5']<row['ema13']: add('ALL_EMA_513','short',row['close']); trig['ALL_EMA_513']=True

    # ALL_EMA_821: EMA8 cross EMA21
    if 'ALL_EMA_821' not in trig and 'ema8' in row.index and pd.notna(row.get('ema8')) and pd.notna(row.get('ema21')):
        if prev['ema8']<prev['ema21'] and row['ema8']>row['ema21']: add('ALL_EMA_821','long',row['close']); trig['ALL_EMA_821']=True
        elif prev['ema8']>prev['ema21'] and row['ema8']<row['ema21']: add('ALL_EMA_821','short',row['close']); trig['ALL_EMA_821']=True

    # ALL_EMA_921: EMA9 cross EMA21
    if 'ALL_EMA_921' not in trig and 'ema9' in row.index and pd.notna(row.get('ema9')) and pd.notna(row.get('ema21')):
        if prev['ema9']<prev['ema21'] and row['ema9']>row['ema21']: add('ALL_EMA_921','long',row['close']); trig['ALL_EMA_921']=True
        elif prev['ema9']>prev['ema21'] and row['ema9']<row['ema21']: add('ALL_EMA_921','short',row['close']); trig['ALL_EMA_921']=True

    # ALL_EMA_TREND_PB: EMA trend pullback
    if 'ALL_EMA_TREND_PB' not in trig and 'ema50' in row.index and pd.notna(row.get('ema50')) and pd.notna(row.get('ema200')) and pd.notna(row.get('ema20')):
        if row['ema50']>row['ema200'] and prev['low']<=prev['ema20'] and row['close']>row['ema20'] and row['close']>row['open']:
            add('ALL_EMA_TREND_PB','long',row['close']); trig['ALL_EMA_TREND_PB']=True
        elif row['ema50']<row['ema200'] and prev['high']>=prev['ema20'] and row['close']<row['ema20'] and row['close']<row['open']:
            add('ALL_EMA_TREND_PB','short',row['close']); trig['ALL_EMA_TREND_PB']=True

    # ALL_WILLR_14: Williams %R 14 reversal (from -80/-20)
    if 'ALL_WILLR_14' not in trig and 'wr14' in row.index and pd.notna(row.get('wr14')):
        if prev['wr14']<-80 and row['wr14']>=-80: add('ALL_WILLR_14','long',row['close']); trig['ALL_WILLR_14']=True
        elif prev['wr14']>-20 and row['wr14']<=-20: add('ALL_WILLR_14','short',row['close']); trig['ALL_WILLR_14']=True

    # ALL_MOM_10: Momentum 10 zero cross
    if 'ALL_MOM_10' not in trig and 'mom10' in row.index and pd.notna(row.get('mom10')):
        if prev['mom10']<0 and row['mom10']>=0: add('ALL_MOM_10','long',row['close']); trig['ALL_MOM_10']=True
        elif prev['mom10']>0 and row['mom10']<=0: add('ALL_MOM_10','short',row['close']); trig['ALL_MOM_10']=True

    # ALL_MOM_14: Momentum 14 zero cross
    if 'ALL_MOM_14' not in trig and 'mom14' in row.index and pd.notna(row.get('mom14')):
        if prev['mom14']<0 and row['mom14']>=0: add('ALL_MOM_14','long',row['close']); trig['ALL_MOM_14']=True
        elif prev['mom14']>0 and row['mom14']<=0: add('ALL_MOM_14','short',row['close']); trig['ALL_MOM_14']=True

    # ALL_DC50: Donchian 50 breakout
    if 'ALL_DC50' not in trig and 'dc50_h' in row.index and pd.notna(prev.get('dc50_h')):
        if row['close']>prev['dc50_h']: add('ALL_DC50','long',row['close']); trig['ALL_DC50']=True
        elif row['close']<prev['dc50_l']: add('ALL_DC50','short',row['close']); trig['ALL_DC50']=True

    # TOK_FISHER: Fisher transform Tokyo
    if 0.0<=hour<6.0 and 'TOK_FISHER' not in trig and 'fisher9' in row.index and pd.notna(row.get('fisher9')):
        if prev['fisher9']<prev['fisher9_sig'] and row['fisher9']>row['fisher9_sig']: add('TOK_FISHER','long',row['close']); trig['TOK_FISHER']=True
        elif prev['fisher9']>prev['fisher9_sig'] and row['fisher9']<row['fisher9_sig']: add('TOK_FISHER','short',row['close']); trig['TOK_FISHER']=True

    # TOK_MACD_MED: MACD med cross Tokyo
    if 0.0<=hour<6.0 and 'TOK_MACD_MED' not in trig and 'macd_med' in row.index and pd.notna(row.get('macd_med')):
        if prev['macd_med']<prev['macd_med_sig'] and row['macd_med']>row['macd_med_sig']: add('TOK_MACD_MED','long',row['close']); trig['TOK_MACD_MED']=True
        elif prev['macd_med']>prev['macd_med_sig'] and row['macd_med']<row['macd_med_sig']: add('TOK_MACD_MED','short',row['close']); trig['TOK_MACD_MED']=True

    # LON_DC10: Donchian 10 London-only
    if 8.0<=hour<14.5 and 'LON_DC10' not in trig and 'dc10_h' in row.index and pd.notna(prev.get('dc10_h')):
        if row['close']>prev['dc10_h']: add('LON_DC10','long',row['close']); trig['LON_DC10']=True
        elif row['close']<prev['dc10_l']: add('LON_DC10','short',row['close']); trig['LON_DC10']=True

    # NY_HMA_CROSS: HMA 9/21 cross NY
    if 14.5<=hour<21.0 and 'NY_HMA_CROSS' not in trig and 'hma9' in row.index and pd.notna(row.get('hma9')) and pd.notna(row.get('hma21')):
        if prev['hma9']<prev['hma21'] and row['hma9']>row['hma21']: add('NY_HMA_CROSS','long',row['close']); trig['NY_HMA_CROSS']=True
        elif prev['hma9']>prev['hma21'] and row['hma9']<row['hma21']: add('NY_HMA_CROSS','short',row['close']); trig['NY_HMA_CROSS']=True

    # ALL_CMO_9: CMO 9 reversal (-50/+50)
    if 'ALL_CMO_9' not in trig and 'cmo9' in row.index and pd.notna(row.get('cmo9')):
        if prev['cmo9']<-50 and row['cmo9']>=-50: add('ALL_CMO_9','long',row['close']); trig['ALL_CMO_9']=True
        elif prev['cmo9']>50 and row['cmo9']<=50: add('ALL_CMO_9','short',row['close']); trig['ALL_CMO_9']=True

    # ALL_CMO_14: CMO 14 reversal (-50/+50)
    if 'ALL_CMO_14' not in trig and 'cmo14' in row.index and pd.notna(row.get('cmo14')):
        if prev['cmo14']<-50 and row['cmo14']>=-50: add('ALL_CMO_14','long',row['close']); trig['ALL_CMO_14']=True
        elif prev['cmo14']>50 and row['cmo14']<=50: add('ALL_CMO_14','short',row['close']); trig['ALL_CMO_14']=True

    # ALL_MACD_FAST_SIG: MACD fast signal cross
    if 'ALL_MACD_FAST_SIG' not in trig and 'macd_fast' in row.index and pd.notna(row.get('macd_fast')):
        if prev['macd_fast']<prev['macd_fast_sig'] and row['macd_fast']>row['macd_fast_sig']: add('ALL_MACD_FAST_SIG','long',row['close']); trig['ALL_MACD_FAST_SIG']=True
        elif prev['macd_fast']>prev['macd_fast_sig'] and row['macd_fast']<row['macd_fast_sig']: add('ALL_MACD_FAST_SIG','short',row['close']); trig['ALL_MACD_FAST_SIG']=True

    # ALL_MACD_MED_SIG: MACD med signal cross
    if 'ALL_MACD_MED_SIG' not in trig and 'macd_med' in row.index and pd.notna(row.get('macd_med')):
        if prev['macd_med']<prev['macd_med_sig'] and row['macd_med']>row['macd_med_sig']: add('ALL_MACD_MED_SIG','long',row['close']); trig['ALL_MACD_MED_SIG']=True
        elif prev['macd_med']>prev['macd_med_sig'] and row['macd_med']<row['macd_med_sig']: add('ALL_MACD_MED_SIG','short',row['close']); trig['ALL_MACD_MED_SIG']=True

    # ALL_WILLR_7: Williams %R 7 reversal
    if 'ALL_WILLR_7' not in trig and 'wr7' in row.index and pd.notna(row.get('wr7')):
        if prev['wr7']<-80 and row['wr7']>=-80: add('ALL_WILLR_7','long',row['close']); trig['ALL_WILLR_7']=True
        elif prev['wr7']>-20 and row['wr7']<=-20: add('ALL_WILLR_7','short',row['close']); trig['ALL_WILLR_7']=True

    # ── NEW STRATS V7 ──

    # ALL_STOCH_CROSS: Stochastic K crosses D
    if 'ALL_STOCH_CROSS' not in trig and 'stoch_k' in row.index and pd.notna(row.get('stoch_k')):
        if prev['stoch_k']<prev['stoch_d'] and row['stoch_k']>row['stoch_d']: add('ALL_STOCH_CROSS','long',row['close']); trig['ALL_STOCH_CROSS']=True
        elif prev['stoch_k']>prev['stoch_d'] and row['stoch_k']<row['stoch_d']: add('ALL_STOCH_CROSS','short',row['close']); trig['ALL_STOCH_CROSS']=True

    # ALL_STOCH_OB: Stochastic overbought/oversold reversal (cross back from extremes)
    if 'ALL_STOCH_OB' not in trig and 'stoch_k' in row.index and pd.notna(row.get('stoch_k')):
        if prev['stoch_k']<20 and row['stoch_k']>=20 and row['close']>row['open']: add('ALL_STOCH_OB','long',row['close']); trig['ALL_STOCH_OB']=True
        elif prev['stoch_k']>80 and row['stoch_k']<=80 and row['close']<row['open']: add('ALL_STOCH_OB','short',row['close']); trig['ALL_STOCH_OB']=True

    # ALL_TRIX: TRIX signal cross
    if 'ALL_TRIX' not in trig and 'trix' in row.index and pd.notna(row.get('trix')):
        if prev['trix']<prev['trix_sig'] and row['trix']>row['trix_sig']: add('ALL_TRIX','long',row['close']); trig['ALL_TRIX']=True
        elif prev['trix']>prev['trix_sig'] and row['trix']<row['trix_sig']: add('ALL_TRIX','short',row['close']); trig['ALL_TRIX']=True

    # ALL_SUPERTREND: Supertrend direction change
    if 'ALL_SUPERTREND' not in trig and 'psar_dir' in row.index:
        if prev.get('psar_dir',0)==-1 and row['psar_dir']==1: add('ALL_SUPERTREND','long',row['close']); trig['ALL_SUPERTREND']=True
        elif prev.get('psar_dir',0)==1 and row['psar_dir']==-1: add('ALL_SUPERTREND','short',row['close']); trig['ALL_SUPERTREND']=True

    # ALL_ROC_ZERO: Rate of Change 10 zero cross
    if 'ALL_ROC_ZERO' not in trig and 'roc10' in row.index and pd.notna(row.get('roc10')):
        if prev['roc10']<0 and row['roc10']>=0: add('ALL_ROC_ZERO','long',row['close']); trig['ALL_ROC_ZERO']=True
        elif prev['roc10']>0 and row['roc10']<=0: add('ALL_ROC_ZERO','short',row['close']); trig['ALL_ROC_ZERO']=True

    # ALL_ELDER_BULL: Bull power crosses zero from below
    if 'ALL_ELDER_BULL' not in trig and 'bull_power' in row.index and pd.notna(row.get('bull_power')):
        if prev['bull_power']<0 and row['bull_power']>=0: add('ALL_ELDER_BULL','long',row['close']); trig['ALL_ELDER_BULL']=True

    # ALL_ELDER_BEAR: Bear power crosses zero from above
    if 'ALL_ELDER_BEAR' not in trig and 'bear_power' in row.index and pd.notna(row.get('bear_power')):
        if prev['bear_power']>0 and row['bear_power']<=0: add('ALL_ELDER_BEAR','short',row['close']); trig['ALL_ELDER_BEAR']=True

    # ALL_AROON_CROSS: Aroon up crosses above Aroon down
    if 'ALL_AROON_CROSS' not in trig and 'aroon_up' in row.index and pd.notna(row.get('aroon_up')):
        if prev['aroon_up']<prev['aroon_dn'] and row['aroon_up']>row['aroon_dn']: add('ALL_AROON_CROSS','long',row['close']); trig['ALL_AROON_CROSS']=True
        elif prev['aroon_up']>prev['aroon_dn'] and row['aroon_up']<row['aroon_dn']: add('ALL_AROON_CROSS','short',row['close']); trig['ALL_AROON_CROSS']=True

    # ALL_STOCH_RSI: Stochastic RSI K crosses D from oversold/overbought
    if 'ALL_STOCH_RSI' not in trig and 'stoch_rsi_k' in row.index and pd.notna(row.get('stoch_rsi_k')):
        if prev['stoch_rsi_k']<prev['stoch_rsi_d'] and row['stoch_rsi_k']>row['stoch_rsi_d'] and row['stoch_rsi_k']<0.3:
            add('ALL_STOCH_RSI','long',row['close']); trig['ALL_STOCH_RSI']=True
        elif prev['stoch_rsi_k']>prev['stoch_rsi_d'] and row['stoch_rsi_k']<row['stoch_rsi_d'] and row['stoch_rsi_k']>0.7:
            add('ALL_STOCH_RSI','short',row['close']); trig['ALL_STOCH_RSI']=True

    # ALL_CCI_100: CCI 14 crosses back from extreme (>100 or <-100)
    if 'ALL_CCI_100' not in trig and 'cci14' in row.index and pd.notna(row.get('cci14')):
        if prev['cci14']<-100 and row['cci14']>=-100 and row['close']>row['open']: add('ALL_CCI_100','long',row['close']); trig['ALL_CCI_100']=True
        elif prev['cci14']>100 and row['cci14']<=100 and row['close']<row['open']: add('ALL_CCI_100','short',row['close']); trig['ALL_CCI_100']=True

    # ALL_KB_SQUEEZE: Keltner-Bollinger squeeze breakout (BB was inside KC, now breaks out)
    if 'ALL_KB_SQUEEZE' not in trig and 'kb_squeeze' in row.index and pd.notna(row.get('kb_squeeze')):
        if prev.get('kb_squeeze',0)==1 and row['kb_squeeze']==0:
            if row['close']>row.get('kc_up',99999): add('ALL_KB_SQUEEZE','long',row['close']); trig['ALL_KB_SQUEEZE']=True
            elif row['close']<row.get('kc_lo',0): add('ALL_KB_SQUEEZE','short',row['close']); trig['ALL_KB_SQUEEZE']=True

    # ALL_LR_BREAK: Linear regression slope reversal (slope changes sign)
    if 'ALL_LR_BREAK' not in trig and 'lr_slope' in row.index and pd.notna(row.get('lr_slope')):
        if prev['lr_slope']<0 and row['lr_slope']>0: add('ALL_LR_BREAK','long',row['close']); trig['ALL_LR_BREAK']=True
        elif prev['lr_slope']>0 and row['lr_slope']<0: add('ALL_LR_BREAK','short',row['close']); trig['ALL_LR_BREAK']=True

    # ALL_ADX_RSI50: ADX > 25 + RSI crosses 50 (trend confirmation + momentum)
    if 'ALL_ADX_RSI50' not in trig and 'adx_f' in row.index and pd.notna(row.get('adx_f')) and pd.notna(row.get('rsi14')):
        if row['adx_f']>25 and prev['rsi14']<50 and row['rsi14']>=50: add('ALL_ADX_RSI50','long',row['close']); trig['ALL_ADX_RSI50']=True
        elif row['adx_f']>25 and prev['rsi14']>50 and row['rsi14']<=50: add('ALL_ADX_RSI50','short',row['close']); trig['ALL_ADX_RSI50']=True

    # ALL_MACD_DIV: MACD divergence (price new low but MACD higher low = bullish)
    if 'ALL_MACD_DIV' not in trig and ci >= 20 and 'macd_hist' in row.index and pd.notna(row.get('macd_hist')):
        l20 = candles.iloc[ci-19:ci+1]
        if row['low']<l20.iloc[:-1]['low'].min() and row['macd_hist']>l20.iloc[:-1]['macd_hist'].min() and row['close']>row['open']:
            add('ALL_MACD_DIV','long',row['close']); trig['ALL_MACD_DIV']=True
        elif row['high']>l20.iloc[:-1]['high'].max() and row['macd_hist']<l20.iloc[:-1]['macd_hist'].max() and row['close']<row['open']:
            add('ALL_MACD_DIV','short',row['close']); trig['ALL_MACD_DIV']=True

    # ALL_STOCH_PIVOT: Stochastic oversold + price near pivot support
    if 'ALL_STOCH_PIVOT' not in trig and 'stoch_k' in row.index and 'pivot' in row.index and pd.notna(row.get('stoch_k')) and pd.notna(row.get('pivot')):
        if row['stoch_k']<20 and prev['low']<=row['pivot']*1.002 and row['close']>row['pivot'] and row['close']>row['open']:
            add('ALL_STOCH_PIVOT','long',row['close']); trig['ALL_STOCH_PIVOT']=True
        elif row['stoch_k']>80 and prev['high']>=row['pivot']*0.998 and row['close']<row['pivot'] and row['close']<row['open']:
            add('ALL_STOCH_PIVOT','short',row['close']); trig['ALL_STOCH_PIVOT']=True

    # Session-filtered versions
    # TOK_STOCH: Stochastic reversal Tokyo
    if 0.0<=hour<6.0 and 'TOK_STOCH' not in trig and 'stoch_k' in row.index and pd.notna(row.get('stoch_k')):
        if prev['stoch_k']<20 and row['stoch_k']>=20: add('TOK_STOCH','long',row['close']); trig['TOK_STOCH']=True
        elif prev['stoch_k']>80 and row['stoch_k']<=80: add('TOK_STOCH','short',row['close']); trig['TOK_STOCH']=True

    # TOK_TRIX: TRIX cross Tokyo
    if 0.0<=hour<6.0 and 'TOK_TRIX' not in trig and 'trix' in row.index and pd.notna(row.get('trix')):
        if prev['trix']<prev['trix_sig'] and row['trix']>row['trix_sig']: add('TOK_TRIX','long',row['close']); trig['TOK_TRIX']=True
        elif prev['trix']>prev['trix_sig'] and row['trix']<row['trix_sig']: add('TOK_TRIX','short',row['close']); trig['TOK_TRIX']=True

    # LON_STOCH: Stochastic reversal London
    if 8.0<=hour<14.5 and 'LON_STOCH' not in trig and 'stoch_k' in row.index and pd.notna(row.get('stoch_k')):
        if prev['stoch_k']<20 and row['stoch_k']>=20: add('LON_STOCH','long',row['close']); trig['LON_STOCH']=True
        elif prev['stoch_k']>80 and row['stoch_k']<=80: add('LON_STOCH','short',row['close']); trig['LON_STOCH']=True

    # NY_ELDER: Elder Ray reversal NY session
    if 14.5<=hour<21.0 and 'NY_ELDER' not in trig and 'bull_power' in row.index and pd.notna(row.get('bull_power')):
        if prev['bull_power']<0 and row['bull_power']>=0 and row['close']>row['open']:
            add('NY_ELDER','long',row['close']); trig['NY_ELDER']=True
        elif prev['bear_power']>0 and row['bear_power']<=0 and row['close']<row['open']:
            add('NY_ELDER','short',row['close']); trig['NY_ELDER']=True
