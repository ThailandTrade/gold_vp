"""
Exploration v3 — concepts pas encore testes.
1. Two-bar reversal (2 grosses bougies opposees)
2. London kill zone (8h-10h UTC = manipulation puis direction)
3. Gap 6h-8h comme predictor (ou est le prix par rapport a Tokyo close ?)
4. Breakout du range des 3 premieres bougies de chaque heure
5. Volatilite comme filtre (ATR jour precedent high/low)
6. Jour de la semaine comme filtre sur les strats existantes
7. Combo: IB break + engulfing dans la meme session = double confirmation
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

def sim_trail(cdf, pos, entry, d, sl, atr, mx, act, trail):
    best = entry
    stop = entry + sl*atr if d == 'short' else entry - sl*atr
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
    gp = df[df['net']>0]['net'].sum()
    gl = abs(df[df['net']<0]['net'].sum())+0.001
    pf = gp/gl; wr = (df['net']>0).mean()*100
    f1 = (df.iloc[:mid]['net']/df.iloc[:mid]['atr']).mean()
    f2 = (df.iloc[mid:]['net']/df.iloc[mid:]['atr']).mean()
    ok = "OK" if f1>0 and f2>0 else "!!" if f1<0 and f2<0 else "~ "
    flag = " ***" if pf >= 1.3 and f1>0 and f2>0 else ""
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
print("EXPLORATION v3 — Nouveaux concepts (spread {:.3f} RT)".format(SPREAD_RT))
print("=" * 80)

# ══════════════════════════════════════════════════════
# 1. TWO-BAR REVERSAL — 2 grosses bougies opposees
# La deuxieme bougie englobe ou depasse la premiere dans l'autre sens
# ══════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("1. TWO-BAR REVERSAL")
print("=" * 80)

for sess_name, sh, eh in [('TOKYO', 0, 6), ('LONDON', 8, 14)]:
    sm = 0; em = 30 if eh == 14 else 0
    for min_size_atr in [0.3, 0.5]:
        for sl, act, trail in [(0.75, 0.5, 0.3)]:
            trades = []
            for day in trading_days:
                obs_s = pd.Timestamp(day.year, day.month, day.day, sh, sm, tz='UTC')
                obs_e = pd.Timestamp(day.year, day.month, day.day, eh, em, tz='UTC')
                period = candles[(candles['ts_dt'] >= obs_s) & (candles['ts_dt'] < obs_e)]
                if len(period) < 8: continue
                pd_ = prev_day(day)
                atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
                if atr == 0: continue
                for i in range(1, len(period)):
                    b1 = period.iloc[i-1]; b2 = period.iloc[i]
                    b1_body = b1['close'] - b1['open']
                    b2_body = b2['close'] - b2['open']
                    # Deux grosses bougies dans des directions opposees
                    if abs(b1_body) < min_size_atr * atr: continue
                    if abs(b2_body) < min_size_atr * atr: continue
                    if b1_body * b2_body >= 0: continue  # meme direction
                    # La 2eme depasse la 1ere
                    if abs(b2_body) <= abs(b1_body): continue

                    pos_i = candles.index.get_loc(period.index[i])
                    entry = b2['close']
                    d = 'long' if b2_body > 0 else 'short'
                    bars, ex = sim_trail(candles, pos_i, entry, d, sl, atr, 24, act, trail)
                    pnl = (ex-entry) if d == 'long' else (entry-ex)
                    trades.append({'date': day, 'pnl_oz': pnl, 'atr': atr})
                    break
            pr(trades, "{} 2bar reversal >{:.1f}ATR SL={}".format(sess_name, min_size_atr, sl))

# ══════════════════════════════════════════════════════
# 2. LONDON KILL ZONE (8h-10h) — premiere direction souvent fausse
# Attendre 10h puis trader dans le sens oppose a 8h-10h
# ══════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("2. LONDON KILL ZONE — fading the 8h-10h move")
print("=" * 80)

for thresh in [0.5, 1.0, 1.5]:
    for sl, act, trail in [(0.75, 0.5, 0.3), (1.0, 1.0, 0.5)]:
        trades = []
        for day in trading_days:
            pd_ = prev_day(day)
            atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
            if atr == 0: continue
            kz_s = pd.Timestamp(day.year, day.month, day.day, 8, 0, tz='UTC')
            kz_e = pd.Timestamp(day.year, day.month, day.day, 10, 0, tz='UTC')
            kz = candles[(candles['ts_dt'] >= kz_s) & (candles['ts_dt'] < kz_e)]
            if len(kz) < 20: continue
            kz_move = (kz.iloc[-1]['close'] - kz.iloc[0]['open']) / atr
            if abs(kz_move) < thresh: continue
            # Entrer a 10h dans le sens oppose
            post_kz = candles[candles['ts_dt'] >= kz_e]
            if len(post_kz) < 6: continue
            pos_i = candles.index.get_loc(post_kz.index[0])
            entry = post_kz.iloc[0]['open']
            d = 'short' if kz_move > 0 else 'long'
            bars, ex = sim_trail(candles, pos_i, entry, d, sl, atr, 24, act, trail)
            pnl = (ex-entry) if d == 'long' else (entry-ex)
            trades.append({'date': day, 'pnl_oz': pnl, 'atr': atr})
        pr(trades, "London KZ fade >{:.1f}ATR SL={} act={} trail={}".format(thresh, sl, act, trail))

# ══════════════════════════════════════════════════════
# 3. GAP 6h-8h — prix a 8h vs close Tokyo 6h
# Si le prix a bouge pendant le gap, trader la continuation ou reversion
# ══════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("3. GAP TOKYO-LONDON (6h-8h)")
print("=" * 80)

for thresh in [0.3, 0.5, 1.0]:
    for mode in ['continuation', 'reversion']:
        for sl, act, trail in [(0.75, 0.5, 0.3)]:
            trades = []
            for day in trading_days:
                pd_ = prev_day(day)
                atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
                if atr == 0: continue
                # Close de Tokyo
                tok_e = pd.Timestamp(day.year, day.month, day.day, 6, 0, tz='UTC')
                tok_candles = candles[candles['ts_dt'] < tok_e]
                if len(tok_candles) < 5: continue
                tok_close = tok_candles.iloc[-1]['close']
                # Open de London
                lon_s = pd.Timestamp(day.year, day.month, day.day, 8, 0, tz='UTC')
                lon_candles = candles[candles['ts_dt'] >= lon_s]
                if len(lon_candles) < 6: continue
                lon_open = lon_candles.iloc[0]['open']
                gap = (lon_open - tok_close) / atr
                if abs(gap) < thresh: continue
                pos_i = candles.index.get_loc(lon_candles.index[0])
                entry = lon_open
                if mode == 'continuation':
                    d = 'long' if gap > 0 else 'short'
                else:
                    d = 'short' if gap > 0 else 'long'
                bars, ex = sim_trail(candles, pos_i, entry, d, sl, atr, 24, act, trail)
                pnl = (ex-entry) if d == 'long' else (entry-ex)
                trades.append({'date': day, 'pnl_oz': pnl, 'atr': atr})
            pr(trades, "Gap>{:.1f}ATR {} SL={}".format(thresh, mode, sl))

# ══════════════════════════════════════════════════════
# 4. HOURLY OPENING RANGE BREAKOUT
# Range des 3 premieres bougies de chaque heure, break de ce range
# ══════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("4. HOURLY ORB — break du range des 15 premieres min de chaque heure")
print("=" * 80)

for test_hour in [0, 1, 2, 3, 4, 5, 8, 9, 10, 14, 15]:
    for direction in ['UP']:
        for sl, act, trail in [(0.75, 0.5, 0.3)]:
            trades = []
            for day in trading_days:
                pd_ = prev_day(day)
                atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
                if atr == 0: continue
                h_s = pd.Timestamp(day.year, day.month, day.day, test_hour, 0, tz='UTC')
                h_e = h_s + pd.Timedelta(hours=1)
                h_candles = candles[(candles['ts_dt'] >= h_s) & (candles['ts_dt'] < h_e)]
                if len(h_candles) < 9: continue
                orb = h_candles.iloc[:3]
                orb_high = orb['high'].max()
                orb_low = orb['low'].min()
                rest = h_candles.iloc[3:]
                for i in range(len(rest)):
                    r = rest.iloc[i]
                    if direction == 'UP' and r['close'] > orb_high:
                        pos_i = candles.index.get_loc(rest.index[i])
                        entry = r['close']
                        bars, ex = sim_trail(candles, pos_i, entry, 'long', sl, atr, 12, act, trail)
                        trades.append({'date': day, 'pnl_oz': ex-entry, 'atr': atr})
                        break
            pr(trades, "ORB {}h UP SL={}".format(test_hour, sl))

# ══════════════════════════════════════════════════════
# 5. VOLATILITE COMME FILTRE — ATR high vs low
# ══════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("5. FILTRE VOLATILITE SUR D2 (le meilleur signal)")
print("=" * 80)

# Calculer la mediane de l'ATR
atr_vals = [daily_atr.get(d, 0) for d in trading_days if daily_atr.get(d, 0) > 0]
atr_med = np.median(atr_vals)
print("  ATR median: {:.2f}".format(atr_med))

for vol_filter in ['all', 'low', 'high']:
    trades = []
    for day in trading_days:
        obs_s = pd.Timestamp(day.year, day.month, day.day, 5, 0, tz='UTC')
        obs_e = pd.Timestamp(day.year, day.month, day.day, 6, 0, tz='UTC')
        period = candles[(candles['ts_dt'] >= obs_s) & (candles['ts_dt'] < obs_e)]
        if len(period) < 6: continue
        pd_ = prev_day(day)
        atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue

        if vol_filter == 'low' and atr > atr_med: continue
        if vol_filter == 'high' and atr <= atr_med: continue

        ib_high = period.iloc[:3]['high'].max()
        for i in range(3, len(period)):
            r = period.iloc[i]
            if r['close'] > ib_high:
                body = abs(r['close'] - r['open'])
                rng = r['high'] - r['low']
                if rng > 0 and body / rng >= 0.5:
                    pos_i = candles.index.get_loc(period.index[i])
                    entry = r['close']
                    bars, ex = sim_trail(candles, pos_i, entry, 'long', 0.75, atr, 24, 0.5, 0.3)
                    trades.append({'date': day, 'pnl_oz': ex-entry, 'atr': atr})
                break
    pr(trades, "D2 vol={} SL=0.75".format(vol_filter))

# ══════════════════════════════════════════════════════
# 6. JOUR DE LA SEMAINE comme filtre
# ══════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("6. D2 PAR JOUR DE LA SEMAINE")
print("=" * 80)

day_names = {0: 'Lun', 1: 'Mar', 2: 'Mer', 3: 'Jeu', 4: 'Ven'}
for dow in range(5):
    trades = []
    for day in trading_days:
        if day.weekday() != dow: continue
        obs_s = pd.Timestamp(day.year, day.month, day.day, 5, 0, tz='UTC')
        obs_e = pd.Timestamp(day.year, day.month, day.day, 6, 0, tz='UTC')
        period = candles[(candles['ts_dt'] >= obs_s) & (candles['ts_dt'] < obs_e)]
        if len(period) < 6: continue
        pd_ = prev_day(day)
        atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        ib_high = period.iloc[:3]['high'].max()
        for i in range(3, len(period)):
            r = period.iloc[i]
            if r['close'] > ib_high:
                body = abs(r['close'] - r['open'])
                rng = r['high'] - r['low']
                if rng > 0 and body / rng >= 0.5:
                    pos_i = candles.index.get_loc(period.index[i])
                    entry = r['close']
                    bars, ex = sim_trail(candles, pos_i, entry, 'long', 0.75, atr, 24, 0.5, 0.3)
                    trades.append({'date': day, 'pnl_oz': ex-entry, 'atr': atr})
                break
    pr(trades, "D2 {} SL=0.75".format(day_names[dow]))

# ══════════════════════════════════════════════════════
# 7. COMBO: IB break B + engulfing H le meme jour
# ══════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("7. COMBO — B+H le meme jour = double confirmation")
print("=" * 80)

# Jours ou B et H ont trigger ensemble (dans le backtest)
b_dates = set()
h_dates = set()

for day in trading_days:
    obs_s = pd.Timestamp(day.year, day.month, day.day, 0, 0, tz='UTC')
    obs_e = pd.Timestamp(day.year, day.month, day.day, 6, 0, tz='UTC')
    period = candles[(candles['ts_dt'] >= obs_s) & (candles['ts_dt'] < obs_e)]
    if len(period) < 18: continue
    pd_ = prev_day(day)
    atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue

    # B trigger ?
    ib_high = period.iloc[:12]['high'].max()
    b_triggered = False
    for i in range(12, len(period)):
        if period.iloc[i]['close'] > ib_high:
            b_triggered = True; break

    # H trigger ?
    h_triggered = False
    for i in range(1, len(period)):
        pc = period.iloc[i-1]; cc = period.iloc[i]
        pb = abs(pc['close']-pc['open']); cb = abs(cc['close']-cc['open'])
        bull = (pc['close']<pc['open'] and cc['close']>cc['open'] and cb>pb and
                cc['open']<=pc['close'] and cc['close']>=pc['open'])
        if bull:
            h_triggered = True; break

    if b_triggered: b_dates.add(day)
    if h_triggered: h_dates.add(day)

both = b_dates & h_dates
b_only = b_dates - h_dates
print("  B seul: {} jours, H seul: {} jours, les deux: {} jours".format(
    len(b_only), len(h_dates - b_dates), len(both)))

# Comparer la performance de B quand H a aussi trigger vs pas
for label, date_set in [("B quand H aussi", both), ("B sans H", b_only)]:
    trades = []
    for day in date_set:
        obs_s = pd.Timestamp(day.year, day.month, day.day, 0, 0, tz='UTC')
        obs_e = pd.Timestamp(day.year, day.month, day.day, 6, 0, tz='UTC')
        period = candles[(candles['ts_dt'] >= obs_s) & (candles['ts_dt'] < obs_e)]
        if len(period) < 18: continue
        pd_ = prev_day(day)
        atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        ib_high = period.iloc[:12]['high'].max()
        for i in range(12, len(period)):
            if period.iloc[i]['close'] > ib_high:
                pos_i = candles.index.get_loc(period.index[i])
                entry = period.iloc[i]['close']
                bars, ex = sim_trail(candles, pos_i, entry, 'long', 0.75, atr, 24, 0.5, 0.3)
                trades.append({'date': day, 'pnl_oz': ex-entry, 'atr': atr})
                break
    pr(trades, label)

conn.close()
print("\n" + "=" * 80)
print("FIN v3")
print("=" * 80)
