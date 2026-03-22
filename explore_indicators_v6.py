"""
Exploration V6 - Indicateurs exotiques:
Parabolic SAR, Supertrend, Awesome Oscillator, Alligator (Bill Williams),
Elder Ray, Aroon, Chande Momentum, DPO, Fisher Transform,
Multi-timeframe proxies, candlestick patterns avances.
Tout sur bougies FERMEES, ZERO look-ahead.
"""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
from dotenv import load_dotenv; load_dotenv()
from phase1_poc_calculator import get_conn, compute_atr, get_trading_days
from phase3_analyze import load_candles_5m
from strats import sim_exit_custom

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

print("Precalcul indicateurs exotiques...", flush=True)
c = candles.copy()
c['body'] = c['close'] - c['open']
c['abs_body'] = abs(c['body'])
c['range'] = c['high'] - c['low']
c['mid'] = (c['high'] + c['low']) / 2
c['tp'] = (c['high'] + c['low'] + c['close']) / 3

# ATR
tr = np.maximum(c['high']-c['low'], np.maximum(abs(c['high']-c['close'].shift(1)), abs(c['low']-c['close'].shift(1))))
c['atr14'] = tr.ewm(span=14, adjust=False).mean()

# ── SUPERTREND ──
for mult, nm in [(2.0,'2'),(3.0,'3')]:
    up = c['mid'] - mult * c['atr14']
    dn = c['mid'] + mult * c['atr14']
    st = np.zeros(len(c)); st_dir = np.zeros(len(c))
    for i in range(1, len(c)):
        if c.iloc[i]['close'] > dn.iloc[i-1]:
            st[i] = up.iloc[i]; st_dir[i] = 1
        elif c.iloc[i]['close'] < up.iloc[i-1]:
            st[i] = dn.iloc[i]; st_dir[i] = -1
        else:
            st_dir[i] = st_dir[i-1]
            if st_dir[i] == 1:
                st[i] = max(up.iloc[i], st[i-1])
            else:
                st[i] = min(dn.iloc[i], st[i-1])
    c[f'st{nm}'] = st; c[f'st{nm}_dir'] = st_dir

# ── AWESOME OSCILLATOR (Bill Williams) ──
c['ao'] = c['mid'].rolling(5).mean() - c['mid'].rolling(34).mean()
c['ao_prev'] = c['ao'].shift(1)

# ── ALLIGATOR (Bill Williams) ──
c['jaw'] = c['mid'].rolling(13).mean().shift(8)    # Blue (13, shift 8)
c['teeth'] = c['mid'].rolling(8).mean().shift(5)   # Red (8, shift 5)
c['lips'] = c['mid'].rolling(5).mean().shift(3)    # Green (5, shift 3)

# ── ELDER RAY ──
c['ema13'] = c['close'].ewm(span=13, adjust=False).mean()
c['bull_power'] = c['high'] - c['ema13']
c['bear_power'] = c['low'] - c['ema13']

# ── AROON ──
for p in [14,25]:
    c[f'aroon_up{p}'] = c['high'].rolling(p+1).apply(lambda x: x.argmax()/p*100, raw=True)
    c[f'aroon_dn{p}'] = c['low'].rolling(p+1).apply(lambda x: x.argmin()/p*100, raw=True)
    c[f'aroon_osc{p}'] = c[f'aroon_up{p}'] - c[f'aroon_dn{p}']

# ── CHANDE MOMENTUM OSCILLATOR (CMO) ──
for p in [9,14]:
    delta = c['close'].diff()
    su = delta.clip(lower=0).rolling(p).sum()
    sd = (-delta.clip(upper=0)).rolling(p).sum()
    c[f'cmo{p}'] = 100 * (su - sd) / (su + sd + 1e-10)

# ── DETRENDED PRICE OSCILLATOR (DPO) ──
for p in [14,20]:
    sma = c['close'].rolling(p).mean()
    c[f'dpo{p}'] = c['close'] - sma.shift(p//2 + 1)

# ── FISHER TRANSFORM ──
for p in [9,14]:
    hh = c['high'].rolling(p).max(); ll = c['low'].rolling(p).min()
    val = 2 * ((c['close'] - ll) / (hh - ll + 1e-10) - 0.5)
    val = val.clip(-0.999, 0.999)
    c[f'fisher{p}'] = 0.5 * np.log((1+val)/(1-val+1e-10))
    c[f'fisher{p}'] = c[f'fisher{p}'].ewm(span=3, adjust=False).mean()
    c[f'fisher{p}_sig'] = c[f'fisher{p}'].shift(1)

# ── TRIX ──
for p in [9,14]:
    e1 = c['close'].ewm(span=p, adjust=False).mean()
    e2 = e1.ewm(span=p, adjust=False).mean()
    e3 = e2.ewm(span=p, adjust=False).mean()
    c[f'trix{p}'] = (e3 - e3.shift(1)) / (e3.shift(1) + 1e-10) * 10000
    c[f'trix{p}_sig'] = c[f'trix{p}'].rolling(9).mean()

# ── SCHAFF TREND CYCLE (simplified) ──
macd_val = c['close'].ewm(span=23, adjust=False).mean() - c['close'].ewm(span=50, adjust=False).mean()
stc_k = 100 * (macd_val - macd_val.rolling(10).min()) / (macd_val.rolling(10).max() - macd_val.rolling(10).min() + 1e-10)
c['stc'] = stc_k.ewm(span=3, adjust=False).mean()

# ── CONNORS RSI (simplified: RSI + streak RSI + percentrank) ──
delta = c['close'].diff()
streak = np.zeros(len(c))
for i in range(1, len(c)):
    if delta.iloc[i] > 0: streak[i] = max(streak[i-1], 0) + 1
    elif delta.iloc[i] < 0: streak[i] = min(streak[i-1], 0) - 1
    else: streak[i] = 0
streak_s = pd.Series(streak)
# RSI of streak
d2 = streak_s.diff(); g2 = d2.clip(lower=0); l2 = (-d2).clip(upper=0)
ag2 = g2.ewm(alpha=1/3, min_periods=3, adjust=False).mean()
al2 = l2.ewm(alpha=1/3, min_periods=3, adjust=False).mean()
streak_rsi = 100 - 100/(1+ag2/(al2.abs()+1e-10))
# Standard RSI
d3 = c['close'].diff(); g3 = d3.clip(lower=0); l3 = (-d3).clip(upper=0)
ag3 = g3.ewm(alpha=1/3, min_periods=3, adjust=False).mean()
al3 = l3.ewm(alpha=1/3, min_periods=3, adjust=False).mean()
rsi3 = 100 - 100/(1+ag3/(al3.abs()+1e-10))
# Percent rank
pct_rank = c['close'].pct_change().rolling(100).apply(lambda x: (x<x.iloc[-1]).sum()/len(x)*100, raw=False)
c['crsi'] = (rsi3 + streak_rsi.values + pct_rank.fillna(50)) / 3

# ── MULTI-TIMEFRAME PROXY (1h = 12 bars) ──
c['ema12_1h'] = c['close'].ewm(span=12*21, adjust=False).mean()  # ~21 period on 1h
c['close_1h'] = c['close'].rolling(12).mean()  # 1h smoothed close
c['high_1h'] = c['high'].rolling(12).max()
c['low_1h'] = c['low'].rolling(12).min()

# EMAs for context
c['ema9'] = c['close'].ewm(span=9, adjust=False).mean()
c['ema21'] = c['close'].ewm(span=21, adjust=False).mean()
c['ema50'] = c['close'].ewm(span=50, adjust=False).mean()

print("Collecte...", flush=True)
S = {}
prev_d = None; trig = {}; day_atr = None

for ci in range(300, len(c)):
    row = c.iloc[ci]; prev = c.iloc[ci-1]; ct = row['ts_dt']; today = ct.date()
    hour = ct.hour + ct.minute / 60.0
    if today != prev_d:
        prev_d = today; trig = {}
        pd_ = prev_day(today); day_atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    atr = day_atr
    if atr == 0 or atr is None: continue

    def add(sn, d, e):
        b, ex = sim_exit_custom(c, ci, e, d, atr, 'TRAIL', 1.0, 0.5, 0.75, check_entry_candle=False)
        pnl = (ex-e) if d=='long' else (e-ex)
        S.setdefault(sn,[]).append({'date':today,'dir':d,'pnl_oz':pnl-get_sp(today)})

    # ═══════════════════════════════════════════
    # SUPERTREND
    # ═══════════════════════════════════════════
    for mult, nm in [('2','2'),('3','3')]:
        sn = f'ALL_ST_{nm}'
        if sn not in trig:
            if prev[f'st{nm}_dir'] == -1 and row[f'st{nm}_dir'] == 1:
                add(sn,'long',row['close']); trig[sn]=True
            elif prev[f'st{nm}_dir'] == 1 and row[f'st{nm}_dir'] == -1:
                add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # AWESOME OSCILLATOR
    # ═══════════════════════════════════════════
    # AO zero cross
    sn = 'ALL_AO_ZERO'
    if sn not in trig and pd.notna(row['ao']):
        if prev['ao'] < 0 and row['ao'] >= 0:
            add(sn,'long',row['close']); trig[sn]=True
        elif prev['ao'] > 0 and row['ao'] <= 0:
            add(sn,'short',row['close']); trig[sn]=True

    # AO twin peaks (saucer)
    sn = 'ALL_AO_SAUCER'
    if sn not in trig and ci >= 4 and pd.notna(row['ao']):
        a = [c.iloc[ci-j]['ao'] for j in range(3,-1,-1)]
        if all(pd.notna(x) for x in a):
            if a[0]>0 and a[1]<a[0] and a[2]<a[1] and a[3]>a[2] and a[3]>0:
                add(sn,'long',row['close']); trig[sn]=True
            elif a[0]<0 and a[1]>a[0] and a[2]>a[1] and a[3]<a[2] and a[3]<0:
                add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # ALLIGATOR (Bill Williams)
    # ═══════════════════════════════════════════
    sn = 'ALL_GATOR_OPEN'
    if sn not in trig and pd.notna(row['jaw']) and pd.notna(row['lips']):
        # Alligator opening mouth: lips > teeth > jaw (bullish) or lips < teeth < jaw (bearish)
        if row['lips']>row['teeth']>row['jaw'] and not(prev['lips']>prev['teeth']>prev['jaw']):
            add(sn,'long',row['close']); trig[sn]=True
        elif row['lips']<row['teeth']<row['jaw'] and not(prev['lips']<prev['teeth']<prev['jaw']):
            add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # ELDER RAY
    # ═══════════════════════════════════════════
    sn = 'ALL_ELDER_RAY'
    if sn not in trig and pd.notna(row['bull_power']):
        if row['ema13'] > prev['ema13']:  # uptrend
            if prev['bear_power'] < 0 and row['bear_power'] > prev['bear_power']:
                add(sn,'long',row['close']); trig[sn]=True
        elif row['ema13'] < prev['ema13']:  # downtrend
            if prev['bull_power'] > 0 and row['bull_power'] < prev['bull_power']:
                add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # AROON
    # ═══════════════════════════════════════════
    for p, nm in [(14,'14'),(25,'25')]:
        sn = f'ALL_AROON_{nm}'
        if sn not in trig and pd.notna(row[f'aroon_up{p}']):
            if prev[f'aroon_up{p}'] < prev[f'aroon_dn{p}'] and row[f'aroon_up{p}'] > row[f'aroon_dn{p}']:
                add(sn,'long',row['close']); trig[sn]=True
            elif prev[f'aroon_up{p}'] > prev[f'aroon_dn{p}'] and row[f'aroon_up{p}'] < row[f'aroon_dn{p}']:
                add(sn,'short',row['close']); trig[sn]=True

    # Aroon extreme
    sn = 'ALL_AROON_EXT'
    if sn not in trig and pd.notna(row['aroon_up14']):
        if row['aroon_up14'] >= 100 and row['aroon_dn14'] <= 30:
            add(sn,'long',row['close']); trig[sn]=True
        elif row['aroon_dn14'] >= 100 and row['aroon_up14'] <= 30:
            add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # CHANDE MOMENTUM OSCILLATOR
    # ═══════════════════════════════════════════
    for p, nm in [(9,'9'),(14,'14')]:
        sn = f'ALL_CMO_{nm}'
        if sn not in trig and pd.notna(row[f'cmo{p}']):
            if prev[f'cmo{p}'] < -50 and row[f'cmo{p}'] >= -50:
                add(sn,'long',row['close']); trig[sn]=True
            elif prev[f'cmo{p}'] > 50 and row[f'cmo{p}'] <= 50:
                add(sn,'short',row['close']); trig[sn]=True

    # CMO zero cross
    for p, nm in [(9,'9'),(14,'14')]:
        sn = f'ALL_CMO_{nm}_ZERO'
        if sn not in trig and pd.notna(row[f'cmo{p}']):
            if prev[f'cmo{p}'] < 0 and row[f'cmo{p}'] >= 0:
                add(sn,'long',row['close']); trig[sn]=True
            elif prev[f'cmo{p}'] > 0 and row[f'cmo{p}'] <= 0:
                add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # DETRENDED PRICE OSCILLATOR
    # ═══════════════════════════════════════════
    for p, nm in [(14,'14'),(20,'20')]:
        sn = f'ALL_DPO_{nm}'
        if sn not in trig and pd.notna(row[f'dpo{p}']):
            if prev[f'dpo{p}'] < 0 and row[f'dpo{p}'] >= 0:
                add(sn,'long',row['close']); trig[sn]=True
            elif prev[f'dpo{p}'] > 0 and row[f'dpo{p}'] <= 0:
                add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # FISHER TRANSFORM
    # ═══════════════════════════════════════════
    for p, nm in [(9,'9'),(14,'14')]:
        sn = f'ALL_FISHER_{nm}'
        if sn not in trig and pd.notna(row[f'fisher{p}']):
            if prev[f'fisher{p}'] < prev[f'fisher{p}_sig'] and row[f'fisher{p}'] > row[f'fisher{p}_sig']:
                add(sn,'long',row['close']); trig[sn]=True
            elif prev[f'fisher{p}'] > prev[f'fisher{p}_sig'] and row[f'fisher{p}'] < row[f'fisher{p}_sig']:
                add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # TRIX
    # ═══════════════════════════════════════════
    for p, nm in [(9,'9'),(14,'14')]:
        sn = f'ALL_TRIX_{nm}'
        if sn not in trig and pd.notna(row[f'trix{p}']):
            if prev[f'trix{p}'] < prev[f'trix{p}_sig'] and row[f'trix{p}'] > row[f'trix{p}_sig']:
                add(sn,'long',row['close']); trig[sn]=True
            elif prev[f'trix{p}'] > prev[f'trix{p}_sig'] and row[f'trix{p}'] < row[f'trix{p}_sig']:
                add(sn,'short',row['close']); trig[sn]=True

    # TRIX zero cross
    for p, nm in [(9,'9'),(14,'14')]:
        sn = f'ALL_TRIX_{nm}_ZERO'
        if sn not in trig and pd.notna(row[f'trix{p}']):
            if prev[f'trix{p}'] < 0 and row[f'trix{p}'] >= 0:
                add(sn,'long',row['close']); trig[sn]=True
            elif prev[f'trix{p}'] > 0 and row[f'trix{p}'] <= 0:
                add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # SCHAFF TREND CYCLE
    # ═══════════════════════════════════════════
    sn = 'ALL_STC'
    if sn not in trig and pd.notna(row['stc']):
        if prev['stc'] < 25 and row['stc'] >= 25:
            add(sn,'long',row['close']); trig[sn]=True
        elif prev['stc'] > 75 and row['stc'] <= 75:
            add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # CONNORS RSI
    # ═══════════════════════════════════════════
    sn = 'ALL_CRSI'
    if sn not in trig and pd.notna(row['crsi']):
        if prev['crsi'] < 10 and row['crsi'] >= 10:
            add(sn,'long',row['close']); trig[sn]=True
        elif prev['crsi'] > 90 and row['crsi'] <= 90:
            add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # MULTI-TIMEFRAME: 1h EMA vs 5m price
    # ═══════════════════════════════════════════
    sn = 'ALL_MTF_EMA'
    if sn not in trig and pd.notna(row['ema12_1h']):
        if prev['close'] < prev['ema12_1h'] and row['close'] > row['ema12_1h'] and row['close'] > row['open']:
            add(sn,'long',row['close']); trig[sn]=True
        elif prev['close'] > prev['ema12_1h'] and row['close'] < row['ema12_1h'] and row['close'] < row['open']:
            add(sn,'short',row['close']); trig[sn]=True

    # 1h range breakout
    sn = 'ALL_MTF_BRK'
    if sn not in trig and pd.notna(row['high_1h']):
        if row['close'] > prev['high_1h'] and prev['close'] <= c.iloc[ci-2]['high_1h']:
            add(sn,'long',row['close']); trig[sn]=True
        elif row['close'] < prev['low_1h'] and prev['close'] >= c.iloc[ci-2]['low_1h']:
            add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # COMBOS
    # ═══════════════════════════════════════════
    # Supertrend + AO
    sn = 'ALL_ST_AO'
    if sn not in trig and pd.notna(row['ao']):
        if prev['st2_dir']==-1 and row['st2_dir']==1 and row['ao']>0:
            add(sn,'long',row['close']); trig[sn]=True
        elif prev['st2_dir']==1 and row['st2_dir']==-1 and row['ao']<0:
            add(sn,'short',row['close']); trig[sn]=True

    # Fisher + CMO
    sn = 'ALL_FISHER_CMO'
    if sn not in trig and pd.notna(row['fisher9']) and pd.notna(row['cmo9']):
        if prev['fisher9']<prev['fisher9_sig'] and row['fisher9']>row['fisher9_sig'] and row['cmo9']>0:
            add(sn,'long',row['close']); trig[sn]=True
        elif prev['fisher9']>prev['fisher9_sig'] and row['fisher9']<row['fisher9_sig'] and row['cmo9']<0:
            add(sn,'short',row['close']); trig[sn]=True

    # Aroon + Supertrend
    sn = 'ALL_AROON_ST'
    if sn not in trig and pd.notna(row['aroon_up14']):
        if row['aroon_up14']>70 and row['aroon_dn14']<30 and row['st2_dir']==1:
            if not(prev['aroon_up14']>70 and prev['aroon_dn14']<30):
                add(sn,'long',row['close']); trig[sn]=True
        elif row['aroon_dn14']>70 and row['aroon_up14']<30 and row['st2_dir']==-1:
            if not(prev['aroon_dn14']>70 and prev['aroon_up14']<30):
                add(sn,'short',row['close']); trig[sn]=True

    # TRIX + Elder Ray
    sn = 'ALL_TRIX_ELDER'
    if sn not in trig and pd.notna(row['trix9']) and pd.notna(row['bull_power']):
        if prev['trix9']<prev['trix9_sig'] and row['trix9']>row['trix9_sig'] and row['bear_power']>prev['bear_power'] and row['ema13']>prev['ema13']:
            add(sn,'long',row['close']); trig[sn]=True
        elif prev['trix9']>prev['trix9_sig'] and row['trix9']<row['trix9_sig'] and row['bull_power']<prev['bull_power'] and row['ema13']<prev['ema13']:
            add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # SESSION-SPECIFIC
    # ═══════════════════════════════════════════
    if 8.0<=hour<14.5:
        sn = 'LON_ST_FLIP'
        if sn not in trig:
            if prev['st2_dir']==-1 and row['st2_dir']==1:
                add(sn,'long',row['close']); trig[sn]=True
            elif prev['st2_dir']==1 and row['st2_dir']==-1:
                add(sn,'short',row['close']); trig[sn]=True

    if 0.0<=hour<6.0:
        sn = 'TOK_FISHER'
        if sn not in trig and pd.notna(row['fisher9']):
            if prev['fisher9']<prev['fisher9_sig'] and row['fisher9']>row['fisher9_sig']:
                add(sn,'long',row['close']); trig[sn]=True
            elif prev['fisher9']>prev['fisher9_sig'] and row['fisher9']<row['fisher9_sig']:
                add(sn,'short',row['close']); trig[sn]=True

    if 14.5<=hour<21.0:
        sn = 'NY_AROON'
        if sn not in trig and pd.notna(row['aroon_up14']):
            if prev['aroon_up14']<prev['aroon_dn14'] and row['aroon_up14']>row['aroon_dn14']:
                add(sn,'long',row['close']); trig[sn]=True
            elif prev['aroon_up14']>prev['aroon_dn14'] and row['aroon_up14']<row['aroon_dn14']:
                add(sn,'short',row['close']); trig[sn]=True

print(f"Done. {len(S)} strats.", flush=True)

# ── RESULTATS ──
print("\n" + "="*130)
print("EXPLORATION V6 - Supertrend, AO, Alligator, Elder Ray, Aroon, CMO, Fisher, TRIX, STC, CRSI")
print("="*130)
print(f"{'Strat':>18s} {'n':>5s} {'WR':>5s} {'PF':>6s} {'Avg':>8s} {'Total':>8s} {'[1st|2nd]':>18s} {'Split':>6s} {'Tiers':>5s}")
print("-"*130)

good = []
for sn in sorted(S.keys()):
    t = S[sn]
    if len(t) < 15: continue
    pnls = [x['pnl_oz'] for x in t]
    n = len(pnls)
    gp = sum(p for p in pnls if p>0); gl = abs(sum(p for p in pnls if p<0))+0.001
    wr = sum(1 for p in pnls if p>0)/n*100
    pf = gp/gl
    mid = n//2; f1 = np.mean(pnls[:mid]); f2 = np.mean(pnls[mid:])
    t1 = sum(pnls[:n//3]); t2 = sum(pnls[n//3:2*n//3]); t3 = sum(pnls[2*n//3:])
    tiers = sum(1 for x in [t1,t2,t3] if x>0)
    split = f1>0 and f2>0
    split_str = "OK" if split else "!!"
    marker = " <--" if pf > 1.2 and split else ""
    print(f"{sn:>18s} {n:5d} {wr:4.0f}% {pf:6.2f} {np.mean(pnls):+8.3f} {sum(pnls):+8.1f} [{f1:+7.3f}|{f2:+7.3f}] {split_str:>6s} {tiers:4d}/3{marker}")
    if pf > 1.2 and split:
        good.append(sn)

print(f"\n  Retenues (PF>1.2 + split OK): {', '.join(good) if good else 'aucune'}")
print()
