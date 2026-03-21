"""
Exploration v3 — strategies session-independantes (24h).
Config: SL=1.0 ACT=0.5 TRAIL=0.75, pas de timeout, trailing sur CLOSE.
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

print("Collecte...", flush=True)
S = {}
prev_d = None; day_atr = None
# Precalcul ATR(50) glissant pour certaines strats
candles['range'] = candles['high'] - candles['low']
candles['body'] = abs(candles['close'] - candles['open'])
candles['body_signed'] = candles['close'] - candles['open']
candles['atr5'] = candles['range'].ewm(span=5, adjust=False).mean()
candles['atr50'] = candles['range'].ewm(span=50, adjust=False).mean()
candles['sma20'] = candles['close'].rolling(20).mean()

for ci in range(60, len(candles)):
    row = candles.iloc[ci]; ct = row['ts_dt']; today = ct.date()
    if today != prev_d:
        prev_d = today
        pd_ = prev_day(today); day_atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    atr = day_atr
    if atr == 0 or atr is None: continue

    def add(sn, d, e):
        b, ex = sim_exit(candles, ci, e, d, atr)
        pnl = (ex-e) if d=='long' else (e-ex)
        S.setdefault(sn,[]).append({'date':today,'dir':d,'pnl_oz':pnl-get_sp(today)})

    # Donnees locales
    prev7 = candles.iloc[ci-7:ci]
    prev10 = candles.iloc[ci-10:ci]
    prev20 = candles.iloc[ci-20:ci]
    prev30 = candles.iloc[ci-30:ci]
    prev50 = candles.iloc[ci-50:ci]

    # ═══════════════════════════════════════════
    # 1. NR7 Breakout — range le plus petit des 7 dernières bougies
    # ═══════════════════════════════════════════
    if row['range'] == prev7['range'].min() and row['range'] > 0:
        # La bougie NR7 est fermee, on entre au break du next bar
        if ci+1 < len(candles):
            nb = candles.iloc[ci+1]
            if nb['close'] > row['high']:
                add('NR7','long',nb['close'])
            elif nb['close'] < row['low']:
                add('NR7','short',nb['close'])

    # ═══════════════════════════════════════════
    # 2. ATR Expansion Continuation — bougie > 1.5x ATR
    # ═══════════════════════════════════════════
    if row['range'] >= 1.5 * atr and row['body'] >= 0.5 * atr:
        d = 'long' if row['body_signed'] > 0 else 'short'
        add('ATR_EXP',d,row['close'])

    # ═══════════════════════════════════════════
    # 3. Inside Bar Breakout — bar inside previous, break on close
    # ═══════════════════════════════════════════
    prev_bar = candles.iloc[ci-1]
    if row['high'] < prev_bar['high'] and row['low'] > prev_bar['low']:
        # Inside bar detectee, attendre le break
        if ci+1 < len(candles):
            nb = candles.iloc[ci+1]
            if nb['close'] > row['high'] and row['atr5'] > 0.7 * row['atr50']:
                add('IB_BREAK','long',nb['close'])
            elif nb['close'] < row['low'] and row['atr5'] > 0.7 * row['atr50']:
                add('IB_BREAK','short',nb['close'])

    # ═══════════════════════════════════════════
    # 4. Consecutive Exhaustion Fade — 5+ bougies meme direction
    # ═══════════════════════════════════════════
    last5 = candles.iloc[ci-4:ci+1]
    if len(last5) == 5:
        all_bull = all(last5['close'] > last5['open'])
        all_bear = all(last5['close'] < last5['open'])
        if all_bull:
            add('EXHAUST5','short',row['close'])
        elif all_bear:
            add('EXHAUST5','long',row['close'])

    # 6+ bougies
    last6 = candles.iloc[ci-5:ci+1]
    if len(last6) == 6:
        all_bull6 = all(last6['close'] > last6['open'])
        all_bear6 = all(last6['close'] < last6['open'])
        if all_bull6:
            add('EXHAUST6','short',row['close'])
        elif all_bear6:
            add('EXHAUST6','long',row['close'])

    # ═══════════════════════════════════════════
    # 5. ATR Compression Release — ATR(5) < 0.5x ATR(50) puis big bar
    # ═══════════════════════════════════════════
    if ci >= 2:
        prev_atr5 = candles.iloc[ci-1]['atr5']
        prev_atr50 = candles.iloc[ci-1]['atr50']
        if prev_atr50 > 0 and prev_atr5 < 0.5 * prev_atr50:
            if row['range'] >= 1.0 * atr and row['body'] >= 0.3 * atr:
                d = 'long' if row['body_signed'] > 0 else 'short'
                add('SQUEEZE',d,row['close'])

    # ═══════════════════════════════════════════
    # 6. Failed Breakout Reversal — break 20-bar high puis close inside
    # ═══════════════════════════════════════════
    high20 = prev20['high'].max()
    low20 = prev20['low'].min()
    if row['high'] > high20 and row['close'] < high20:
        add('FAIL_BRK','short',row['close'])
    elif row['low'] < low20 and row['close'] > low20:
        add('FAIL_BRK','long',row['close'])

    # ═══════════════════════════════════════════
    # 7. Wide Range Bar Fade — range > 2 ATR avec longue meche
    # ═══════════════════════════════════════════
    if row['range'] >= 2.0 * atr:
        upper_wick = row['high'] - max(row['open'], row['close'])
        lower_wick = min(row['open'], row['close']) - row['low']
        if upper_wick > 0.5 * row['range'] and row['body'] >= 0.1 * atr:
            add('WRB_FADE','short',row['close'])
        elif lower_wick > 0.5 * row['range'] and row['body'] >= 0.1 * atr:
            add('WRB_FADE','long',row['close'])

    # ═══════════════════════════════════════════
    # 8. VCP — 3+ bougies avec ranges decroissants
    # ═══════════════════════════════════════════
    if ci >= 4:
        r1 = candles.iloc[ci-3]['range']; r2 = candles.iloc[ci-2]['range']
        r3 = candles.iloc[ci-1]['range']; r4 = row['range']
        if r1 > r2 > r3 > r4 and r4 > 0:
            if ci+1 < len(candles):
                nb = candles.iloc[ci+1]
                if nb['close'] > row['high']:
                    add('VCP','long',nb['close'])
                elif nb['close'] < row['low']:
                    add('VCP','short',nb['close'])

    # ═══════════════════════════════════════════
    # 9. Body Ratio Momentum — body > 80% range, body > 0.5 ATR
    # ═══════════════════════════════════════════
    if row['range'] > 0 and row['body'] / row['range'] > 0.80 and row['body'] >= 0.5 * atr:
        d = 'long' if row['body_signed'] > 0 else 'short'
        add('BODY80',d,row['close'])

    # ═══════════════════════════════════════════
    # 10. ATR Overshoot Mean Reversion — close > 2 ATR from SMA20
    # ═══════════════════════════════════════════
    if pd.notna(row['sma20']) and atr > 0:
        dist = (row['close'] - row['sma20']) / atr
        if dist >= 2.0:
            add('MR_2ATR','short',row['close'])
        elif dist <= -2.0:
            add('MR_2ATR','long',row['close'])
        # Version 1.5 ATR
        if dist >= 1.5:
            add('MR_15ATR','short',row['close'])
        elif dist <= -1.5:
            add('MR_15ATR','long',row['close'])

    # ═══════════════════════════════════════════
    # 11. Pin Bar at 30-bar Extreme
    # ═══════════════════════════════════════════
    if row['range'] >= 0.3 * atr and row['body'] >= 0.1 * atr:
        upper_wick = row['high'] - max(row['open'], row['close'])
        lower_wick = min(row['open'], row['close']) - row['low']
        is_hammer = lower_wick > 2 * row['body'] and upper_wick < row['body']
        is_star = upper_wick > 2 * row['body'] and lower_wick < row['body']
        at_low30 = row['low'] <= prev30['low'].min()
        at_high30 = row['high'] >= prev30['high'].max()
        if is_hammer and at_low30:
            add('PIN_EXT','long',row['close'])
        elif is_star and at_high30:
            add('PIN_EXT','short',row['close'])

    # ═══════════════════════════════════════════
    # 12. Three-Bar Reversal
    # ═══════════════════════════════════════════
    if ci >= 3:
        b1 = candles.iloc[ci-2]; b2 = candles.iloc[ci-1]; b3 = row
        # Bearish: b1 new 10-bar high, b2 small, b3 closes below b2 open
        if b1['high'] >= prev10['high'].max() and b2['range'] < b1['range'] * 0.5:
            if b3['close'] < b2['open'] and b3['body'] >= 0.3 * atr:
                add('3BAR_REV','short',b3['close'])
        # Bullish: b1 new 10-bar low, b2 small, b3 closes above b2 open
        if b1['low'] <= prev10['low'].min() and b2['range'] < b1['range'] * 0.5:
            if b3['close'] > b2['open'] and b3['body'] >= 0.3 * atr:
                add('3BAR_REV','long',b3['close'])

    # ═══════════════════════════════════════════
    # 13. ATR Channel Breakout — 50-bar high/low + expanding vol
    # ═══════════════════════════════════════════
    if row['atr50'] > 0 and row['atr5'] / row['atr50'] > 1.2:
        if row['close'] > prev50['high'].max():
            add('ATR_CH50','long',row['close'])
        elif row['close'] < prev50['low'].min():
            add('ATR_CH50','short',row['close'])

    # ═══════════════════════════════════════════
    # 14. Engulfing Bar Continuation (dans le sens du trend)
    # ═══════════════════════════════════════════
    if ci >= 6:
        prev5_dir = sum(1 for i in range(ci-5,ci) if candles.iloc[i]['close'] > candles.iloc[i]['open'])
        pb = candles.iloc[ci-1]
        # Bullish engulfing in uptrend
        if prev5_dir >= 3 and pb['close'] < pb['open'] and row['close'] > row['open']:
            if row['close'] >= pb['open'] and row['open'] <= pb['close'] and row['body'] >= 0.3*atr:
                add('ENG_CONT','long',row['close'])
        # Bearish engulfing in downtrend
        if prev5_dir <= 2 and pb['close'] > pb['open'] and row['close'] < row['open']:
            if row['close'] <= pb['open'] and row['open'] >= pb['close'] and row['body'] >= 0.3*atr:
                add('ENG_CONT','short',row['close'])

    # ═══════════════════════════════════════════
    # 15. Micro-Gap Continuation — gap > 0.1 ATR entre 2 bougies
    # ═══════════════════════════════════════════
    gap = row['open'] - prev_bar['close']
    if abs(gap) >= 0.1 * atr and row['body'] >= 0.2 * atr:
        if gap > 0 and row['body_signed'] > 0:
            add('MICROGAP','long',row['close'])
        elif gap < 0 and row['body_signed'] < 0:
            add('MICROGAP','short',row['close'])

    # ═══════════════════════════════════════════
    # 16. Double Inside Bar — 2 inside bars consecutives
    # ═══════════════════════════════════════════
    if ci >= 3:
        b0 = candles.iloc[ci-2]; b1 = candles.iloc[ci-1]; b2 = row
        ib1 = b1['high'] < b0['high'] and b1['low'] > b0['low']
        ib2 = b2['high'] < b1['high'] and b2['low'] > b1['low']
        if ib1 and ib2:
            if ci+1 < len(candles):
                nb = candles.iloc[ci+1]
                if nb['close'] > b2['high']:
                    add('DBL_IB','long',nb['close'])
                elif nb['close'] < b2['low']:
                    add('DBL_IB','short',nb['close'])

print(f"Done. {len(S)} strats.", flush=True)

# ── RESULTATS ──
print("\n" + "="*120)
print("EXPLORATION V3 — Strategies session-independantes (24h)")
print("Config: SL=1.0 ACT=0.5 TRAIL=0.75, pas de timeout")
print("="*120)
print(f"{'Strat':>10s} {'n':>5s} {'WR':>5s} {'PF':>6s} {'Avg':>8s} {'Total':>8s} {'[1st|2nd]':>18s} {'Split':>6s} {'Tiers':>5s}")
print("-"*120)

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
    nl = sum(1 for x in t if x['dir']=='long'); ns = sum(1 for x in t if x['dir']=='short')
    marker = " <--" if pf > 1.5 and split else " *" if pf > 1.2 and split else ""
    print(f"{sn:>10s} {n:5d} {wr:4.0f}% {pf:6.2f} {np.mean(pnls):+8.3f} {sum(pnls):+8.1f} [{f1:+7.3f}|{f2:+7.3f}] {split_str:>6s} {tiers:4d}/3 L:{nl} S:{ns}{marker}")
    if pf > 1.2 and split:
        good.append(sn)

print(f"\n  Retenues (PF>1.2 + split OK): {', '.join(good) if good else 'aucune'}")
print()
