"""
Paper Trading Live — AA+D+E+F+H+NY6+NY16+NY17+O
Config: TRAIL SL=1.0 ACT=0.5 TRAIL=0.75 MX=12 (sur CLOSE)
PF 1.54, WR 44%, DD -26.2%, Calmar 481, +12624%
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
SL, ACT, TRAIL, MAX_BARS = 1.0, 0.5, 0.75, 12  # trailing sur close

STRATS = ['AA','D','E','F','H','NY6','NY16','NY17','O']

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
        # 5. Timeout
        if pos['bars_held'] >= MAX_BARS:
            pos['exit'] = last['close']; pos['exit_reason'] = 'timeout'; closed.append(pos)

    for c in closed:
        state['open_positions'].remove(c)
        if c['exit_reason'] == 'timeout':
            tick = get_current_bidask(conn)
            if tick:
                c['exit'] = tick['bid'] if c['strat_dir'] == 'long' else tick['ask']
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
    signals = []; hour = candle_time.hour + candle_time.minute / 60.0
    trig = state.setdefault('_triggered', {})

    # AA: Close near extreme London (pin bar, close dans top/bottom 10% du range)
    if 8.0 <= hour < 14.5:
        k = str(today)+'_AA'
        if k not in trig:
            r = candles.iloc[-1]; rng = r['high'] - r['low']
            if rng >= 0.3*atr and abs(r['close']-r['open']) >= 0.2*atr:
                pos_in_range = (r['close'] - r['low']) / rng
                if pos_in_range >= 0.9:
                    signals.append({'strat':'AA','dir':'long'}); trig[k] = True
                elif pos_in_range <= 0.1:
                    signals.append({'strat':'AA','dir':'short'}); trig[k] = True

    # D: GAP Tokyo-London > 0.5 ATR continuation
    if 8.0 <= hour < 8.1:
        k = str(today)+'_D'
        if k not in trig:
            tc = candles[candles['ts_dt']<pd.Timestamp(today.year,today.month,today.day,6,0,tz='UTC')]
            if len(tc) >= 5:
                gap = (candles.iloc[-1]['open'] - tc.iloc[-1]['close']) / atr
                if abs(gap) >= 0.5:
                    signals.append({'strat':'D','dir':'long' if gap>0 else 'short'}); trig[k] = True

    # E: KZ London Kill Zone 8h-10h fade
    if 10.0 <= hour < 10.1:
        k = str(today)+'_E'
        if k not in trig:
            kz = candles[(candles['ts_dt']>=pd.Timestamp(today.year,today.month,today.day,8,0,tz='UTC')) &
                         (candles['ts_dt']<pd.Timestamp(today.year,today.month,today.day,10,0,tz='UTC'))]
            if len(kz) >= 20:
                m = (kz.iloc[-1]['close'] - kz.iloc[0]['open']) / atr
                if abs(m) >= 0.5:
                    signals.append({'strat':'E','dir':'short' if m>0 else 'long'}); trig[k] = True

    # F: 2BAR Tokyo two-bar reversal
    if 0.0 <= hour < 6.0:
        k = str(today)+'_F'
        if k not in trig:
            tok_f = candles[(candles['ts_dt']>=pd.Timestamp(today.year,today.month,today.day,0,0,tz='UTC')) &
                            (candles['ts_dt']<pd.Timestamp(today.year,today.month,today.day,6,0,tz='UTC'))]
            if len(tok_f) >= 2:
                b1 = tok_f.iloc[-2]; b2 = tok_f.iloc[-1]
                b1b = b1['close']-b1['open']; b2b = b2['close']-b2['open']
                if abs(b1b)>=0.5*atr and abs(b2b)>=0.5*atr and b1b*b2b<0 and abs(b2b)>abs(b1b):
                    signals.append({'strat':'F','dir':'long' if b2b>0 else 'short'}); trig[k] = True

    # H: TOKEND 3 dernieres bougies Tokyo > 1 ATR continuation
    if 8.0 <= hour < 8.1:
        k = str(today)+'_H'
        if k not in trig:
            tok = candles[(candles['ts_dt']>=pd.Timestamp(today.year,today.month,today.day,0,0,tz='UTC')) &
                          (candles['ts_dt']<pd.Timestamp(today.year,today.month,today.day,6,0,tz='UTC'))]
            if len(tok) >= 9:
                last3 = tok.iloc[-3:]
                m = (last3.iloc[-1]['close'] - last3.iloc[0]['open']) / atr
                if abs(m) >= 1.0:
                    signals.append({'strat':'H','dir':'long' if m>0 else 'short'}); trig[k] = True

    # O: Big candle Tokyo > 1 ATR continuation
    if 0.0 <= hour < 6.0:
        k = str(today)+'_O'
        if k not in trig:
            r = candles.iloc[-1]; body = r['close'] - r['open']
            if abs(body) >= 1.0 * atr:
                signals.append({'strat':'O','dir':'long' if body>0 else 'short'}); trig[k] = True

    # NY6: GAP London close vs NY open > 0.5 ATR continuation
    if 14.5 <= hour < 14.6:
        k = str(today)+'_NY6'
        if k not in trig:
            lon = candles[(candles['ts_dt']>=pd.Timestamp(today.year,today.month,today.day,8,0,tz='UTC')) &
                          (candles['ts_dt']<pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC'))]
            if len(lon) >= 5:
                gap = (candles.iloc[-1]['open'] - lon.iloc[-1]['close']) / atr
                if abs(gap) >= 0.5:
                    signals.append({'strat':'NY6','dir':'long' if gap>0 else 'short'}); trig[k] = True

    # NY16: 3 dernieres bougies London > 1 ATR, continuation NY
    if 14.5 <= hour < 14.6:
        k = str(today)+'_NY16'
        if k not in trig:
            lon = candles[(candles['ts_dt']>=pd.Timestamp(today.year,today.month,today.day,8,0,tz='UTC')) &
                          (candles['ts_dt']<pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC'))]
            if len(lon) >= 9:
                last3 = lon.iloc[-3:]
                m = (last3.iloc[-1]['close'] - last3.iloc[0]['open']) / atr
                if abs(m) >= 1.0:
                    signals.append({'strat':'NY16','dir':'long' if m>0 else 'short'}); trig[k] = True

    # NY17: 3 dernieres bougies London > 0.5 ATR, continuation NY
    if 14.5 <= hour < 14.6:
        k = str(today)+'_NY17'
        if k not in trig:
            lon = candles[(candles['ts_dt']>=pd.Timestamp(today.year,today.month,today.day,8,0,tz='UTC')) &
                          (candles['ts_dt']<pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC'))]
            if len(lon) >= 9:
                last3 = lon.iloc[-3:]
                m = (last3.iloc[-1]['close'] - last3.iloc[0]['open']) / atr
                if abs(m) >= 0.5:
                    signals.append({'strat':'NY17','dir':'long' if m>0 else 'short'}); trig[k] = True

    return signals

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
