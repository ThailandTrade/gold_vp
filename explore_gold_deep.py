"""
Deep gold exploration — concepts inedits.
Tout avec trailing + spread reel.
"""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
from dotenv import load_dotenv
from datetime import datetime, timedelta
load_dotenv()
from phase1_poc_calculator import (
    get_conn, SESSIONS_CONFIG, compute_vp, load_ticks_for_period,
    compute_atr, get_trading_days
)
from phase3_analyze import load_candles_5m

SLIPPAGE = 0.10

def sim_trail(cdf, pos, entry, d, sl_atr, atr, mx, act, trail):
    best = entry
    stop = entry + sl_atr*atr if d == 'short' else entry - sl_atr*atr
    ta = False
    for j in range(1, mx+1):
        if pos+j >= len(cdf): break
        b = cdf.iloc[pos+j]
        if d == 'long':
            if b['low'] <= stop: return j, stop - SLIPPAGE
            if b['high'] > best: best = b['high']
            if not ta and (best-entry) >= act*atr: ta = True
            if ta: stop = max(stop, best - trail*atr)
        else:
            if b['high'] >= stop: return j, stop + SLIPPAGE
            if b['low'] < best: best = b['low']
            if not ta and (entry-best) >= act*atr: ta = True
            if ta: stop = min(stop, best + trail*atr)
    if pos+mx < len(cdf): return mx, cdf.iloc[pos+mx]['close']
    return mx, entry

def pr(trades, label, spread_rt=0.188):
    if len(trades) < 20:
        print("    {:60s}: n={:3d} --".format(label, len(trades)))
        return
    df = pd.DataFrame(trades).sort_values('date')
    n = len(df); mid = n // 2
    df['net'] = df['pnl_oz'] - spread_rt
    gp = df[df['net'] > 0]['net'].sum()
    gl = abs(df[df['net'] < 0]['net'].sum()) + 0.001
    pf = gp / gl
    wr = (df['net'] > 0).mean() * 100
    f1 = (df.iloc[:mid]['net'] / df.iloc[:mid]['atr']).mean()
    f2 = (df.iloc[mid:]['net'] / df.iloc[mid:]['atr']).mean()
    ok = "OK" if f1 > 0 and f2 > 0 else "!!" if f1 < 0 and f2 < 0 else "~ "
    flag = " ***" if pf >= 1.3 and f1 > 0 and f2 > 0 else ""
    print("    {:60s}: n={:4d} WR={:4.0f}% PF={:.2f} [{:+.3f}|{:+.3f}] {}{}".format(
        label, n, wr, pf, f1, f2, ok, flag))

conn = get_conn()
candles = load_candles_5m(conn)
daily_atr, global_atr = compute_atr(conn)
trading_days = get_trading_days(conn)

cur = conn.cursor()
cur.execute("""SELECT DATE_TRUNC('month', time), AVG(ask-bid)
    FROM market_ticks_xauusd WHERE ask>bid AND ask-bid<10 GROUP BY 1""")
monthly_spread = {r[0].strftime("%Y-%m"): float(r[1]) for r in cur.fetchall()}
cur.close()
avg_sp = np.mean(list(monthly_spread.values()))
SPREAD_RT = 2 * avg_sp

def prev_day(day):
    for di, d in enumerate(trading_days):
        if d >= day: return trading_days[di-1] if di > 0 else None
    return None

print("=" * 80)
print("DEEP GOLD — Concepts inedits (spread {:.3f} RT)".format(SPREAD_RT))
print("=" * 80)

# ══════════════════════════════════════════════════════
# 1. IB BREAK + GROS BODY (confirmation de momentum)
# Le break IB est plus fiable quand la bougie qui casse a un gros body
# ══════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("1. IB BREAK + GROS BODY (body > X% du range de la bougie)")
print("=" * 80)

for sess_name, sh, eh, sm, em, ib_b in [('TOKYO', 0, 6, 0, 0, 12), ('TOKYO_5h', 5, 6, 0, 0, 3)]:
    for direction in ['UP', 'DOWN']:
        for min_body_pct in [0.0, 0.5, 0.7]:
            for sl, act, trail in [(0.75, 0.5, 0.3), (1.0, 1.0, 0.5)]:
                trades = []
                for day in trading_days:
                    obs_s = pd.Timestamp(day.year, day.month, day.day, sh, sm, tz='UTC')
                    obs_e = pd.Timestamp(day.year, day.month, day.day, eh, em, tz='UTC')
                    mask = (candles['ts_dt'] >= obs_s) & (candles['ts_dt'] < obs_e)
                    period = candles[mask]
                    if len(period) < ib_b + 6: continue
                    pd_ = prev_day(day)
                    atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
                    if atr == 0: continue
                    ib = period.iloc[:ib_b]
                    lvl = ib['high'].max() if direction == 'UP' else ib['low'].min()
                    rest = period.iloc[ib_b:]
                    for i in range(len(rest)):
                        r = rest.iloc[i]
                        d = 'long' if direction == 'UP' else 'short'
                        trig = (d == 'long' and r['close'] > lvl) or (d == 'short' and r['close'] < lvl)
                        if trig:
                            body = abs(r['close'] - r['open'])
                            rng = r['high'] - r['low']
                            body_pct = body / rng if rng > 0 else 0
                            if body_pct < min_body_pct:
                                break  # bougie trop hesitante, skip
                            pos_i = candles.index.get_loc(rest.index[i])
                            entry = r['close']
                            bars, ex = sim_trail(candles, pos_i, entry, d, sl, atr, 24, act, trail)
                            pnl = (ex-entry) if d == 'long' else (entry-ex)
                            trades.append({'date': day, 'pnl_oz': pnl, 'atr': atr})
                            break
                pr(trades, "{} {} body>{:.0f}% SL={} act={} trail={}".format(
                    sess_name, direction, min_body_pct*100, sl, act, trail))

# ══════════════════════════════════════════════════════
# 2. FADING — Tokyo fait un gros move, shorter au debut de London
# ══════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("2. FADING — Tokyo gros move -> trader l'inverse a London")
print("=" * 80)

for thresh in [1.0, 1.5, 2.0, 3.0]:
    for sl, act, trail in [(0.75, 0.5, 0.3), (1.0, 1.0, 0.5)]:
        trades = []
        for day in trading_days:
            tok_s = pd.Timestamp(day.year, day.month, day.day, 0, 0, tz='UTC')
            tok_e = pd.Timestamp(day.year, day.month, day.day, 6, 0, tz='UTC')
            tok = candles[(candles['ts_dt'] >= tok_s) & (candles['ts_dt'] < tok_e)]
            if len(tok) < 10: continue
            pd_ = prev_day(day)
            atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
            if atr == 0: continue
            tok_move = (tok.iloc[-1]['close'] - tok.iloc[0]['open']) / atr

            if abs(tok_move) < thresh: continue

            # London open
            lon_s = pd.Timestamp(day.year, day.month, day.day, 8, 0, tz='UTC')
            lon_e = pd.Timestamp(day.year, day.month, day.day, 14, 30, tz='UTC')
            lon = candles[(candles['ts_dt'] >= lon_s) & (candles['ts_dt'] < lon_e)]
            if len(lon) < 6: continue

            pos_i = candles.index.get_loc(lon.index[0])
            entry = lon.iloc[0]['open']

            # Fading = trader l'inverse de Tokyo
            d = 'short' if tok_move > 0 else 'long'
            bars, ex = sim_trail(candles, pos_i, entry, d, sl, atr, 24, act, trail)
            pnl = (ex-entry) if d == 'long' else (entry-ex)
            trades.append({'date': day, 'pnl_oz': pnl, 'atr': atr})

        pr(trades, "Fade Tokyo>{:.0f}ATR SL={} act={} trail={}".format(thresh, sl, act, trail))

# ══════════════════════════════════════════════════════
# 3. RANGE COMPRESSION — IB range minuscule = explosion a venir
# ══════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("3. RANGE COMPRESSION — petite IB = gros move apres")
print("=" * 80)

for sess_name, sh, eh, ib_b in [('TOKYO', 0, 6, 12), ('LONDON', 8, 14, 12)]:
    sm = 0; em = 30 if eh == 14 else 0

    # Calculer la mediane des IB ranges
    ib_ranges = []
    for day in trading_days:
        obs_s = pd.Timestamp(day.year, day.month, day.day, sh, sm, tz='UTC')
        obs_e = pd.Timestamp(day.year, day.month, day.day, eh, em, tz='UTC')
        mask = (candles['ts_dt'] >= obs_s) & (candles['ts_dt'] < obs_e)
        period = candles[mask]
        if len(period) < ib_b + 6: continue
        pd_ = prev_day(day)
        atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        ib = period.iloc[:ib_b]
        ib_range = (ib['high'].max() - ib['low'].min()) / atr
        ib_ranges.append(ib_range)

    if not ib_ranges: continue
    ib_med = np.median(ib_ranges)
    ib_q25 = np.percentile(ib_ranges, 25)
    print("  {} IB range: Q25={:.2f} Med={:.2f}".format(sess_name, ib_q25, ib_med))

    for max_ib_range in [ib_q25, ib_med * 0.5]:
        for direction in ['UP', 'DOWN']:
            for sl, act, trail in [(0.75, 0.5, 0.3), (1.0, 1.0, 0.5)]:
                trades = []
                for day in trading_days:
                    obs_s = pd.Timestamp(day.year, day.month, day.day, sh, sm, tz='UTC')
                    obs_e = pd.Timestamp(day.year, day.month, day.day, eh, em, tz='UTC')
                    mask = (candles['ts_dt'] >= obs_s) & (candles['ts_dt'] < obs_e)
                    period = candles[mask]
                    if len(period) < ib_b + 6: continue
                    pd_ = prev_day(day)
                    atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
                    if atr == 0: continue
                    ib = period.iloc[:ib_b]
                    ib_range = (ib['high'].max() - ib['low'].min()) / atr
                    if ib_range > max_ib_range: continue

                    ib_high = ib['high'].max()
                    ib_low = ib['low'].min()
                    rest = period.iloc[ib_b:]
                    for i in range(len(rest)):
                        r = rest.iloc[i]
                        d = 'long' if direction == 'UP' else 'short'
                        trig = (d == 'long' and r['close'] > ib_high) or (d == 'short' and r['close'] < ib_low)
                        if trig:
                            pos_i = candles.index.get_loc(rest.index[i])
                            entry = r['close']
                            bars, ex = sim_trail(candles, pos_i, entry, d, sl, atr, 24, act, trail)
                            pnl = (ex-entry) if d == 'long' else (entry-ex)
                            trades.append({'date': day, 'pnl_oz': pnl, 'atr': atr})
                            break
                pr(trades, "{} compress<{:.1f} {} SL={} act={} trail={}".format(
                    sess_name, max_ib_range, direction, sl, act, trail))

# ══════════════════════════════════════════════════════
# 4. PIN BAR / HAMMER — longue meche = rejet
# ══════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("4. PIN BAR — meche > 2x le body = rejet")
print("=" * 80)

for sess_name, sh, eh in [('TOKYO', 0, 6), ('LONDON', 8, 14)]:
    sm = 0; em = 30 if eh == 14 else 0
    for sl, act, trail in [(0.75, 0.5, 0.3), (1.0, 1.0, 0.5)]:
        trades = []
        for day in trading_days:
            obs_s = pd.Timestamp(day.year, day.month, day.day, sh, sm, tz='UTC')
            obs_e = pd.Timestamp(day.year, day.month, day.day, eh, em, tz='UTC')
            mask = (candles['ts_dt'] >= obs_s) & (candles['ts_dt'] < obs_e)
            period = candles[mask]
            if len(period) < 8: continue
            pd_ = prev_day(day)
            atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
            if atr == 0: continue
            traded = False
            for i in range(1, len(period)):
                if traded: break
                r = period.iloc[i]
                body = abs(r['close'] - r['open'])
                if body < 0.01: continue
                upper_wick = r['high'] - max(r['close'], r['open'])
                lower_wick = min(r['close'], r['open']) - r['low']

                # Bullish pin bar: longue meche basse, petit corps en haut
                if lower_wick > 2 * body and upper_wick < body:
                    pos_i = candles.index.get_loc(period.index[i])
                    entry = r['close']
                    bars, ex = sim_trail(candles, pos_i, entry, 'long', sl, atr, 24, act, trail)
                    trades.append({'date': day, 'pnl_oz': ex-entry, 'atr': atr, 'type': 'bull_pin'})
                    traded = True

                # Bearish pin bar: longue meche haute
                elif upper_wick > 2 * body and lower_wick < body:
                    pos_i = candles.index.get_loc(period.index[i])
                    entry = r['close']
                    bars, ex = sim_trail(candles, pos_i, entry, 'short', sl, atr, 24, act, trail)
                    trades.append({'date': day, 'pnl_oz': entry-ex, 'atr': atr, 'type': 'bear_pin'})
                    traded = True

        pr(trades, "{} pin bar SL={} act={} trail={}".format(sess_name, sl, act, trail))

# ══════════════════════════════════════════════════════
# 5. SESSION OPEN comme S/R
# ══════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("5. SESSION OPEN — le prix revient-il vers l'open ?")
print("=" * 80)

for sess_name, sh, eh in [('TOKYO', 0, 6), ('LONDON', 8, 14)]:
    sm = 0; em = 30 if eh == 14 else 0
    for sl, act, trail in [(0.75, 0.5, 0.3), (1.0, 1.0, 0.5)]:
        trades = []
        for day in trading_days:
            obs_s = pd.Timestamp(day.year, day.month, day.day, sh, sm, tz='UTC')
            obs_e = pd.Timestamp(day.year, day.month, day.day, eh, em, tz='UTC')
            mask = (candles['ts_dt'] >= obs_s) & (candles['ts_dt'] < obs_e)
            period = candles[mask]
            if len(period) < 12: continue
            pd_ = prev_day(day)
            atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
            if atr == 0: continue

            sess_open = period.iloc[0]['open']

            # Apres 1h, si le prix est loin de l'open, trader le retour
            for i in range(12, len(period)):
                r = period.iloc[i]
                dist = (r['close'] - sess_open) / atr

                if abs(dist) < 1.5: continue

                pos_i = candles.index.get_loc(period.index[i])
                entry = r['close']

                # Mean reversion vers l'open
                if dist > 1.5:  # prix au-dessus -> short
                    d = 'short'
                else:  # prix en-dessous -> long
                    d = 'long'

                bars, ex = sim_trail(candles, pos_i, entry, d, sl, atr, 24, act, trail)
                pnl = (ex-entry) if d == 'long' else (entry-ex)
                trades.append({'date': day, 'pnl_oz': pnl, 'atr': atr})
                break

        pr(trades, "{} revert to open SL={} act={} trail={}".format(sess_name, sl, act, trail))

# ══════════════════════════════════════════════════════
# 6. TOKYO 3 CONSEC BEARISH (miroir du 3 bull qui marche)
# ══════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("6. TOKYO 3 CONSEC BEARISH (miroir du 3 bull)")
print("=" * 80)

for n_consec in [3, 4]:
    for sl, act, trail in [(0.75, 0.5, 0.3), (1.0, 1.0, 0.5)]:
        trades = []
        for day in trading_days:
            obs_s = pd.Timestamp(day.year, day.month, day.day, 0, 0, tz='UTC')
            obs_e = pd.Timestamp(day.year, day.month, day.day, 6, 0, tz='UTC')
            mask = (candles['ts_dt'] >= obs_s) & (candles['ts_dt'] < obs_e)
            period = candles[mask]
            if len(period) < n_consec + 6: continue
            pd_ = prev_day(day)
            atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
            if atr == 0: continue
            for i in range(n_consec, len(period)):
                prev_n = period.iloc[i-n_consec:i]
                if (prev_n['close'] < prev_n['open']).all():
                    pos_i = candles.index.get_loc(period.index[i-1])
                    entry = period.iloc[i-1]['close']
                    bars, ex = sim_trail(candles, pos_i, entry, 'short', sl, atr, 24, act, trail)
                    trades.append({'date': day, 'pnl_oz': entry-ex, 'atr': atr})
                    break
        pr(trades, "Tokyo {}bear SL={} act={} trail={}".format(n_consec, sl, act, trail))

# ══════════════════════════════════════════════════════
# 7. LONDON ENGULFING (comme Tokyo mais sur London)
# ══════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("7. LONDON ENGULFING")
print("=" * 80)

for sl, act, trail in [(0.75, 0.5, 0.3), (1.0, 1.0, 0.5)]:
    trades = []
    for day in trading_days:
        obs_s = pd.Timestamp(day.year, day.month, day.day, 8, 0, tz='UTC')
        obs_e = pd.Timestamp(day.year, day.month, day.day, 14, 30, tz='UTC')
        mask = (candles['ts_dt'] >= obs_s) & (candles['ts_dt'] < obs_e)
        period = candles[mask]
        if len(period) < 8: continue
        pd_ = prev_day(day)
        atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        for i in range(1, len(period)):
            prev_c = period.iloc[i-1]; curr = period.iloc[i]
            pb = abs(prev_c['close'] - prev_c['open'])
            cb = abs(curr['close'] - curr['open'])
            bull = (prev_c['close'] < prev_c['open'] and curr['close'] > curr['open'] and
                    cb > pb and curr['open'] <= prev_c['close'] and curr['close'] >= prev_c['open'])
            bear = (prev_c['close'] > prev_c['open'] and curr['close'] < curr['open'] and
                    cb > pb and curr['open'] >= prev_c['close'] and curr['close'] <= prev_c['open'])
            if bull or bear:
                pos_i = candles.index.get_loc(period.index[i])
                entry = curr['close']
                d = 'long' if bull else 'short'
                bars, ex = sim_trail(candles, pos_i, entry, d, sl, atr, 24, act, trail)
                pnl = (ex-entry) if d == 'long' else (entry-ex)
                trades.append({'date': day, 'pnl_oz': pnl, 'atr': atr})
                break
    pr(trades, "London engulfing SL={} act={} trail={}".format(sl, act, trail))

conn.close()
print("\n" + "=" * 80)
print("FIN DEEP GOLD")
print("=" * 80)
