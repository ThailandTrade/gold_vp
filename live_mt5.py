"""
Live MT5 — 11 strats, ordres reels.
Les trades sont places et geres par MT5. Resultats lus depuis MT5.
Config: TRAIL SL=1.0 ACT=0.5 TRAIL=0.75, pas de timeout (sur CLOSE).

Usage: python live_mt5.py [--risk 0.1] [--dry]
  --risk 0.1  : risque par trade en % du capital (defaut: 0.1%)
  --dry       : mode dry run (log les signaux sans placer d'ordres)
"""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, time, logging, argparse
import numpy as np, pandas as pd
import MetaTrader5 as mt5
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
load_dotenv()
from phase1_poc_calculator import get_conn
from strats import SL, ACT, TRAIL, STRATS, STRAT_NAMES

# ── ARGS ─────────────────────────────────────────────

parser = argparse.ArgumentParser()
parser.add_argument('--risk', type=float, default=0.1, help='Risque par trade en %%')
parser.add_argument('--dry', action='store_true', help='Dry run (pas d ordres)')
parser.add_argument('--magic', type=int, default=20260321, help='Magic number MT5')
args = parser.parse_args()

RISK_PCT = args.risk / 100
DRY_RUN = args.dry
MAGIC = args.magic
SYMBOL = 'XAUUSD'
CHECK_INTERVAL = 5  # secondes entre chaque poll

# ── LOGGING ──────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(),
              logging.FileHandler('live_mt5.log', encoding='utf-8')])
log = logging.getLogger('mt5live')

# ── STATE (persistant) ───────────────────────────────

STATE_FILE = 'live_mt5_state.json'

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f: return json.load(f)
    return {'_triggered': {}, '_prev_day_data': None, '_prev_day_date': None,
            'positions': {}, 'last_candle_ts': 0, 'trades_log': []}

def save_state(state):
    with open(STATE_FILE, 'w') as f: json.dump(state, f, indent=2, default=str)

# ── MT5 ──────────────────────────────────────────────

def mt5_init():
    if not mt5.initialize():
        log.error(f"MT5 init failed: {mt5.last_error()}")
        sys.exit(1)
    info = mt5.account_info()
    log.info(f"MT5 connected: {info.login} | Balance: ${info.balance:,.2f} | Server: {info.server}")
    sym = mt5.symbol_info(SYMBOL)
    if sym is None or not sym.visible:
        mt5.symbol_select(SYMBOL, True)
    return info

def get_account_balance():
    info = mt5.account_info()
    return info.balance if info else 0

def get_mt5_positions():
    """Retourne les positions ouvertes MT5 pour notre magic number."""
    positions = mt5.positions_get(symbol=SYMBOL)
    if positions is None: return []
    return [p for p in positions if p.magic == MAGIC]

def place_order(strat, direction, atr):
    """Place un ordre market avec SL. Retourne le ticket ou None."""
    tick = mt5.symbol_info_tick(SYMBOL)
    if not tick:
        log.error("Pas de tick"); return None

    balance = get_account_balance()
    risk_amount = balance * RISK_PCT
    sl_distance = SL * atr
    # XAUUSD: 1 lot = 100 oz, tick_value depend du broker
    sym_info = mt5.symbol_info(SYMBOL)
    lot_size = risk_amount / (sl_distance * sym_info.trade_contract_size)
    # Arrondir au step
    lot_step = sym_info.volume_step
    lot_size = max(sym_info.volume_min, round(lot_size / lot_step) * lot_step)
    lot_size = min(lot_size, sym_info.volume_max)

    if direction == 'long':
        price = tick.ask
        sl = round(price - sl_distance, 2)
        order_type = mt5.ORDER_TYPE_BUY
    else:
        price = tick.bid
        sl = round(price + sl_distance, 2)
        order_type = mt5.ORDER_TYPE_SELL

    request = {
        'action': mt5.TRADE_ACTION_DEAL,
        'symbol': SYMBOL,
        'volume': lot_size,
        'type': order_type,
        'price': price,
        'sl': sl,
        'magic': MAGIC,
        'comment': strat,
        'type_filling': mt5.ORDER_FILLING_IOC,
    }

    if DRY_RUN:
        log.info(f"DRY RUN: {strat} {direction} {lot_size:.2f}lots @ {price:.2f} SL={sl:.2f}")
        return None

    result = mt5.order_send(request)
    if result is None:
        log.error(f"order_send None: {mt5.last_error()}")
        return None
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        log.error(f"Order failed: {result.retcode} {result.comment}")
        return None

    log.info(f"OPEN {strat} {direction} | ticket={result.order} | {lot_size:.2f}lots @ {result.price:.2f} | SL={sl:.2f}")
    return result.order

def modify_sl(ticket, new_sl):
    """Modifie le SL d'une position ouverte."""
    pos = mt5.positions_get(ticket=ticket)
    if not pos:
        log.warning(f"Position {ticket} introuvable pour modify"); return False

    request = {
        'action': mt5.TRADE_ACTION_SLTP,
        'position': ticket,
        'symbol': SYMBOL,
        'sl': round(new_sl, 2),
        'tp': 0,
    }

    if DRY_RUN:
        log.info(f"DRY RUN modify: ticket={ticket} new_sl={new_sl:.2f}")
        return True

    result = mt5.order_send(request)
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        log.error(f"Modify SL failed: {result.retcode if result else 'None'} {result.comment if result else ''}")
        return False
    return True

def close_position(ticket):
    """Ferme une position au marche."""
    pos = mt5.positions_get(ticket=ticket)
    if not pos: return
    p = pos[0]
    close_type = mt5.ORDER_TYPE_SELL if p.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
    tick = mt5.symbol_info_tick(SYMBOL)
    price = tick.bid if p.type == mt5.ORDER_TYPE_BUY else tick.ask

    request = {
        'action': mt5.TRADE_ACTION_DEAL,
        'symbol': SYMBOL,
        'volume': p.volume,
        'type': close_type,
        'position': ticket,
        'price': price,
        'magic': MAGIC,
        'comment': 'close',
        'type_filling': mt5.ORDER_FILLING_IOC,
    }

    if DRY_RUN:
        log.info(f"DRY RUN close: ticket={ticket} @ {price:.2f}"); return

    result = mt5.order_send(request)
    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        log.info(f"CLOSE ticket={ticket} @ {result.price:.2f}")
    else:
        log.error(f"Close failed: {result.retcode if result else 'None'}")

# ── DB ───────────────────────────────────────────────

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

# ── SIGNAL DETECTION ─────────────────────────────────

def detect_signals(candles, state, atr, candle_time, today):
    signals = []; hour = candle_time.hour + candle_time.minute / 60.0
    trig = state.setdefault('_triggered', {})
    ds = pd.Timestamp(today.year,today.month,today.day,0,0,tz='UTC')
    te = pd.Timestamp(today.year,today.month,today.day,6,0,tz='UTC')
    ls = pd.Timestamp(today.year,today.month,today.day,8,0,tz='UTC')
    ns = pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC')
    tok = candles[(candles['ts_dt']>=ds)&(candles['ts_dt']<te)]
    lon = candles[(candles['ts_dt']>=ls)&(candles['ts_dt']<ns)]
    r = candles.iloc[-1]
    prev_day_data = state.get('_prev_day_data')

    # ── TOKYO ──
    if 0.0<=hour<6.0:
        k = str(today)+'_TOK_2BAR'
        if k not in trig and len(tok)>=2:
            b1=tok.iloc[-2];b2=tok.iloc[-1];b1b=b1['close']-b1['open'];b2b=b2['close']-b2['open']
            if abs(b1b)>=0.5*atr and abs(b2b)>=0.5*atr and b1b*b2b<0 and abs(b2b)>abs(b1b):
                signals.append({'strat':'TOK_2BAR','dir':'long' if b2b>0 else 'short'}); trig[k]=True
        k = str(today)+'_TOK_BIG'
        if k not in trig:
            body=r['close']-r['open']
            if abs(body)>=1.0*atr:
                signals.append({'strat':'TOK_BIG','dir':'long' if body>0 else 'short'}); trig[k]=True
    if 0.0<=hour<0.1:
        k = str(today)+'_TOK_FADE'
        if k not in trig and prev_day_data:
            prev_dir = prev_day_data['close'] - prev_day_data['open']
            if abs(prev_dir) >= 1.0*atr:
                signals.append({'strat':'TOK_FADE','dir':'short' if prev_dir>0 else 'long'}); trig[k]=True

    # ── LONDON ──
    if 8.0<=hour<14.5:
        k = str(today)+'_LON_PIN'
        if k not in trig:
            rng=r['high']-r['low']
            if rng>=0.3*atr and abs(r['close']-r['open'])>=0.2*atr:
                pir=(r['close']-r['low'])/rng
                if pir>=0.9: signals.append({'strat':'LON_PIN','dir':'long'}); trig[k]=True
                elif pir<=0.1: signals.append({'strat':'LON_PIN','dir':'short'}); trig[k]=True
    if 8.0<=hour<8.1:
        k = str(today)+'_LON_GAP'
        if k not in trig:
            tc=candles[candles['ts_dt']<te]
            if len(tc)>=5:
                gap=(r['open']-tc.iloc[-1]['close'])/atr
                if abs(gap)>=0.5:
                    signals.append({'strat':'LON_GAP','dir':'long' if gap>0 else 'short'}); trig[k]=True
        k = str(today)+'_LON_TOKEND'
        if k not in trig and len(tok)>=9:
            l3=tok.iloc[-3:]; m=(l3.iloc[-1]['close']-l3.iloc[0]['open'])/atr
            if abs(m)>=1.0:
                signals.append({'strat':'LON_TOKEND','dir':'long' if m>0 else 'short'}); trig[k]=True
        k = str(today)+'_LON_PREV'
        if k not in trig and prev_day_data:
            prev_body=(prev_day_data['close']-prev_day_data['open'])/atr
            if abs(prev_body)>=1.0:
                signals.append({'strat':'LON_PREV','dir':'long' if prev_body>0 else 'short'}); trig[k]=True
    if 10.0<=hour<10.1:
        k = str(today)+'_LON_KZ'
        if k not in trig:
            kz=candles[(candles['ts_dt']>=ls)&(candles['ts_dt']<pd.Timestamp(today.year,today.month,today.day,10,0,tz='UTC'))]
            if len(kz)>=20:
                m=(kz.iloc[-1]['close']-kz.iloc[0]['open'])/atr
                if abs(m)>=0.5:
                    signals.append({'strat':'LON_KZ','dir':'short' if m>0 else 'long'}); trig[k]=True

    # ── NY ──
    if 14.5<=hour<14.6:
        k = str(today)+'_NY_GAP'
        if k not in trig and len(lon)>=5:
            gap=(r['open']-lon.iloc[-1]['close'])/atr
            if abs(gap)>=0.5:
                signals.append({'strat':'NY_GAP','dir':'long' if gap>0 else 'short'}); trig[k]=True
        k = str(today)+'_NY_LONEND'
        if k not in trig and len(lon)>=9:
            l3=lon.iloc[-3:]; m=(l3.iloc[-1]['close']-l3.iloc[0]['open'])/atr
            if abs(m)>=1.0:
                signals.append({'strat':'NY_LONEND','dir':'long' if m>0 else 'short'}); trig[k]=True
        k = str(today)+'_NY_LONMOM'
        if k not in trig and len(lon)>=9:
            l3=lon.iloc[-3:]; m=(l3.iloc[-1]['close']-l3.iloc[0]['open'])/atr
            if abs(m)>=0.5:
                signals.append({'strat':'NY_LONMOM','dir':'long' if m>0 else 'short'}); trig[k]=True

    return signals

# ── TRAILING MANAGEMENT (sur bougie fermee) ──────────

def manage_trailing(state):
    """Met a jour le trailing sur les positions ouvertes MT5.
    Appele a chaque nouvelle bougie fermee."""
    mt5_positions = get_mt5_positions()
    if not mt5_positions: return

    for pos in mt5_positions:
        ticket = pos.ticket
        key = str(ticket)
        if key not in state['positions']:
            # Position ouverte hors de notre systeme, on ignore
            continue

        pdata = state['positions'][key]
        d = pdata['dir']
        atr = pdata['atr']
        entry = pdata['entry']

        # Prix actuel (close de la derniere bougie = prix MT5 actuel)
        current_price = pos.price_current
        current_sl = pos.sl

        # Update best close
        best = pdata.get('best', entry)
        if d == 'long' and current_price > best:
            best = current_price
        elif d == 'short' and current_price < best:
            best = current_price
        pdata['best'] = best

        # Trailing activation
        if not pdata.get('trail_active', False):
            fav = (best - entry) if d == 'long' else (entry - best)
            if fav >= ACT * atr:
                pdata['trail_active'] = True
                log.info(f"TRAIL ACTIVE ticket={ticket} {pdata['strat']} best={best:.2f}")

        # Trailing stop update
        if pdata.get('trail_active', False):
            if d == 'long':
                new_sl = round(best - TRAIL * atr, 2)
                if new_sl > current_sl:
                    if modify_sl(ticket, new_sl):
                        log.info(f"TRAIL UPDATE ticket={ticket} {pdata['strat']} SL {current_sl:.2f} -> {new_sl:.2f} (best={best:.2f})")
                    pdata['sl'] = new_sl
            else:
                new_sl = round(best + TRAIL * atr, 2)
                if new_sl < current_sl:
                    if modify_sl(ticket, new_sl):
                        log.info(f"TRAIL UPDATE ticket={ticket} {pdata['strat']} SL {current_sl:.2f} -> {new_sl:.2f} (best={best:.2f})")
                    pdata['sl'] = new_sl

    save_state(state)

# ── SYNC POSITIONS (lire l'etat reel MT5) ────────────

def sync_positions(state):
    """Synchronise notre state avec les positions reelles MT5.
    Detecte les positions fermees par MT5 (SL touche)."""
    mt5_tickets = {p.ticket for p in get_mt5_positions()}
    our_tickets = set(state['positions'].keys())

    for key in list(our_tickets):
        ticket = int(key)
        if ticket not in mt5_tickets:
            # Position fermee par MT5 (SL ou autre)
            pdata = state['positions'].pop(key)

            # Lire le resultat depuis MT5
            deals = mt5.history_deals_get(position=ticket)
            if deals and len(deals) >= 2:
                close_deal = deals[-1]
                pnl = close_deal.profit + close_deal.commission + close_deal.swap
                exit_price = close_deal.price
                log.info(f"CLOSED BY MT5 | {pdata['strat']} {pdata['dir']} | "
                         f"{pdata['entry']:.2f} -> {exit_price:.2f} | "
                         f"PnL: ${pnl:+,.2f} | ticket={ticket}")
                state['trades_log'].append({
                    'strat': pdata['strat'], 'dir': pdata['dir'],
                    'entry': pdata['entry'], 'exit': exit_price,
                    'pnl': pnl, 'ticket': ticket,
                    'entry_time': pdata.get('entry_time'),
                    'exit_time': str(datetime.now(timezone.utc)),
                })
            else:
                log.warning(f"Position {ticket} fermee mais pas de deals trouves")

    save_state(state)

# ── MAIN ─────────────────────────────────────────────

def main():
    info = mt5_init()
    conn = get_conn_autocommit()
    state = load_state()

    log.info(f"{'DRY RUN — ' if DRY_RUN else ''}11 strats | Risk {args.risk}% | Magic {MAGIC}")
    log.info(f"Balance: ${info.balance:,.2f} | Strats: {', '.join(STRATS)}")

    last_candle_ts = state.get('last_candle_ts', 0)
    if last_candle_ts == 0:
        ci = get_recent_candles(conn, 1)
        if len(ci) > 0: last_candle_ts = int(ci.iloc[-1]['ts'])

    while True:
        try:
            # Reconnexion DB si necessaire
            try: conn.isolation_level
            except Exception:
                log.warning("Reconnexion DB...")
                try: conn.close()
                except: pass
                conn = get_conn_autocommit()

            # Reconnexion MT5 si necessaire
            if not mt5.terminal_info():
                log.warning("Reconnexion MT5...")
                mt5_init()

            candles = get_recent_candles(conn, 1500)
            if len(candles) == 0: time.sleep(CHECK_INTERVAL); continue

            current_ts = int(candles.iloc[-1]['ts'])
            candle_time = candles.iloc[-1]['ts_dt'].to_pydatetime()
            today = candle_time.date()

            # ATR
            atr = get_yesterday_atr(candles, today)
            if not atr or atr == 0: time.sleep(CHECK_INTERVAL); continue

            # Prev day data
            if state.get('_prev_day_date') != str(today):
                yc = candles[candles['date'] < today]
                if len(yc) > 0:
                    last_day = yc['date'].iloc[-1]
                    dc = yc[yc['date']==last_day]
                    state['_prev_day_data'] = {'open':float(dc.iloc[0]['open']),'close':float(dc.iloc[-1]['close']),
                                               'high':float(dc['high'].max()),'low':float(dc['low'].min())}
                state['_prev_day_date'] = str(today)

            # Sync avec MT5 (detecter les positions fermees)
            sync_positions(state)

            # Nouvelle bougie ?
            is_new = current_ts != last_candle_ts
            if not is_new:
                time.sleep(CHECK_INTERVAL); continue

            log.info(f"CANDLE {candle_time.strftime('%Y-%m-%d %H:%M')} | close={candles.iloc[-1]['close']:.2f} | ATR={atr:.2f}")

            # Trailing update sur bougie fermee
            manage_trailing(state)

            last_candle_ts = current_ts; state['last_candle_ts'] = current_ts

            # Reset triggers au changement de jour
            if str(today) not in str(state.get('_triggered', {}).keys()):
                pass  # les triggers sont prefixes par la date, pas besoin de reset

            # Detect signals
            mt5_pos = get_mt5_positions()
            open_dirs = set()
            for p in mt5_pos:
                if p.type == mt5.ORDER_TYPE_BUY: open_dirs.add('long')
                else: open_dirs.add('short')

            signals = detect_signals(candles, state, atr, candle_time, today)

            for sig in signals:
                if sig['strat'] not in STRATS: continue
                # Conflit de direction
                if sig['dir'] == 'long' and 'short' in open_dirs:
                    log.info(f"SKIP {sig['strat']} — conflit short"); continue
                if sig['dir'] == 'short' and 'long' in open_dirs:
                    log.info(f"SKIP {sig['strat']} — conflit long"); continue

                ticket = place_order(sig['strat'], sig['dir'], atr)
                if ticket:
                    state['positions'][str(ticket)] = {
                        'strat': sig['strat'], 'dir': sig['dir'],
                        'entry': mt5.positions_get(ticket=ticket)[0].price_open,
                        'atr': atr, 'best': mt5.positions_get(ticket=ticket)[0].price_open,
                        'trail_active': False,
                        'entry_time': str(candle_time),
                    }
                    open_dirs.add(sig['dir'])

            if signals:
                log.info(f"  {len(signals)} signal(s)")

            # Dashboard console
            balance = get_account_balance()
            n_pos = len(get_mt5_positions())
            n_trades = len(state['trades_log'])
            log.info(f"  Balance=${balance:,.2f} | Positions={n_pos} | Trades={n_trades}")

            save_state(state)

        except KeyboardInterrupt:
            log.info("Arret."); save_state(state); break
        except Exception as e:
            log.error(f"Erreur: {e}")
            import traceback; traceback.print_exc()
            time.sleep(30)

        time.sleep(CHECK_INTERVAL)

    mt5.shutdown()
    log.info("MT5 shutdown.")

if __name__ == '__main__':
    main()
