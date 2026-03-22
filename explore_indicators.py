"""
Exploration MASSIVE — toutes les strategies indicators + price action.
Tout sur bougies FERMEES, ZERO look-ahead.
Config exit: SL=1.0 ACT=0.5 TRAIL=0.75, trailing sur CLOSE, check entry candle.
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

# ── PRECALCUL INDICATEURS (sur bougies fermees) ──
print("Precalcul indicateurs...", flush=True)
c = candles.copy()
c['body'] = c['close'] - c['open']
c['abs_body'] = abs(c['body'])
c['range'] = c['high'] - c['low']

# EMA
for p in [5,8,9,13,21,50,100]:
    c[f'ema{p}'] = c['close'].ewm(span=p, adjust=False).mean()

# RSI
for p in [7,14,21]:
    delta = c['close'].diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1.0/p, min_periods=p, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0/p, min_periods=p, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    c[f'rsi{p}'] = 100.0 - (100.0 / (1.0 + rs))

# MACD
ema12 = c['close'].ewm(span=12, adjust=False).mean()
ema26 = c['close'].ewm(span=26, adjust=False).mean()
c['macd'] = ema12 - ema26
c['macd_signal'] = c['macd'].ewm(span=9, adjust=False).mean()
c['macd_hist'] = c['macd'] - c['macd_signal']

# Bollinger Bands
c['bb_mid'] = c['close'].rolling(20).mean()
c['bb_std'] = c['close'].rolling(20).std()
c['bb_upper'] = c['bb_mid'] + 2 * c['bb_std']
c['bb_lower'] = c['bb_mid'] - 2 * c['bb_std']
c['bb_width'] = (c['bb_upper'] - c['bb_lower']) / c['bb_mid']

# Stochastic
c['stoch_low14'] = c['low'].rolling(14).min()
c['stoch_high14'] = c['high'].rolling(14).max()
c['stoch_k'] = 100 * (c['close'] - c['stoch_low14']) / (c['stoch_high14'] - c['stoch_low14'] + 0.0001)
c['stoch_d'] = c['stoch_k'].rolling(3).mean()

# ADX
plus_dm = c['high'].diff().clip(lower=0)
minus_dm = (-c['low'].diff()).clip(lower=0)
# Only keep the larger one
mask = plus_dm > minus_dm
plus_dm = plus_dm.where(mask, 0)
minus_dm = minus_dm.where(~mask, 0)
tr = np.maximum(c['high']-c['low'], np.maximum(abs(c['high']-c['close'].shift(1)), abs(c['low']-c['close'].shift(1))))
atr14 = tr.ewm(span=14, adjust=False).mean()
plus_di = 100 * plus_dm.ewm(span=14, adjust=False).mean() / (atr14 + 0.0001)
minus_di = 100 * minus_dm.ewm(span=14, adjust=False).mean() / (atr14 + 0.0001)
dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 0.0001)
c['adx'] = dx.ewm(span=14, adjust=False).mean()
c['plus_di'] = plus_di
c['minus_di'] = minus_di

# Donchian
for p in [10,20,50]:
    c[f'dc{p}_high'] = c['high'].rolling(p).max()
    c[f'dc{p}_low'] = c['low'].rolling(p).min()

# Keltner Channel
c['kc_mid'] = c['close'].ewm(span=20, adjust=False).mean()
c['kc_atr'] = tr.ewm(span=14, adjust=False).mean()
c['kc_upper'] = c['kc_mid'] + 1.5 * c['kc_atr']
c['kc_lower'] = c['kc_mid'] - 1.5 * c['kc_atr']

# Previous values (shift = bougie precedente, pas look-ahead)
for col in ['macd','macd_signal','macd_hist','stoch_k','stoch_d','rsi14','rsi7',
            'ema9','ema21','ema5','ema13','ema8','bb_width','adx','plus_di','minus_di']:
    c[f'prev_{col}'] = c[col].shift(1)

print("Collecte des signaux...", flush=True)
S = {}
prev_d = None; trig = {}; day_atr = None; prev_day_data = None
OPEN_STRATS_SET = set()  # will be populated

for ci in range(100, len(c)):
    row = c.iloc[ci]; ct = row['ts_dt']; today = ct.date()
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

    # Toutes les strats entrent au CLOSE de la bougie fermee (indicateurs)
    # Donc check_entry_candle=False pour les strats indicators
    def add(sn, d, e, is_open=False):
        b, ex = sim_exit(c, ci, e, d, atr, check_entry_candle=is_open)
        pnl = (ex-e) if d=='long' else (e-ex)
        S.setdefault(sn,[]).append({'date':today,'dir':d,'pnl_oz':pnl-get_sp(today)})

    # Valeurs de la bougie FERMEE (ci) et de la precedente (ci-1)
    # Tous les indicateurs utilisent shift(1) pour les signaux de croisement
    # = on compare la bougie fermee actuelle avec la bougie fermee precedente
    prev = c.iloc[ci-1]

    # ═══════════════════════════════════════════════════════
    # EMA CROSSOVERS (bougie fermee)
    # ═══════════════════════════════════════════════════════
    for fast, slow, name in [(9,21,'921'),(5,13,'513'),(8,21,'821')]:
        sn = f'ALL_EMA_{name}'
        if sn not in trig:
            # Cross: prev fast < prev slow AND current fast > current slow
            ef, es = f'ema{fast}', f'ema{slow}'
            if pd.notna(row[ef]) and pd.notna(row[es]) and pd.notna(prev[ef]) and pd.notna(prev[es]):
                if prev[ef] < prev[es] and row[ef] > row[es]:
                    add(sn,'long',row['close']); trig[sn]=True
                elif prev[ef] > prev[es] and row[ef] < row[es]:
                    add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════════════════
    # RSI
    # ═══════════════════════════════════════════════════════
    for p, ob, os_val, suffix in [(14,70,30,'14'),(7,70,30,'7'),(14,80,20,'14EXT')]:
        sn = f'ALL_RSI_{suffix}'
        if sn not in trig:
            rsi_col = f'rsi{p}'
            if pd.notna(row[rsi_col]):
                if row[rsi_col] < os_val and prev[rsi_col] >= os_val:  # cross into oversold
                    add(sn,'long',row['close']); trig[sn]=True
                elif row[rsi_col] > ob and prev[rsi_col] <= ob:  # cross into overbought
                    add(sn,'short',row['close']); trig[sn]=True

    # RSI centerline cross
    sn = 'ALL_RSI_50'
    if sn not in trig and pd.notna(row['rsi14']) and pd.notna(prev['rsi14']):
        if prev['rsi14'] < 50 and row['rsi14'] >= 50:
            add(sn,'long',row['close']); trig[sn]=True
        elif prev['rsi14'] > 50 and row['rsi14'] <= 50:
            add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════════════════
    # MACD
    # ═══════════════════════════════════════════════════════
    # Signal line cross
    sn = 'ALL_MACD_SIG'
    if sn not in trig and pd.notna(row['macd']) and pd.notna(row['macd_signal']):
        if prev['macd'] < prev['macd_signal'] and row['macd'] > row['macd_signal']:
            add(sn,'long',row['close']); trig[sn]=True
        elif prev['macd'] > prev['macd_signal'] and row['macd'] < row['macd_signal']:
            add(sn,'short',row['close']); trig[sn]=True

    # Zero line cross
    sn = 'ALL_MACD_ZERO'
    if sn not in trig and pd.notna(row['macd']):
        if prev['macd'] < 0 and row['macd'] >= 0:
            add(sn,'long',row['close']); trig[sn]=True
        elif prev['macd'] > 0 and row['macd'] <= 0:
            add(sn,'short',row['close']); trig[sn]=True

    # Histogram reversal (3 declining then 1 rising)
    sn = 'ALL_MACD_HIST'
    if sn not in trig and ci >= 4:
        h = [c.iloc[ci-3]['macd_hist'], c.iloc[ci-2]['macd_hist'], c.iloc[ci-1]['macd_hist'], row['macd_hist']]
        if all(pd.notna(x) for x in h):
            if h[0]<h[1]<h[2] and h[3]>h[2] and h[2]<0:  # declining then uptick in negative
                add(sn,'long',row['close']); trig[sn]=True
            elif h[0]>h[1]>h[2] and h[3]<h[2] and h[2]>0:  # rising then downtick in positive
                add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════════════════
    # BOLLINGER BANDS
    # ═══════════════════════════════════════════════════════
    # Mean reversion (touch band, enter toward middle)
    sn = 'ALL_BB_MR'
    if sn not in trig and pd.notna(row['bb_upper']):
        if row['close'] < row['bb_lower']:
            add(sn,'long',row['close']); trig[sn]=True
        elif row['close'] > row['bb_upper']:
            add(sn,'short',row['close']); trig[sn]=True

    # Squeeze breakout (bandwidth contracts then expands)
    sn = 'ALL_BB_SQUEEZE'
    if sn not in trig and ci >= 20 and pd.notna(row['bb_width']):
        bw_min = c.iloc[ci-20:ci]['bb_width'].min()
        if pd.notna(bw_min) and row['bb_width'] > bw_min * 1.5 and prev['bb_width'] <= bw_min * 1.2:
            if row['close'] > row['bb_upper']:
                add(sn,'long',row['close']); trig[sn]=True
            elif row['close'] < row['bb_lower']:
                add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════════════════
    # STOCHASTIC
    # ═══════════════════════════════════════════════════════
    sn = 'ALL_STOCH_OB'
    if sn not in trig and pd.notna(row['stoch_k']) and pd.notna(row['stoch_d']):
        if row['stoch_k'] < 20 and prev['stoch_k'] < prev['stoch_d'] and row['stoch_k'] > row['stoch_d']:
            add(sn,'long',row['close']); trig[sn]=True
        elif row['stoch_k'] > 80 and prev['stoch_k'] > prev['stoch_d'] and row['stoch_k'] < row['stoch_d']:
            add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════════════════
    # ADX + DI
    # ═══════════════════════════════════════════════════════
    sn = 'ALL_ADX_TREND'
    if sn not in trig and pd.notna(row['adx']):
        if row['adx'] > 25:
            if prev['plus_di'] < prev['minus_di'] and row['plus_di'] > row['minus_di']:
                add(sn,'long',row['close']); trig[sn]=True
            elif prev['plus_di'] > prev['minus_di'] and row['plus_di'] < row['minus_di']:
                add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════════════════
    # DONCHIAN CHANNEL
    # ═══════════════════════════════════════════════════════
    for p in [10,20,50]:
        sn = f'ALL_DC{p}'
        if sn not in trig and pd.notna(row[f'dc{p}_high']):
            if row['close'] > prev[f'dc{p}_high'] if pd.notna(prev.get(f'dc{p}_high')) else False:
                add(sn,'long',row['close']); trig[sn]=True
            elif row['close'] < prev[f'dc{p}_low'] if pd.notna(prev.get(f'dc{p}_low')) else False:
                add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════════════════
    # KELTNER CHANNEL
    # ═══════════════════════════════════════════════════════
    sn = 'ALL_KC_BRK'
    if sn not in trig and pd.notna(row['kc_upper']):
        if row['close'] > row['kc_upper'] and prev['close'] <= prev['kc_upper']:
            add(sn,'long',row['close']); trig[sn]=True
        elif row['close'] < row['kc_lower'] and prev['close'] >= prev['kc_lower']:
            add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════════════════
    # COMBOS (multi-indicator)
    # ═══════════════════════════════════════════════════════
    # RSI oversold + price above EMA21
    sn = 'ALL_RSI_EMA'
    if sn not in trig and pd.notna(row['rsi14']) and pd.notna(row['ema21']):
        if row['rsi14'] < 30 and row['close'] > row['ema21']:
            add(sn,'long',row['close']); trig[sn]=True
        elif row['rsi14'] > 70 and row['close'] < row['ema21']:
            add(sn,'short',row['close']); trig[sn]=True

    # MACD signal cross + ADX > 25
    sn = 'ALL_MACD_ADX'
    if sn not in trig and pd.notna(row['macd']) and pd.notna(row['adx']):
        if row['adx'] > 25:
            if prev['macd'] < prev['macd_signal'] and row['macd'] > row['macd_signal']:
                add(sn,'long',row['close']); trig[sn]=True
            elif prev['macd'] > prev['macd_signal'] and row['macd'] < row['macd_signal']:
                add(sn,'short',row['close']); trig[sn]=True

    # BB lower + RSI < 30
    sn = 'ALL_BB_RSI'
    if sn not in trig and pd.notna(row['bb_lower']) and pd.notna(row['rsi14']):
        if row['close'] < row['bb_lower'] and row['rsi14'] < 30:
            add(sn,'long',row['close']); trig[sn]=True
        elif row['close'] > row['bb_upper'] and row['rsi14'] > 70:
            add(sn,'short',row['close']); trig[sn]=True

    # EMA cross + MACD same direction
    sn = 'ALL_EMA_MACD'
    if sn not in trig and pd.notna(row['ema9']) and pd.notna(row['macd']):
        if prev['ema9'] < prev['ema21'] and row['ema9'] > row['ema21'] and row['macd'] > row['macd_signal']:
            add(sn,'long',row['close']); trig[sn]=True
        elif prev['ema9'] > prev['ema21'] and row['ema9'] < row['ema21'] and row['macd'] < row['macd_signal']:
            add(sn,'short',row['close']); trig[sn]=True

    # Stoch oversold + BB lower band
    sn = 'ALL_STOCH_BB'
    if sn not in trig and pd.notna(row['stoch_k']) and pd.notna(row['bb_lower']):
        if row['stoch_k'] < 20 and row['close'] < row['bb_lower']:
            add(sn,'long',row['close']); trig[sn]=True
        elif row['stoch_k'] > 80 and row['close'] > row['bb_upper']:
            add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════════════════
    # SESSION-SPECIFIC INDICATORS
    # ═══════════════════════════════════════════════════════
    # RSI oversold during Tokyo
    sn = 'TOK_RSI_OB'
    if 0.0<=hour<6.0 and sn not in trig and pd.notna(row['rsi14']):
        if row['rsi14'] < 30 and prev['rsi14'] >= 30:
            add(sn,'long',row['close']); trig[sn]=True
        elif row['rsi14'] > 70 and prev['rsi14'] <= 70:
            add(sn,'short',row['close']); trig[sn]=True

    # EMA 9/21 cross during London open
    sn = 'LON_EMA_CROSS'
    if 8.0<=hour<10.0 and sn not in trig and pd.notna(row['ema9']):
        if prev['ema9'] < prev['ema21'] and row['ema9'] > row['ema21']:
            add(sn,'long',row['close']); trig[sn]=True
        elif prev['ema9'] > prev['ema21'] and row['ema9'] < row['ema21']:
            add(sn,'short',row['close']); trig[sn]=True

    # MACD signal cross at NY
    sn = 'NY_MACD_SIG'
    if 14.5<=hour<17.0 and sn not in trig and pd.notna(row['macd']):
        if prev['macd'] < prev['macd_signal'] and row['macd'] > row['macd_signal']:
            add(sn,'long',row['close']); trig[sn]=True
        elif prev['macd'] > prev['macd_signal'] and row['macd'] < row['macd_signal']:
            add(sn,'short',row['close']); trig[sn]=True

    # BB squeeze during London
    sn = 'LON_BB_SQUEEZE'
    if 8.0<=hour<14.5 and sn not in trig and ci >= 20 and pd.notna(row['bb_width']):
        bw_min = c.iloc[ci-20:ci]['bb_width'].min()
        if pd.notna(bw_min) and row['bb_width'] > bw_min * 1.5 and prev['bb_width'] <= bw_min * 1.2:
            if row['close'] > row['bb_upper']:
                add(sn,'long',row['close']); trig[sn]=True
            elif row['close'] < row['bb_lower']:
                add(sn,'short',row['close']); trig[sn]=True

    # RSI extreme during NY
    sn = 'NY_RSI_EXT'
    if 14.5<=hour<21.0 and sn not in trig and pd.notna(row['rsi14']):
        if row['rsi14'] < 20:
            add(sn,'long',row['close']); trig[sn]=True
        elif row['rsi14'] > 80:
            add(sn,'short',row['close']); trig[sn]=True

    # ADX trend + EMA slope during London
    sn = 'LON_ADX_EMA'
    if 8.0<=hour<14.5 and sn not in trig and pd.notna(row['adx']) and pd.notna(row['ema21']):
        if row['adx'] > 30 and row['ema21'] > prev['ema21'] and row['plus_di'] > row['minus_di']:
            add(sn,'long',row['close']); trig[sn]=True
        elif row['adx'] > 30 and row['ema21'] < prev['ema21'] and row['minus_di'] > row['plus_di']:
            add(sn,'short',row['close']); trig[sn]=True

    # Donchian 20 breakout during Tokyo
    sn = 'TOK_DC20'
    if 0.0<=hour<6.0 and sn not in trig and pd.notna(prev.get('dc20_high')):
        if row['close'] > prev['dc20_high']:
            add(sn,'long',row['close']); trig[sn]=True
        elif row['close'] < prev['dc20_low']:
            add(sn,'short',row['close']); trig[sn]=True

    # KC breakout during NY
    sn = 'NY_KC_BRK'
    if 14.5<=hour<21.0 and sn not in trig and pd.notna(row['kc_upper']):
        if row['close'] > row['kc_upper'] and prev['close'] <= prev['kc_upper']:
            add(sn,'long',row['close']); trig[sn]=True
        elif row['close'] < row['kc_lower'] and prev['close'] >= prev['kc_lower']:
            add(sn,'short',row['close']); trig[sn]=True

print(f"Done. {len(S)} strats.", flush=True)

# ── RESULTATS ──
print("\n" + "="*130)
print("EXPLORATION INDICATORS — Donnees ICMarkets")
print("Config: SL=1.0 ACT=0.5 TRAIL=0.75 | Trailing sur CLOSE | Check entry candle")
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
