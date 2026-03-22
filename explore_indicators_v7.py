"""
Exploration V7 - Derniere vague:
Parabolic SAR, Mass Index, McGinley Dynamic, Chaikin Money Flow,
Coppock Curve, Morning Star, Three Soldiers, Dark Cloud,
Doji at extreme, Engulfing+ATR, Double Smoothed Stoch,
Session overlap momentum.
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

print("Precalcul...", flush=True)
c = candles.copy()
c['body'] = c['close'] - c['open']
c['abs_body'] = abs(c['body'])
c['range'] = c['high'] - c['low']
c['mid'] = (c['high'] + c['low']) / 2
c['upper_wick'] = c['high'] - c[['open','close']].max(axis=1)
c['lower_wick'] = c[['open','close']].min(axis=1) - c['low']

# ATR
tr = np.maximum(c['high']-c['low'], np.maximum(abs(c['high']-c['close'].shift(1)), abs(c['low']-c['close'].shift(1))))
c['atr14'] = tr.ewm(span=14, adjust=False).mean()

# EMA/SMA for context
c['ema9'] = c['close'].ewm(span=9, adjust=False).mean()
c['ema20'] = c['close'].ewm(span=20, adjust=False).mean()
c['sma20'] = c['close'].rolling(20).mean()
c['bb_up'] = c['sma20'] + 2*c['close'].rolling(20).std()
c['bb_lo'] = c['sma20'] - 2*c['close'].rolling(20).std()

# ── PARABOLIC SAR ──
print("  Parabolic SAR...", flush=True)
psar = np.zeros(len(c)); psar_dir = np.zeros(len(c))
af = 0.02; af_step = 0.02; af_max = 0.20
ep = c.iloc[0]['high']; psar[0] = c.iloc[0]['low']; psar_dir[0] = 1
for i in range(1, len(c)):
    if psar_dir[i-1] == 1:  # uptrend
        psar[i] = psar[i-1] + af * (ep - psar[i-1])
        psar[i] = min(psar[i], c.iloc[i-1]['low'], c.iloc[i-2]['low'] if i>=2 else c.iloc[i-1]['low'])
        if c.iloc[i]['low'] < psar[i]:  # flip to downtrend
            psar_dir[i] = -1; psar[i] = ep; ep = c.iloc[i]['low']; af = af_step
        else:
            psar_dir[i] = 1
            if c.iloc[i]['high'] > ep: ep = c.iloc[i]['high']; af = min(af + af_step, af_max)
    else:  # downtrend
        psar[i] = psar[i-1] + af * (ep - psar[i-1])
        psar[i] = max(psar[i], c.iloc[i-1]['high'], c.iloc[i-2]['high'] if i>=2 else c.iloc[i-1]['high'])
        if c.iloc[i]['high'] > psar[i]:  # flip to uptrend
            psar_dir[i] = 1; psar[i] = ep; ep = c.iloc[i]['high']; af = af_step
        else:
            psar_dir[i] = -1
            if c.iloc[i]['low'] < ep: ep = c.iloc[i]['low']; af = min(af + af_step, af_max)
c['psar'] = psar; c['psar_dir'] = psar_dir

# ── MASS INDEX ──
print("  Mass Index...", flush=True)
ema9_hl = (c['high']-c['low']).ewm(span=9, adjust=False).mean()
ema9_ema9_hl = ema9_hl.ewm(span=9, adjust=False).mean()
ratio_mi = ema9_hl / (ema9_ema9_hl + 1e-10)
c['mass_idx'] = ratio_mi.rolling(25).sum()

# ── MCGINLEY DYNAMIC ──
print("  McGinley Dynamic...", flush=True)
md8 = np.zeros(len(c)); md21 = np.zeros(len(c))
md8[0] = c.iloc[0]['close']; md21[0] = c.iloc[0]['close']
for i in range(1, len(c)):
    cl = c.iloc[i]['close']
    r8 = cl/md8[i-1] if md8[i-1] != 0 else 1
    r21 = cl/md21[i-1] if md21[i-1] != 0 else 1
    md8[i] = md8[i-1] + (cl - md8[i-1]) / (8 * r8**4 + 1e-10)
    md21[i] = md21[i-1] + (cl - md21[i-1]) / (21 * r21**4 + 1e-10)
c['md8'] = md8; c['md21'] = md21

# ── CHAIKIN MONEY FLOW (OHLC proxy) ──
print("  Chaikin MF...", flush=True)
mfm = ((c['close']-c['low']) - (c['high']-c['close'])) / (c['range'] + 1e-10)
mfv = mfm * c['range']  # range as volume proxy
c['cmf20'] = mfv.rolling(20).sum() / (c['range'].rolling(20).sum() + 1e-10)

# ── COPPOCK CURVE (adapted for 5m) ──
print("  Coppock...", flush=True)
roc14 = (c['close'] - c['close'].shift(14)) / (c['close'].shift(14) + 1e-10) * 100
roc11 = (c['close'] - c['close'].shift(11)) / (c['close'].shift(11) + 1e-10) * 100
def wma_calc(s, n):
    w = np.arange(1, n+1)
    return s.rolling(n).apply(lambda x: np.dot(x, w)/w.sum(), raw=True)
c['coppock'] = wma_calc(roc14 + roc11, 10)

# ── DOUBLE SMOOTHED STOCHASTIC ──
print("  Double Smoothed Stoch...", flush=True)
cl_ll = c['close'] - c['low'].rolling(14).min()
hh_ll = c['high'].rolling(14).max() - c['low'].rolling(14).min()
ds_k = 100 * cl_ll.rolling(3).mean().rolling(3).mean() / (hh_ll.rolling(3).mean().rolling(3).mean() + 1e-10)
c['dss_k'] = ds_k; c['dss_d'] = ds_k.rolling(3).mean()

# ── PRE-COMPUTE rolling lows/highs ──
c['low20'] = c['low'].rolling(20).min()
c['high20'] = c['high'].rolling(20).max()

print("Collecte...", flush=True)
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

    prev2 = c.iloc[ci-2] if ci >= 2 else prev

    def add(sn, d, e):
        b, ex = sim_exit_custom(c, ci, e, d, atr, 'TRAIL', 1.0, 0.5, 0.75, check_entry_candle=False)
        pnl = (ex-e) if d=='long' else (e-ex)
        S.setdefault(sn,[]).append({'date':today,'dir':d,'pnl_oz':pnl-get_sp(today)})

    # ═══════════════════════════════════════════
    # PARABOLIC SAR FLIP
    # ═══════════════════════════════════════════
    sn = 'ALL_PSAR_FLIP'
    if sn not in trig:
        if prev['psar_dir'] == -1 and row['psar_dir'] == 1:
            add(sn,'long',row['close']); trig[sn]=True
        elif prev['psar_dir'] == 1 and row['psar_dir'] == -1:
            add(sn,'short',row['close']); trig[sn]=True

    # PSAR + EMA filter
    sn = 'ALL_PSAR_EMA'
    if sn not in trig and pd.notna(row['ema20']):
        if prev['psar_dir']==-1 and row['psar_dir']==1 and row['close']>row['ema20']:
            add(sn,'long',row['close']); trig[sn]=True
        elif prev['psar_dir']==1 and row['psar_dir']==-1 and row['close']<row['ema20']:
            add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # MASS INDEX (reversal bulge)
    # ═══════════════════════════════════════════
    sn = 'ALL_MASS_BULGE'
    if sn not in trig and pd.notna(row['mass_idx']):
        if prev['mass_idx'] >= 27 and row['mass_idx'] < 26.5:
            if row['close'] > row['ema9']:
                add(sn,'long',row['close']); trig[sn]=True
            elif row['close'] < row['ema9']:
                add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # MCGINLEY DYNAMIC CROSSOVER
    # ═══════════════════════════════════════════
    sn = 'ALL_MCGINLEY'
    if sn not in trig:
        if prev['md8'] < prev['md21'] and row['md8'] > row['md21'] and row['close'] > row['md8']:
            add(sn,'long',row['close']); trig[sn]=True
        elif prev['md8'] > prev['md21'] and row['md8'] < row['md21'] and row['close'] < row['md8']:
            add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # CHAIKIN MONEY FLOW
    # ═══════════════════════════════════════════
    sn = 'ALL_CMF_CROSS'
    if sn not in trig and pd.notna(row['cmf20']):
        if prev['cmf20'] < 0.05 and row['cmf20'] >= 0.05:
            add(sn,'long',row['close']); trig[sn]=True
        elif prev['cmf20'] > -0.05 and row['cmf20'] <= -0.05:
            add(sn,'short',row['close']); trig[sn]=True

    # CMF zero cross
    sn = 'ALL_CMF_ZERO'
    if sn not in trig and pd.notna(row['cmf20']):
        if prev['cmf20'] < 0 and row['cmf20'] >= 0:
            add(sn,'long',row['close']); trig[sn]=True
        elif prev['cmf20'] > 0 and row['cmf20'] <= 0:
            add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # COPPOCK CURVE
    # ═══════════════════════════════════════════
    sn = 'ALL_COPPOCK'
    if sn not in trig and pd.notna(row['coppock']):
        if prev['coppock'] < 0 and row['coppock'] >= 0:
            add(sn,'long',row['close']); trig[sn]=True
        elif prev['coppock'] > 0 and row['coppock'] <= 0:
            add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # DOUBLE SMOOTHED STOCHASTIC
    # ═══════════════════════════════════════════
    sn = 'ALL_DSS'
    if sn not in trig and pd.notna(row['dss_k']) and pd.notna(row['dss_d']):
        if row['dss_k'] < 20 and prev['dss_k'] < prev['dss_d'] and row['dss_k'] > row['dss_d']:
            add(sn,'long',row['close']); trig[sn]=True
        elif row['dss_k'] > 80 and prev['dss_k'] > prev['dss_d'] and row['dss_k'] < row['dss_d']:
            add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # MORNING STAR / EVENING STAR
    # ═══════════════════════════════════════════
    if ci >= 3:
        sn = 'ALL_MORN_STAR'
        if sn not in trig:
            b1 = c.iloc[ci-2]; b2 = c.iloc[ci-1]; b3 = row
            # Morning star
            if (b1['close']<b1['open'] and abs(b1['body'])>=0.5*atr and  # strong bearish
                abs(b2['body'])<0.25*atr and  # small body (doji/indecision)
                b3['close']>b3['open'] and b3['close']>(b1['open']+b1['close'])/2 and abs(b3['body'])>=0.3*atr):
                add(sn,'long',row['close']); trig[sn]=True
            # Evening star
            if (b1['close']>b1['open'] and abs(b1['body'])>=0.5*atr and
                abs(b2['body'])<0.25*atr and
                b3['close']<b3['open'] and b3['close']<(b1['open']+b1['close'])/2 and abs(b3['body'])>=0.3*atr):
                add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # THREE WHITE SOLDIERS / THREE BLACK CROWS
    # ═══════════════════════════════════════════
    if ci >= 3:
        sn = 'ALL_3SOLDIERS'
        if sn not in trig:
            b1 = c.iloc[ci-2]; b2 = c.iloc[ci-1]; b3 = row
            # Three white soldiers
            if (b1['close']>b1['open'] and b2['close']>b2['open'] and b3['close']>b3['open'] and
                b2['close']>b1['close'] and b3['close']>b2['close'] and
                b2['open']>=b1['open'] and b2['open']<=b1['close'] and
                b3['open']>=b2['open'] and b3['open']<=b2['close'] and
                min(abs(b1['body']),abs(b2['body']),abs(b3['body']))>=0.3*atr and
                b3['upper_wick']<0.2*abs(b3['body'])):
                add(sn,'long',row['close']); trig[sn]=True
            # Three black crows
            if (b1['close']<b1['open'] and b2['close']<b2['open'] and b3['close']<b3['open'] and
                b2['close']<b1['close'] and b3['close']<b2['close'] and
                b2['open']<=b1['open'] and b2['open']>=b1['close'] and
                b3['open']<=b2['open'] and b3['open']>=b2['close'] and
                min(abs(b1['body']),abs(b2['body']),abs(b3['body']))>=0.3*atr and
                b3['lower_wick']<0.2*abs(b3['body'])):
                add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # DARK CLOUD COVER / PIERCING LINE
    # ═══════════════════════════════════════════
    sn = 'ALL_DARK_CLOUD'
    if sn not in trig:
        # Piercing line (long)
        if (prev['close']<prev['open'] and abs(prev['body'])>=0.5*atr and
            row['open']<prev['low'] and row['close']>(prev['open']+prev['close'])/2 and row['close']>row['open']):
            add(sn,'long',row['close']); trig[sn]=True
        # Dark cloud cover (short)
        if (prev['close']>prev['open'] and abs(prev['body'])>=0.5*atr and
            row['open']>prev['high'] and row['close']<(prev['open']+prev['close'])/2 and row['close']<row['open']):
            add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # DOJI AT EXTREME
    # ═══════════════════════════════════════════
    sn = 'ALL_DOJI_EXT'
    if sn not in trig and ci >= 20:
        is_doji = row['abs_body'] < 0.1*row['range'] and row['range'] >= 0.3*atr
        if is_doji:
            # Count bearish bars before
            bear_count = sum(1 for j in range(1,4) if c.iloc[ci-j]['close']<c.iloc[ci-j]['open'])
            bull_count = sum(1 for j in range(1,4) if c.iloc[ci-j]['close']>c.iloc[ci-j]['open'])
            if bear_count >= 3 and row['low'] <= c.iloc[ci-20:ci]['low'].min():
                add(sn,'long',row['close']); trig[sn]=True
            elif bull_count >= 3 and row['high'] >= c.iloc[ci-20:ci]['high'].max():
                add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # ENGULFING + ATR FILTER
    # ═══════════════════════════════════════════
    sn = 'ALL_ENGULF_ATR'
    if sn not in trig and pd.notna(row.get('sma20')):
        # Bullish engulfing + close > SMA20
        if (prev['close']<prev['open'] and row['close']>row['open'] and
            row['close']>=prev['open'] and row['open']<=prev['close'] and
            row['abs_body']>=0.5*atr and row['close']>row['sma20']):
            add(sn,'long',row['close']); trig[sn]=True
        # Bearish engulfing + close < SMA20
        if (prev['close']>prev['open'] and row['close']<row['open'] and
            row['close']<=prev['open'] and row['open']>=prev['close'] and
            row['abs_body']>=0.5*atr and row['close']<row['sma20']):
            add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # SESSION OVERLAP MOMENTUM (London/NY 12:30 UTC)
    # ═══════════════════════════════════════════
    ds = pd.Timestamp(today.year,today.month,today.day,0,0,tz='UTC')
    ls = pd.Timestamp(today.year,today.month,today.day,8,0,tz='UTC')
    if 12.5<=hour<12.6:
        sn = 'OVERLAP_MOM'
        if sn not in trig:
            lon_candles = c[(c['ts_dt']>=ls)&(c['ts_dt']<ct)]
            if len(lon_candles) >= 40:
                lon_h = lon_candles['high'].max(); lon_l = lon_candles['low'].min()
                lon_mid = (lon_h + lon_l) / 2
                lon_open = lon_candles.iloc[0]['open']
                momentum = (row['close'] - lon_open) / atr
                if row['close'] > lon_mid and momentum > 0.5:
                    add(sn,'long',row['close']); trig[sn]=True
                elif row['close'] < lon_mid and momentum < -0.5:
                    add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # SESSION-SPECIFIC
    # ═══════════════════════════════════════════
    # PSAR at London
    if 8.0<=hour<14.5:
        sn = 'LON_PSAR'
        if sn not in trig:
            if prev['psar_dir']==-1 and row['psar_dir']==1:
                add(sn,'long',row['close']); trig[sn]=True
            elif prev['psar_dir']==1 and row['psar_dir']==-1:
                add(sn,'short',row['close']); trig[sn]=True

    # McGinley at Tokyo
    if 0.0<=hour<6.0:
        sn = 'TOK_MCGINLEY'
        if sn not in trig:
            if prev['md8']<prev['md21'] and row['md8']>row['md21']:
                add(sn,'long',row['close']); trig[sn]=True
            elif prev['md8']>prev['md21'] and row['md8']<row['md21']:
                add(sn,'short',row['close']); trig[sn]=True

    # Coppock at NY
    if 14.5<=hour<21.0:
        sn = 'NY_COPPOCK'
        if sn not in trig and pd.notna(row['coppock']):
            if prev['coppock']<0 and row['coppock']>=0:
                add(sn,'long',row['close']); trig[sn]=True
            elif prev['coppock']>0 and row['coppock']<=0:
                add(sn,'short',row['close']); trig[sn]=True

print(f"Done. {len(S)} strats.", flush=True)

# ── RESULTATS ──
print("\n" + "="*130)
print("EXPLORATION V7 - PSAR, Mass Index, McGinley, CMF, Coppock, Candlestick patterns")
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
    marker = " <--" if pf > 1.3 and split else " *" if pf > 1.2 and split else ""
    print(f"{sn:>18s} {n:5d} {wr:4.0f}% {pf:6.2f} {np.mean(pnls):+8.3f} {sum(pnls):+8.1f} [{f1:+7.3f}|{f2:+7.3f}] {split_str:>6s} {tiers:4d}/3{marker}")
    if pf > 1.3 and split:
        good.append(sn)

print(f"\n  Retenues PF>1.3 + split OK: {', '.join(good) if good else 'aucune'}")
# Also show PF>1.2
good12 = [sn for sn in sorted(S.keys()) if len(S[sn])>=15 and sum(p for p in [x['pnl_oz'] for x in S[sn]] if p>0)/(abs(sum(p for p in [x['pnl_oz'] for x in S[sn]] if p<0))+0.001)>1.2 and np.mean([x['pnl_oz'] for x in S[sn]][:len(S[sn])//2])>0 and np.mean([x['pnl_oz'] for x in S[sn]][len(S[sn])//2:])>0]
print(f"  Retenues PF>1.2 + split OK: {', '.join(good12)}")
print()
