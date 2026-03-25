"""
Live Trading MT5 — multi-compte, vrais ordres.
Usage:
  python live_mt5.py icm --dry              → dry run ICM
  python live_mt5.py ftmo                   → FTMO live
  python live_mt5.py 5ers --symbol XAUUSDm  → 5ers symbole custom

- Magic number unique par strat (identification sur MT5)
- Positions et trades lus directement depuis MT5
- State minimal: triggers + trailing info
- TPSL: SL + TP sur l'ordre → MT5 gere les exits
- TRAIL: SL initial → modify SL a chaque bougie fermee
"""
import warnings; warnings.filterwarnings('ignore')
import sys, argparse; sys.stdout.reconfigure(encoding='utf-8')
import os, json, time, logging
import numpy as np, pandas as pd
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
load_dotenv()
import MetaTrader5 as mt5
from phase1_poc_calculator import get_conn

# ── CONFIG ────────────────────────────────────────────

parser = argparse.ArgumentParser(description='Live MT5 trading')
parser.add_argument('account', nargs='?', default='icm', choices=['icm','ftmo','5ers'])
parser.add_argument('-r', '--risk', type=float, default=None, help='Risk %% par trade')
parser.add_argument('--reset', action='store_true', help='Reset state')
parser.add_argument('--symbol', default='XAUUSD', help='MT5 symbol')
parser.add_argument('--dry', action='store_true', help='Dry run')
args = parser.parse_args()
_account = args.account

if _account == 'ftmo':
    from config_ftmo import PORTFOLIO as STRATS, RISK_PCT, BROKER
elif _account == '5ers':
    from config_5ers import PORTFOLIO as STRATS, RISK_PCT, BROKER
else:
    from config_icm import PORTFOLIO as STRATS, RISK_PCT, BROKER

RISK_PCT = args.risk / 100 if args.risk else RISK_PCT
SYMBOL = args.symbol
DRY_RUN = args.dry
CHECK_INTERVAL = 1

os.makedirs(f'data/{_account}', exist_ok=True)
STATE_FILE = f"data/{_account}/live_mt5.json"
from strats import STRAT_NAMES, STRAT_SESSION, detect_all, compute_indicators
from strat_exits import STRAT_EXITS, DEFAULT_EXIT

OPEN_STRATS = ['TOK_FADE','TOK_PREVEXT','LON_GAP','LON_BIGGAP','LON_KZ','LON_TOKEND','LON_PREV','NY_GAP','NY_LONEND','NY_LONMOM','NY_DAYMOM']
CLOSE_STRATS = [s for s in STRATS if s not in OPEN_STRATS]

# ── MAGIC NUMBERS (stable hash par strat) ────────────

MAGIC_BASE = 240000
def _strat_magic(name):
    """Hash deterministe: stable entre redemarrages Python."""
    import hashlib
    return MAGIC_BASE + int(hashlib.md5(name.encode()).hexdigest()[:4], 16) % 9999
MAGIC_MAP = {sn: _strat_magic(sn) for sn in set(list(STRAT_EXITS.keys()) + list(STRATS))}
MAGIC_REVERSE = {v: k for k, v in MAGIC_MAP.items()}
ALL_OUR_MAGICS = set(MAGIC_MAP.values())

# ── LOGGING ──────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(),
              logging.FileHandler(f'data/{_account}/live_mt5.log', encoding='utf-8')])
log = logging.getLogger('mt5')

# ── MT5 ──────────────────────────────────────────────

def mt5_init():
    if not mt5.initialize():
        log.error("MT5 init failed: {}".format(mt5.last_error()))
        return False
    info = mt5.account_info()
    if info is None:
        log.error("MT5 account_info failed")
        return False
    log.info("MT5: {} {} bal=${:,.2f} eq=${:,.2f}".format(
        info.company, info.server, info.balance, info.equity))
    sym = mt5.symbol_info(SYMBOL)
    if sym is None:
        log.error("Symbole {} non trouve".format(SYMBOL))
        return False
    if not sym.visible:
        mt5.symbol_select(SYMBOL, True)
    log.info("  {}: lot_min={} step={} max={} digits={} contract={}".format(
        SYMBOL, sym.volume_min, sym.volume_step, sym.volume_max, sym.digits, sym.trade_contract_size))
    return True

def mt5_balance():
    info = mt5.account_info()
    return info.balance if info else 0

def mt5_tick():
    t = mt5.symbol_info_tick(SYMBOL)
    return {'bid': t.bid, 'ask': t.ask, 'spread': t.ask - t.bid} if t else None

def mt5_our_positions():
    """Get our positions (filtered by our magic numbers)."""
    positions = mt5.positions_get(symbol=SYMBOL) or []
    return [p for p in positions if p.magic in ALL_OUR_MAGICS]

def mt5_lot_size(risk_amount, sl_distance):
    sym = mt5.symbol_info(SYMBOL)
    if not sym or sl_distance <= 0: return sym.volume_min if sym else 0.01
    pos_units = risk_amount / sl_distance
    lots = pos_units / sym.trade_contract_size
    lots = max(sym.volume_min, round(lots / sym.volume_step) * sym.volume_step)
    lots = min(lots, sym.volume_max)
    return round(lots, 2)

def mt5_send_order(strat, direction, sl, tp, lots):
    sym = mt5.symbol_info(SYMBOL)
    if not sym: return None
    order_type = mt5.ORDER_TYPE_BUY if direction == 'long' else mt5.ORDER_TYPE_SELL
    price = sym.ask if direction == 'long' else sym.bid
    magic = MAGIC_MAP.get(strat, MAGIC_BASE)

    request = {
        'action': mt5.TRADE_ACTION_DEAL,
        'symbol': SYMBOL,
        'volume': lots,
        'type': order_type,
        'price': price,
        'sl': round(sl, sym.digits),
        'tp': round(tp, sym.digits) if tp else 0.0,
        'deviation': 20,
        'magic': magic,
        'comment': strat,
        'type_time': mt5.ORDER_TIME_GTC,
    }

    log.info(">>> {} {} {} {:.2f}lots @ {:.2f} SL={:.2f} TP={:.2f} magic={} <<<".format(
        'BUY' if direction == 'long' else 'SELL', strat, direction.upper(),
        lots, price, sl, tp or 0, magic))

    if DRY_RUN:
        log.info("    [DRY] Ordre non envoye")
        return {'ticket': int(time.time()*1000) % 1000000, 'price': price, 'volume': lots}

    result = mt5.order_send(request)
    if result is None:
        log.error("    order_send None: {}".format(mt5.last_error()))
        return None
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        log.error("    ECHEC: {} {}".format(result.retcode, result.comment))
        return None

    log.info("    OK #{} fill={:.2f}".format(result.order, result.price))
    return {'ticket': result.order, 'price': result.price, 'volume': result.volume}

def mt5_modify_sl(ticket, new_sl):
    sym = mt5.symbol_info(SYMBOL)
    if not sym: return False
    positions = mt5.positions_get(ticket=ticket)
    if not positions: return False

    request = {
        'action': mt5.TRADE_ACTION_SLTP,
        'symbol': SYMBOL,
        'position': ticket,
        'sl': round(new_sl, sym.digits),
        'tp': positions[0].tp,
    }

    if DRY_RUN:
        log.info("    [DRY] SL #{} -> {:.2f}".format(ticket, new_sl))
        return True

    result = mt5.order_send(request)
    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        return True
    log.error("    Modify SL #{} failed: {}".format(ticket, result.retcode if result else '?'))
    return False

# ── DB ────────────────────────────────────────────────

def get_conn_autocommit():
    conn = get_conn(); conn.autocommit = True; return conn

def get_recent_candles(conn, n=1500):
    cur = conn.cursor()
    cur.execute("SELECT ts, open, high, low, close FROM candles_mt5_xauusd_5m ORDER BY ts DESC LIMIT %s", (n,))
    rows = cur.fetchall(); cur.close()
    if not rows: return pd.DataFrame()
    df = pd.DataFrame(rows, columns=['ts','open','high','low','close']).sort_values('ts').reset_index(drop=True)
    df['ts_dt'] = pd.to_datetime(df['ts'], unit='ms', utc=True)
    for c in ['open','high','low','close']: df[c] = df[c].astype(float)
    df['date'] = df['ts_dt'].dt.date
    return df

def get_yesterday_atr(candles_df, today):
    yc = candles_df[candles_df['date'] < today].copy()
    if len(yc) < 20: return None
    yc['pc'] = yc['close'].shift(1)
    yc['tr'] = np.maximum(yc['high']-yc['low'], np.maximum(abs(yc['high']-yc['pc']), abs(yc['low']-yc['pc'])))
    yc['atr'] = yc['tr'].ewm(span=14, adjust=False).mean()
    return float(yc['atr'].iloc[-1])

# ── STATE (minimal: triggers + trailing info) ─────────

def new_state():
    return {'broker': BROKER, 'risk_pct': RISK_PCT,
            'daily_cache': {}, '_triggered_open': {}, '_triggered_close': {},
            '_prev_day_data': None, '_prev_day_date': None,
            'last_candle_ts': 0,
            'trail': {}}  # ticket -> {strat, best, trail_active, act_val, trail_val, atr}

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
            state.setdefault('trail', {})
            return state
    return new_state()

def save_state(state):
    with open(STATE_FILE, 'w') as f: json.dump(state, f, indent=2, default=str)

def reset_state():
    if os.path.exists(STATE_FILE): os.remove(STATE_FILE)
    state = new_state()
    save_state(state)
    log.info("RESET {} @ {:.1f}% risk".format(BROKER, RISK_PCT*100))
    return state

def ensure_daily_cache(state, conn, candles_df, today):
    k = str(today)
    if k in state['daily_cache']: return state['daily_cache'][k]
    atr = get_yesterday_atr(candles_df, today)
    cache = {'atr': atr}
    state['daily_cache'] = {k: cache}
    log.info("ATR {}: {}".format(today, "{:.2f}".format(atr) if atr else "None"))
    return cache

# ── SIGNAL DETECTION ─────────────────────────────────

def detect_open_strats(candles, state, atr, now_utc, today):
    if len(candles) < 2: return []
    signals = []
    trig = state.setdefault('_triggered_open', {})
    hour = now_utc.hour + now_utc.minute / 60.0
    r = candles.iloc[-2]; ci = len(candles) - 2
    ds = pd.Timestamp(today.year,today.month,today.day,0,0,tz='UTC')
    te = pd.Timestamp(today.year,today.month,today.day,6,0,tz='UTC')
    ls = pd.Timestamp(today.year,today.month,today.day,8,0,tz='UTC')
    ns = pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC')
    tv = candles[(candles['ts_dt']>=ds)&(candles['ts_dt']<=r['ts_dt'])]
    tok = tv[tv['ts_dt']<te]; lon = tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<ns)]
    prev_day_data = state.get('_prev_day_data')
    def add_sig(sn, d, e):
        if sn in OPEN_STRATS and sn in STRATS:
            signals.append({'strat': sn, 'dir': d})
    detect_all(candles, ci, r, r['ts_dt'], today, hour, atr, trig, tv, tok, lon, prev_day_data, add_sig)
    return signals

def detect_close_strats(candles, state, atr, candle_time, today):
    signals = []
    trig = state.setdefault('_triggered_close', {})
    hour = candle_time.hour + candle_time.minute / 60.0
    r = candles.iloc[-1]
    ds = pd.Timestamp(today.year,today.month,today.day,0,0,tz='UTC')
    te = pd.Timestamp(today.year,today.month,today.day,6,0,tz='UTC')
    ls = pd.Timestamp(today.year,today.month,today.day,8,0,tz='UTC')
    ns = pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC')
    tv = candles[(candles['ts_dt']>=ds)&(candles['ts_dt']<=candle_time)]
    tok = tv[tv['ts_dt']<te]; lon = tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<ns)]
    prev_day_data = state.get('_prev_day_data')
    def add_sig(sn, d, e):
        if sn in CLOSE_STRATS and sn in STRATS:
            signals.append({'strat': sn, 'dir': d})
    detect_all(candles, len(candles)-1, r, r['ts_dt'], today, hour, atr, trig, tv, tok, lon, prev_day_data, add_sig)
    return signals

# ── OPEN POSITION ────────────────────────────────────

def open_position(state, sig, atr):
    d = sig['dir']; sn = sig['strat']

    # Guard: check if strat already has an open position on MT5
    magic = MAGIC_MAP.get(sn)
    for p in mt5_our_positions():
        if p.magic == magic:
            log.info("SKIP {} — deja une position ouverte #{}".format(sn, p.ticket))
            return

    tick = mt5_tick()
    if not tick:
        log.warning("SKIP {} — no tick".format(sn)); return

    entry = tick['ask'] if d == 'long' else tick['bid']
    exit_cfg = STRAT_EXITS.get(sn, DEFAULT_EXIT)
    exit_type = exit_cfg[0]; sl_val = exit_cfg[1]
    stop = entry - sl_val * atr if d == 'long' else entry + sl_val * atr

    capital = mt5_balance()
    risk = capital * RISK_PCT
    sl_distance = abs(entry - stop)
    lots = mt5_lot_size(risk, sl_distance)

    # Risk warning
    sym = mt5.symbol_info(SYMBOL)
    actual_risk = lots * sym.trade_contract_size * sl_distance if sym else 0
    actual_risk_pct = actual_risk / capital * 100 if capital > 0 else 0
    if actual_risk_pct > RISK_PCT * 100 * 1.5:
        log.warning("RISK {} {:.1f}% > cible {:.1f}%".format(sn, actual_risk_pct, RISK_PCT*100))

    tp = 0.0
    if exit_type == 'TPSL':
        tp = entry + exit_cfg[2] * atr if d == 'long' else entry - exit_cfg[2] * atr

    result = mt5_send_order(sn, d, stop, tp, lots)
    if not result: return

    # Track trailing info if TRAIL type
    if exit_type == 'TRAIL':
        state['trail'][str(result['ticket'])] = {
            'strat': sn, 'dir': d, 'entry': result['price'],
            'best': result['price'], 'trail_active': False,
            'atr': atr, 'act_val': exit_cfg[2], 'trail_val': exit_cfg[3],
            'stop': stop,
        }

    log.info("    Cap=${:,.0f} Risk=${:.0f} ({:.1f}%) Spread={:.3f}".format(
        capital, risk, RISK_PCT*100, tick['spread']))

# ── TRAILING (on candle close) ───────────────────────

def manage_trailing(state, candles):
    last = candles.iloc[-1]
    # Get current MT5 positions to check which are still open
    mt5_pos = {p.ticket: p for p in mt5_our_positions()}

    closed_tickets = []
    for ticket_str, info in state['trail'].items():
        ticket = int(ticket_str)
        if ticket not in mt5_pos:
            closed_tickets.append(ticket_str)
            continue

        d = info['dir']; atr = info['atr']
        act_val = info['act_val']; trail_val = info['trail_val']

        # Update best on close
        px = last['close']
        if d == 'long' and px > info['best']: info['best'] = px
        if d == 'short' and px < info['best']: info['best'] = px

        # Activation
        if not info['trail_active']:
            fav = (info['best'] - info['entry']) if d == 'long' else (info['entry'] - info['best'])
            if fav >= act_val * atr:
                info['trail_active'] = True
                log.info("TRAIL ACTIVE {} {} best={:.2f} fav={:.1f}".format(
                    info['strat'], d, info['best'], fav))

        # Update SL
        if info['trail_active']:
            if d == 'long':
                new_sl = info['best'] - trail_val * atr
                if new_sl > info['stop']:
                    log.info("TRAIL {} SL {:.2f}->{:.2f} (best={:.2f})".format(
                        info['strat'], info['stop'], new_sl, info['best']))
                    if mt5_modify_sl(ticket, new_sl):
                        info['stop'] = new_sl
            else:
                new_sl = info['best'] + trail_val * atr
                if new_sl < info['stop']:
                    log.info("TRAIL {} SL {:.2f}->{:.2f} (best={:.2f})".format(
                        info['strat'], info['stop'], new_sl, info['best']))
                    if mt5_modify_sl(ticket, new_sl):
                        info['stop'] = new_sl

    # Clean closed trail entries
    for t in closed_tickets:
        sn = state['trail'][t].get('strat', '?')
        log.info("TRAIL cleanup #{} {} (position fermee)".format(t, sn))
        del state['trail'][t]

# ── MAIN ─────────────────────────────────────────────

def main():
    if not mt5_init():
        log.error("MT5 init failed. Arret."); return

    if args.reset:
        state = reset_state()
    else:
        state = load_state()

    log.info("=== {} LIVE{} === {} strats @ {:.1f}% === {}".format(
        BROKER, " [DRY]" if DRY_RUN else "", len(STRATS), RISK_PCT*100, ','.join(STRATS)))

    # Show magic numbers
    for sn in STRATS:
        log.info("  {} magic={}".format(sn, MAGIC_MAP.get(sn)))

    our_pos = mt5_our_positions()
    log.info("MT5 positions: {} | Balance: ${:,.2f}".format(len(our_pos), mt5_balance()))
    for p in our_pos:
        sn = MAGIC_REVERSE.get(p.magic, '?')
        log.info("  #{} {} {} {:.2f}lots entry={:.2f} sl={:.2f} tp={:.2f} pnl=${:+,.2f}".format(
            p.ticket, sn, 'LONG' if p.type == 0 else 'SHORT',
            p.volume, p.price_open, p.sl, p.tp, p.profit))
        # Re-mark as triggered so we don't re-detect
        if sn in OPEN_STRATS:
            state.setdefault('_triggered_open', {})[sn] = True
        elif sn != '?':
            state.setdefault('_triggered_close', {})[sn] = True

    conn = get_conn_autocommit()
    ci = get_recent_candles(conn, 1)
    if len(ci) > 0:
        last_candle_ts = int(ci.iloc[-1]['ts'])
        log.info("Calage: {}".format(ci.iloc[-1]['ts_dt']))
    else:
        last_candle_ts = 0

    while True:
        try:
            # Reconnect
            try: conn.isolation_level
            except Exception:
                log.warning("Reconnexion DB...")
                try: conn.close()
                except: pass
                conn = get_conn_autocommit()
            if not mt5.terminal_info():
                log.warning("MT5 reconnexion...")
                mt5_init()

            candles = get_recent_candles(conn, 1500)
            if len(candles) == 0: time.sleep(CHECK_INTERVAL); continue
            candles = compute_indicators(candles)

            current_ts = int(candles.iloc[-1]['ts'])
            candle_time = candles.iloc[-1]['ts_dt'].to_pydatetime()
            today = candle_time.date()

            cache = ensure_daily_cache(state, conn, candles, today)
            if not cache['atr'] or cache['atr'] == 0: time.sleep(CHECK_INTERVAL); continue
            atr = cache['atr']

            # Day reset
            if state.get('_prev_day_date') != str(today):
                yc = candles[candles['date'] < today]
                if len(yc) > 0:
                    last_day = yc['date'].iloc[-1]; dc = yc[yc['date']==last_day]
                    state['_prev_day_data'] = {'open':float(dc.iloc[0]['open']),'close':float(dc.iloc[-1]['close']),
                                               'high':float(dc['high'].max()),'low':float(dc['low'].min()),
                                               'range':float(dc['high'].max()-dc['low'].min())}
                state['_prev_day_date'] = str(today)
                state['_triggered_open'] = {}
                state['_triggered_close'] = {}
                log.info("Reset triggers {}".format(today))

            # Conflict check from MT5
            our_pos = mt5_our_positions()
            open_dirs = set()
            for p in our_pos:
                open_dirs.add('long' if p.type == 0 else 'short')

            # Open strats: every poll
            now_utc = datetime.now(timezone.utc)
            for sig in detect_open_strats(candles, state, atr, now_utc, today):
                if sig['dir'] == 'long' and 'short' in open_dirs:
                    log.info("SKIP {} — conflit short".format(sig['strat'])); continue
                if sig['dir'] == 'short' and 'long' in open_dirs:
                    log.info("SKIP {} — conflit long".format(sig['strat'])); continue
                open_position(state, sig, atr)
                open_dirs.add(sig['dir'])

            is_new = current_ts != last_candle_ts
            if not is_new:
                time.sleep(CHECK_INTERVAL); continue

            # Heartbeat
            bal = mt5_balance()
            log.info("~ {} | C={:.2f} | ATR={:.2f} | {}pos | ${:,.0f}".format(
                candle_time.strftime("%H:%M"), candles.iloc[-1]['close'],
                atr, len(our_pos), bal))

            # Trailing
            if state['trail']:
                manage_trailing(state, candles)

            last_candle_ts = current_ts; state['last_candle_ts'] = current_ts

            # Close strats: on candle close
            our_pos = mt5_our_positions()
            open_dirs = set()
            for p in our_pos:
                open_dirs.add('long' if p.type == 0 else 'short')

            for sig in detect_close_strats(candles, state, atr, candle_time, today):
                if sig['dir'] == 'long' and 'short' in open_dirs:
                    log.info("SKIP {} — conflit short".format(sig['strat'])); continue
                if sig['dir'] == 'short' and 'long' in open_dirs:
                    log.info("SKIP {} — conflit long".format(sig['strat'])); continue
                open_position(state, sig, atr)
                open_dirs.add(sig['dir'])

            save_state(state)

        except KeyboardInterrupt:
            log.info("Arret."); save_state(state); break
        except Exception as e:
            log.error("Erreur: {}".format(e))
            import traceback; traceback.print_exc(); time.sleep(30)

        time.sleep(CHECK_INTERVAL)

    mt5.shutdown(); conn.close()

if __name__ == '__main__':
    main()
