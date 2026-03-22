"""
Exploration indicators V3 — encore plus de variantes.
Pivots, OBV, Williams %R, CCI, momentum, HMA, patterns avec indicateurs,
session-specific combos, multi-timeframe proxies, range filters.
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
for p in [5,8,9,13,20,21,50,100,200]:
    c[f'ema{p}'] = c['close'].ewm(span=p, adjust=False).mean()

# HMA (Hull Moving Average) = WMA(2*WMA(n/2) - WMA(n), sqrt(n))
def wma(s, n):
    weights = np.arange(1, n+1)
    return s.rolling(n).apply(lambda x: np.dot(x, weights)/weights.sum(), raw=True)
c['hma9'] = wma(2*wma(c['close'],4) - wma(c['close'],9), 3)
c['hma21'] = wma(2*wma(c['close'],10) - wma(c['close'],21), 4)

# Williams %R
for p in [14,7]:
    hh = c['high'].rolling(p).max()
    ll = c['low'].rolling(p).min()
    c[f'willr{p}'] = -100 * (hh - c['close']) / (hh - ll + 1e-10)

# CCI (Commodity Channel Index)
for p in [14,20]:
    tp = (c['high'] + c['low'] + c['close']) / 3
    sma_tp = tp.rolling(p).mean()
    mad = tp.rolling(p).apply(lambda x: np.mean(np.abs(x - np.mean(x))), raw=True)
    c[f'cci{p}'] = (tp - sma_tp) / (0.015 * mad + 1e-10)

# Momentum (ROC)
for p in [5,10,14]:
    c[f'mom{p}'] = c['close'] / c['close'].shift(p) * 100 - 100

# RSI
for p in [7,14]:
    delta = c['close'].diff()
    gain = delta.clip(lower=0); loss = (-delta).clip(lower=0)
    ag = gain.ewm(alpha=1.0/p, min_periods=p, adjust=False).mean()
    al = loss.ewm(alpha=1.0/p, min_periods=p, adjust=False).mean()
    c[f'rsi{p}'] = 100 - 100/(1+ag/(al+1e-10))

# MACD
for fast,slow,sig,name in [(12,26,9,'std'),(5,13,1,'fast'),(8,17,9,'med')]:
    ef = c['close'].ewm(span=fast, adjust=False).mean()
    es = c['close'].ewm(span=slow, adjust=False).mean()
    c[f'macd_{name}'] = ef - es
    c[f'macd_{name}_sig'] = c[f'macd_{name}'].ewm(span=max(sig,2), adjust=False).mean()

# Bollinger
c['bb_mid'] = c['close'].rolling(20).mean()
c['bb_std'] = c['close'].rolling(20).std()
c['bb_up'] = c['bb_mid'] + 2 * c['bb_std']
c['bb_lo'] = c['bb_mid'] - 2 * c['bb_std']
c['bb_pct'] = (c['close'] - c['bb_lo']) / (c['bb_up'] - c['bb_lo'] + 1e-10)

# Stochastic
c['stk_l14'] = c['low'].rolling(14).min()
c['stk_h14'] = c['high'].rolling(14).max()
c['stk_k'] = 100*(c['close']-c['stk_l14'])/(c['stk_h14']-c['stk_l14']+1e-10)
c['stk_d'] = c['stk_k'].rolling(3).mean()

# ADX
tr = np.maximum(c['high']-c['low'], np.maximum(abs(c['high']-c['close'].shift(1)), abs(c['low']-c['close'].shift(1))))
c['atr14'] = tr.ewm(span=14, adjust=False).mean()
plus_dm = c['high'].diff().clip(lower=0)
minus_dm = (-c['low'].diff()).clip(lower=0)
mask = plus_dm > minus_dm
pdm = plus_dm.where(mask, 0); mdm = minus_dm.where(~mask, 0)
pdi = 100*pdm.ewm(span=14, adjust=False).mean()/(c['atr14']+1e-10)
mdi = 100*mdm.ewm(span=14, adjust=False).mean()/(c['atr14']+1e-10)
dx = 100*abs(pdi-mdi)/(pdi+mdi+1e-10)
c['adx'] = dx.ewm(span=14, adjust=False).mean()
c['pdi'] = pdi; c['mdi'] = mdi

# Donchian
for p in [10,20]:
    c[f'dc{p}_h'] = c['high'].rolling(p).max()
    c[f'dc{p}_l'] = c['low'].rolling(p).min()

# OBV (On Balance Volume proxy — using range as volume proxy)
c['obv'] = 0.0
obv_vals = np.zeros(len(c))
for i in range(1, len(c)):
    if c.iloc[i]['close'] > c.iloc[i-1]['close']:
        obv_vals[i] = obv_vals[i-1] + c.iloc[i]['range']
    elif c.iloc[i]['close'] < c.iloc[i-1]['close']:
        obv_vals[i] = obv_vals[i-1] - c.iloc[i]['range']
    else:
        obv_vals[i] = obv_vals[i-1]
c['obv'] = obv_vals
c['obv_ema5'] = pd.Series(obv_vals).ewm(span=5, adjust=False).mean().values
c['obv_ema20'] = pd.Series(obv_vals).ewm(span=20, adjust=False).mean().values

# Rolling highs/lows for pattern detection
c['high5'] = c['high'].rolling(5).max()
c['low5'] = c['low'].rolling(5).min()
c['high20'] = c['high'].rolling(20).max()
c['low20'] = c['low'].rolling(20).min()

# Close position in range
c['close_pos'] = (c['close'] - c['low5']) / (c['high5'] - c['low5'] + 1e-10)

# Avg body ratio (close conviction)
c['body_ratio'] = abs(c['body']) / (c['range'] + 1e-10)
c['avg_body_ratio'] = c['body_ratio'].rolling(10).mean()

print("Collecte des signaux...", flush=True)
S = {}
prev_d = None; trig = {}; day_atr = None; prev_day_data = None

for ci in range(200, len(c)):
    row = c.iloc[ci]; prev = c.iloc[ci-1]; ct = row['ts_dt']; today = ct.date()
    hour = ct.hour + ct.minute / 60.0
    if today != prev_d:
        if prev_d:
            yc = c[c['date']==prev_d]
            if len(yc) > 0:
                prev_day_data = {'open': float(yc.iloc[0]['open']), 'close': float(yc.iloc[-1]['close']),
                                 'high': float(yc['high'].max()), 'low': float(yc['low'].min()),
                                 'range': float(yc['high'].max()-yc['low'].min()),
                                 'body': float(yc.iloc[-1]['close']-yc.iloc[0]['open'])}
        prev_d = today; trig = {}
        pd_ = prev_day(today); day_atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    atr = day_atr
    if atr == 0 or atr is None: continue

    def add(sn, d, e):
        b, ex = sim_exit(c, ci, e, d, atr, check_entry_candle=False)
        pnl = (ex-e) if d=='long' else (e-ex)
        S.setdefault(sn,[]).append({'date':today,'dir':d,'pnl_oz':pnl-get_sp(today)})

    # ═══════════════════════════════════════════
    # WILLIAMS %R
    # ═══════════════════════════════════════════
    for p, name in [(14,'14'),(7,'7')]:
        sn = f'ALL_WILLR_{name}'
        if sn not in trig and pd.notna(row[f'willr{p}']):
            if prev[f'willr{p}'] < -80 and row[f'willr{p}'] >= -80:
                add(sn,'long',row['close']); trig[sn]=True
            elif prev[f'willr{p}'] > -20 and row[f'willr{p}'] <= -20:
                add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # CCI
    # ═══════════════════════════════════════════
    for p, name in [(14,'14'),(20,'20')]:
        # CCI cross +100/-100
        sn = f'ALL_CCI_{name}_EXT'
        if sn not in trig and pd.notna(row[f'cci{p}']):
            if prev[f'cci{p}'] < -100 and row[f'cci{p}'] >= -100:
                add(sn,'long',row['close']); trig[sn]=True
            elif prev[f'cci{p}'] > 100 and row[f'cci{p}'] <= 100:
                add(sn,'short',row['close']); trig[sn]=True

        # CCI zero cross
        sn = f'ALL_CCI_{name}_ZERO'
        if sn not in trig and pd.notna(row[f'cci{p}']):
            if prev[f'cci{p}'] < 0 and row[f'cci{p}'] >= 0:
                add(sn,'long',row['close']); trig[sn]=True
            elif prev[f'cci{p}'] > 0 and row[f'cci{p}'] <= 0:
                add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # MOMENTUM (ROC)
    # ═══════════════════════════════════════════
    for p, name in [(5,'5'),(10,'10'),(14,'14')]:
        sn = f'ALL_MOM_{name}'
        if sn not in trig and pd.notna(row[f'mom{p}']):
            if prev[f'mom{p}'] < 0 and row[f'mom{p}'] >= 0:
                add(sn,'long',row['close']); trig[sn]=True
            elif prev[f'mom{p}'] > 0 and row[f'mom{p}'] <= 0:
                add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # HMA CROSSOVER (9 vs 21)
    # ═══════════════════════════════════════════
    sn = 'ALL_HMA_CROSS'
    if sn not in trig and pd.notna(row['hma9']) and pd.notna(row['hma21']):
        if prev['hma9'] < prev['hma21'] and row['hma9'] > row['hma21']:
            add(sn,'long',row['close']); trig[sn]=True
        elif prev['hma9'] > prev['hma21'] and row['hma9'] < row['hma21']:
            add(sn,'short',row['close']); trig[sn]=True

    # HMA direction change
    sn = 'ALL_HMA_DIR'
    if sn not in trig and pd.notna(row['hma9']) and ci >= 3:
        h1 = c.iloc[ci-2]['hma9']; h2 = c.iloc[ci-1]['hma9']; h3 = row['hma9']
        if pd.notna(h1):
            if h1 > h2 and h3 > h2:  # valley
                add(sn,'long',row['close']); trig[sn]=True
            elif h1 < h2 and h3 < h2:  # peak
                add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # OBV CROSSOVER (EMA5 vs EMA20)
    # ═══════════════════════════════════════════
    sn = 'ALL_OBV_CROSS'
    if sn not in trig and pd.notna(row['obv_ema5']):
        if prev['obv_ema5'] < prev['obv_ema20'] and row['obv_ema5'] > row['obv_ema20']:
            add(sn,'long',row['close']); trig[sn]=True
        elif prev['obv_ema5'] > prev['obv_ema20'] and row['obv_ema5'] < row['obv_ema20']:
            add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # BB %B (Bollinger percent)
    # ═══════════════════════════════════════════
    sn = 'ALL_BB_PCT'
    if sn not in trig and pd.notna(row['bb_pct']):
        if prev['bb_pct'] < 0 and row['bb_pct'] >= 0:
            add(sn,'long',row['close']); trig[sn]=True
        elif prev['bb_pct'] > 1 and row['bb_pct'] <= 1:
            add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # EMA 100/200 trend + pullback to EMA50
    # ═══════════════════════════════════════════
    sn = 'ALL_EMA_TREND_PB'
    if sn not in trig and pd.notna(row['ema50']) and pd.notna(row['ema200']):
        if row['ema50'] > row['ema200']:
            if prev['low'] <= prev['ema50'] and row['close'] > row['ema50'] and row['close'] > row['open']:
                add(sn,'long',row['close']); trig[sn]=True
        elif row['ema50'] < row['ema200']:
            if prev['high'] >= prev['ema50'] and row['close'] < row['ema50'] and row['close'] < row['open']:
                add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # CLOSE CONVICTION (body ratio momentum)
    # ═══════════════════════════════════════════
    sn = 'ALL_CONVICTION'
    if sn not in trig and pd.notna(row['avg_body_ratio']):
        if row['body_ratio'] > 0.85 and row['avg_body_ratio'] > 0.6 and abs(row['body']) >= 0.3*atr:
            add(sn,'long' if row['body']>0 else 'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # COMBOS AVANCEES
    # ═══════════════════════════════════════════

    # CCI + RSI combo
    sn = 'ALL_CCI_RSI'
    if sn not in trig and pd.notna(row['cci14']) and pd.notna(row['rsi14']):
        if row['cci14'] < -100 and row['rsi14'] < 30:
            add(sn,'long',row['close']); trig[sn]=True
        elif row['cci14'] > 100 and row['rsi14'] > 70:
            add(sn,'short',row['close']); trig[sn]=True

    # MACD med + RSI50 cross
    sn = 'ALL_MACD_RSI'
    if sn not in trig and pd.notna(row['macd_med']) and pd.notna(row['rsi14']):
        if prev['macd_med']<prev['macd_med_sig'] and row['macd_med']>row['macd_med_sig'] and row['rsi14']>50:
            add(sn,'long',row['close']); trig[sn]=True
        elif prev['macd_med']>prev['macd_med_sig'] and row['macd_med']<row['macd_med_sig'] and row['rsi14']<50:
            add(sn,'short',row['close']); trig[sn]=True

    # DC10 + EMA21 trend filter
    sn = 'ALL_DC10_EMA'
    if sn not in trig and pd.notna(prev.get('dc10_h')) and pd.notna(row['ema21']):
        if row['close'] > prev['dc10_h'] and row['close'] > row['ema21']:
            add(sn,'long',row['close']); trig[sn]=True
        elif row['close'] < prev['dc10_l'] and row['close'] < row['ema21']:
            add(sn,'short',row['close']); trig[sn]=True

    # HMA + ADX trend
    sn = 'ALL_HMA_ADX'
    if sn not in trig and pd.notna(row['hma9']) and pd.notna(row['adx']):
        if row['adx'] > 25 and prev['hma9']<prev['hma21'] and row['hma9']>row['hma21']:
            add(sn,'long',row['close']); trig[sn]=True
        elif row['adx'] > 25 and prev['hma9']>prev['hma21'] and row['hma9']<row['hma21']:
            add(sn,'short',row['close']); trig[sn]=True

    # MACD fast + Stoch oversold
    sn = 'ALL_MACD_STOCH'
    if sn not in trig and pd.notna(row['macd_fast']) and pd.notna(row['stk_k']):
        if prev['macd_fast']<prev['macd_fast_sig'] and row['macd_fast']>row['macd_fast_sig'] and row['stk_k']<30:
            add(sn,'long',row['close']); trig[sn]=True
        elif prev['macd_fast']>prev['macd_fast_sig'] and row['macd_fast']<row['macd_fast_sig'] and row['stk_k']>70:
            add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # SESSION-SPECIFIC
    # ═══════════════════════════════════════════

    # CCI zero cross at London
    sn = 'LON_CCI_ZERO'
    if 8.0<=hour<14.5 and sn not in trig and pd.notna(row['cci20']):
        if prev['cci20'] < 0 and row['cci20'] >= 0:
            add(sn,'long',row['close']); trig[sn]=True
        elif prev['cci20'] > 0 and row['cci20'] <= 0:
            add(sn,'short',row['close']); trig[sn]=True

    # Williams %R at Tokyo
    sn = 'TOK_WILLR'
    if 0.0<=hour<6.0 and sn not in trig and pd.notna(row['willr14']):
        if prev['willr14'] < -80 and row['willr14'] >= -80:
            add(sn,'long',row['close']); trig[sn]=True
        elif prev['willr14'] > -20 and row['willr14'] <= -20:
            add(sn,'short',row['close']); trig[sn]=True

    # HMA cross at NY
    sn = 'NY_HMA_CROSS'
    if 14.5<=hour<21.0 and sn not in trig and pd.notna(row['hma9']) and pd.notna(row['hma21']):
        if prev['hma9'] < prev['hma21'] and row['hma9'] > row['hma21']:
            add(sn,'long',row['close']); trig[sn]=True
        elif prev['hma9'] > prev['hma21'] and row['hma9'] < row['hma21']:
            add(sn,'short',row['close']); trig[sn]=True

    # MACD med + ADX at London
    sn = 'LON_MACD_ADX'
    if 8.0<=hour<14.5 and sn not in trig and pd.notna(row['macd_med']) and pd.notna(row['adx']):
        if row['adx'] > 25 and prev['macd_med']<prev['macd_med_sig'] and row['macd_med']>row['macd_med_sig']:
            add(sn,'long',row['close']); trig[sn]=True
        elif row['adx'] > 25 and prev['macd_med']>prev['macd_med_sig'] and row['macd_med']<row['macd_med_sig']:
            add(sn,'short',row['close']); trig[sn]=True

    # DC10 + Momentum at London
    sn = 'LON_DC10_MOM'
    if 8.0<=hour<14.5 and sn not in trig and pd.notna(prev.get('dc10_h')) and pd.notna(row['mom5']):
        if row['close'] > prev['dc10_h'] and row['mom5'] > 0:
            add(sn,'long',row['close']); trig[sn]=True
        elif row['close'] < prev['dc10_l'] and row['mom5'] < 0:
            add(sn,'short',row['close']); trig[sn]=True

    # MACD med signal at Tokyo
    sn = 'TOK_MACD_MED'
    if 0.0<=hour<6.0 and sn not in trig and pd.notna(row['macd_med']):
        if prev['macd_med']<prev['macd_med_sig'] and row['macd_med']>row['macd_med_sig']:
            add(sn,'long',row['close']); trig[sn]=True
        elif prev['macd_med']>prev['macd_med_sig'] and row['macd_med']<row['macd_med_sig']:
            add(sn,'short',row['close']); trig[sn]=True

    # RSI divergence at NY
    sn = 'NY_RSI_DIV'
    if 14.5<=hour<21.0 and sn not in trig and ci >= 10 and pd.notna(row['rsi14']):
        last10 = c.iloc[ci-9:ci+1]
        price_ll = row['low'] < last10.iloc[:-1]['low'].min()
        rsi_hl = row['rsi14'] > last10.iloc[:-1]['rsi14'].min()
        if price_ll and rsi_hl and row['close'] > row['open']:
            add(sn,'long',row['close']); trig[sn]=True
        price_hh = row['high'] > last10.iloc[:-1]['high'].max()
        rsi_lh = row['rsi14'] < last10.iloc[:-1]['rsi14'].max()
        if price_hh and rsi_lh and row['close'] < row['open']:
            add(sn,'short',row['close']); trig[sn]=True

print(f"Done. {len(S)} strats.", flush=True)

# ── RESULTATS ──
print("\n" + "="*130)
print("EXPLORATION INDICATORS V3 — Williams %R, CCI, Momentum, HMA, OBV, combos")
print("="*130)
print(f"{'Strat':>18s} {'n':>5s} {'WR':>5s} {'PF':>6s} {'Avg':>8s} {'Total':>8s} {'[1st|2nd]':>18s} {'Split':>6s} {'Tiers':>5s}")
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
    print(f"{sn:>18s} {n:5d} {wr:4.0f}% {pf:6.2f} {np.mean(pnls):+8.3f} {sum(pnls):+8.1f} [{f1:+7.3f}|{f2:+7.3f}] {split_str:>6s} {tiers:4d}/3{marker}")
    if pf > 1.2 and split:
        good.append(sn)

print(f"\n  Retenues (PF>1.2 + split OK): {', '.join(good) if good else 'aucune'}")
print()
