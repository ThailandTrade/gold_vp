"""
Exploration Saint Graal — concepts jamais testes.
Seuil: PF >= 1.3, split OK, trailing inclus.
Spread reel + slippage inclus dans chaque resultat.
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
    # Deduire le spread
    df['net'] = df['pnl_oz'] - spread_rt
    gp = df[df['net'] > 0]['net'].sum()
    gl = abs(df[df['net'] < 0]['net'].sum()) + 0.001
    pf = gp / gl
    wr = (df['net'] > 0).mean() * 100
    avg = df['net'].mean() / df['atr'].mean()  # en ATR
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

# Spread par mois
cur = conn.cursor()
cur.execute("""SELECT DATE_TRUNC('month', time), AVG(ask-bid)
    FROM market_ticks_xauusd WHERE ask>bid AND ask-bid<10 GROUP BY 1""")
monthly_spread = {r[0].strftime("%Y-%m"): float(r[1]) for r in cur.fetchall()}
cur.close()
avg_spread = np.mean(list(monthly_spread.values()))
SPREAD_RT = 2 * avg_spread

def prev_day(day):
    for di, d in enumerate(trading_days):
        if d >= day: return trading_days[di-1] if di > 0 else None
    return None

print("=" * 80)
print("EXPLORATION SAINT GRAAL — Spread {:.3f} RT inclus".format(SPREAD_RT))
print("=" * 80)

# ══════════════════════════════════════════════════════
# 1. ASIAN RANGE BREAKOUT POUR LONDON
# Le range COMPLET de Tokyo (0h-6h) comme reference pour London (8h-14h30)
# ══════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("1. ASIAN RANGE BREAKOUT -> LONDON")
print("=" * 80)

for direction in ['UP', 'DOWN']:
    for sl, act, trail in [(0.75, 0.5, 0.3), (1.0, 0.75, 0.5), (1.0, 1.0, 0.5)]:
        trades = []
        for day in trading_days:
            # Range Tokyo complet
            tok_s = pd.Timestamp(day.year, day.month, day.day, 0, 0, tz='UTC')
            tok_e = pd.Timestamp(day.year, day.month, day.day, 6, 0, tz='UTC')
            tok_mask = (candles['ts_dt'] >= tok_s) & (candles['ts_dt'] < tok_e)
            tok = candles[tok_mask]
            if len(tok) < 20: continue

            atr_d = daily_atr.get(prev_day(day), global_atr) if prev_day(day) else global_atr
            if atr_d == 0: continue

            asian_high = tok['high'].max()
            asian_low = tok['low'].min()

            # London session
            lon_s = pd.Timestamp(day.year, day.month, day.day, 8, 0, tz='UTC')
            lon_e = pd.Timestamp(day.year, day.month, day.day, 14, 30, tz='UTC')
            lon_mask = (candles['ts_dt'] >= lon_s) & (candles['ts_dt'] < lon_e)
            lon = candles[lon_mask]
            if len(lon) < 6: continue

            for i in range(len(lon)):
                r = lon.iloc[i]
                pos_i = candles.index.get_loc(lon.index[i])

                if direction == 'UP' and r['close'] > asian_high:
                    entry = r['close']
                    bars, ex = sim_trail(candles, pos_i, entry, 'long', sl, atr_d, 24, act, trail)
                    trades.append({'date': day, 'pnl_oz': ex - entry, 'atr': atr_d})
                    break
                elif direction == 'DOWN' and r['close'] < asian_low:
                    entry = r['close']
                    bars, ex = sim_trail(candles, pos_i, entry, 'short', sl, atr_d, 24, act, trail)
                    trades.append({'date': day, 'pnl_oz': entry - ex, 'atr': atr_d})
                    break

        pr(trades, "Asian->{} {} SL={} act={} trail={}".format('London', direction, sl, act, trail))

# ══════════════════════════════════════════════════════
# 2. PREVIOUS SESSION HIGH/LOW comme niveaux
# ══════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("2. PREVIOUS SESSION HIGH/LOW BREAK")
print("=" * 80)

for src_sess, tgt_sess in [('TOKYO', 'LONDON'), ('LONDON', 'NY'), ('NY', 'TOKYO')]:
    src = SESSIONS_CONFIG[src_sess]
    tgt = SESSIONS_CONFIG[tgt_sess]

    for direction in ['UP', 'DOWN']:
        for sl, act, trail in [(0.75, 0.5, 0.3), (1.0, 1.0, 0.5)]:
            trades = []
            for day_idx, day in enumerate(trading_days):
                # Session source
                if tgt_sess == 'TOKYO' and src_sess == 'NY':
                    src_day = day  # NY du meme jour, Tokyo du lendemain
                    tgt_day = trading_days[day_idx + 1] if day_idx + 1 < len(trading_days) else None
                    if tgt_day is None: continue
                else:
                    src_day = day
                    tgt_day = day

                src_s = pd.Timestamp(src_day.year, src_day.month, src_day.day,
                                     int(src['start']), int((src['start']%1)*60), tz='UTC')
                src_e = pd.Timestamp(src_day.year, src_day.month, src_day.day,
                                     int(src['end']), int((src['end']%1)*60), tz='UTC')
                src_mask = (candles['ts_dt'] >= src_s) & (candles['ts_dt'] < src_e)
                src_candles = candles[src_mask]
                if len(src_candles) < 10: continue

                prev_d_atr = prev_day(tgt_day) if prev_day(tgt_day) else day
                atr_d = daily_atr.get(prev_d_atr, global_atr)
                if atr_d == 0: continue

                sess_high = src_candles['high'].max()
                sess_low = src_candles['low'].min()

                # Session cible
                tgt_s = pd.Timestamp(tgt_day.year, tgt_day.month, tgt_day.day,
                                     int(tgt['start']), int((tgt['start']%1)*60), tz='UTC')
                tgt_e = pd.Timestamp(tgt_day.year, tgt_day.month, tgt_day.day,
                                     int(tgt['end']), int((tgt['end']%1)*60), tz='UTC')
                tgt_mask = (candles['ts_dt'] >= tgt_s) & (candles['ts_dt'] < tgt_e)
                tgt_candles = candles[tgt_mask]
                if len(tgt_candles) < 6: continue

                for i in range(len(tgt_candles)):
                    r = tgt_candles.iloc[i]
                    pos_i = candles.index.get_loc(tgt_candles.index[i])

                    if direction == 'UP' and r['close'] > sess_high:
                        entry = r['close']
                        bars, ex = sim_trail(candles, pos_i, entry, 'long', sl, atr_d, 24, act, trail)
                        trades.append({'date': tgt_day, 'pnl_oz': ex - entry, 'atr': atr_d})
                        break
                    elif direction == 'DOWN' and r['close'] < sess_low:
                        entry = r['close']
                        bars, ex = sim_trail(candles, pos_i, entry, 'short', sl, atr_d, 24, act, trail)
                        trades.append({'date': tgt_day, 'pnl_oz': entry - ex, 'atr': atr_d})
                        break

            pr(trades, "{}H/L->{} {} SL={} act={} trail={}".format(
                src_sess[:3], tgt_sess[:3], direction, sl, act, trail))

# ══════════════════════════════════════════════════════
# 3. DOUBLE BREAK — le prix casse l'IB, revient, recasse
# ══════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("3. DOUBLE BREAK (casse, revient, recasse = confirmation)")
print("=" * 80)

for sess_name, sh, eh, ib_b in [('TOKYO', 0, 6, 12), ('NY', 14, 21, 12)]:
    sm = 30 if sh == 14 else 0
    em = 30 if eh == 21 else 0

    for direction in ['UP', 'DOWN']:
        for sl, act, trail in [(0.75, 0.5, 0.3), (1.0, 1.0, 0.5)]:
            trades = []
            for day in trading_days:
                obs_s = pd.Timestamp(day.year, day.month, day.day, sh, sm, tz='UTC')
                obs_e = pd.Timestamp(day.year, day.month, day.day, eh, em, tz='UTC')
                mask = (candles['ts_dt'] >= obs_s) & (candles['ts_dt'] < obs_e)
                period = candles[mask]
                if len(period) < ib_b + 12: continue

                atr_d = daily_atr.get(prev_day(day), global_atr) if prev_day(day) else global_atr
                if atr_d == 0: continue

                ib = period.iloc[:ib_b]
                ib_high = ib['high'].max()
                ib_low = ib['low'].min()
                rest = period.iloc[ib_b:]

                # Chercher: 1er break, puis retour, puis 2eme break
                first_break = False
                returned = False

                for i in range(len(rest)):
                    r = rest.iloc[i]

                    if direction == 'UP':
                        if not first_break and r['close'] > ib_high:
                            first_break = True
                            continue
                        if first_break and not returned and r['close'] <= ib_high:
                            returned = True
                            continue
                        if first_break and returned and r['close'] > ib_high:
                            # Double break confirme !
                            pos_i = candles.index.get_loc(rest.index[i])
                            entry = r['close']
                            bars, ex = sim_trail(candles, pos_i, entry, 'long',
                                                sl, atr_d, 24, act, trail)
                            trades.append({'date': day, 'pnl_oz': ex - entry, 'atr': atr_d})
                            break
                    else:
                        if not first_break and r['close'] < ib_low:
                            first_break = True
                            continue
                        if first_break and not returned and r['close'] >= ib_low:
                            returned = True
                            continue
                        if first_break and returned and r['close'] < ib_low:
                            pos_i = candles.index.get_loc(rest.index[i])
                            entry = r['close']
                            bars, ex = sim_trail(candles, pos_i, entry, 'short',
                                                sl, atr_d, 24, act, trail)
                            trades.append({'date': day, 'pnl_oz': entry - ex, 'atr': atr_d})
                            break

            pr(trades, "{} double break {} SL={} act={} trail={}".format(
                sess_name, direction, sl, act, trail))

# ══════════════════════════════════════════════════════
# 4. MOMENTUM BURST — toutes les N premieres bougies bullish/bearish
# ══════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("4. MOMENTUM BURST — N bougies consecutives dans le meme sens")
print("=" * 80)

for sess_name, sh, eh in [('TOKYO', 0, 6), ('LONDON', 8, 14), ('NY', 14, 21)]:
    sm = 30 if sh == 14 else 0
    em = 30 if eh == 21 else 0

    for n_consec in [3, 4, 5]:
        for sl, act, trail in [(0.75, 0.5, 0.3), (1.0, 1.0, 0.5)]:
            trades_up = []; trades_dn = []
            for day in trading_days:
                obs_s = pd.Timestamp(day.year, day.month, day.day, sh, sm, tz='UTC')
                obs_e = pd.Timestamp(day.year, day.month, day.day, eh, em, tz='UTC')
                mask = (candles['ts_dt'] >= obs_s) & (candles['ts_dt'] < obs_e)
                period = candles[mask]
                if len(period) < n_consec + 6: continue

                atr_d = daily_atr.get(prev_day(day), global_atr) if prev_day(day) else global_atr
                if atr_d == 0: continue

                traded = False
                for i in range(n_consec, len(period)):
                    if traded: break
                    prev_n = period.iloc[i-n_consec:i]
                    all_bull = (prev_n['close'] > prev_n['open']).all()
                    all_bear = (prev_n['close'] < prev_n['open']).all()

                    if all_bull or all_bear:
                        pos_i = candles.index.get_loc(period.index[i-1])
                        entry = period.iloc[i-1]['close']
                        d = 'long' if all_bull else 'short'
                        bars, ex = sim_trail(candles, pos_i, entry, d,
                                            sl, atr_d, 24, act, trail)
                        pnl = (ex - entry) if d == 'long' else (entry - ex)
                        target = trades_up if d == 'long' else trades_dn
                        target.append({'date': day, 'pnl_oz': pnl, 'atr': atr_d})
                        traded = True

            pr(trades_up, "{} {}consec BULL SL={} act={} trail={}".format(
                sess_name, n_consec, sl, act, trail))
            pr(trades_dn, "{} {}consec BEAR SL={} act={} trail={}".format(
                sess_name, n_consec, sl, act, trail))

# ══════════════════════════════════════════════════════
# 5. INSIDE BAR BREAKOUT — bougie inside puis break
# ══════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("5. INSIDE BAR BREAKOUT")
print("=" * 80)

for sess_name, sh, eh in [('TOKYO', 0, 6), ('LONDON', 8, 14), ('NY', 14, 21)]:
    sm = 30 if sh == 14 else 0
    em = 30 if eh == 21 else 0

    for sl, act, trail in [(0.75, 0.5, 0.3), (1.0, 1.0, 0.5)]:
        trades = []
        for day in trading_days:
            obs_s = pd.Timestamp(day.year, day.month, day.day, sh, sm, tz='UTC')
            obs_e = pd.Timestamp(day.year, day.month, day.day, eh, em, tz='UTC')
            mask = (candles['ts_dt'] >= obs_s) & (candles['ts_dt'] < obs_e)
            period = candles[mask]
            if len(period) < 10: continue

            atr_d = daily_atr.get(prev_day(day), global_atr) if prev_day(day) else global_atr
            if atr_d == 0: continue

            traded = False
            for i in range(2, len(period)):
                if traded: break
                mother = period.iloc[i-2]
                inside = period.iloc[i-1]
                breakout = period.iloc[i]

                # Inside bar: high < mother high AND low > mother low
                is_inside = (inside['high'] < mother['high']) and (inside['low'] > mother['low'])
                if not is_inside: continue

                pos_i = candles.index.get_loc(period.index[i])

                if breakout['close'] > mother['high']:
                    entry = breakout['close']
                    bars, ex = sim_trail(candles, pos_i, entry, 'long',
                                        sl, atr_d, 24, act, trail)
                    trades.append({'date': day, 'pnl_oz': ex - entry, 'atr': atr_d, 'dir': 'long'})
                    traded = True
                elif breakout['close'] < mother['low']:
                    entry = breakout['close']
                    bars, ex = sim_trail(candles, pos_i, entry, 'short',
                                        sl, atr_d, 24, act, trail)
                    trades.append({'date': day, 'pnl_oz': entry - ex, 'atr': atr_d, 'dir': 'short'})
                    traded = True

        pr(trades, "{} inside bar break SL={} act={} trail={}".format(
            sess_name, sl, act, trail))

# ══════════════════════════════════════════════════════
# 6. ENGULFING CANDLE comme signal
# ══════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("6. ENGULFING CANDLE — grosse bougie qui englobe la precedente")
print("=" * 80)

for sess_name, sh, eh in [('TOKYO', 0, 6), ('LONDON', 8, 14), ('NY', 14, 21)]:
    sm = 30 if sh == 14 else 0
    em = 30 if eh == 21 else 0

    for sl, act, trail in [(0.75, 0.5, 0.3), (1.0, 1.0, 0.5)]:
        trades = []
        for day in trading_days:
            obs_s = pd.Timestamp(day.year, day.month, day.day, sh, sm, tz='UTC')
            obs_e = pd.Timestamp(day.year, day.month, day.day, eh, em, tz='UTC')
            mask = (candles['ts_dt'] >= obs_s) & (candles['ts_dt'] < obs_e)
            period = candles[mask]
            if len(period) < 10: continue

            atr_d = daily_atr.get(prev_day(day), global_atr) if prev_day(day) else global_atr
            if atr_d == 0: continue

            traded = False
            for i in range(1, len(period)):
                if traded: break
                prev_c = period.iloc[i-1]
                curr = period.iloc[i]

                prev_body = abs(prev_c['close'] - prev_c['open'])
                curr_body = abs(curr['close'] - curr['open'])

                # Bull engulfing: prev bearish, curr bullish, curr body > prev body
                bull_engulf = (prev_c['close'] < prev_c['open'] and
                              curr['close'] > curr['open'] and
                              curr_body > prev_body and
                              curr['open'] <= prev_c['close'] and
                              curr['close'] >= prev_c['open'])

                bear_engulf = (prev_c['close'] > prev_c['open'] and
                              curr['close'] < curr['open'] and
                              curr_body > prev_body and
                              curr['open'] >= prev_c['close'] and
                              curr['close'] <= prev_c['open'])

                if bull_engulf or bear_engulf:
                    pos_i = candles.index.get_loc(period.index[i])
                    entry = curr['close']
                    d = 'long' if bull_engulf else 'short'
                    bars, ex = sim_trail(candles, pos_i, entry, d,
                                        sl, atr_d, 24, act, trail)
                    pnl = (ex - entry) if d == 'long' else (entry - ex)
                    trades.append({'date': day, 'pnl_oz': pnl, 'atr': atr_d})
                    traded = True

        pr(trades, "{} engulfing SL={} act={} trail={}".format(
            sess_name, sl, act, trail))

conn.close()
print("\n" + "=" * 80)
print("FIN EXPLORATION GRAAL")
print("=" * 80)
