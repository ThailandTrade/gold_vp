"""
Paper Trading Live — MIROIR EXACT du backtest (portfolio_final_clean.py).
Chaque decision est identique au backtest. Zero divergence.

Usage: python live_paper.py
Ctrl+C pour arreter.
"""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, time, logging
import numpy as np, pandas as pd
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from collections import defaultdict
load_dotenv()

from phase1_poc_calculator import (
    get_conn, compute_atr
)


def get_conn_autocommit():
    """Connexion en autocommit — pas de lock entre les queries."""
    conn = get_conn()
    conn.autocommit = True
    return conn

# ── CONFIG (identique au backtest) ────────────────────

CAPITAL_INITIAL = 10000.0
SLIPPAGE = 0.10
CHECK_INTERVAL = 1
LOG_FILE = "paper_trades.json"

STRAT_CONFIG = {
    'B_tok_0h1h_UP': {'type': 'trailing', 'sl_atr': 0.75, 'act': 0.5, 'trail': 0.3, 'max_bars': 24, 'dir': 'long'},
    'D2_tok_5h_body': {'type': 'trailing', 'sl_atr': 0.75, 'act': 0.5, 'trail': 0.3, 'max_bars': 24, 'dir': 'long'},
    'FADE_tok_lon': {'type': 'trailing', 'sl_atr': 0.75, 'act': 0.5, 'trail': 0.3, 'max_bars': 24, 'dir': None},
    'GAP_tok_lon': {'type': 'trailing', 'sl_atr': 0.75, 'act': 0.5, 'trail': 0.3, 'max_bars': 24, 'dir': None},
    'KZ_lon_fade': {'type': 'trailing', 'sl_atr': 0.75, 'act': 0.5, 'trail': 0.3, 'max_bars': 24, 'dir': None},
    '2BAR_tok_rev': {'type': 'trailing', 'sl_atr': 0.75, 'act': 0.5, 'trail': 0.3, 'max_bars': 24, 'dir': None},
}

RISK_PCT = 0.004  # 0.4% pour le champion

# ── LOGGING ───────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('paper_trading.log', encoding='utf-8'),
    ]
)
log = logging.getLogger('paper')


# ── HELPERS (identiques au backtest) ──────────────────

def get_recent_candles(conn, n=500):
    """Charge les N dernieres candles 5m."""
    cur = conn.cursor()
    cur.execute("""SELECT ts, open, high, low, close FROM candles_mt5_xauusd_5m
                   ORDER BY ts DESC LIMIT %s""", (n,))
    rows = cur.fetchall()
    cur.close()
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows, columns=['ts', 'open', 'high', 'low', 'close'])
    df = df.sort_values('ts').reset_index(drop=True)
    df['ts_dt'] = pd.to_datetime(df['ts'], unit='ms', utc=True)
    for c in ['open', 'high', 'low', 'close']:
        df[c] = df[c].astype(float)
    df['date'] = df['ts_dt'].dt.date
    return df


def get_current_bidask(conn):
    """Dernier tick MT5 : retourne (bid, ask, last, spread)."""
    cur = conn.cursor()
    cur.execute("""SELECT bid, ask, last FROM market_ticks_xauusd
                   ORDER BY ts DESC LIMIT 1""")
    row = cur.fetchone()
    cur.close()
    if row:
        bid, ask, last = float(row[0]), float(row[1]), float(row[2])
        return {'bid': bid, 'ask': ask, 'last': last, 'spread': ask - bid}
    return None


def get_yesterday_atr(candles_df, today):
    """ATR du jour PRECEDENT — identique au backtest.
    Calcule l'EMA-14 du TR sur les candles du jour precedent."""
    yesterday_candles = candles_df[candles_df['date'] < today].copy()
    if len(yesterday_candles) < 20:
        return None
    yesterday_candles['prev_close'] = yesterday_candles['close'].shift(1)
    yesterday_candles['tr'] = np.maximum(
        yesterday_candles['high'] - yesterday_candles['low'],
        np.maximum(abs(yesterday_candles['high'] - yesterday_candles['prev_close']),
                   abs(yesterday_candles['low'] - yesterday_candles['prev_close'])))
    yesterday_candles['atr'] = yesterday_candles['tr'].ewm(span=14, adjust=False).mean()
    return float(yesterday_candles['atr'].iloc[-1])


def get_spread_rt(conn, today):
    """Spread round-trip reel du mois courant."""
    cur = conn.cursor()
    month_start = datetime(today.year, today.month, 1, 0, 0)
    cur.execute("""SELECT AVG(ask - bid) FROM market_ticks_xauusd
                   WHERE ask > bid AND ask - bid < 10
                   AND time >= %s""", (month_start,))
    row = cur.fetchone()
    cur.close()
    if row and row[0]:
        return 2 * float(row[0])
    return 0.188  # fallback


# ── LOAD/SAVE STATE ──────────────────────────────────

def load_state():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r') as f:
            return json.load(f)
    return {
        'capital': CAPITAL_INITIAL,
        'trades': [],
        'open_positions': [],
        'ib_levels': {},
        'daily_cache': {},
        '_triggered': {},
        'last_candle_ts': 0,
    }


def save_state(state):
    with open(LOG_FILE, 'w') as f:
        json.dump(state, f, indent=2, default=str)


# ── DAILY CACHE — recalcule 1x par jour ──────────────

def ensure_daily_cache(state, conn, candles_df, today):
    """Calcule ATR, VA, median 1 fois par jour. Identique au backtest."""
    cache_key = str(today)
    if cache_key in state['daily_cache']:
        return state['daily_cache'][cache_key]

    log.info("Calcul cache journalier pour {}...".format(today))

    atr = get_yesterday_atr(candles_df, today)
    spread_rt = get_spread_rt(conn, today)

    cache = {
        'atr': atr,
        'spread_rt': spread_rt,
    }

    # Ne garder que le cache du jour courant
    state['daily_cache'] = {cache_key: cache}

    log.info("  ATR={}, spread_rt={}".format(
        "{:.2f}".format(atr) if atr else "None",
        "{:.3f}".format(spread_rt)))

    return cache


# ── POSITION MANAGEMENT (identique au backtest) ──────

def manage_positions(candles_df, state, cache, conn):
    """Gere les positions ouvertes.
    IDENTIQUE au backtest: stop verifie AVANT best update.
    ATR fixe a l'ouverture du trade (stocke dans la position)."""
    last = candles_df.iloc[-1]
    closed = []
    spread_rt = cache['spread_rt']

    for pos in state['open_positions']:
        cfg = STRAT_CONFIG[pos['strat']]
        bars_held = pos.get('bars_held', 0) + 1
        pos['bars_held'] = bars_held

        # ATR fixe du trade (pas l'ATR courant)
        trade_atr = pos['trade_atr']

        trade_dir = pos['strat_dir']  # direction reelle du trade

        if cfg['type'] == 'trailing':
            if trade_dir == 'long':
                # 1. Stop verifie AVANT best update (identique backtest)
                if last['low'] <= pos['stop']:
                    pos['exit'] = pos['stop'] - SLIPPAGE
                    pos['exit_reason'] = 'stop'
                    closed.append(pos)
                    continue
                # 2. Update best
                if last['high'] > pos.get('best', pos['entry']):
                    pos['best'] = last['high']
                # 3. Activation trailing (avec ATR du trade, pas courant)
                if not pos.get('trail_active', False):
                    if pos['best'] - pos['entry'] >= cfg['act'] * trade_atr:
                        pos['trail_active'] = True
                # 4. Update trailing stop
                if pos.get('trail_active', False):
                    new_stop = pos['best'] - cfg['trail'] * trade_atr
                    pos['stop'] = max(pos['stop'], new_stop)
            else:  # short
                if last['high'] >= pos['stop']:
                    pos['exit'] = pos['stop'] + SLIPPAGE
                    pos['exit_reason'] = 'stop'
                    closed.append(pos)
                    continue
                if last['low'] < pos.get('best', pos['entry']):
                    pos['best'] = last['low']
                if not pos.get('trail_active', False):
                    if pos['entry'] - pos['best'] >= cfg['act'] * trade_atr:
                        pos['trail_active'] = True
                if pos.get('trail_active', False):
                    new_stop = pos['best'] + cfg['trail'] * trade_atr
                    pos['stop'] = min(pos['stop'], new_stop)

        elif cfg['type'] == 'standard':
            if trade_dir == 'short':
                # Stop verifie AVANT TP (identique backtest)
                if last['high'] >= pos['stop']:
                    pos['exit'] = pos['stop'] + SLIPPAGE
                    pos['exit_reason'] = 'stop'
                    closed.append(pos)
                    continue
                if last['low'] <= pos['target']:
                    pos['exit'] = pos['target']
                    pos['exit_reason'] = 'tp'
                    closed.append(pos)
                    continue

        # Timeout
        if bars_held >= cfg['max_bars']:
            pos['exit'] = last['close']
            pos['exit_reason'] = 'timeout'
            closed.append(pos)

    # Fermer les positions — prix MT5 reel (bid/ask)
    for c in closed:
        state['open_positions'].remove(c)

        # Prix de sortie reel: LONG ferme au BID, SHORT ferme a l'ASK
        # Pour les stops/TP intra-bar, on utilise le prix du stop + slippage
        # (deja calcule ci-dessus). Le spread est dans le prix d'entree.
        # Pour les timeouts, on prend le prix actuel bid/ask.
        if c['exit_reason'] == 'timeout':
            tick = get_current_bidask(conn)
            if tick:
                if c['strat_dir'] == 'long':
                    c['exit'] = tick['bid']  # on vend au BID
                else:
                    c['exit'] = tick['ask']  # on rachete a l'ASK
                c['exit_bid'] = tick['bid']
                c['exit_ask'] = tick['ask']
                c['exit_spread'] = tick['spread']

        if c['strat_dir'] == 'long':
            pnl_oz = c['exit'] - c['entry']
        else:
            pnl_oz = c['entry'] - c['exit']

        # PAS de deduction de spread separee — le spread est DANS les prix bid/ask
        pnl_dollar = pnl_oz * c['pos_oz']
        state['capital'] += pnl_dollar

        trade_record = {
            'strat': c['strat'], 'dir': c['strat_dir'],
            'entry': c['entry'], 'exit': c['exit'],
            'entry_bid': c.get('entry_bid'), 'entry_ask': c.get('entry_ask'),
            'entry_spread': c.get('entry_spread'),
            'entry_time': c['entry_time'],
            'exit_time': str(datetime.now(timezone.utc)),
            'pnl_oz': pnl_oz,
            'pnl_dollar': pnl_dollar,
            'bars_held': c['bars_held'],
            'exit_reason': c['exit_reason'],
            'capital_after': state['capital'],
        }
        state['trades'].append(trade_record)
        log.info("CLOSE {} {} | {:.2f}->{:.2f} | pnl_oz={:+.3f} ${:+.2f} ({}) | Cap=${:,.2f}".format(
            c['strat'], c['strat_dir'], c['entry'], c['exit'],
            pnl_oz, pnl_dollar, c['exit_reason'], state['capital']))


# ── SIGNAL DETECTION ─────────────────────────────────

def check_ib_signals(candles_df, state, atr, candle_time):
    """Detecte les IB breaks. Utilise le timestamp de la candle, pas l'horloge PC."""
    signals = []
    today = candle_time.date()
    hour = candle_time.hour + candle_time.minute / 60.0

    ib_key = str(today)
    if ib_key not in state['ib_levels']:
        state['ib_levels'] = {ib_key: {}}

    ibs = state['ib_levels'][ib_key]

    # B: IB 0h-1h (12 bougies), break UP 1h-6h
    if 'B_done' not in ibs and hour >= 1.0:
        start = pd.Timestamp(today.year, today.month, today.day, 0, 0, tz='UTC')
        end = start + pd.Timedelta(hours=1)
        ib_c = candles_df[(candles_df['ts_dt'] >= start) & (candles_df['ts_dt'] < end)]
        if len(ib_c) >= 12:
            ibs['B_high'] = float(ib_c['high'].max())
            ibs['B_done'] = True

    if 'B_high' in ibs and 'B_trig' not in ibs and 1.0 <= hour < 6.0:
        if candles_df.iloc[-1]['close'] > ibs['B_high']:
            signals.append({'strat': 'B_tok_0h1h_UP', 'dir': 'long',
                            'entry': candles_df.iloc[-1]['close']})
            ibs['B_trig'] = True

    # D2: IB 5h-5h15 (3 bougies), break UP + body >= 50% du range
    if 'D2_done' not in ibs and hour >= 5.25:
        start = pd.Timestamp(today.year, today.month, today.day, 5, 0, tz='UTC')
        end = start + pd.Timedelta(minutes=15)
        ib_c = candles_df[(candles_df['ts_dt'] >= start) & (candles_df['ts_dt'] < end)]
        if len(ib_c) >= 3:
            ibs['D2_high'] = float(ib_c['high'].max())
            ibs['D2_done'] = True

    if 'D2_high' in ibs and 'D2_trig' not in ibs and 5.25 <= hour < 6.0:
        last = candles_df.iloc[-1]
        if last['close'] > ibs['D2_high']:
            # Filtre body >= 50% du range de la bougie
            body = abs(last['close'] - last['open'])
            rng = last['high'] - last['low']
            if rng > 0 and body / rng >= 0.5:
                signals.append({'strat': 'D2_tok_5h_body', 'dir': 'long',
                                'entry': last['close']})
                ibs['D2_trig'] = True

    return signals


# ── DASHBOARD ─────────────────────────────────────────

def print_dashboard(state, cache, candle_time):
    lines = []
    lines.append("=" * 70)
    lines.append("PAPER TRADING — {} | ATR={} | Spread RT={}".format(
        candle_time.strftime("%Y-%m-%d %H:%M UTC"),
        "{:.2f}".format(cache['atr']) if cache['atr'] else "?",
        "{:.3f}".format(cache['spread_rt'])))
    lines.append("  Capital: ${:,.2f} (PnL: ${:+,.2f})".format(
        state['capital'], state['capital'] - CAPITAL_INITIAL))

    lines.append("  Strats: B, D2, FADE, GAP, KZ, 2BAR")

    lines.append("  Positions: {}".format(len(state['open_positions'])))
    for p in state['open_positions']:
        lines.append("    {} {} entry={:.2f} stop={:.2f} best={:.2f} trail={} bars={}".format(
            p['strat'], p['strat_dir'], p['entry'], p['stop'],
            p.get('best', p['entry']),
            "ON" if p.get('trail_active') else "off", p.get('bars_held', 0)))

    trades = state['trades']
    if trades:
        wins = [t for t in trades if t['pnl_dollar'] > 0]
        gp = sum(t['pnl_dollar'] for t in wins) if wins else 0
        gl = abs(sum(t['pnl_dollar'] for t in trades if t['pnl_dollar'] < 0)) + 0.01
        lines.append("  Trades: {} | WR={:.0f}% | PF={:.2f} | PnL=${:+,.2f}".format(
            len(trades), len(wins) / len(trades) * 100, gp / gl,
            sum(t['pnl_dollar'] for t in trades)))
        for t in trades[-3:]:
            lines.append("    {} {} {:.2f}->{:.2f} ${:+.2f} ({})".format(
                t['strat'], t['dir'], t['entry'], t['exit'],
                t['pnl_dollar'], t['exit_reason']))

    lines.append("=" * 70)
    dashboard = "\n".join(lines)
    print("\033c" + dashboard)

    with open("paper_dashboard.txt", 'w', encoding='utf-8') as f:
        f.write(dashboard)


# ── MAIN LOOP ─────────────────────────────────────────

def reset_state():
    """Reset complet du paper trading."""
    state = {
        'capital': CAPITAL_INITIAL,
        'trades': [],
        'open_positions': [],
        'ib_levels': {},
        'daily_cache': {},
        '_triggered': {},
        'last_candle_ts': 0,
    }
    save_state(state)
    log.info("RESET — Capital ${:,.2f}, 0 trades, 0 positions".format(CAPITAL_INITIAL))
    return state


def main():
    # python live_paper.py --reset pour tout effacer
    if '--reset' in sys.argv:
        reset_state()
        print("Paper trading reset. Relancez sans --reset.")
        return

    log.info("Demarrage paper trading (miroir exact du backtest)...")
    state = load_state()
    log.info("Capital: ${:,.2f} | Trades: {} | Positions: {}".format(
        state['capital'], len(state['trades']), len(state['open_positions'])))

    conn = get_conn_autocommit()

    # Au premier demarrage (ou apres reset), se caler sur la derniere bougie en DB
    # pour ne traiter que les FUTURES bougies
    saved_ts = state.get('last_candle_ts', 0)
    if saved_ts == 0:
        candles_init = get_recent_candles(conn, 1)
        if len(candles_init) > 0:
            saved_ts = int(candles_init.iloc[-1]['ts'])
            log.info("Premier demarrage — calage sur la derniere bougie: {}".format(
                candles_init.iloc[-1]['ts_dt']))
    last_candle_ts = saved_ts

    while True:
        try:
            # Reconnecter si la connexion est morte
            try:
                conn.isolation_level
            except Exception:
                log.warning("Reconnexion DB...")
                try:
                    conn.close()
                except Exception:
                    pass
                conn = get_conn_autocommit()

            candles = get_recent_candles(conn, 500)
            if len(candles) == 0:
                time.sleep(CHECK_INTERVAL)
                continue

            current_ts = int(candles.iloc[-1]['ts'])
            candle_time = candles.iloc[-1]['ts_dt'].to_pydatetime()
            today = candle_time.date()

            # Cache journalier (ATR, VA, median, spread — 1x par jour)
            cache = ensure_daily_cache(state, conn, candles, today)

            if cache['atr'] is None or cache['atr'] == 0:
                time.sleep(CHECK_INTERVAL)
                continue

            atr = cache['atr']

            # Nouvelle bougie ?
            is_new_candle = (current_ts != last_candle_ts)

            if is_new_candle:
                last_close = candles.iloc[-1]['close']
                log.info("CANDLE {} | close={:.2f} | ATR={:.2f} | pos={}".format(
                    candle_time.strftime("%Y-%m-%d %H:%M"),
                    last_close, atr,
                    "{} open".format(len(state['open_positions'])) if state['open_positions'] else "0 open"))

                # Gerer les positions ouvertes (1x par bougie, pas 1x par seconde)
                # C'est ici que bars_held est incremente — uniquement sur nouvelle bougie
                if state['open_positions']:
                    manage_positions(candles, state, cache, conn)

                last_candle_ts = current_ts
                state['last_candle_ts'] = current_ts
            else:
                time.sleep(CHECK_INTERVAL)
                continue

            # 2. Directions ouvertes (no-conflict rule)
            open_dirs = set(p['strat_dir'] for p in state['open_positions'])

            # 3. Detecter signaux IB (B, D2)
            signals = check_ib_signals(candles, state, atr, candle_time)

            hour = candle_time.hour + candle_time.minute / 60.0
            if '_triggered' not in state:
                state['_triggered'] = {}
            trig = state['_triggered']

            # 4. FADE — Tokyo move > 1 ATR -> inverse a London open
            if 8.0 <= hour < 8.1:
                k = str(today) + '_FADE'
                if k not in trig:
                    tok_s = pd.Timestamp(today.year, today.month, today.day, 0, 0, tz='UTC')
                    tok_e = pd.Timestamp(today.year, today.month, today.day, 6, 0, tz='UTC')
                    tok = candles[(candles['ts_dt'] >= tok_s) & (candles['ts_dt'] < tok_e)]
                    if len(tok) >= 10:
                        tok_move = (tok.iloc[-1]['close'] - tok.iloc[0]['open']) / atr
                        if abs(tok_move) >= 1.0:
                            d = 'short' if tok_move > 0 else 'long'
                            signals.append({'strat': 'FADE_tok_lon', 'dir': d,
                                            'entry': candles.iloc[-1]['close']})
                            trig[k] = True

            # 5. GAP — Gap Tokyo close vs London open > 0.5 ATR, continuation
            if 8.0 <= hour < 8.1:
                k = str(today) + '_GAP'
                if k not in trig:
                    tok_e = pd.Timestamp(today.year, today.month, today.day, 6, 0, tz='UTC')
                    tok_c = candles[candles['ts_dt'] < tok_e]
                    if len(tok_c) >= 5:
                        tok_close = tok_c.iloc[-1]['close']
                        lon_open = candles.iloc[-1]['close']  # sera remplace par tick bid/ask
                        gap = (lon_open - tok_close) / atr
                        if abs(gap) >= 0.5:
                            d = 'long' if gap > 0 else 'short'
                            signals.append({'strat': 'GAP_tok_lon', 'dir': d,
                                            'entry': lon_open})
                            trig[k] = True

            # 6. KZ — London Kill Zone fade (8h-10h move > 0.5 ATR -> inverse a 10h)
            if 10.0 <= hour < 10.1:
                k = str(today) + '_KZ'
                if k not in trig:
                    kz_s = pd.Timestamp(today.year, today.month, today.day, 8, 0, tz='UTC')
                    kz_e = pd.Timestamp(today.year, today.month, today.day, 10, 0, tz='UTC')
                    kz = candles[(candles['ts_dt'] >= kz_s) & (candles['ts_dt'] < kz_e)]
                    if len(kz) >= 20:
                        kz_move = (kz.iloc[-1]['close'] - kz.iloc[0]['open']) / atr
                        if abs(kz_move) >= 0.5:
                            d = 'short' if kz_move > 0 else 'long'
                            signals.append({'strat': 'KZ_lon_fade', 'dir': d,
                                            'entry': candles.iloc[-1]['close']})
                            trig[k] = True

            # 7. 2BAR — Tokyo two-bar reversal (body > 0.5 ATR, opposees, 2eme > 1ere)
            if 0.0 <= hour < 6.0 and len(candles) >= 3:
                k = str(today) + '_2BAR'
                if k not in trig:
                    b1 = candles.iloc[-2]; b2 = candles.iloc[-1]
                    b1b = b1['close'] - b1['open']
                    b2b = b2['close'] - b2['open']
                    if (abs(b1b) >= 0.5 * atr and abs(b2b) >= 0.5 * atr and
                        b1b * b2b < 0 and abs(b2b) > abs(b1b)):
                        d = 'long' if b2b > 0 else 'short'
                        signals.append({'strat': '2BAR_tok_rev', 'dir': d,
                                        'entry': b2['close']})
                        trig[k] = True

            # 5. Ouvrir les positions — prix MT5 reel (bid/ask)
            for sig in signals:
                if sig['dir'] == 'long' and 'short' in open_dirs:
                    log.info("SKIP {} — conflit short ouvert".format(sig['strat']))
                    continue
                if sig['dir'] == 'short' and 'long' in open_dirs:
                    log.info("SKIP {} — conflit long ouvert".format(sig['strat']))
                    continue

                # Prix MT5 reel au moment du signal
                tick = get_current_bidask(conn)
                if tick is None:
                    log.warning("SKIP {} — pas de tick disponible".format(sig['strat']))
                    continue

                cfg = STRAT_CONFIG[sig['strat']]
                trade_dir = sig['dir']  # direction du signal (pas cfg, car H est dynamique)

                # LONG = on achete a l'ASK, SHORT = on vend au BID
                if trade_dir == 'long':
                    entry = tick['ask']
                else:
                    entry = tick['bid']

                # Position sizing (avec ATR du jour precedent)
                risk_dollar = state['capital'] * RISK_PCT
                stop_dollar = cfg['sl_atr'] * atr
                pos_oz = risk_dollar / stop_dollar if stop_dollar > 0 else 0
                lots = pos_oz / 100

                if trade_dir == 'long':
                    stop = entry - cfg['sl_atr'] * atr
                else:
                    stop = entry + cfg['sl_atr'] * atr

                position = {
                    'strat': sig['strat'],
                    'strat_dir': sig['dir'],
                    'entry': entry,
                    'stop': stop,
                    'best': entry,
                    'trail_active': False,
                    'pos_oz': pos_oz,
                    'lots': lots,
                    'bars_held': 0,
                    'entry_time': str(candle_time),
                    'trade_atr': atr,  # ATR FIXE pour toute la duree du trade
                    'entry_bid': tick['bid'],
                    'entry_ask': tick['ask'],
                    'entry_spread': tick['spread'],
                }

                if cfg['type'] == 'standard':
                    if trade_dir == 'short':
                        position['target'] = entry - cfg['tp_atr'] * atr
                    else:
                        position['target'] = entry + cfg['tp_atr'] * atr

                state['open_positions'].append(position)
                open_dirs.add(sig['dir'])

                log.info("OPEN {} {} | entry={:.2f} (bid={:.2f} ask={:.2f} spread={:.3f}) | stop={:.2f} | {:.3f} lots".format(
                    sig['strat'], sig['dir'], entry, tick['bid'], tick['ask'],
                    tick['spread'], stop, lots))

            # Log si aucun signal
            if not signals:
                log.debug("  -> pas de signal")
            else:
                log.info("  -> {} signal(s) detecte(s)".format(len(signals)))

            # Dashboard
            print_dashboard(state, cache, candle_time)

            # Save
            save_state(state)

        except KeyboardInterrupt:
            log.info("Arret.")
            save_state(state)
            break
        except Exception as e:
            log.error("Erreur: {}".format(e))
            import traceback
            traceback.print_exc()
            time.sleep(30)

        time.sleep(CHECK_INTERVAL)

    conn.close()
    log.info("Capital final: ${:,.2f}".format(state['capital']))


if __name__ == '__main__':
    main()
