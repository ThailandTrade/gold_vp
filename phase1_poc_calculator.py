"""
Phase 1 — Calcul exhaustif des POC sur toutes les périodes.
Explorateur POC · XAUUSD 5m
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

# ── Connexion DB ──────────────────────────────────────────────

def get_conn():
    return psycopg2.connect(
        host=os.getenv('PG_HOST'), port=os.getenv('PG_PORT'),
        dbname=os.getenv('PG_DB'), user=os.getenv('PG_USER'),
        password=os.getenv('PG_PASSWORD')
    )

# ── Sessions UTC ──────────────────────────────────────────────

SESSIONS_CONFIG = {
    'TOKYO':  {'start': 0,    'end': 6},
    'LONDON': {'start': 8,    'end': 14.5},
    'NY':     {'start': 14.5, 'end': 21.5},
}

# ── Volume Profile depuis les ticks ──────────────────────────

def compute_vp(prices, volumes, tick_size=0.10):
    """
    Distribue le volume dans des bins de prix.
    Retourne (poc_price, vah, val, profile_dict).

    tick_size : taille du bin en dollars (résolution du profil).
    """
    if len(prices) == 0:
        return None, None, None, {}

    # Discrétiser les prix en bins
    binned = np.round(prices / tick_size) * tick_size

    # Accumuler le volume par bin
    profile = defaultdict(float)
    for p, v in zip(binned, volumes):
        profile[p] += v

    if not profile:
        return None, None, None, {}

    # POC = bin avec le plus de volume
    poc = max(profile, key=profile.get)

    # Value Area (70% du volume total)
    total_vol = sum(profile.values())
    target = total_vol * 0.70

    # Trier les bins par volume décroissant, accumuler jusqu'à 70%
    sorted_bins = sorted(profile.items(), key=lambda x: x[1], reverse=True)
    accumulated = 0.0
    va_prices = []
    for price, vol in sorted_bins:
        accumulated += vol
        va_prices.append(price)
        if accumulated >= target:
            break

    vah = max(va_prices) if va_prices else None
    val = min(va_prices) if va_prices else None

    return poc, vah, val, profile


# ── Chargement des ticks par blocs ────────────────────────────

def load_ticks_for_period(conn, start_dt, end_dt):
    """Charge les ticks entre deux timestamps. Retourne arrays numpy."""
    cur = conn.cursor()
    cur.execute(
        "SELECT last, volume FROM market_ticks_xauusd WHERE time >= %s AND time < %s ORDER BY time",
        (start_dt, end_dt)
    )
    rows = cur.fetchall()
    cur.close()

    if not rows:
        return np.array([]), np.array([])

    data = np.array(rows, dtype=np.float64)
    return data[:, 0], data[:, 1]


# ── Calcul ATR sur candles 5m ─────────────────────────────────

def compute_atr(conn, period=14, symbol='xauusd'):
    """ATR sur candles 5m, calculé par jour (moyenne des TR des candles du jour)."""
    table = f"candles_mt5_{symbol}_5m"
    cur = conn.cursor()
    cur.execute(f"SELECT ts, open, high, low, close FROM {table} ORDER BY ts")
    rows = cur.fetchall()
    cur.close()

    df = pd.DataFrame(rows, columns=['ts', 'open', 'high', 'low', 'close'])
    df['ts_dt'] = pd.to_datetime(df['ts'], unit='ms', utc=True)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['close'] = df['close'].astype(float)

    # True Range
    df['prev_close'] = df['close'].shift(1)
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['prev_close']),
            abs(df['low'] - df['prev_close'])
        )
    )

    # ATR rolling
    df['atr'] = df['tr'].ewm(span=period, adjust=False).mean()

    # ATR par jour (dernière valeur ATR du jour)
    df['date'] = df['ts_dt'].dt.date
    daily_atr = df.groupby('date')['atr'].last().to_dict()

    # ATR global moyen pour référence
    global_atr = df['atr'].mean()

    return daily_atr, global_atr


# ── Identification des jours de trading ───────────────────────

def get_trading_days(conn, symbol='xauusd'):
    """Récupère les jours uniques (ticks si dispo, sinon candles)."""
    cur = conn.cursor()
    try:
        table = f"market_ticks_{symbol}"
        cur.execute(f"SELECT DISTINCT DATE(time) FROM {table} ORDER BY 1")
        days = [r[0] for r in cur.fetchall()]
    except Exception:
        conn.rollback()
        table = f"candles_mt5_{symbol}_5m"
        cur.execute(f"SELECT DISTINCT DATE(to_timestamp(ts/1000)) FROM {table} ORDER BY 1")
        days = [r[0].date() if hasattr(r[0], 'date') else r[0] for r in cur.fetchall()]
    cur.close()
    return days


# ── Identification des semaines de trading ────────────────────

def get_trading_weeks(trading_days):
    """Groupe les jours de trading par semaine ISO."""
    weeks = defaultdict(list)
    for d in trading_days:
        iso = d.isocalendar()
        key = (iso[0], iso[1])  # (year, week)
        weeks[key].append(d)
    return weeks


# ── MAIN ──────────────────────────────────────────────────────

def main():
    conn = get_conn()

    print("=" * 70)
    print("PHASE 1 — CALCUL EXHAUSTIF DES POC")
    print("=" * 70)

    # 1. Jours de trading
    trading_days = get_trading_days(conn)
    print(f"\nJours de trading disponibles: {len(trading_days)}")
    print(f"  Du {trading_days[0]} au {trading_days[-1]}")

    # 2. ATR
    print("\n── Calcul ATR ──")
    daily_atr, global_atr = compute_atr(conn)
    print(f"  ATR global moyen (5m, EMA-14): {global_atr:.2f}")
    print(f"  ATR jours disponibles: {len(daily_atr)}")

    # 3. POC par SESSION
    print("\n── POC par session ──")
    session_pocs = []

    for day in trading_days:
        for sess_name, sess_times in SESSIONS_CONFIG.items():
            start_h = sess_times['start']
            end_h = sess_times['end']

            start_dt = datetime(day.year, day.month, day.day, int(start_h), int((start_h % 1) * 60))
            end_dt = datetime(day.year, day.month, day.day, int(end_h), int((end_h % 1) * 60))

            prices, volumes = load_ticks_for_period(conn, start_dt, end_dt)

            if len(prices) < 10:
                continue

            poc, vah, val, _ = compute_vp(prices, volumes)

            if poc is not None:
                session_pocs.append({
                    'date': day,
                    'session': sess_name,
                    'poc': poc,
                    'vah': vah,
                    'val': val,
                    'n_ticks': len(prices),
                    'start': start_dt,
                    'end': end_dt,
                })

    print(f"  Sessions calculées: {len(session_pocs)}")
    by_sess = defaultdict(int)
    for sp in session_pocs:
        by_sess[sp['session']] += 1
    for s, c in by_sess.items():
        print(f"    {s}: {c} POC")

    # Montrer quelques exemples
    if session_pocs:
        print("\n  Exemples (3 premiers):")
        for sp in session_pocs[:3]:
            atr = daily_atr.get(sp['date'], global_atr)
            va_width = (sp['vah'] - sp['val']) / atr if atr > 0 else 0
            print(f"    {sp['date']} {sp['session']}: POC={sp['poc']:.2f}, "
                  f"VA width={va_width:.2f} ATR, ticks={sp['n_ticks']}")

    # 4. POC par JOUR
    print("\n── POC par jour ──")
    daily_pocs = []

    for day in trading_days:
        start_dt = datetime(day.year, day.month, day.day, 0, 0)
        end_dt = start_dt + timedelta(days=1)

        prices, volumes = load_ticks_for_period(conn, start_dt, end_dt)

        if len(prices) < 100:
            continue

        poc, vah, val, _ = compute_vp(prices, volumes)

        if poc is not None:
            daily_pocs.append({
                'date': day,
                'poc': poc,
                'vah': vah,
                'val': val,
                'n_ticks': len(prices),
            })

    print(f"  Jours calculés: {len(daily_pocs)}")
    if daily_pocs:
        print("\n  Exemples (3 premiers):")
        for dp in daily_pocs[:3]:
            atr = daily_atr.get(dp['date'], global_atr)
            va_width = (dp['vah'] - dp['val']) / atr if atr > 0 else 0
            print(f"    {dp['date']}: POC={dp['poc']:.2f}, "
                  f"VA width={va_width:.2f} ATR, ticks={dp['n_ticks']}")

    # 5. POC par SEMAINE
    print("\n── POC par semaine ──")
    trading_weeks = get_trading_weeks(trading_days)
    weekly_pocs = []

    for (year, week), days in sorted(trading_weeks.items()):
        start_dt = datetime(days[0].year, days[0].month, days[0].day, 0, 0)
        end_dt = datetime(days[-1].year, days[-1].month, days[-1].day, 23, 59, 59)

        prices, volumes = load_ticks_for_period(conn, start_dt, end_dt)

        if len(prices) < 100:
            continue

        poc, vah, val, _ = compute_vp(prices, volumes)

        if poc is not None:
            weekly_pocs.append({
                'year': year,
                'week': week,
                'start_date': days[0],
                'end_date': days[-1],
                'poc': poc,
                'vah': vah,
                'val': val,
                'n_ticks': len(prices),
            })

    print(f"  Semaines calculées: {len(weekly_pocs)}")
    if weekly_pocs:
        print("\n  Exemples (3 premiers):")
        for wp in weekly_pocs[:3]:
            atr = daily_atr.get(wp['start_date'], global_atr)
            va_width = (wp['vah'] - wp['val']) / atr if atr > 0 else 0
            print(f"    W{wp['week']:02d}-{wp['year']}: POC={wp['poc']:.2f}, "
                  f"VA width={va_width:.2f} ATR, ticks={wp['n_ticks']:,}")

    # 6. Résumé
    print("\n" + "=" * 70)
    print("RÉSUMÉ PHASE 1")
    print("=" * 70)
    print(f"  POC sessions : {len(session_pocs)}")
    print(f"  POC daily    : {len(daily_pocs)}")
    print(f"  POC weekly   : {len(weekly_pocs)}")
    print(f"  ATR moyen 5m : {global_atr:.2f}")
    print(f"  Période      : {trading_days[0]} → {trading_days[-1]}")
    print("=" * 70)

    conn.close()

    return session_pocs, daily_pocs, weekly_pocs, daily_atr, global_atr


if __name__ == '__main__':
    main()
