"""
Live Trading MT5 — multi-compte, multi-instrument.
Usage:
  python live_mt5.py icm                    → ICM tous instruments
  python live_mt5.py ftmo                   → FTMO tous instruments
  python live_mt5.py 5ers                   → 5ers tous instruments
  python live_mt5.py 5ers --reset           → reset state

Un seul process par broker. Gere tous les instruments configures.
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
from strats import STRAT_NAMES, STRAT_SESSION, detect_all, make_magic
from strat_exits import STRAT_EXITS, DEFAULT_EXIT
from backtest_engine import load_data, prev_trading_day, OPEN_STRATS, _make_day_data

# ── CONFIG ────────────────────────────────────────────

parser = argparse.ArgumentParser(description='Live MT5 trading')
parser.add_argument('account', choices=['ftmo','5ers','pepperstone'])
parser.add_argument('--reset', action='store_true', help='Reset state')
parser.add_argument('--tf', default='5m', help='Timeframe: 5m or 15m')
args = parser.parse_args()
_account = args.account

import importlib
cfg_mod = importlib.import_module(f'config_{_account}')
BROKER = cfg_mod.BROKER
INSTRUMENTS = cfg_mod.INSTRUMENTS
CHECK_INTERVAL = 1

with open(os.path.join(os.path.dirname(__file__), 'broker_offsets.json')) as f:
    _offsets = json.load(f)
BROKER_OFFSET = timedelta(hours=_offsets[_account])

os.makedirs(f'data/{_account}', exist_ok=True)
STATE_FILE = f"data/{_account}/live_mt5.json"

# OPEN_STRATS importe depuis backtest_engine (source unique)

# ── MAGIC NUMBERS ────────────────────────────────────

def _magic(symbol, strat):
    return make_magic(_account, symbol, strat)

# Build reverse lookup
ALL_MAGICS = {}  # magic -> (symbol, strat)
for sym, icfg in INSTRUMENTS.items():
    for sn in icfg['portfolio']:
        m = _magic(sym, sn)
        ALL_MAGICS[m] = (sym, sn)
ALL_MAGIC_SET = set(ALL_MAGICS.keys())

# ── LOGGING ──────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(),
              logging.FileHandler(f'data/{_account}/live_mt5.log', encoding='utf-8')])
log = logging.getLogger('mt5')

# ── MT5 ──────────────────────────────────────────────

def mt5_init():
    if not mt5.initialize():
        log.error("MT5 init failed: {}".format(mt5.last_error())); return False
    info = mt5.account_info()
    if not info: log.error("MT5 account_info failed"); return False
    if not info.trade_allowed:
        log.error("Trading DESACTIVE!"); return False
    log.info("MT5: {} {} bal=${:,.2f}".format(info.company, info.server, info.balance))
    for sym in INSTRUMENTS:
        si = mt5.symbol_info(sym)
        if si:
            if not si.visible: mt5.symbol_select(sym, True)
            log.info("  {}: lot_min={} step={} contract={}".format(sym, si.volume_min, si.volume_step, si.trade_contract_size))
        else:
            log.warning("  {} NON TROUVE sur MT5".format(sym))
    return True

def mt5_balance():
    info = mt5.account_info()
    return info.balance if info else 0

def mt5_tick(symbol):
    t = mt5.symbol_info_tick(symbol)
    return {'bid': t.bid, 'ask': t.ask, 'spread': t.ask - t.bid} if t else None

def mt5_our_positions(symbol=None):
    if symbol:
        positions = mt5.positions_get(symbol=symbol) or []
    else:
        positions = mt5.positions_get() or []
    return [p for p in positions if p.magic in ALL_MAGIC_SET]

def mt5_lot_size(symbol, risk_amount, entry, stop, direction):
    sym = mt5.symbol_info(symbol)
    if not sym or entry == stop: return sym.volume_min if sym else 0.01
    order_type = mt5.ORDER_TYPE_BUY if direction == 'long' else mt5.ORDER_TYPE_SELL
    try:
        loss_per_lot = mt5.order_calc_profit(order_type, symbol, 1.0, float(entry), float(stop))
    except Exception:
        loss_per_lot = None
    if loss_per_lot is None:
        log.warning("LOT {} — order_calc_profit failed, fallback".format(symbol))
        loss_per_lot = abs(entry - stop) * sym.trade_contract_size
    else:
        loss_per_lot = abs(loss_per_lot)
    if loss_per_lot == 0: return sym.volume_min
    lots = risk_amount / loss_per_lot
    lots = max(sym.volume_min, round(lots / sym.volume_step) * sym.volume_step)
    lots = min(lots, sym.volume_max)
    return round(lots, 2)

def mt5_send_order(symbol, strat, direction, sl, tp, lots):
    sym = mt5.symbol_info(symbol)
    if not sym: return None
    order_type = mt5.ORDER_TYPE_BUY if direction == 'long' else mt5.ORDER_TYPE_SELL
    price = sym.ask if direction == 'long' else sym.bid
    magic = _magic(symbol, strat)
    request = {
        'action': mt5.TRADE_ACTION_DEAL, 'symbol': symbol, 'volume': lots,
        'type': order_type, 'price': price,
        'sl': round(sl, sym.digits), 'tp': round(tp, sym.digits) if tp else 0.0,
        'deviation': 20, 'magic': magic, 'comment': strat,
        'type_time': mt5.ORDER_TIME_GTC,
    }
    log.info(">>> {} {} {} {} {:.2f}lots @ {:.2f} SL={:.2f} TP={:.2f} <<<".format(
        'BUY' if direction == 'long' else 'SELL', symbol, strat, direction.upper(),
        lots, price, sl, tp or 0))
    result = mt5.order_send(request)
    if not result:
        log.error("    order_send None: {}".format(mt5.last_error())); return None
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        log.error("    ECHEC: {} {}".format(result.retcode, result.comment)); return None
    fill_price = result.price if result.price > 0 else price  # MT5 quirk: certains brokers renvoient price=0
    log.info("    OK #{} fill={:.2f}".format(result.order, fill_price))
    return {'ticket': result.order, 'price': fill_price, 'volume': result.volume}

def mt5_modify_sl(ticket, new_sl, symbol):
    sym = mt5.symbol_info(symbol)
    if not sym: return False
    positions = mt5.positions_get(ticket=ticket)
    if not positions: return False
    request = {
        'action': mt5.TRADE_ACTION_SLTP, 'symbol': symbol, 'position': ticket,
        'sl': round(new_sl, sym.digits), 'tp': positions[0].tp,
    }
    result = mt5.order_send(request)
    if result and result.retcode == mt5.TRADE_RETCODE_DONE: return True
    log.error("    Modify SL #{} failed: {}".format(ticket, result.retcode if result else '?'))
    return False

def mt5_close_position(ticket, symbol):
    sym = mt5.symbol_info(symbol)
    positions = mt5.positions_get(ticket=ticket)
    if not sym or not positions: return False
    p = positions[0]
    order_type = mt5.ORDER_TYPE_SELL if p.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
    price = sym.bid if p.type == mt5.POSITION_TYPE_BUY else sym.ask
    req = {
        'action': mt5.TRADE_ACTION_DEAL, 'symbol': symbol, 'volume': p.volume,
        'type': order_type, 'price': price, 'position': ticket,
        'deviation': 20, 'magic': p.magic, 'comment': 'TRAIL_VIOLATED',
        'type_time': mt5.ORDER_TIME_GTC,
    }
    r = mt5.order_send(req)
    if r and r.retcode == mt5.TRADE_RETCODE_DONE: return True
    log.error("    Close #{} failed: {}".format(ticket, r.retcode if r else '?'))
    return False

# ── DB ────────────────────────────────────────────────

def get_conn_autocommit():
    conn = get_conn(); conn.autocommit = True; return conn

def get_recent_candles(conn, symbol, n=1500, tf=None):
    import re
    if tf is None: tf = args.tf
    table = f"candles_mt5_{re.sub(r'[^a-z0-9]+', '_', symbol.lower()).strip('_')}_{tf}"
    cur = conn.cursor()
    cur.execute(f"SELECT ts, open, high, low, close FROM {table} ORDER BY ts DESC LIMIT %s", (n,))
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

# ── STATE ─────────────────────────────────────────────

def new_state():
    return {'broker': BROKER, 'instruments': list(INSTRUMENTS.keys()),
            'daily_cache': {}, 'trail': {}, 'be_tp': {},
            'closed_this_bar': {}, 'closed_prev_bar': {}, '_tracked_tickets': {},
            'per_symbol': {sym: {'_triggered_open': {}, '_triggered_close': {},
                                  '_prev_day_data': None, '_prev2_day_data': None,
                                  '_prev_day_date': None,
                                  'last_candle_ts': 0} for sym in INSTRUMENTS}}

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
            state.setdefault('trail', {})
            state.setdefault('be_tp', {})
            state.setdefault('per_symbol', {})
            # Nouvelles cles pour mutex LONG/SHORT aligne sur BT (tracking interne)
            state.setdefault('closed_this_bar', {})
            state.setdefault('closed_prev_bar', {})
            state.setdefault('_tracked_tickets', {})
            # Conversion lists -> sets au load (JSON ne supporte pas sets)
            for key in ('closed_this_bar', 'closed_prev_bar'):
                for sym, v in list(state[key].items()):
                    if isinstance(v, list):
                        state[key][sym] = set(v)
            for sym in INSTRUMENTS:
                state['per_symbol'].setdefault(sym, {
                    '_triggered_open': {}, '_triggered_close': {},
                    '_prev_day_data': None, '_prev2_day_data': None,
                    '_prev_day_date': None,
                    'last_candle_ts': 0})
            return state
    return new_state()

def _state_for_json(state):
    """Convertit les sets en lists pour serialisation JSON."""
    out = {}
    for k, v in state.items():
        if k in ('closed_this_bar', 'closed_prev_bar'):
            out[k] = {sym: list(dirs) if isinstance(dirs, set) else dirs for sym, dirs in v.items()}
        else:
            out[k] = v
    return out

def save_state(state):
    with open(STATE_FILE, 'w') as f: json.dump(_state_for_json(state), f, indent=2, default=str)

def reset_state():
    if os.path.exists(STATE_FILE): os.remove(STATE_FILE)
    state = new_state()
    save_state(state)
    log.info("RESET {} — {} instruments".format(BROKER, len(INSTRUMENTS)))
    return state

# ── SIGNAL DETECTION ─────────────────────────────────

def detect_open_strats(candles, sym_state, atr, candle_time_utc, today, portfolio):
    if len(candles) < 2: return []
    signals = []
    trig = sym_state.setdefault('_triggered_open', {})
    hour = candle_time_utc.hour + candle_time_utc.minute / 60.0  # UTC from candle ts_dt
    r = candles.iloc[-2]; ci = len(candles) - 2
    ds = pd.Timestamp(today.year,today.month,today.day,0,0,tz='UTC')
    te = pd.Timestamp(today.year,today.month,today.day,6,0,tz='UTC')
    ls = pd.Timestamp(today.year,today.month,today.day,8,0,tz='UTC')
    ns = pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC')
    tv = candles[(candles['ts_dt']>=ds)&(candles['ts_dt']<=r['ts_dt'])]
    tok = tv[tv['ts_dt']<te]; lon = tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<ns)]
    prev_day_data = sym_state.get('_prev_day_data')
    prev2_day_data = sym_state.get('_prev2_day_data')
    def add_sig(sn, d, e):
        if sn in OPEN_STRATS and sn in portfolio:
            signals.append({'strat': sn, 'dir': d, 'entry': e})
    detect_all(candles, ci, r, r['ts_dt'], today, hour, atr, trig, tv, tok, lon, prev_day_data, add_sig, prev2_day_data=prev2_day_data)
    return signals

def detect_close_strats(candles, sym_state, atr, candle_time_utc, today, portfolio):
    signals = []
    trig = sym_state.setdefault('_triggered_close', {})
    hour = candle_time_utc.hour + candle_time_utc.minute / 60.0  # UTC from candle ts_dt
    r = candles.iloc[-1]
    ds = pd.Timestamp(today.year,today.month,today.day,0,0,tz='UTC')
    te = pd.Timestamp(today.year,today.month,today.day,6,0,tz='UTC')
    ls = pd.Timestamp(today.year,today.month,today.day,8,0,tz='UTC')
    ns = pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC')
    tv = candles[(candles['ts_dt']>=ds)&(candles['ts_dt']<=candle_time_utc)]
    tok = tv[tv['ts_dt']<te]; lon = tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<ns)]
    prev_day_data = sym_state.get('_prev_day_data')
    prev2_day_data = sym_state.get('_prev2_day_data')
    close_strats = [s for s in portfolio if s not in OPEN_STRATS]
    def add_sig(sn, d, e):
        if sn in close_strats:
            signals.append({'strat': sn, 'dir': d, 'entry': e})
    detect_all(candles, len(candles)-1, r, r['ts_dt'], today, hour, atr, trig, tv, tok, lon, prev_day_data, add_sig, prev2_day_data=prev2_day_data)
    return signals

# ── OPEN POSITION ────────────────────────────────────

def open_position(state, symbol, sig, atr, risk_pct):
    d = sig['dir']; sn = sig['strat']
    signal_close = sig['entry']  # close de la bougie signal (= entry theorique BT)
    magic = _magic(symbol, sn)
    for p in mt5_our_positions(symbol):
        if p.magic == magic:
            log.info("SKIP {} {} — deja ouvert #{}".format(symbol, sn, p.ticket)); return
    capital = mt5_balance()
    if capital <= 0:
        log.warning("SKIP {} — balance zero".format(sn)); return
    tick = mt5_tick(symbol)
    if not tick:
        log.warning("SKIP {} {} — no tick".format(symbol, sn)); return
    entry = tick['ask'] if d == 'long' else tick['bid']
    sym_exits = STRAT_EXITS.get((_account, symbol), {})
    exit_cfg = sym_exits.get(sn, DEFAULT_EXIT)
    exit_type = exit_cfg[0]; sl_val = exit_cfg[1]
    # SL/TP bases sur signal_close (= meme que BT), pas sur fill price
    stop = signal_close - sl_val * atr if d == 'long' else signal_close + sl_val * atr
    risk = capital * risk_pct
    lots = mt5_lot_size(symbol, risk, entry, stop, d)
    tp = 0.0
    if exit_type == 'TPSL':
        tp = signal_close + exit_cfg[2] * atr if d == 'long' else signal_close - exit_cfg[2] * atr
    elif exit_type == 'BE_TP':
        # p2=be_act (R), p3=tp (R). TP envoye a l'ordre, SL bougera a BE quand be_act atteint.
        tp = signal_close + exit_cfg[3] * atr if d == 'long' else signal_close - exit_cfg[3] * atr
    result = mt5_send_order(symbol, sn, d, stop, tp, lots)
    if not result: return
    if exit_type == 'TRAIL':
        state['trail'][str(result['ticket'])] = {
            'symbol': symbol, 'strat': sn, 'dir': d, 'entry': signal_close,
            'best': signal_close, 'trail_active': False,
            'atr': atr, 'act_val': exit_cfg[2], 'trail_val': exit_cfg[3], 'stop': stop,
        }
    elif exit_type == 'BE_TP':
        state['be_tp'][str(result['ticket'])] = {
            'symbol': symbol, 'strat': sn, 'dir': d, 'entry': signal_close,
            'be_active': False,
            'atr': atr, 'be_val': exit_cfg[2], 'tp_val': exit_cfg[3], 'stop': stop,
        }
    log.info("    Cap=${:,.0f} Risk=${:.0f} ({:.1f}%)".format(capital, risk, risk_pct*100))
    save_state(state)

# ── TRAILING ─────────────────────────────────────────

def manage_trailing(state, symbol, candles):
    last = candles.iloc[-1]
    mt5_pos = {p.ticket: p for p in mt5_our_positions(symbol)}
    closed_tickets = []
    for ticket_str, info in state['trail'].items():
        if info.get('symbol') != symbol: continue
        ticket = int(ticket_str)
        if ticket not in mt5_pos:
            closed_tickets.append(ticket_str); continue
        d = info['dir']; atr = info['atr']
        act_val = info['act_val']; trail_val = info['trail_val']
        px = last['close']
        if d == 'long' and px > info['best']: info['best'] = px
        if d == 'short' and px < info['best']: info['best'] = px
        if not info['trail_active']:
            fav = (info['best'] - info['entry']) if d == 'long' else (info['entry'] - info['best'])
            if fav >= act_val * atr:
                info['trail_active'] = True
                log.info("TRAIL ACTIVE {} {} {} best={:.2f}".format(symbol, info['strat'], d, info['best']))
        if info['trail_active']:
            if d == 'long':
                new_sl = info['best'] - trail_val * atr
                if new_sl > info['stop']:
                    if px < new_sl:
                        log.info("TRAIL VIOLATED {} {} long close @ {:.2f} (new_sl {:.2f} > px)".format(
                            symbol, info['strat'], px, new_sl))
                        if mt5_close_position(ticket, symbol):
                            closed_tickets.append(ticket_str)
                    else:
                        log.info("TRAIL {} {} SL {:.2f}->{:.2f}".format(symbol, info['strat'], info['stop'], new_sl))
                        if mt5_modify_sl(ticket, new_sl, symbol): info['stop'] = new_sl
            else:
                new_sl = info['best'] + trail_val * atr
                if new_sl < info['stop']:
                    if px > new_sl:
                        log.info("TRAIL VIOLATED {} {} short close @ {:.2f} (new_sl {:.2f} < px)".format(
                            symbol, info['strat'], px, new_sl))
                        if mt5_close_position(ticket, symbol):
                            closed_tickets.append(ticket_str)
                    else:
                        log.info("TRAIL {} {} SL {:.2f}->{:.2f}".format(symbol, info['strat'], info['stop'], new_sl))
                        if mt5_modify_sl(ticket, new_sl, symbol): info['stop'] = new_sl
    for t in closed_tickets:
        sn = state['trail'][t].get('strat', '?')
        log.info("TRAIL cleanup #{} {} {} (fermee)".format(t, symbol, sn))
        del state['trail'][t]

# ── BE_TP MANAGEMENT ─────────────────────────────────

def manage_be_tp(state, symbol, candles):
    """Move SL to break-even quand prix atteint be_val*atr favorable. TP envoye a l'ordre."""
    last = candles.iloc[-1]
    mt5_pos = {p.ticket: p for p in mt5_our_positions(symbol)}
    closed_tickets = []
    for ticket_str, info in state['be_tp'].items():
        if info.get('symbol') != symbol: continue
        ticket = int(ticket_str)
        if ticket not in mt5_pos:
            closed_tickets.append(ticket_str); continue
        if info['be_active']: continue  # deja move a BE
        d = info['dir']; atr = info['atr']; be_val = info['be_val']
        px = last['close']
        fav = (px - info['entry']) if d == 'long' else (info['entry'] - px)
        if fav >= be_val * atr:
            new_sl = info['entry']  # move SL a entry = break-even
            log.info("BE_TP ACTIVE {} {} {} SL {:.2f}->{:.2f} (BE)".format(
                symbol, info['strat'], d, info['stop'], new_sl))
            if mt5_modify_sl(ticket, new_sl, symbol):
                info['stop'] = new_sl; info['be_active'] = True
    for t in closed_tickets:
        sn = state['be_tp'][t].get('strat', '?')
        log.info("BE_TP cleanup #{} {} {} (fermee)".format(t, symbol, sn))
        del state['be_tp'][t]

# ── MAIN ─────────────────────────────────────────────

def main():
    if not mt5_init(): log.error("MT5 init failed."); return

    if args.reset:
        def _is_managed(p):
            sym, sn = ALL_MAGICS.get(p.magic, ('',''))
            et = STRAT_EXITS.get((_account, sym), {}).get(sn, DEFAULT_EXIT)[0]
            return et in ('TRAIL', 'BE_TP')
        open_trail = [p for p in mt5_our_positions() if _is_managed(p)]
        if open_trail:
            log.warning("!!! RESET avec {} TRAIL ouvertes !!!".format(len(open_trail)))
        state = reset_state()
    else:
        state = load_state()

    syms = list(INSTRUMENTS.keys())
    log.info("=== {} LIVE === {} instruments: {} ===".format(BROKER, len(syms), ', '.join(syms)))
    for sym in syms:
        icfg = INSTRUMENTS[sym]
        log.info("  {} — {} strats @ {:.2f}%: {}".format(
            sym, len(icfg['portfolio']), icfg['risk_pct']*100, ', '.join(icfg['portfolio'])))

    # Rebuild triggers from MT5 positions
    # Get current date from DB candles (UTC), not system clock
    _conn_tmp = get_conn_autocommit()
    _last_candle = get_recent_candles(_conn_tmp, syms[0] if syms else 'XAUUSD', 1)
    _conn_tmp.close()
    _db_today = _last_candle.iloc[-1]['ts_dt'].date() if len(_last_candle) > 0 else datetime.now(timezone.utc).date()
    for p in mt5_our_positions():
        sym_sn = ALL_MAGICS.get(p.magic)
        if not sym_sn: continue
        sym, sn = sym_sn
        pos_date = (datetime.fromtimestamp(p.time, tz=timezone.utc) - BROKER_OFFSET).date()
        if pos_date == _db_today:
            ss = state['per_symbol'].get(sym, {})
            if sn in OPEN_STRATS: ss.setdefault('_triggered_open', {})[sn] = True
            else: ss.setdefault('_triggered_close', {})[sn] = True
        d = 'LONG' if p.type == 0 else 'SHORT'
        log.info("  MT5 #{} {} {} {} {:.2f}lots pnl={:+.2f}".format(p.ticket, sym, sn, d, p.volume, p.profit))

    conn = get_conn_autocommit()
    _atr_cache = {}  # sym -> {'date', 'atr', 'trading_days', 'daily_atr', 'global_atr'}

    # Calage per symbol
    last_ts = {}
    for sym in syms:
        ci = get_recent_candles(conn, sym, 1)
        if len(ci) > 0:
            last_ts[sym] = int(ci.iloc[-1]['ts'])
        else:
            last_ts[sym] = 0
    log.info("Calage done.")

    while True:
        try:
            try: conn.isolation_level
            except Exception:
                log.warning("Reconnexion DB...")
                try: conn.close()
                except: pass
                conn = get_conn_autocommit()
            if not mt5.terminal_info():
                log.warning("MT5 reconnexion..."); mt5_init()

            for sym in syms:
                icfg = INSTRUMENTS[sym]
                portfolio = icfg['portfolio']
                risk_pct = icfg['risk_pct']
                ss = state['per_symbol'][sym]

                if not portfolio: continue

                # Candles recentes (rapide) + indicateurs
                candles = get_recent_candles(conn, sym, 500)
                if len(candles) == 0: continue
                from strats import compute_indicators
                candles = compute_indicators(candles)

                current_ts = int(candles.iloc[-1]['ts'])
                # REGLE: seule source de temps = ts_dt UTC des candles en DB
                candle_time_utc = candles.iloc[-1]['ts_dt'].to_pydatetime()
                today = candle_time_utc.date()

                # ATR via backtest_engine (supporte 5m et 15m)
                if sym not in _atr_cache or _atr_cache[sym]['date'] != str(today):
                    from backtest_engine import _load_candles_raw, _compute_atr_from_df, _get_trading_days_from_df, prev_trading_day as _ptd
                    _full = _load_candles_raw(conn, sym, tf=args.tf, limit=1500)
                    _da, _ga = _compute_atr_from_df(_full)
                    _td = _get_trading_days_from_df(_full)
                    _pd = _ptd(today, _td)
                    _atr_val = _da.get(_pd, _ga) if _pd else _ga
                    _atr_cache[sym] = {'date': str(today), 'atr': _atr_val}
                atr = _atr_cache[sym]['atr']
                if not atr or atr == 0: continue

                # Day reset
                if ss.get('_prev_day_date') != str(today):
                    yc = candles[candles['date'] < today]
                    if len(yc) > 0:
                        ld = yc['date'].iloc[-1]; dc = yc[yc['date'] == ld]
                        ss['_prev_day_data'] = _make_day_data(dc)
                        yc2 = yc[yc['date'] < ld]
                        if len(yc2) > 0:
                            ld2 = yc2['date'].iloc[-1]; dc2 = yc2[yc2['date'] == ld2]
                            ss['_prev2_day_data'] = _make_day_data(dc2)
                        else:
                            ss['_prev2_day_data'] = None
                    ss['_prev_day_date'] = str(today)
                    ss['_triggered_open'] = {}
                    ss['_triggered_close'] = {}

                # Conflict filter retire 2026-04-29: SHORT et LONG simultanes autorises
                our_pos = mt5_our_positions(sym)

                is_new = current_ts != last_ts.get(sym, 0)
                if not is_new: continue

                # Heartbeat
                bal = mt5_balance()
                log.info("~ {} {} C={:.2f} ATR={:.2f} {}pos ${:,.0f}".format(
                    sym, candle_time_utc.strftime("%H:%M"), candles.iloc[-1]['close'],
                    atr, len(our_pos), bal))

                # Trailing
                trail_syms = [t for t, info in state['trail'].items() if info.get('symbol') == sym]
                if trail_syms:
                    manage_trailing(state, sym, candles)

                # BE_TP (move SL to break-even)
                be_tp_syms = [t for t, info in state['be_tp'].items() if info.get('symbol') == sym]
                if be_tp_syms:
                    manage_be_tp(state, sym, candles)

                last_ts[sym] = current_ts

                # Open new positions sur signaux detectes (sans filtre conflit)
                for sig in sorted(detect_close_strats(candles, ss, atr, candle_time_utc, today, portfolio), key=lambda s: s['strat']):
                    open_position(state, sym, sig, atr, risk_pct)

            save_state(state)

        except KeyboardInterrupt:
            log.info("Arret."); save_state(state); break
        except Exception as e:
            log.error("Erreur: {}".format(e))
            import traceback; traceback.print_exc(); time.sleep(30)

        time.sleep(CHECK_INTERVAL)

    conn.close()

if __name__ == '__main__':
    try:
        main()
    finally:
        mt5.shutdown()
