"""
Moteur de backtest unifie — source unique de verite pour tout le pipeline.
Importe par: bt_portfolio, compare_today, live_mt5, optimize_all.

Garantit: memes candles, meme ATR, memes indicateurs, memes signaux,
memes exits, meme conflict filter — partout.
"""
import numpy as np
import pandas as pd
from phase1_poc_calculator import get_conn, compute_atr, get_trading_days
from phase3_analyze import load_candles_5m
from strats import detect_all, compute_indicators, sim_exit_custom
from strat_exits import STRAT_EXITS, DEFAULT_EXIT


# ══════════════════════════════════════════════════════════════
#  CONSTANTES — definies UNE SEULE FOIS
# ══════════════════════════════════════════════════════════════

OPEN_STRATS = frozenset({
    'TOK_FADE', 'TOK_PREVEXT', 'LON_GAP', 'LON_BIGGAP', 'LON_KZ',
    'LON_TOKEND', 'LON_PREV', 'NY_GAP', 'NY_LONEND', 'NY_LONMOM', 'NY_DAYMOM',
})


# ══════════════════════════════════════════════════════════════
#  LOAD DATA — candles + ATR + trading_days + indicateurs
# ══════════════════════════════════════════════════════════════

def load_data(conn, symbol):
    """Charge candles FULL history + ATR + trading_days + indicateurs precalcules.
    Retourne (candles_df, daily_atr_dict, global_atr_float, trading_days_list).
    """
    candles = load_candles_5m(conn, symbol=symbol.lower())
    daily_atr, global_atr = compute_atr(conn, symbol=symbol.lower())
    trading_days_list = get_trading_days(conn, symbol=symbol.lower())
    candles = compute_indicators(candles)
    return candles, daily_atr, global_atr, trading_days_list


# ══════════════════════════════════════════════════════════════
#  PREV DAY — jour de trading precedent
# ══════════════════════════════════════════════════════════════

def prev_trading_day(day, trading_days_list):
    """Retourne le jour de trading precedent."""
    for di, d in enumerate(trading_days_list):
        if d >= day:
            return trading_days_list[di - 1] if di > 0 else None
    return trading_days_list[-1] if trading_days_list else None


# ══════════════════════════════════════════════════════════════
#  COLLECT TRADES — signaux + exits + conflict filter
# ══════════════════════════════════════════════════════════════

def collect_trades(candles, daily_atr, global_atr, trading_days_list, portfolio, sym_exits, date_filter=None):
    """
    Detecte tous les signaux + simule les exits en temps reel.
    Meme code pour bt_portfolio, compare_today, et live.

    Args:
        candles: DataFrame avec indicateurs precalcules (from load_data)
        daily_atr: dict date -> ATR (from compute_atr)
        global_atr: float ATR global (fallback)
        trading_days_list: list de dates
        portfolio: list de noms de strats a detecter
        sym_exits: dict strat -> (type, p1, p2, p3)
        date_filter: si specifie, ne collecte que les signaux de ce jour (date object)

    Returns:
        list of (ci, xi, di, pnl_oz, sl_atr, atr, mo, sn) — meme format que strat_arrays
    """
    portfolio_set = set(portfolio)

    # Phase 1: collecter les signaux bruts
    signals = []
    prev_d = None; trig = {}; day_atr = None
    prev_day_data = None; prev2_day_data = None

    for ci in range(200, len(candles)):
        row = candles.iloc[ci]; ct = row['ts_dt']; today = ct.date()
        hour = ct.hour + ct.minute / 60.0

        # Gestion du changement de jour (toujours, meme si on filtre)
        if today != prev_d:
            if prev_d:
                yc = candles[candles['date'] == prev_d]
                if len(yc) > 0:
                    prev2_day_data = prev_day_data
                    prev_day_data = _make_day_data(yc)
            prev_d = today; trig = {}
            pd_ = prev_trading_day(today, trading_days_list)
            day_atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr

        # Si date_filter actif, skip les bars hors du jour demande
        if date_filter is not None and today != date_filter:
            continue

        atr = day_atr
        if atr == 0 or atr is None:
            continue

        ds = pd.Timestamp(today.year, today.month, today.day, 0, 0, tz='UTC')
        te = pd.Timestamp(today.year, today.month, today.day, 6, 0, tz='UTC')
        ls = pd.Timestamp(today.year, today.month, today.day, 8, 0, tz='UTC')
        ns = pd.Timestamp(today.year, today.month, today.day, 14, 30, tz='UTC')
        tv = candles[(candles['ts_dt'] >= ds) & (candles['ts_dt'] <= ct)]
        tok = tv[tv['ts_dt'] < te]
        lon = tv[(tv['ts_dt'] >= ls) & (tv['ts_dt'] < ns)]

        def add_sig(sn, d_dir, e):
            if sn in portfolio_set:
                signals.append((ci, sn, d_dir, e, atr, today))

        detect_all(candles, ci, row, ct, today, hour, atr, trig, tv, tok, lon,
                   prev_day_data, add_sig, prev2_day_data)

    # Phase 2: simuler exits + conflict filter
    signals.sort(key=lambda x: (x[0], x[1]))
    trades = []
    active_pos = []

    for ci, sn, d_dir, entry, atr, today in signals:
        is_open = sn in OPEN_STRATS
        exit_cfg = sym_exits.get(sn, DEFAULT_EXIT)
        etype = exit_cfg[0]; p1 = exit_cfg[1]; p2 = exit_cfg[2]
        p3 = exit_cfg[3] if len(exit_cfg) > 3 else 0

        b, ex = sim_exit_custom(candles, ci, entry, d_dir, atr,
                                etype, p1, p2, p3, check_entry_candle=is_open)
        xi = ci + b
        di = 1 if d_dir == 'long' else -1
        pnl_oz = (ex - entry) if d_dir == 'long' else (entry - ex)
        mo = f"{today.year}-{str(today.month).zfill(2)}"

        # Conflict filter: pas de trades opposes simultanes
        active_pos = [(axi, ad) for axi, ad in active_pos if axi >= ci]
        if any(ad != di for _, ad in active_pos):
            continue
        active_pos.append((xi, di))

        trades.append((ci, xi, di, pnl_oz, p1, atr, mo, sn))

    return trades


def _make_day_data(yc):
    """Cree le dict prev_day_data a partir des candles d'un jour."""
    return {
        'open': float(yc.iloc[0]['open']),
        'close': float(yc.iloc[-1]['close']),
        'high': float(yc['high'].max()),
        'low': float(yc['low'].min()),
        'range': float(yc['high'].max() - yc['low'].min()),
        'body': float(yc.iloc[-1]['close'] - yc.iloc[0]['open']),
    }


# ══════════════════════════════════════════════════════════════
#  EVAL PORTFOLIO — PF / WR / DD / Rend
# ══════════════════════════════════════════════════════════════

def eval_portfolio(trades, risk, capital=100000.0):
    """
    Evalue un portefeuille de trades (event-based simulation).

    Args:
        trades: list of (ci, xi, di, pnl_oz, sl_atr, atr, mo, sn)
        risk: float (e.g. 0.0005 pour 0.05%)
        capital: float capital initial

    Returns:
        dict with n, pf, wr, mdd, ret, capital, pm, tm, months, strat_stats, accepted
        ou None si aucun trade
    """
    if not trades:
        return None
    n = len(trades)
    events = [(ei, 0, idx) for idx, (ei, *_) in enumerate(trades)] + \
             [(xi, 1, idx) for idx, (_, xi, *__) in enumerate(trades)]
    events.sort()

    cap = capital; peak = cap; max_dd = 0; gp = 0; gl = 0; wins = 0
    months = {}; entry_caps = {}; strat_stats = {}
    month_detail = {}

    for bar, evt, idx in events:
        if evt == 0:
            entry_caps[idx] = cap
        else:
            ei, xi, di, pnl_oz, sl_atr, atr, mo, _sn = trades[idx]
            pnl = pnl_oz * (entry_caps[idx] * risk) / (sl_atr * atr)
            cap += pnl
            if cap > peak: peak = cap
            dd = (cap - peak) / peak
            if dd < max_dd: max_dd = dd
            if pnl > 0: gp += pnl; wins += 1
            else: gl += abs(pnl)
            months[mo] = months.get(mo, 0.0) + pnl
            md = month_detail.setdefault(mo, {'n': 0, 'w': 0, 'gp': 0, 'gl': 0})
            md['n'] += 1
            if pnl > 0: md['w'] += 1; md['gp'] += pnl
            else: md['gl'] += abs(pnl)
            month_detail[mo]['cap'] = cap
            month_detail[mo]['peak'] = peak
            month_detail[mo]['dd'] = max_dd
            ss = strat_stats.setdefault(_sn, {'n': 0, 'w': 0, 'gp': 0, 'gl': 0})
            ss['n'] += 1
            if pnl > 0: ss['w'] += 1; ss['gp'] += pnl
            else: ss['gl'] += abs(pnl)

    pm = sum(1 for v in months.values() if v > 0)
    return {
        'n': n, 'pf': gp / (gl + 0.01), 'wr': wins / n * 100, 'mdd': max_dd * 100,
        'ret': (cap - capital) / capital * 100, 'capital': cap, 'pm': pm, 'tm': len(months),
        'months': months, 'strat_stats': strat_stats, 'month_detail': month_detail,
        'accepted': trades,
    }
