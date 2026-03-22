"""
Exploration indicators V2 — strategies de la recherche web.
MACD rapide, triple EMA, RSI divergence, TTM Squeeze, Ichimoku, Stoch+EMA, ADX rapide.
Tout sur bougies FERMEES, ZERO look-ahead.
"""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
from dotenv import load_dotenv; load_dotenv()
from phase1_poc_calculator import get_conn, compute_atr, get_trading_days
from phase3_analyze import load_candles_5m
from strats import SL, ACT, TRAIL, sim_exit

conn = get_conn()
candles = load_candles_5m(conn)
daily_atr, global_atr = compute_atr(conn)
trading_days = get_trading_days(conn)
cur = conn.cursor()
cur.execute("""SELECT DATE_TRUNC('month', time), AVG(ask-bid) FROM market_ticks_xauusd WHERE ask>bid AND ask-bid<10 GROUP BY 1""")
monthly_spread = {r[0].strftime("%Y-%m"): float(r[1]) for r in cur.fetchall()}
cur.close(); conn.close()
avg_sp = np.mean(list(monthly_spread.values()))
def prev_day(day):
    for di, d in enumerate(trading_days):
        if d >= day: return trading_days[di-1] if di > 0 else None
    return None
def get_sp(day):
    return 2 * monthly_spread.get(str(day.year)+"-"+str(day.month).zfill(2), avg_sp)

print("Precalcul indicateurs...", flush=True)
c = candles.copy()
c['body'] = c['close'] - c['open']
c['range'] = c['high'] - c['low']

# EMAs
for p in [5,8,9,13,20,21,50]:
    c[f'ema{p}'] = c['close'].ewm(span=p, adjust=False).mean()

# RSI multiple periodes
for p in [7,9,14]:
    delta = c['close'].diff()
    gain = delta.clip(lower=0); loss = (-delta).clip(lower=0)
    ag = gain.ewm(alpha=1.0/p, min_periods=p, adjust=False).mean()
    al = loss.ewm(alpha=1.0/p, min_periods=p, adjust=False).mean()
    c[f'rsi{p}'] = 100 - 100/(1+ag/(al+1e-10))

# MACD standard + rapide
for fast,slow,sig,name in [(12,26,9,'std'),(5,13,1,'fast'),(8,17,9,'med')]:
    ef = c['close'].ewm(span=fast, adjust=False).mean()
    es = c['close'].ewm(span=slow, adjust=False).mean()
    c[f'macd_{name}'] = ef - es
    c[f'macd_{name}_sig'] = c[f'macd_{name}'].ewm(span=max(sig,2), adjust=False).mean()
    c[f'macd_{name}_hist'] = c[f'macd_{name}'] - c[f'macd_{name}_sig']

# Bollinger standard + tight
for per,std,name in [(20,2.0,'std'),(10,1.5,'tight')]:
    c[f'bb_{name}_mid'] = c['close'].rolling(per).mean()
    c[f'bb_{name}_std'] = c['close'].rolling(per).std()
    c[f'bb_{name}_up'] = c[f'bb_{name}_mid'] + std * c[f'bb_{name}_std']
    c[f'bb_{name}_lo'] = c[f'bb_{name}_mid'] - std * c[f'bb_{name}_std']
    c[f'bb_{name}_w'] = (c[f'bb_{name}_up'] - c[f'bb_{name}_lo']) / (c[f'bb_{name}_mid']+1e-10)

# Stochastic multiple
for k_per,name in [(5,'fast'),(9,'med'),(14,'std')]:
    c[f'stk_{name}_l'] = c['low'].rolling(k_per).min()
    c[f'stk_{name}_h'] = c['high'].rolling(k_per).max()
    c[f'stk_{name}_k'] = 100*(c['close']-c[f'stk_{name}_l'])/(c[f'stk_{name}_h']-c[f'stk_{name}_l']+1e-10)
    c[f'stk_{name}_d'] = c[f'stk_{name}_k'].rolling(3).mean()

# ADX standard + rapide
tr = np.maximum(c['high']-c['low'], np.maximum(abs(c['high']-c['close'].shift(1)), abs(c['low']-c['close'].shift(1))))
for p,name in [(14,'std'),(7,'fast')]:
    plus_dm = c['high'].diff().clip(lower=0)
    minus_dm = (-c['low'].diff()).clip(lower=0)
    mask = plus_dm > minus_dm
    pdm = plus_dm.where(mask, 0); mdm = minus_dm.where(~mask, 0)
    atr_p = tr.ewm(span=p, adjust=False).mean()
    pdi = 100*pdm.ewm(span=p, adjust=False).mean()/(atr_p+1e-10)
    mdi = 100*mdm.ewm(span=p, adjust=False).mean()/(atr_p+1e-10)
    dx = 100*abs(pdi-mdi)/(pdi+mdi+1e-10)
    c[f'adx_{name}'] = dx.ewm(span=p, adjust=False).mean()
    c[f'pdi_{name}'] = pdi; c[f'mdi_{name}'] = mdi

# Donchian
for p in [10,20,55]:
    c[f'dc{p}_h'] = c['high'].rolling(p).max()
    c[f'dc{p}_l'] = c['low'].rolling(p).min()

# Keltner
c['kc_mid'] = c['ema20']
c['kc_atr'] = tr.ewm(span=10, adjust=False).mean()
c['kc_up'] = c['kc_mid'] + 2.0*c['kc_atr']
c['kc_lo'] = c['kc_mid'] - 2.0*c['kc_atr']

# TTM Squeeze: BB inside KC
c['bb_inside_kc'] = (c['bb_std_up'] < c['kc_up']) & (c['bb_std_lo'] > c['kc_lo'])
# Momentum for TTM
c['ttm_mom'] = c['close'] - c['close'].rolling(20).mean()

# Ichimoku (fast: 6,13,26)
c['ichi_tenkan'] = (c['high'].rolling(6).max() + c['low'].rolling(6).min()) / 2
c['ichi_kijun'] = (c['high'].rolling(13).max() + c['low'].rolling(13).min()) / 2
c['ichi_senkou_a'] = ((c['ichi_tenkan'] + c['ichi_kijun']) / 2).shift(13)
c['ichi_senkou_b'] = ((c['high'].rolling(26).max() + c['low'].rolling(26).min()) / 2).shift(13)

# StochRSI
rsi14 = c['rsi14']
c['stochrsi_k'] = 100*(rsi14 - rsi14.rolling(14).min()) / (rsi14.rolling(14).max() - rsi14.rolling(14).min() + 1e-10)
c['stochrsi_d'] = c['stochrsi_k'].rolling(3).mean()

# EMA slopes
c['ema21_slope'] = c['ema21'] - c['ema21'].shift(3)

print("Collecte des signaux...", flush=True)
S = {}
prev_d = None; trig = {}; day_atr = None

for ci in range(100, len(c)):
    row = c.iloc[ci]; prev = c.iloc[ci-1]; ct = row['ts_dt']; today = ct.date()
    hour = ct.hour + ct.minute / 60.0
    if today != prev_d:
        prev_d = today; trig = {}
        pd_ = prev_day(today); day_atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    atr = day_atr
    if atr == 0 or atr is None: continue

    def add(sn, d, e):
        b, ex = sim_exit(c, ci, e, d, atr, check_entry_candle=False)
        pnl = (ex-e) if d=='long' else (e-ex)
        S.setdefault(sn,[]).append({'date':today,'dir':d,'pnl_oz':pnl-get_sp(today)})

    # ═══════════════════════════════════════════
    # MACD RAPIDE (5,13,1)
    # ═══════════════════════════════════════════
    sn = 'ALL_MACD_FAST_SIG'
    if sn not in trig and pd.notna(row['macd_fast']) and pd.notna(prev['macd_fast']):
        if prev['macd_fast'] < prev['macd_fast_sig'] and row['macd_fast'] > row['macd_fast_sig']:
            add(sn,'long',row['close']); trig[sn]=True
        elif prev['macd_fast'] > prev['macd_fast_sig'] and row['macd_fast'] < row['macd_fast_sig']:
            add(sn,'short',row['close']); trig[sn]=True

    sn = 'ALL_MACD_FAST_ZERO'
    if sn not in trig and pd.notna(row['macd_fast']):
        if prev['macd_fast'] < 0 and row['macd_fast'] >= 0:
            add(sn,'long',row['close']); trig[sn]=True
        elif prev['macd_fast'] > 0 and row['macd_fast'] <= 0:
            add(sn,'short',row['close']); trig[sn]=True

    # MACD (8,17,9)
    sn = 'ALL_MACD_MED_SIG'
    if sn not in trig and pd.notna(row['macd_med']):
        if prev['macd_med'] < prev['macd_med_sig'] and row['macd_med'] > row['macd_med_sig']:
            add(sn,'long',row['close']); trig[sn]=True
        elif prev['macd_med'] > prev['macd_med_sig'] and row['macd_med'] < row['macd_med_sig']:
            add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # TRIPLE EMA RIBBON (8/13/21)
    # ═══════════════════════════════════════════
    sn = 'ALL_EMA_RIBBON'
    if sn not in trig and pd.notna(row['ema8']):
        # Stacked bullish: 8>13>21
        if row['ema8']>row['ema13']>row['ema21'] and not(prev['ema8']>prev['ema13']>prev['ema21']):
            add(sn,'long',row['close']); trig[sn]=True
        elif row['ema8']<row['ema13']<row['ema21'] and not(prev['ema8']<prev['ema13']<prev['ema21']):
            add(sn,'short',row['close']); trig[sn]=True

    # EMA 20/50 pullback
    sn = 'ALL_EMA_2050_PB'
    if sn not in trig and pd.notna(row['ema20']) and pd.notna(row['ema50']):
        if row['ema20'] > row['ema50']:
            if prev['low'] <= prev['ema20'] and row['close'] > row['ema20']:
                add(sn,'long',row['close']); trig[sn]=True
        elif row['ema20'] < row['ema50']:
            if prev['high'] >= prev['ema20'] and row['close'] < row['ema20']:
                add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # RSI DIVERGENCE (simplified)
    # ═══════════════════════════════════════════
    sn = 'ALL_RSI_DIV'
    if sn not in trig and ci >= 10 and pd.notna(row['rsi14']):
        # Bullish: price lower low, RSI higher low (look at last 10 bars)
        last10 = c.iloc[ci-9:ci+1]
        price_ll = row['low'] < last10.iloc[:-1]['low'].min()
        rsi_hl = row['rsi14'] > last10.iloc[:-1]['rsi14'].min()
        if price_ll and rsi_hl and row['close'] > row['open']:
            add(sn,'long',row['close']); trig[sn]=True
        price_hh = row['high'] > last10.iloc[:-1]['high'].max()
        rsi_lh = row['rsi14'] < last10.iloc[:-1]['rsi14'].max()
        if price_hh and rsi_lh and row['close'] < row['open']:
            add(sn,'short',row['close']); trig[sn]=True

    # RSI(9) extreme 25/75
    sn = 'ALL_RSI9_EXT'
    if sn not in trig and pd.notna(row['rsi9']):
        if prev['rsi9'] < 25 and row['rsi9'] >= 25:
            add(sn,'long',row['close']); trig[sn]=True
        elif prev['rsi9'] > 75 and row['rsi9'] <= 75:
            add(sn,'short',row['close']); trig[sn]=True

    # RSI(14) + EMA(50) filter
    sn = 'ALL_RSI_EMA50'
    if sn not in trig and pd.notna(row['rsi14']) and pd.notna(row['ema50']):
        if row['rsi14'] < 30 and row['close'] > row['ema50']:
            add(sn,'long',row['close']); trig[sn]=True
        elif row['rsi14'] > 70 and row['close'] < row['ema50']:
            add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # TTM SQUEEZE
    # ═══════════════════════════════════════════
    sn = 'ALL_TTM_SQUEEZE'
    if sn not in trig and pd.notna(row['bb_inside_kc']):
        was_squeeze = prev['bb_inside_kc'] if pd.notna(prev['bb_inside_kc']) else False
        now_free = not row['bb_inside_kc']
        if was_squeeze and now_free:
            if row['ttm_mom'] > 0 and row['ttm_mom'] > prev['ttm_mom']:
                add(sn,'long',row['close']); trig[sn]=True
            elif row['ttm_mom'] < 0 and row['ttm_mom'] < prev['ttm_mom']:
                add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # ICHIMOKU (fast 6/13/26)
    # ═══════════════════════════════════════════
    sn = 'ALL_ICHI_CLOUD'
    if sn not in trig and pd.notna(row['ichi_senkou_a']) and pd.notna(row['ichi_senkou_b']):
        cloud_top = max(row['ichi_senkou_a'], row['ichi_senkou_b'])
        cloud_bot = min(row['ichi_senkou_a'], row['ichi_senkou_b'])
        prev_cloud_top = max(prev['ichi_senkou_a'], prev['ichi_senkou_b']) if pd.notna(prev['ichi_senkou_a']) else cloud_top
        if prev['close'] <= prev_cloud_top and row['close'] > cloud_top and row['ichi_tenkan'] > row['ichi_kijun']:
            add(sn,'long',row['close']); trig[sn]=True
        elif prev['close'] >= cloud_bot and row['close'] < cloud_bot and row['ichi_tenkan'] < row['ichi_kijun']:
            add(sn,'short',row['close']); trig[sn]=True

    # Ichimoku TK cross
    sn = 'ALL_ICHI_TK'
    if sn not in trig and pd.notna(row['ichi_tenkan']):
        if prev['ichi_tenkan'] < prev['ichi_kijun'] and row['ichi_tenkan'] > row['ichi_kijun']:
            if row['close'] > max(row['ichi_senkou_a'], row['ichi_senkou_b']) if pd.notna(row['ichi_senkou_a']) else True:
                add(sn,'long',row['close']); trig[sn]=True
        elif prev['ichi_tenkan'] > prev['ichi_kijun'] and row['ichi_tenkan'] < row['ichi_kijun']:
            if row['close'] < min(row['ichi_senkou_a'], row['ichi_senkou_b']) if pd.notna(row['ichi_senkou_a']) else True:
                add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # STOCHASTIC + EMA FILTER
    # ═══════════════════════════════════════════
    sn = 'ALL_STOCH_EMA'
    if sn not in trig and pd.notna(row['stk_med_k']) and pd.notna(row['ema21']):
        if row['stk_med_k']<20 and prev['stk_med_k']<prev['stk_med_d'] and row['stk_med_k']>row['stk_med_d'] and row['close']>row['ema21']:
            add(sn,'long',row['close']); trig[sn]=True
        elif row['stk_med_k']>80 and prev['stk_med_k']>prev['stk_med_d'] and row['stk_med_k']<row['stk_med_d'] and row['close']<row['ema21']:
            add(sn,'short',row['close']); trig[sn]=True

    # Stoch ultra-fast (5,3,3) extreme 15/85
    sn = 'ALL_STOCH_ULTRA'
    if sn not in trig and pd.notna(row['stk_fast_k']):
        if row['stk_fast_k']<15 and prev['stk_fast_k']<prev['stk_fast_d'] and row['stk_fast_k']>row['stk_fast_d']:
            add(sn,'long',row['close']); trig[sn]=True
        elif row['stk_fast_k']>85 and prev['stk_fast_k']>prev['stk_fast_d'] and row['stk_fast_k']<row['stk_fast_d']:
            add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # ADX RAPIDE (7) + DI + EMA
    # ═══════════════════════════════════════════
    sn = 'ALL_ADX_FAST'
    if sn not in trig and pd.notna(row['adx_fast']) and pd.notna(row['ema21']):
        if row['adx_fast']>25 and row['pdi_fast']>row['mdi_fast'] and row['close']>row['ema21']:
            if not(prev['pdi_fast']>prev['mdi_fast']):
                add(sn,'long',row['close']); trig[sn]=True
        elif row['adx_fast']>25 and row['mdi_fast']>row['pdi_fast'] and row['close']<row['ema21']:
            if not(prev['mdi_fast']>prev['pdi_fast']):
                add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # DONCHIAN DUAL (20+55)
    # ═══════════════════════════════════════════
    sn = 'ALL_DC_DUAL'
    if sn not in trig and pd.notna(row.get('dc20_h')) and pd.notna(row.get('dc55_h')):
        if row['close'] > prev['dc20_h'] and row['close'] > prev['dc55_h']:
            add(sn,'long',row['close']); trig[sn]=True
        elif row['close'] < prev['dc20_l'] and row['close'] < prev['dc55_l']:
            add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # KELTNER (20, 2.0 ATR) breakout + body filter
    # ═══════════════════════════════════════════
    sn = 'ALL_KC_BODY'
    if sn not in trig and pd.notna(row['kc_up']):
        if row['close']>row['kc_up'] and prev['close']<=prev['kc_up'] and abs(row['body'])>=0.5*atr:
            add(sn,'long',row['close']); trig[sn]=True
        elif row['close']<row['kc_lo'] and prev['close']>=prev['kc_lo'] and abs(row['body'])>=0.5*atr:
            add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # BB TIGHT (10,1.5) squeeze scalp
    # ═══════════════════════════════════════════
    sn = 'ALL_BB_TIGHT'
    if sn not in trig and pd.notna(row['bb_tight_up']):
        if row['close'] > row['bb_tight_up'] and prev['close'] <= prev['bb_tight_up']:
            add(sn,'long',row['close']); trig[sn]=True
        elif row['close'] < row['bb_tight_lo'] and prev['close'] >= prev['bb_tight_lo']:
            add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # StochRSI extreme (< 0.1 / > 0.9)
    # ═══════════════════════════════════════════
    sn = 'ALL_STOCHRSI'
    if sn not in trig and pd.notna(row['stochrsi_k']):
        if prev['stochrsi_k'] < 10 and row['stochrsi_k'] >= 10:
            add(sn,'long',row['close']); trig[sn]=True
        elif prev['stochrsi_k'] > 90 and row['stochrsi_k'] <= 90:
            add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # TRIPLE CONFIRM: EMA(9/21) + RSI(14)>50 + MACD>signal
    # ═══════════════════════════════════════════
    sn = 'ALL_TRIPLE'
    if sn not in trig and pd.notna(row['ema9']) and pd.notna(row['rsi14']) and pd.notna(row['macd_std']):
        if row['ema9']>row['ema21'] and row['rsi14']>50 and row['macd_std']>row['macd_std_sig']:
            if not(prev['ema9']>prev['ema21'] and prev['rsi14']>50 and prev['macd_std']>prev['macd_std_sig']):
                add(sn,'long',row['close']); trig[sn]=True
        elif row['ema9']<row['ema21'] and row['rsi14']<50 and row['macd_std']<row['macd_std_sig']:
            if not(prev['ema9']<prev['ema21'] and prev['rsi14']<50 and prev['macd_std']<prev['macd_std_sig']):
                add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # EMA(8/21) + ADX(14) + MACD_fast trend rider
    # ═══════════════════════════════════════════
    sn = 'ALL_TREND_RIDER'
    if sn not in trig and pd.notna(row['ema8']) and pd.notna(row['adx_std']) and pd.notna(row['macd_fast']):
        if row['ema8']>row['ema21'] and row['adx_std']>25 and row['macd_fast']>0:
            if not(prev['ema8']>prev['ema21'] and prev['adx_std']>25 and prev['macd_fast']>0):
                add(sn,'long',row['close']); trig[sn]=True
        elif row['ema8']<row['ema21'] and row['adx_std']>25 and row['macd_fast']<0:
            if not(prev['ema8']<prev['ema21'] and prev['adx_std']>25 and prev['macd_fast']<0):
                add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # SESSION-SPECIFIC
    # ═══════════════════════════════════════════
    # MACD fast signal at London open
    sn = 'LON_MACD_FAST'
    if 8.0<=hour<10.0 and sn not in trig and pd.notna(row['macd_fast']):
        if prev['macd_fast']<prev['macd_fast_sig'] and row['macd_fast']>row['macd_fast_sig']:
            add(sn,'long',row['close']); trig[sn]=True
        elif prev['macd_fast']>prev['macd_fast_sig'] and row['macd_fast']<row['macd_fast_sig']:
            add(sn,'short',row['close']); trig[sn]=True

    # EMA ribbon at NY
    sn = 'NY_EMA_RIBBON'
    if 14.5<=hour<17.0 and sn not in trig and pd.notna(row['ema8']):
        if row['ema8']>row['ema13']>row['ema21'] and not(prev['ema8']>prev['ema13']>prev['ema21']):
            add(sn,'long',row['close']); trig[sn]=True
        elif row['ema8']<row['ema13']<row['ema21'] and not(prev['ema8']<prev['ema13']<prev['ema21']):
            add(sn,'short',row['close']); trig[sn]=True

    # TTM squeeze at London
    sn = 'LON_TTM'
    if 8.0<=hour<14.5 and sn not in trig and pd.notna(row['bb_inside_kc']):
        was = prev['bb_inside_kc'] if pd.notna(prev['bb_inside_kc']) else False
        if was and not row['bb_inside_kc']:
            if row['ttm_mom']>0 and row['ttm_mom']>prev['ttm_mom']:
                add(sn,'long',row['close']); trig[sn]=True
            elif row['ttm_mom']<0 and row['ttm_mom']<prev['ttm_mom']:
                add(sn,'short',row['close']); trig[sn]=True

    # ADX fast + DI cross at Tokyo
    sn = 'TOK_ADX_FAST'
    if 0.0<=hour<6.0 and sn not in trig and pd.notna(row['adx_fast']):
        if row['adx_fast']>25 and prev['pdi_fast']<prev['mdi_fast'] and row['pdi_fast']>row['mdi_fast']:
            add(sn,'long',row['close']); trig[sn]=True
        elif row['adx_fast']>25 and prev['pdi_fast']>prev['mdi_fast'] and row['pdi_fast']<row['mdi_fast']:
            add(sn,'short',row['close']); trig[sn]=True

    # Donchian 10 at London
    sn = 'LON_DC10'
    if 8.0<=hour<14.5 and sn not in trig and pd.notna(prev.get('dc10_h')):
        if row['close'] > prev['dc10_h']:
            add(sn,'long',row['close']); trig[sn]=True
        elif row['close'] < prev['dc10_l']:
            add(sn,'short',row['close']); trig[sn]=True

print(f"Done. {len(S)} strats.", flush=True)

# ── RESULTATS ──
print("\n" + "="*130)
print("EXPLORATION INDICATORS V2 — Strategies avancees")
print("="*130)
print(f"{'Strat':>22s} {'n':>5s} {'WR':>5s} {'PF':>6s} {'Avg':>8s} {'Total':>8s} {'[1st|2nd]':>18s} {'Split':>6s} {'Tiers':>5s}")
print("-"*130)

good = []
for sn in sorted(S.keys()):
    t = S[sn]
    if len(t) < 20: continue
    pnls = [x['pnl_oz'] for x in t]
    n = len(pnls)
    gp = sum(p for p in pnls if p>0); gl = abs(sum(p for p in pnls if p<0))+0.001
    wr = sum(1 for p in pnls if p>0)/n*100
    pf = gp/gl
    mid = n//2; f1 = np.mean(pnls[:mid]); f2 = np.mean(pnls[mid:])
    t1 = sum(pnls[:n//3]); t2 = sum(pnls[n//3:2*n//3]); t3 = sum(pnls[2*n//3:])
    tiers = sum(1 for x in [t1, t2, t3] if x > 0)
    split = f1 > 0 and f2 > 0
    split_str = "OK" if split else "!!"
    marker = " <--" if pf > 1.2 and split else ""
    print(f"{sn:>22s} {n:5d} {wr:4.0f}% {pf:6.2f} {np.mean(pnls):+8.3f} {sum(pnls):+8.1f} [{f1:+7.3f}|{f2:+7.3f}] {split_str:>6s} {tiers:4d}/3{marker}")
    if pf > 1.2 and split:
        good.append(sn)

print(f"\n  Retenues (PF>1.2 + split OK): {', '.join(good) if good else 'aucune'}")
print()
