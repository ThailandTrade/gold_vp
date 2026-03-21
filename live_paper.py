"""
Paper Trading Live — 11 strats, noms par session.
Config: TRAIL SL=1.0 ACT=0.5 TRAIL=0.75, pas de timeout (sur CLOSE)
PF 1.51, WR 44%, DD -27.1%, Calmar 1018, 13/13 mois+
Usage: python live_paper.py [--reset]
"""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, time, logging
import numpy as np, pandas as pd
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
load_dotenv()
from phase1_poc_calculator import get_conn

# ── CONFIG ────────────────────────────────────────────

CAPITAL_INITIAL = 1000.0
RISK_PCT = 0.01
CHECK_INTERVAL = 1
LOG_FILE = "paper_trades.json"
from strats import SL, ACT, TRAIL, STRATS, STRAT_NAMES, STRAT_SESSION, detect_all

# ── LOGGING ───────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(),
              logging.FileHandler('paper_trading.log', encoding='utf-8')])
log = logging.getLogger('paper')

# ── DB ────────────────────────────────────────────────

def get_conn_autocommit():
    conn = get_conn(); conn.autocommit = True; return conn

def get_recent_candles(conn, n=500):
    cur = conn.cursor()
    cur.execute("SELECT ts, open, high, low, close FROM candles_mt5_xauusd_5m ORDER BY ts DESC LIMIT %s", (n,))
    rows = cur.fetchall(); cur.close()
    if not rows: return pd.DataFrame()
    df = pd.DataFrame(rows, columns=['ts','open','high','low','close']).sort_values('ts').reset_index(drop=True)
    df['ts_dt'] = pd.to_datetime(df['ts'], unit='ms', utc=True)
    for c in ['open','high','low','close']: df[c] = df[c].astype(float)
    df['date'] = df['ts_dt'].dt.date
    return df

def get_current_bidask(conn):
    cur = conn.cursor()
    cur.execute("SELECT bid, ask, last FROM market_ticks_xauusd ORDER BY ts DESC LIMIT 1")
    row = cur.fetchone(); cur.close()
    if row:
        bid, ask, last = float(row[0]), float(row[1]), float(row[2])
        return {'bid': bid, 'ask': ask, 'last': last, 'spread': ask - bid}
    return None

def get_yesterday_atr(candles_df, today):
    yc = candles_df[candles_df['date'] < today].copy()
    if len(yc) < 20: return None
    yc['pc'] = yc['close'].shift(1)
    yc['tr'] = np.maximum(yc['high']-yc['low'], np.maximum(abs(yc['high']-yc['pc']), abs(yc['low']-yc['pc'])))
    yc['atr'] = yc['tr'].ewm(span=14, adjust=False).mean()
    return float(yc['atr'].iloc[-1])

def get_spread_rt(conn, today):
    cur = conn.cursor()
    cur.execute("SELECT AVG(ask-bid) FROM market_ticks_xauusd WHERE ask>bid AND ask-bid<10 AND time >= %s",
                (datetime(today.year, today.month, 1, 0, 0),))
    row = cur.fetchone(); cur.close()
    return 2 * float(row[0]) if row and row[0] else 0.188

# ── STATE ─────────────────────────────────────────────

def load_state():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r') as f: return json.load(f)
    return {'capital': CAPITAL_INITIAL, 'trades': [], 'open_positions': [],
            'daily_cache': {}, '_triggered': {}, 'last_candle_ts': 0}

def save_state(state):
    with open(LOG_FILE, 'w') as f: json.dump(state, f, indent=2, default=str)

def reset_state():
    state = {'capital': CAPITAL_INITIAL, 'trades': [], 'open_positions': [],
             'daily_cache': {}, '_triggered': {}, 'last_candle_ts': 0}
    save_state(state)
    log.info("RESET — ${:,.2f}".format(CAPITAL_INITIAL))
    return state

# ── DAILY CACHE ───────────────────────────────────────

def ensure_daily_cache(state, conn, candles_df, today):
    k = str(today)
    if k in state['daily_cache']: return state['daily_cache'][k]
    log.info("Cache journalier {}...".format(today))
    atr = get_yesterday_atr(candles_df, today)
    spread_rt = get_spread_rt(conn, today)
    cache = {'atr': atr, 'spread_rt': spread_rt}
    state['daily_cache'] = {k: cache}
    log.info("  ATR={} spread_rt={:.3f}".format("{:.2f}".format(atr) if atr else "None", spread_rt))
    return cache

# ── STOP CHECK TEMPS REEL (chaque seconde) ──────────

def check_stops_realtime(state, tick, conn):
    """Verifie les stops contre le bid/ask reel, comme MT5 le ferait."""
    closed = []
    for pos in state['open_positions']:
        d = pos['strat_dir']
        # MT5: long SL = sell order, triggered when BID <= stop
        # MT5: short SL = buy order, triggered when ASK >= stop
        if d == 'long' and tick['bid'] <= pos['stop']:
            pos['exit'] = tick['bid']  # exit au bid reel
            pos['exit_reason'] = 'stop_rt'
            closed.append(pos)
        elif d == 'short' and tick['ask'] >= pos['stop']:
            pos['exit'] = tick['ask']  # exit au ask reel
            pos['exit_reason'] = 'stop_rt'
            closed.append(pos)

    for c in closed:
        state['open_positions'].remove(c)
        pnl_oz = (c['exit']-c['entry']) if c['strat_dir']=='long' else (c['entry']-c['exit'])
        pnl_dollar = pnl_oz * c['pos_oz']
        state['capital'] += pnl_dollar
        state['trades'].append({
            'strat': c['strat'], 'dir': c['strat_dir'],
            'entry': c['entry'], 'exit': c['exit'],
            'entry_time': c['entry_time'],
            'exit_time': str(datetime.now(timezone.utc)),
            'pnl_oz': pnl_oz, 'pnl_dollar': pnl_dollar,
            'bars_held': c.get('bars_held', 0),
            'exit_reason': c['exit_reason'],
            'capital_after': state['capital'],
        })
        log.info("STOP RT {} {} | {:.2f}->{:.2f} | ${:+.2f} | bid={:.2f} ask={:.2f} | Cap=${:,.2f}".format(
            c['strat'], c['strat_dir'], c['entry'], c['exit'],
            pnl_dollar, tick['bid'], tick['ask'], state['capital']))

    if closed:
        save_state(state)

# ── POSITION MANAGEMENT (sur bougie fermee) ─────────

def manage_positions(candles_df, state, conn):
    last = candles_df.iloc[-1]; closed = []
    for pos in state['open_positions']:
        pos['bars_held'] = pos.get('bars_held', 0) + 1
        ta = pos['trade_atr']; d = pos['strat_dir']
        # 1. Stop check (exit au niveau exact du stop — MT5 execute l'ordre serveur)
        if d == 'long' and last['low'] <= pos['stop']:
            pos['exit'] = pos['stop']; pos['exit_reason'] = 'stop'; closed.append(pos); continue
        if d == 'short' and last['high'] >= pos['stop']:
            pos['exit'] = pos['stop']; pos['exit_reason'] = 'stop'; closed.append(pos); continue
        # 2. Best update (sur le CLOSE, pas le high/low — coherence temporelle)
        if d == 'long' and last['close'] > pos.get('best', pos['entry']): pos['best'] = last['close']
        if d == 'short' and last['close'] < pos.get('best', pos['entry']): pos['best'] = last['close']
        # 3. Trailing activation
        if not pos.get('trail_active', False):
            fav = (pos['best'] - pos['entry']) if d == 'long' else (pos['entry'] - pos['best'])
            if fav >= ACT * ta: pos['trail_active'] = True
        # 4. Trailing stop update
        if pos.get('trail_active', False):
            if d == 'long':
                ns = pos['best'] - TRAIL * ta; pos['stop'] = max(pos['stop'], ns)
            else:
                ns = pos['best'] + TRAIL * ta; pos['stop'] = min(pos['stop'], ns)
        # 4b. Re-check close vs nouveau stop (LOW/HIGH happened pendant la bougie avec l'ANCIEN stop)
        if d == 'long' and last['close'] < pos['stop']:
            pos['exit'] = last['close']; pos['exit_reason'] = 'stop_close'; closed.append(pos); continue
        if d == 'short' and last['close'] > pos['stop']:
            pos['exit'] = last['close']; pos['exit_reason'] = 'stop_close'; closed.append(pos); continue

    for c in closed:
        state['open_positions'].remove(c)
        pnl_oz = (c['exit']-c['entry']) if c['strat_dir']=='long' else (c['entry']-c['exit'])
        pnl_dollar = pnl_oz * c['pos_oz']
        state['capital'] += pnl_dollar
        state['trades'].append({
            'strat': c['strat'], 'dir': c['strat_dir'],
            'entry': c['entry'], 'exit': c['exit'],
            'entry_time': c['entry_time'], 'exit_time': str(datetime.now(timezone.utc)),
            'pnl_oz': pnl_oz, 'pnl_dollar': pnl_dollar,
            'bars_held': c['bars_held'], 'exit_reason': c['exit_reason'],
            'capital_after': state['capital'],
        })
        log.info("CLOSE {} {} | {:.2f}->{:.2f} | ${:+.2f} ({}) | Cap=${:,.2f}".format(
            c['strat'], c['strat_dir'], c['entry'], c['exit'],
            pnl_dollar, c['exit_reason'], state['capital']))

# ── SIGNAL DETECTION ──────────────────────────────────

def detect_signals(candles, state, atr, candle_time, today):
    """Utilise detect_all de strats.py pour rester synchronise avec le backtest."""
    signals = []
    trig = state.setdefault('_triggered', {})
    hour = candle_time.hour + candle_time.minute / 60.0
    ds = pd.Timestamp(today.year,today.month,today.day,0,0,tz='UTC')
    te = pd.Timestamp(today.year,today.month,today.day,6,0,tz='UTC')
    ls = pd.Timestamp(today.year,today.month,today.day,8,0,tz='UTC')
    ns = pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC')
    tv = candles[(candles['ts_dt']>=ds)&(candles['ts_dt']<=candle_time)]
    tok = tv[tv['ts_dt']<te]; lon = tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<ns)]
    r = candles.iloc[-1]
    prev_day_data = state.get('_prev_day_data')
    ct = candles.iloc[-1]['ts_dt']

    # Collect via detect_all (meme logique que backtest)
    collected = []
    def add_signal(sn, d, e):
        collected.append({'strat': sn, 'dir': d})
    detect_all(candles, len(candles)-1, r, ct, today, hour, atr, trig, tv, tok, lon, prev_day_data, add_signal)
    return collected

# ── OPEN POSITION ─────────────────────────────────────

def open_position(state, sig, atr, candle_time, conn):
    tick = get_current_bidask(conn)
    if not tick: log.warning("SKIP {} — no tick".format(sig['strat'])); return
    d = sig['dir']
    entry = tick['ask'] if d == 'long' else tick['bid']
    stop = entry - SL*atr if d == 'long' else entry + SL*atr
    risk = state['capital'] * RISK_PCT
    pos_oz = risk / (SL * atr) if atr > 0 else 0
    state['open_positions'].append({
        'strat': sig['strat'], 'strat_dir': d, 'entry': entry, 'stop': stop,
        'best': entry, 'trail_active': False, 'pos_oz': pos_oz, 'lots': pos_oz/100,
        'bars_held': 0, 'entry_time': str(candle_time), 'trade_atr': atr,
        'entry_bid': tick['bid'], 'entry_ask': tick['ask'], 'entry_spread': tick['spread'],
    })
    log.info("OPEN {} {} | {:.2f} (bid={:.2f} ask={:.2f} sp={:.3f}) | stop={:.2f} | {:.3f}lots".format(
        sig['strat'], d, entry, tick['bid'], tick['ask'], tick['spread'], stop, pos_oz/100))

# ── DASHBOARD ─────────────────────────────────────────

def print_dashboard(state, cache, candle_time):
    lines = ["=" * 70,
        "PAPER TRADING — {} | ATR={} | Strats: {}".format(
            candle_time.strftime("%Y-%m-%d %H:%M UTC"),
            "{:.2f}".format(cache['atr']) if cache['atr'] else "?",
            ','.join(STRATS)),
        "  Capital: ${:,.2f} (PnL: ${:+,.2f})".format(state['capital'], state['capital']-CAPITAL_INITIAL),
        "  Positions: {}".format(len(state['open_positions']))]
    for p in state['open_positions']:
        lines.append("    {} {} entry={:.2f} stop={:.2f} best={:.2f} trail={} bars={}".format(
            p['strat'], p['strat_dir'], p['entry'], p['stop'], p.get('best',p['entry']),
            "ON" if p.get('trail_active') else "off", p.get('bars_held',0)))
    trades = state['trades']
    if trades:
        wins = [t for t in trades if t['pnl_dollar'] > 0]
        gp = sum(t['pnl_dollar'] for t in wins) if wins else 0
        gl = abs(sum(t['pnl_dollar'] for t in trades if t['pnl_dollar'] < 0)) + 0.01
        lines.append("  Trades: {} | WR={:.0f}% | PF={:.2f} | PnL=${:+,.2f}".format(
            len(trades), len(wins)/len(trades)*100, gp/gl, sum(t['pnl_dollar'] for t in trades)))
        for t in trades[-3:]:
            lines.append("    {} {} {:.2f}->{:.2f} ${:+.2f} ({})".format(
                t['strat'], t['dir'], t['entry'], t['exit'], t['pnl_dollar'], t['exit_reason']))
    lines.append("=" * 70)
    dashboard = "\n".join(lines)
    print("\033c" + dashboard)
    with open("paper_dashboard.txt", 'w', encoding='utf-8') as f: f.write(dashboard)

# ── MAIN ──────────────────────────────────────────────

def main():
    if '--reset' in sys.argv:
        reset_state(); print("Reset. Relancez sans --reset."); return

    log.info("Demarrage — {} strats: {}".format(len(STRATS), ','.join(STRATS)))
    state = load_state()
    log.info("Capital: ${:,.2f} | Trades: {} | Positions: {}".format(
        state['capital'], len(state['trades']), len(state['open_positions'])))

    conn = get_conn_autocommit()
    saved_ts = state.get('last_candle_ts', 0)
    if saved_ts == 0:
        ci = get_recent_candles(conn, 1)
        if len(ci) > 0:
            saved_ts = int(ci.iloc[-1]['ts'])
            log.info("Calage: {}".format(ci.iloc[-1]['ts_dt']))
    last_candle_ts = saved_ts

    while True:
        try:
            try: conn.isolation_level
            except Exception:
                log.warning("Reconnexion DB...");
                try: conn.close()
                except: pass
                conn = get_conn_autocommit()

            candles = get_recent_candles(conn, 1500)
            if len(candles) == 0: time.sleep(CHECK_INTERVAL); continue

            current_ts = int(candles.iloc[-1]['ts'])
            candle_time = candles.iloc[-1]['ts_dt'].to_pydatetime()
            today = candle_time.date()

            cache = ensure_daily_cache(state, conn, candles, today)
            if not cache['atr'] or cache['atr'] == 0: time.sleep(CHECK_INTERVAL); continue
            atr = cache['atr']
            # Prev day data for TOK_FADE and LON_PREV
            if '_prev_day_data' not in state or state.get('_prev_day_date') != str(today):
                yc = candles[candles['date'] < today]
                if len(yc) > 0:
                    last_day = yc['date'].iloc[-1]
                    dc = yc[yc['date']==last_day]
                    state['_prev_day_data'] = {'open':float(dc.iloc[0]['open']),'close':float(dc.iloc[-1]['close']),
                                               'high':float(dc['high'].max()),'low':float(dc['low'].min()),
                                               'range':float(dc['high'].max()-dc['low'].min())}
                state['_prev_day_date'] = str(today)

            # Verifier les stops sur chaque poll (comme MT5 le ferait)
            if state['open_positions']:
                tick = get_current_bidask(conn)
                if tick:
                    check_stops_realtime(state, tick, conn)

            is_new = current_ts != last_candle_ts
            if is_new:
                log.info("CANDLE {} | close={:.2f} | ATR={:.2f} | pos={}".format(
                    candle_time.strftime("%Y-%m-%d %H:%M"), candles.iloc[-1]['close'], atr,
                    len(state['open_positions'])))
                if state['open_positions']:
                    manage_positions(candles, state, conn)
                last_candle_ts = current_ts; state['last_candle_ts'] = current_ts
            else:
                time.sleep(CHECK_INTERVAL); continue

            # Detect signals
            open_dirs = set(p['strat_dir'] for p in state['open_positions'])
            signals = detect_signals(candles, state, atr, candle_time, today)

            for sig in signals:
                if sig['strat'] not in STRATS:
                    continue
                if sig['dir'] == 'long' and 'short' in open_dirs:
                    log.info("SKIP {} — conflit short".format(sig['strat'])); continue
                if sig['dir'] == 'short' and 'long' in open_dirs:
                    log.info("SKIP {} — conflit long".format(sig['strat'])); continue
                open_position(state, sig, atr, candle_time, conn)
                open_dirs.add(sig['dir'])

            if signals: log.info("  -> {} signal(s)".format(len(signals)))
            print_dashboard(state, cache, candle_time)
            save_state(state)

        except KeyboardInterrupt:
            log.info("Arret."); save_state(state); break
        except Exception as e:
            log.error("Erreur: {}".format(e))
            import traceback; traceback.print_exc(); time.sleep(30)

        time.sleep(CHECK_INTERVAL)

    conn.close()
    log.info("Capital final: ${:,.2f}".format(state['capital']))

if __name__ == '__main__':
    main()
