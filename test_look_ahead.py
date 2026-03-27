"""
Test look-ahead: compare signals from full dataset vs truncated dataset.
If ANY signal differs → look-ahead bias detected.

Principle: signals on bar N should ONLY depend on bars 0..N.
So truncating data after bar N should produce identical signals for bars 0..N.
"""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd, pickle
from strats import detect_all, compute_indicators

# Load full dataset
SYMBOL = sys.argv[1] if len(sys.argv) > 1 else 'xauusd'
ACCOUNT = sys.argv[2] if len(sys.argv) > 2 else '5ers'
sym_dir = f'/{SYMBOL}' if SYMBOL != 'xauusd' else ''
pkl_path = f'data/{ACCOUNT}{sym_dir}/optim_data.pkl'

# We need the raw candles, not the pkl. Load from DB.
from phase1_poc_calculator import get_conn
conn = get_conn(); conn.autocommit = True
table = f"candles_mt5_{SYMBOL}_5m"
cur = conn.cursor()
cur.execute(f"SELECT ts, open, high, low, close FROM {table} ORDER BY ts")
rows = cur.fetchall(); cur.close(); conn.close()
c = pd.DataFrame(rows, columns=['ts','open','high','low','close'])
c['ts_dt'] = pd.to_datetime(c['ts'], unit='ms', utc=True)
for col in ['open','high','low','close']: c[col] = c[col].astype(float)
c['date'] = c['ts_dt'].dt.date
print(f"Loaded {len(c)} candles for {SYMBOL}")

# Split point: 60% of data
split = int(len(c) * 0.6)
print(f"Split at bar {split} ({c.iloc[split]['ts_dt'].date()})")

# Collect signals on FULL dataset
def collect_signals(candles, max_bar=None):
    candles = compute_indicators(candles.copy())
    if max_bar is None: max_bar = len(candles)

    signals = {}  # (ci, strat, dir) -> entry_price
    prev_d = None; trig = {}; prev_day_data = None; prev2_day_data = None

    # Pre-compute daily ATR
    daily_atr = {}
    for d in candles['date'].unique():
        dc = candles[candles['date'] == d]
        if len(dc) < 14: continue
        tr = np.maximum(dc['high']-dc['low'],
                       np.maximum(abs(dc['high']-dc['close'].shift(1)),
                                  abs(dc['low']-dc['close'].shift(1))))
        daily_atr[d] = float(tr.ewm(span=14, adjust=False).mean().iloc[-1])

    trading_days = sorted(daily_atr.keys())
    def prev_day(today):
        for di, d in enumerate(trading_days):
            if d >= today: return trading_days[di-1] if di > 0 else None
        return None

    global_atr = np.mean(list(daily_atr.values())) if daily_atr else 1.0

    for ci in range(200, min(max_bar, len(candles))):
        row = candles.iloc[ci]; ct = row['ts_dt']; today = ct.date()
        hour = ct.hour + ct.minute / 60.0
        if today != prev_d:
            if prev_d:
                yc = candles[candles['date'] == prev_d]
                if len(yc) > 0:
                    prev2_day_data = prev_day_data
                    prev_day_data = {'open':float(yc.iloc[0]['open']), 'close':float(yc.iloc[-1]['close']),
                                     'high':float(yc['high'].max()), 'low':float(yc['low'].min()),
                                     'range':float(yc['high'].max()-yc['low'].min())}
            prev_d = today; trig = {}
            pd_ = prev_day(today)
            atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0 or atr is None: continue

        ds = pd.Timestamp(today.year,today.month,today.day,0,0,tz='UTC')
        te = pd.Timestamp(today.year,today.month,today.day,6,0,tz='UTC')
        ls = pd.Timestamp(today.year,today.month,today.day,8,0,tz='UTC')
        ns = pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC')
        tv = candles[(candles['ts_dt']>=ds)&(candles['ts_dt']<=ct)]
        tok = tv[tv['ts_dt']<te]; lon = tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<ns)]

        def add_sig(sn, d, e):
            signals[(ci, sn)] = (d, round(e, 6))

        detect_all(candles, ci, row, ct, today, hour, atr, trig, tv, tok, lon, prev_day_data, add_sig, prev2_day_data)

    return signals

print("\n1. Collecting signals on FULL dataset...")
sigs_full = collect_signals(c)
print(f"   {len(sigs_full)} signals")

print("\n2. Collecting signals on TRUNCATED dataset (first 60%)...")
c_trunc = c.iloc[:split].copy().reset_index(drop=True)
sigs_trunc = collect_signals(c_trunc)
print(f"   {len(sigs_trunc)} signals")

# Compare: every signal in truncated should match full dataset
print("\n3. Comparing signals...")
mismatches = 0
missing_in_full = 0
missing_in_trunc = 0
price_diffs = 0

# Signals in truncated that differ from full
for key, (d_t, e_t) in sigs_trunc.items():
    if key not in sigs_full:
        missing_in_full += 1
        ci, sn = key
        print(f"  EXTRA in trunc: bar={ci} strat={sn} dir={d_t} — NOT in full dataset")
        mismatches += 1
    else:
        d_f, e_f = sigs_full[key]
        if d_t != d_f:
            ci, sn = key
            print(f"  DIR MISMATCH: bar={ci} strat={sn} trunc={d_t} full={d_f}")
            mismatches += 1
        elif abs(e_t - e_f) > 0.01:
            ci, sn = key
            print(f"  PRICE DIFF: bar={ci} strat={sn} trunc={e_t:.4f} full={e_f:.4f}")
            price_diffs += 1

# Signals in full (within truncated range) missing from truncated
max_trunc_bar = split - 1
for key, (d_f, e_f) in sigs_full.items():
    ci, sn = key
    if ci < split and key not in sigs_trunc:
        missing_in_trunc += 1
        if missing_in_trunc <= 10:
            print(f"  MISSING in trunc: bar={ci} strat={sn} dir={d_f} — in full but NOT in trunc")
        mismatches += 1

if missing_in_trunc > 10:
    print(f"  ... and {missing_in_trunc - 10} more MISSING in trunc")

print(f"\n{'='*60}")
print(f"RESULTS:")
print(f"  Full signals (first 60%): {sum(1 for (ci,_) in sigs_full if ci < split)}")
print(f"  Trunc signals:            {len(sigs_trunc)}")
print(f"  Mismatches:               {mismatches}")
print(f"  Price diffs (>0.01):      {price_diffs}")

if mismatches == 0 and price_diffs == 0:
    print(f"\n  PASS — ZERO look-ahead detected")
else:
    print(f"\n  FAIL — {mismatches} mismatches + {price_diffs} price diffs")
    print(f"  LOOK-AHEAD BIAS DETECTED!")
