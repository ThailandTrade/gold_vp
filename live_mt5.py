"""
Live Trading MT5 — multi-compte, vrais ordres.
Usage:
  python live_mt5.py icm                        → ICM
  python live_mt5.py ftmo                       → FTMO
  python live_mt5.py 5ers                       → 5ers
  python live_mt5.py icm --dry                  → dry run (log sans envoyer)
  python live_mt5.py ftmo -c 200000 --reset     → reset + capital override

Identique a live_paper.py mais envoie de vrais ordres MT5.
- Close strats: detection sur DB (bougie fermee)
- Open strats: detection sur bougie precedente, entry au tick MT5
- TPSL: SL + TP poses sur l'ordre MT5
- TRAIL: SL initial, puis ModifyPosition a chaque bougie fermee
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
parser.add_argument('-c', '--capital', type=float, default=None, help='Capital override')
parser.add_argument('-r', '--risk', type=float, default=None, help='Risk %% par trade')
parser.add_argument('--reset', action='store_true', help='Reset state')
parser.add_argument('--symbol', default='XAUUSD', help='MT5 symbol (default XAUUSD)')
parser.add_argument('--dry', action='store_true', help='Dry run (log orders but dont send)')
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
    log.info("MT5 connecte: {} {} balance=${:,.2f} equity=${:,.2f}".format(
        info.company, info.server, info.balance, info.equity))
    sym = mt5.symbol_info(SYMBOL)
    if sym is None:
        log.error("Symbole {} non trouve".format(SYMBOL))
        return False
    if not sym.visible:
        mt5.symbol_select(SYMBOL, True)
    log.info("Symbole {}: lot_min={} lot_step={} lot_max={} digits={}".format(
        SYMBOL, sym.volume_min, sym.volume_step, sym.volume_max, sym.digits))
    return True

def mt5_get_balance():
    info = mt5.account_info()
    return info.balance if info else 0

def mt5_get_tick():
    tick = mt5.symbol_info_tick(SYMBOL)
    if tick:
        return {'bid': tick.bid, 'ask': tick.ask, 'spread': tick.ask - tick.bid}
    return None

def mt5_get_positions():
    positions = mt5.positions_get(symbol=SYMBOL)
    return list(positions) if positions else []

def mt5_lot_size(risk_amount, sl_distance):
    sym = mt5.symbol_info(SYMBOL)
    if not sym or sl_distance <= 0: return sym.volume_min if sym else 0.01
    pos_oz = risk_amount / sl_distance
    lots = pos_oz / sym.trade_contract_size  # contract_size = 100 pour gold
    lots = max(sym.volume_min, round(lots / sym.volume_step) * sym.volume_step)
    lots = min(lots, sym.volume_max)
    return round(lots, 2)

def mt5_open_order(strat, direction, sl, tp, lots):
    sym = mt5.symbol_info(SYMBOL)
    if not sym: return None

    order_type = mt5.ORDER_TYPE_BUY if direction == 'long' else mt5.ORDER_TYPE_SELL
    price = sym.ask if direction == 'long' else sym.bid

    request = {
        'action': mt5.TRADE_ACTION_DEAL,
        'symbol': SYMBOL,
        'volume': lots,
        'type': order_type,
        'price': price,
        'sl': round(sl, sym.digits),
        'tp': round(tp, sym.digits) if tp else 0.0,
        'deviation': 20,
        'magic': 240325,
        'comment': 'VP_{}'.format(strat),
        'type_time': mt5.ORDER_TIME_GTC,
    }

    log.info(">>> MT5 {} {} {} lots @ {:.2f} SL={:.2f} TP={:.2f} <<<".format(
        'BUY' if direction == 'long' else 'SELL', strat, lots, price, sl, tp or 0))

    if DRY_RUN:
        log.info("    [DRY RUN] Ordre non envoye")
        return {'ticket': int(time.time()), 'price': price, 'volume': lots}

    result = mt5.order_send(request)
    if result is None:
        log.error("    order_send None: {}".format(mt5.last_error()))
        return None
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        log.error("    order_send failed: {} {}".format(result.retcode, result.comment))
        return None

    log.info("    OK ticket={} fill={:.2f}".format(result.order, result.price))
    return {'ticket': result.order, 'price': result.price, 'volume': result.volume}

def mt5_modify_sl(ticket, new_sl):
    sym = mt5.symbol_info(SYMBOL)
    if not sym: return False
    positions = mt5.positions_get(ticket=ticket)
    if not positions: return False
    pos = positions[0]

    request = {
        'action': mt5.TRADE_ACTION_SLTP,
        'symbol': SYMBOL,
        'position': ticket,
        'sl': round(new_sl, sym.digits),
        'tp': pos.tp,
    }

    if DRY_RUN:
        log.info("    [DRY] Modify SL #{} -> {:.2f}".format(ticket, new_sl))
        return True

    result = mt5.order_send(request)
    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        return True
    log.error("    Modify SL failed: {}".format(result.retcode if result else mt5.last_error()))
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

# ── STATE ─────────────────────────────────────────────

def new_state(capital):
    return {'capital_initial': capital, 'broker': BROKER, 'risk_pct': RISK_PCT,
            'trades': [], 'positions': [],
            'daily_cache': {}, '_triggered_open': {}, '_triggered_close': {},
            '_prev_day_data': None, '_prev_day_date': None,
            'last_candle_ts': 0}

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f: return json.load(f)
    cap = args.capital or mt5_get_balance() or 1000.0
    return new_state(cap)

def save_state(state):
    with open(STATE_FILE, 'w') as f: json.dump(state, f, indent=2, default=str)

def reset_state():
    if os.path.exists(STATE_FILE): os.remove(STATE_FILE)
    cap = args.capital or mt5_get_balance() or 1000.0
    state = new_state(cap)
    save_state(state)
    log.info("RESET {} — ${:,.2f} @ {:.1f}% risk".format(BROKER, cap, RISK_PCT*100))
    return state

# ── DAILY CACHE ──────────────────────────────────────

def ensure_daily_cache(state, conn, candles_df, today):
    k = str(today)
    if k in state['daily_cache']: return state['daily_cache'][k]
    atr = get_yesterday_atr(candles_df, today)
    cache = {'atr': atr}
    state['daily_cache'] = {k: cache}
    log.info("Cache journalier {}: ATR={}".format(today, "{:.2f}".format(atr) if atr else "None"))
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
    d = sig['dir']
    tick = mt5_get_tick()
    if not tick:
        log.warning("SKIP {} — no tick".format(sig['strat'])); return

    entry = tick['ask'] if d == 'long' else tick['bid']
    exit_cfg = STRAT_EXITS.get(sig['strat'], DEFAULT_EXIT)
    exit_type = exit_cfg[0]; sl_val = exit_cfg[1]
    stop = entry - sl_val * atr if d == 'long' else entry + sl_val * atr

    capital = mt5_get_balance() or state.get('capital_initial', 1000)
    risk = capital * RISK_PCT
    sl_distance = abs(entry - stop)
    lots = mt5_lot_size(risk, sl_distance)

    actual_risk = lots * mt5.symbol_info(SYMBOL).trade_contract_size * sl_distance
    actual_risk_pct = actual_risk / capital * 100 if capital > 0 else 0
    if actual_risk_pct > RISK_PCT * 100 * 1.5:
        log.warning("RISK {} {:.1f}% > cible {:.1f}% (min lot)".format(
            sig['strat'], actual_risk_pct, RISK_PCT*100))

    tp = 0.0
    if exit_type == 'TPSL':
        tp_val = exit_cfg[2]
        tp = entry + tp_val * atr if d == 'long' else entry - tp_val * atr

    result = mt5_open_order(sig['strat'], d, stop, tp, lots)
    if not result: return

    state['positions'].append({
        'strat': sig['strat'], 'dir': d, 'entry': result['price'],
        'stop': stop, 'tp': tp, 'lots': result['volume'],
        'ticket': result['ticket'], 'exit_type': exit_type,
        'best': result['price'], 'trail_active': False,
        'trade_atr': atr, 'bars_held': 0,
        'entry_time': str(datetime.now(timezone.utc)),
        'sl_val': sl_val,
        'act_val': exit_cfg[2] if exit_type == 'TRAIL' else 0,
        'trail_val': exit_cfg[3] if exit_type == 'TRAIL' else 0,
    })
    log.info("    Risk=${:.2f} ({:.1f}%) Cap=${:,.2f} Spread={:.3f}".format(
        risk, RISK_PCT*100, capital, tick['spread']))

# ── MANAGE TRAILING ──────────────────────────────────

def manage_trailing(state, candles):
    last = candles.iloc[-1]
    for pos in state['positions']:
        if pos['exit_type'] != 'TRAIL': continue
        pos['bars_held'] = pos.get('bars_held', 0) + 1

        d = pos['dir']; atr = pos['trade_atr']
        act_val = pos['act_val']; trail_val = pos['trail_val']

        # Update best on CLOSE (like backtest)
        px = last['close']
        if d == 'long' and px > pos['best']: pos['best'] = px
        if d == 'short' and px < pos['best']: pos['best'] = px

        if not pos['trail_active']:
            fav = (pos['best'] - pos['entry']) if d == 'long' else (pos['entry'] - pos['best'])
            if fav >= act_val * atr:
                pos['trail_active'] = True
                log.info("TRAIL ACTIVE {} {} | best={:.2f} fav={:.2f}".format(
                    pos['strat'], d, pos['best'], fav))

        if pos['trail_active']:
            if d == 'long':
                new_sl = pos['best'] - trail_val * atr
                if new_sl > pos['stop']:
                    log.info("TRAIL {} SL {:.2f} -> {:.2f} (best={:.2f})".format(
                        pos['strat'], pos['stop'], new_sl, pos['best']))
                    if mt5_modify_sl(pos['ticket'], new_sl):
                        pos['stop'] = new_sl
            else:
                new_sl = pos['best'] + trail_val * atr
                if new_sl < pos['stop']:
                    log.info("TRAIL {} SL {:.2f} -> {:.2f} (best={:.2f})".format(
                        pos['strat'], pos['stop'], new_sl, pos['best']))
                    if mt5_modify_sl(pos['ticket'], new_sl):
                        pos['stop'] = new_sl

# ── SYNC WITH MT5 ───────────────────────────────────

def sync_positions(state):
    if DRY_RUN: return
    mt5_pos = mt5_get_positions()
    mt5_tickets = {p.ticket for p in mt5_pos}

    closed = []
    for pos in state['positions']:
        ticket = pos['ticket']
        if ticket not in mt5_tickets:
            log.info("CLOSED {} {} #{} (MT5 SL/TP)".format(pos['strat'], pos['dir'], ticket))
            deals = mt5.history_deals_get(position=ticket)
            pnl = sum(d.profit + d.commission + d.swap for d in deals) if deals else 0
            state['trades'].append({
                'strat': pos['strat'], 'dir': pos['dir'],
                'entry': pos['entry'], 'lots': pos['lots'],
                'pnl': pnl, 'ticket': ticket,
                'entry_time': pos['entry_time'],
                'exit_time': str(datetime.now(timezone.utc)),
                'bars_held': pos.get('bars_held', 0),
            })
            log.info("    PnL=${:+,.2f} (incl commission+swap)".format(pnl))
            closed.append(pos)

    for c in closed:
        state['positions'].remove(c)
    if closed: save_state(state)

# ── MAIN ─────────────────────────────────────────────

def main():
    if not mt5_init():
        log.error("MT5 init failed. Arret.")
        return

    if args.reset:
        state = reset_state()
    else:
        state = load_state()

    log.info("Demarrage {} LIVE{} — {} strats @ {:.1f}% risk: {}".format(
        BROKER, " [DRY]" if DRY_RUN else "",
        len(STRATS), RISK_PCT*100, ','.join(STRATS)))
    log.info("Balance MT5: ${:,.2f} | Positions state: {}".format(
        mt5_get_balance(), len(state['positions'])))

    conn = get_conn_autocommit()
    ci = get_recent_candles(conn, 1)
    if len(ci) > 0:
        last_candle_ts = int(ci.iloc[-1]['ts'])
        log.info("Calage: {} (triggers apres prochaine bougie)".format(ci.iloc[-1]['ts_dt']))
    else:
        last_candle_ts = 0

    while True:
        try:
            try: conn.isolation_level
            except Exception:
                log.warning("Reconnexion DB...")
                try: conn.close()
                except: pass
                conn = get_conn_autocommit()

            if not mt5.terminal_info():
                log.warning("MT5 deconnecte, reconnexion...")
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

            # Prev day data + reset triggered
            if '_prev_day_data' not in state or state.get('_prev_day_date') != str(today):
                yc = candles[candles['date'] < today]
                if len(yc) > 0:
                    last_day = yc['date'].iloc[-1]
                    dc = yc[yc['date']==last_day]
                    state['_prev_day_data'] = {'open':float(dc.iloc[0]['open']),'close':float(dc.iloc[-1]['close']),
                                               'high':float(dc['high'].max()),'low':float(dc['low'].min()),
                                               'range':float(dc['high'].max()-dc['low'].min())}
                state['_prev_day_date'] = str(today)
                state['_triggered_open'] = {}
                state['_triggered_close'] = {}
                log.info("Reset triggered pour {}".format(today))

            # Sync: detect MT5 closed positions
            sync_positions(state)

            # Open strats: every poll
            now_utc = datetime.now(timezone.utc)
            open_sigs = detect_open_strats(candles, state, atr, now_utc, today)
            if open_sigs:
                mt5_pos = mt5_get_positions()
                open_dirs = set()
                for p in mt5_pos:
                    open_dirs.add('long' if p.type == mt5.ORDER_TYPE_BUY else 'short')
                for sig in open_sigs:
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
            last_row = candles.iloc[-1]
            n_trig_o = len(state.get('_triggered_open', {}))
            n_trig_c = len(state.get('_triggered_close', {}))
            balance = mt5_get_balance()
            log.info("~ {} | C={:.2f} | ATR={:.2f} | {}o {}c | {}pos | ${:,.0f}".format(
                candle_time.strftime("%H:%M"), last_row['close'], atr,
                n_trig_o, n_trig_c, len(state['positions']), balance))

            # Trailing
            if state['positions']:
                manage_trailing(state, candles)

            last_candle_ts = current_ts; state['last_candle_ts'] = current_ts

            # Close strats
            close_sigs = detect_close_strats(candles, state, atr, candle_time, today)
            if close_sigs:
                mt5_pos = mt5_get_positions()
                open_dirs = set()
                for p in mt5_pos:
                    open_dirs.add('long' if p.type == mt5.ORDER_TYPE_BUY else 'short')
                for sig in close_sigs:
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
    log.info("Arrete.")

if __name__ == '__main__':
    main()
