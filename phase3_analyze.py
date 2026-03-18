"""
Phase 3 — Analyser : comparer les interactions POC a une baseline random.
Est-ce que le comportement pres des POC est DIFFERENT du comportement aleatoire ?
"""

import warnings
warnings.filterwarnings('ignore')
import sys
sys.stdout.reconfigure(encoding='utf-8')

import os
import numpy as np
import pandas as pd
import psycopg2
from collections import defaultdict
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

from phase1_poc_calculator import (
    get_conn, SESSIONS_CONFIG, compute_vp, load_ticks_for_period,
    compute_atr, get_trading_days, get_trading_weeks
)


def load_candles_5m(conn):
    cur = conn.cursor()
    cur.execute("SELECT ts, open, high, low, close FROM candles_mt5_xauusd_5m ORDER BY ts")
    rows = cur.fetchall()
    cur.close()
    df = pd.DataFrame(rows, columns=['ts', 'open', 'high', 'low', 'close'])
    df['ts_dt'] = pd.to_datetime(df['ts'], unit='ms', utc=True)
    for c in ['open', 'high', 'low', 'close']:
        df[c] = df[c].astype(float)
    df['date'] = df['ts_dt'].dt.date
    df['hour'] = df['ts_dt'].dt.hour + df['ts_dt'].dt.minute / 60.0
    return df


def compute_baseline(candles_df, daily_atr, global_atr, lookahead_bars=12, n_samples=5000):
    """
    Calcule le mouvement 'normal' sur N barres a partir de points aleatoires.
    C'est le benchmark : si les POC ne font pas mieux, ils n'ont pas d'edge.
    """
    np.random.seed(42)
    max_idx = len(candles_df) - lookahead_bars - 1
    if max_idx < 100:
        return {}

    indices = np.random.choice(max_idx, size=min(n_samples, max_idx), replace=False)

    results = []
    for idx in indices:
        row = candles_df.iloc[idx]
        future = candles_df.iloc[idx + 1: idx + 1 + lookahead_bars]
        if len(future) == 0:
            continue

        date = row['date']
        atr = daily_atr.get(date, global_atr)
        if atr == 0:
            continue

        entry = row['close']
        max_up = (future['high'].max() - entry) / atr
        max_down = (entry - future['low'].min()) / atr
        final = (future['close'].iloc[-1] - entry) / atr

        results.append({
            'max_up_atr': max_up,
            'max_down_atr': max_down,
            'final_move_atr': final,
        })

    return pd.DataFrame(results)


def analyze_poc_type(candles_df, conn, daily_atr, global_atr, trading_days,
                     poc_type, lookahead_bars=12):
    """
    Calcule les POC et les interactions pour un type donne,
    et compare avec la baseline.
    """
    proximity_atrs = [0.25, 0.5, 1.0]

    all_interactions = []

    if poc_type == 'session':
        session_order = ['TOKYO', 'LONDON', 'NY']
        for day_idx, day in enumerate(trading_days):
            for sess_idx, sess_name in enumerate(session_order):
                sess_times = SESSIONS_CONFIG[sess_name]
                start_h = sess_times['start']
                end_h = sess_times['end']

                start_dt = datetime(day.year, day.month, day.day,
                                    int(start_h), int((start_h % 1) * 60))
                end_dt = datetime(day.year, day.month, day.day,
                                  int(end_h), int((end_h % 1) * 60))

                prices, volumes = load_ticks_for_period(conn, start_dt, end_dt)
                if len(prices) < 10:
                    continue
                poc, vah, val, _ = compute_vp(prices, volumes)
                if poc is None:
                    continue

                # Session suivante
                if sess_idx < 2:
                    next_sess = session_order[sess_idx + 1]
                    next_day = day
                else:
                    if day_idx + 1 < len(trading_days):
                        next_sess = 'TOKYO'
                        next_day = trading_days[day_idx + 1]
                    else:
                        continue

                nt = SESSIONS_CONFIG[next_sess]
                obs_start = pd.Timestamp(next_day.year, next_day.month, next_day.day,
                                         int(nt['start']), int((nt['start'] % 1) * 60), tz='UTC')
                obs_end = pd.Timestamp(next_day.year, next_day.month, next_day.day,
                                       int(nt['end']), int((nt['end'] % 1) * 60), tz='UTC')

                atr = daily_atr.get(day, global_atr)
                interactions = _find_interactions(candles_df, poc, obs_start, obs_end,
                                                  atr, proximity_atrs, lookahead_bars)
                for inter in interactions:
                    inter['source_session'] = sess_name
                    inter['obs_session'] = next_sess
                    inter['date'] = day

                all_interactions.extend(interactions)

    elif poc_type == 'daily':
        for day_idx in range(1, len(trading_days)):
            prev_day = trading_days[day_idx - 1]
            curr_day = trading_days[day_idx]

            start_dt = datetime(prev_day.year, prev_day.month, prev_day.day, 0, 0)
            end_dt = start_dt + timedelta(days=1)

            prices, volumes = load_ticks_for_period(conn, start_dt, end_dt)
            if len(prices) < 100:
                continue
            poc, vah, val, _ = compute_vp(prices, volumes)
            if poc is None:
                continue

            obs_start = pd.Timestamp(curr_day.year, curr_day.month, curr_day.day, 0, 0, tz='UTC')
            obs_end = obs_start + pd.Timedelta(days=1)

            atr = daily_atr.get(prev_day, global_atr)
            interactions = _find_interactions(candles_df, poc, obs_start, obs_end,
                                              atr, proximity_atrs, lookahead_bars)
            for inter in interactions:
                inter['date'] = curr_day
            all_interactions.extend(interactions)

    elif poc_type == 'weekly':
        trading_weeks = get_trading_weeks(trading_days)
        sorted_weeks = sorted(trading_weeks.items())

        for w_idx in range(1, len(sorted_weeks)):
            prev_key, prev_days = sorted_weeks[w_idx - 1]
            curr_key, curr_days = sorted_weeks[w_idx]

            start_dt = datetime(prev_days[0].year, prev_days[0].month, prev_days[0].day, 0, 0)
            end_dt = datetime(prev_days[-1].year, prev_days[-1].month, prev_days[-1].day, 23, 59, 59)

            prices, volumes = load_ticks_for_period(conn, start_dt, end_dt)
            if len(prices) < 100:
                continue
            poc, vah, val, _ = compute_vp(prices, volumes)
            if poc is None:
                continue

            obs_start = pd.Timestamp(curr_days[0].year, curr_days[0].month,
                                     curr_days[0].day, 0, 0, tz='UTC')
            obs_end = pd.Timestamp(curr_days[-1].year, curr_days[-1].month,
                                   curr_days[-1].day, 23, 59, 59, tz='UTC')

            atr = daily_atr.get(curr_days[0], global_atr)
            interactions = _find_interactions(candles_df, poc, obs_start, obs_end,
                                              atr, proximity_atrs, lookahead_bars)
            for inter in interactions:
                inter['week'] = curr_key
            all_interactions.extend(interactions)

    return all_interactions


def _find_interactions(candles_df, poc_level, start_dt, end_dt, atr,
                       proximity_atrs, lookahead_bars):
    """Detecte les interactions prix-POC dans une periode."""
    mask = (candles_df['ts_dt'] >= start_dt) & (candles_df['ts_dt'] < end_dt)
    period = candles_df[mask]

    if len(period) < 5:
        return []

    interactions = []
    for prox_atr in proximity_atrs:
        zone_size = prox_atr * atr
        zone_high = poc_level + zone_size
        zone_low = poc_level - zone_size

        in_zone = False
        for i in range(len(period)):
            row = period.iloc[i]
            touches = (row['low'] <= zone_high) and (row['high'] >= zone_low)

            if touches and not in_zone:
                in_zone = True

                if i > 0:
                    prev_close = period.iloc[i - 1]['close']
                    direction = 'from_above' if prev_close > poc_level else 'from_below'
                else:
                    direction = 'unknown'

                global_idx = period.index[i]
                pos = candles_df.index.get_loc(global_idx)
                future_start = pos + 1
                future_end = min(pos + 1 + lookahead_bars, len(candles_df))

                if future_start >= len(candles_df):
                    continue
                future = candles_df.iloc[future_start:future_end]
                if len(future) < lookahead_bars:
                    continue

                entry = row['close']
                max_up = (future['high'].max() - entry) / atr
                max_down = (entry - future['low'].min()) / atr
                final = (future['close'].iloc[-1] - entry) / atr

                interactions.append({
                    'proximity_atr': prox_atr,
                    'direction': direction,
                    'entry_price': entry,
                    'poc_level': poc_level,
                    'dist_to_poc_atr': (entry - poc_level) / atr,
                    'max_up_atr': max_up,
                    'max_down_atr': max_down,
                    'final_move_atr': final,
                    'hour': row['hour'],
                })

            elif not touches:
                in_zone = False

    return interactions


def print_comparison(label, interactions_df, baseline_df, proximity):
    """Compare les interactions POC vs baseline pour une proximite donnee."""
    sub = interactions_df[interactions_df['proximity_atr'] == proximity]
    if len(sub) < 30:
        print(f"  [{label}] prox={proximity} ATR: seulement {len(sub)} obs, pas assez")
        return

    b = baseline_df

    print(f"\n  [{label}] Proximite {proximity} ATR — n={len(sub)} (baseline n={len(b)})")
    print(f"  {'':20s} {'POC':>12s} {'Baseline':>12s} {'Delta':>12s}")
    print(f"  {'─' * 56}")

    metrics = [
        ('Max up (ATR)', 'max_up_atr'),
        ('Max down (ATR)', 'max_down_atr'),
        ('Move final (ATR)', 'final_move_atr'),
    ]

    for name, col in metrics:
        poc_val = sub[col].mean()
        base_val = b[col].mean()
        delta = poc_val - base_val
        print(f"  {name:20s} {poc_val:>+12.3f} {base_val:>+12.3f} {delta:>+12.3f}")

    # Par direction
    for d in ['from_above', 'from_below']:
        ds = sub[sub['direction'] == d]
        if len(ds) < 30:
            continue
        print(f"\n    Direction: {d} (n={len(ds)})")
        for name, col in metrics:
            poc_val = ds[col].mean()
            base_val = b[col].mean()
            delta = poc_val - base_val
            sign = "**" if abs(delta) > 0.3 else ""
            print(f"    {name:20s} {poc_val:>+12.3f} {base_val:>+12.3f} {delta:>+12.3f} {sign}")

    # Ratio up/down — asymetrie
    for d in ['from_above', 'from_below']:
        ds = sub[sub['direction'] == d]
        if len(ds) < 30:
            continue
        ratio = ds['max_up_atr'].mean() / ds['max_down_atr'].mean() if ds['max_down_atr'].mean() != 0 else 0
        base_ratio = b['max_up_atr'].mean() / b['max_down_atr'].mean() if b['max_down_atr'].mean() != 0 else 0
        print(f"    Ratio up/down:   POC={ratio:.3f}  Baseline={base_ratio:.3f}")


def main():
    conn = get_conn()

    print("=" * 70)
    print("PHASE 3 — ANALYSE : POC vs BASELINE")
    print("=" * 70)

    # Charger
    candles = load_candles_5m(conn)
    daily_atr, global_atr = compute_atr(conn)
    trading_days = get_trading_days(conn)

    # Baseline
    print("\nCalcul baseline (mouvement aleatoire sur 12 barres)...")
    baseline = compute_baseline(candles, daily_atr, global_atr, lookahead_bars=12, n_samples=10000)
    print(f"  n={len(baseline)}")
    print(f"  Max up moyen:    {baseline['max_up_atr'].mean():.3f} ATR")
    print(f"  Max down moyen:  {baseline['max_down_atr'].mean():.3f} ATR")
    print(f"  Move final moy:  {baseline['final_move_atr'].mean():.3f} ATR")

    # POC Session
    print("\n" + "=" * 70)
    print("A. POC SESSION PRECEDENTE vs BASELINE")
    print("=" * 70)
    print("Calcul en cours...")
    session_inter = analyze_poc_type(candles, conn, daily_atr, global_atr,
                                      trading_days, 'session', lookahead_bars=12)
    df_session = pd.DataFrame(session_inter) if session_inter else pd.DataFrame()
    if len(df_session) > 0:
        for prox in [0.25, 0.5, 1.0]:
            print_comparison("Session", df_session, baseline, prox)

    # POC Daily
    print("\n" + "=" * 70)
    print("B. POC JOUR PRECEDENT vs BASELINE")
    print("=" * 70)
    print("Calcul en cours...")
    daily_inter = analyze_poc_type(candles, conn, daily_atr, global_atr,
                                    trading_days, 'daily', lookahead_bars=12)
    df_daily = pd.DataFrame(daily_inter) if daily_inter else pd.DataFrame()
    if len(df_daily) > 0:
        for prox in [0.25, 0.5, 1.0]:
            print_comparison("Daily", df_daily, baseline, prox)

    # POC Weekly
    print("\n" + "=" * 70)
    print("C. POC SEMAINE PRECEDENTE vs BASELINE")
    print("=" * 70)
    print("Calcul en cours...")
    weekly_inter = analyze_poc_type(candles, conn, daily_atr, global_atr,
                                     trading_days, 'weekly', lookahead_bars=12)
    df_weekly = pd.DataFrame(weekly_inter) if weekly_inter else pd.DataFrame()
    if len(df_weekly) > 0:
        for prox in [0.25, 0.5, 1.0]:
            print_comparison("Weekly", df_weekly, baseline, prox)

    # ── SYNTHESE ──────────────────────────────────────────────

    print("\n" + "=" * 70)
    print("SYNTHESE — QU'EST-CE QUE JE VOIS ?")
    print("=" * 70)

    # Pour chaque type de POC, regarder si le comportement est different de la baseline
    for label, df in [("Session", df_session), ("Daily", df_daily), ("Weekly", df_weekly)]:
        if len(df) == 0:
            continue
        print(f"\n--- {label} POC ---")
        for prox in [0.25, 0.5, 1.0]:
            sub = df[df['proximity_atr'] == prox]
            if len(sub) < 30:
                continue

            # Test : est-ce que le move final a un biais directionnel ?
            above = sub[sub['direction'] == 'from_above']['final_move_atr']
            below = sub[sub['direction'] == 'from_below']['final_move_atr']

            if len(above) >= 30 and len(below) >= 30:
                # Si from_above -> final positif = rebond (support)
                # Si from_below -> final negatif = rejet (resistance)
                support_effect = above.mean()
                resistance_effect = -below.mean()  # negatif = prix descend = resistance
                combined = (support_effect + resistance_effect) / 2

                print(f"  Prox {prox} ATR: support={support_effect:+.3f}, "
                      f"resistance={resistance_effect:+.3f}, "
                      f"combined={combined:+.3f} "
                      f"(above n={len(above)}, below n={len(below)})")

    conn.close()


if __name__ == '__main__':
    main()
