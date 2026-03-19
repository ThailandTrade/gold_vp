"""
Paper Trading Live — Compte PROP FIRM (6 strats, risk 0.5%, PF 2.12)
AA+AC+C+D+E+H
No look-ahead backtest v7. DD -15.1%, 12/13 mois+.
Usage: python live_propfirm.py [--reset]
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
RISK_PCT = 0.005
CHECK_INTERVAL = 1
LOG_FILE = "paper_propfirm.json"
SL, ACT, TRAIL, MAX_BARS = 0.75, 0.5, 0.3, 24

STRATS = ['AA','AC','C','D','E','H']

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
            'ib_levels': {}, 'daily_cache': {}, '_triggered': {}, 'last_candle_ts': 0}

def save_state(state):
    with open(LOG_FILE, 'w') as f: json.dump(state, f, indent=2, default=str)

def reset_state():
    state = {'capital': CAPITAL_INITIAL, 'trades': [], 'open_positions': [],
             'ib_levels': {}, 'daily_cache': {}, '_triggered': {}, 'last_candle_ts': 0}
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

# ── POSITION MANAGEMENT ──────────────────────────────

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
        # 2. Best update
        if d == 'long' and last['high'] > pos.get('best', pos['entry']): pos['best'] = last['high']
        if d == 'short' and last['low'] < pos.get('best', pos['entry']): pos['best'] = last['low']
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
    ibs = state.setdefault('ib_levels', {}).setdefault(str(today), {})

    # A: IB Tokyo 0h-1h break UP (backtest exige >=18 bougies dans tout Tokyo)
    if 'A_done' not in ibs and hour >= 1.0:
        s = pd.Timestamp(today.year,today.month,today.day,0,0,tz='UTC')
        tok_all = candles[(candles['ts_dt']>=s) & (candles['ts_dt']<pd.Timestamp(today.year,today.month,today.day,6,0,tz='UTC'))]
        ib = candles[(candles['ts_dt']>=s) & (candles['ts_dt']<s+pd.Timedelta(hours=1))]
        if len(ib) >= 12 and len(tok_all) >= 18: ibs['A_high'] = float(ib['high'].max()); ibs['A_done'] = True
    if 'A_high' in ibs and 'A_trig' not in ibs and 1.0 <= hour < 6.0:
        if candles.iloc[-1]['close'] > ibs['A_high']:
            signals.append({'strat':'A','dir':'long'}); ibs['A_trig'] = True

    # C: FADE Tokyo > 1 ATR → inverse London open
    if 8.0 <= hour < 8.1:
        k = str(today)+'_C'
        if k not in trig:
            tok = candles[(candles['ts_dt']>=pd.Timestamp(today.year,today.month,today.day,0,0,tz='UTC')) &
                          (candles['ts_dt']<pd.Timestamp(today.year,today.month,today.day,6,0,tz='UTC'))]
            if len(tok) >= 10:
                m = (tok.iloc[-1]['close'] - tok.iloc[0]['open']) / atr
                if abs(m) >= 1.0:
                    signals.append({'strat':'C','dir':'short' if m>0 else 'long'}); trig[k] = True

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

    # F: 2BAR Tokyo two-bar reversal (backtest exige >=8 bougies Tokyo)
    if 0.0 <= hour < 6.0:
        k = str(today)+'_F'
        if k not in trig:
            tok_f = candles[(candles['ts_dt']>=pd.Timestamp(today.year,today.month,today.day,0,0,tz='UTC')) &
                            (candles['ts_dt']<pd.Timestamp(today.year,today.month,today.day,6,0,tz='UTC'))]
            if len(tok_f) >= 2:  # F: 2 bougies min
                b1 = tok_f.iloc[-2]; b2 = tok_f.iloc[-1]
                b1b = b1['close']-b1['open']; b2b = b2['close']-b2['open']
                if abs(b1b)>=0.5*atr and abs(b2b)>=0.5*atr and b1b*b2b<0 and abs(b2b)>abs(b1b):
                    signals.append({'strat':'F','dir':'long' if b2b>0 else 'short'}); trig[k] = True

    # G: NY 1st candle > 0.3 ATR
    if 14.5 <= hour < 14.6:
        k = str(today)+'_G'
        if k not in trig:
            first = candles.iloc[-1]; body = first['close'] - first['open']
            if abs(body) >= 0.3 * atr:
                signals.append({'strat':'G','dir':'long' if body>0 else 'short'}); trig[k] = True

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

    # I: FADENY 1ere heure NY > 1 ATR → inverse
    if 15.5 <= hour < 15.6:
        k = str(today)+'_I'
        if k not in trig:
            ny1 = candles[(candles['ts_dt']>=pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC')) &
                          (candles['ts_dt']<pd.Timestamp(today.year,today.month,today.day,15,30,tz='UTC'))]
            if len(ny1) >= 10:
                m = (ny1.iloc[-1]['close'] - ny1.iloc[0]['open']) / atr
                if abs(m) >= 1.0:
                    signals.append({'strat':'I','dir':'short' if m>0 else 'long'}); trig[k] = True

    # J: LON 1st candle > 0.3 ATR
    if 8.0 <= hour < 8.1:
        k = str(today)+'_J'
        if k not in trig:
            first = candles.iloc[-1]; body = first['close'] - first['open']
            if abs(body) >= 0.3 * atr:
                signals.append({'strat':'J','dir':'long' if body>0 else 'short'}); trig[k] = True

    # O: Big candle >1ATR Tokyo continuation (min 6 bougies Tokyo)
    if 0.0 <= hour < 6.0:
        k = str(today)+'_O'
        if k not in trig:
            tok = candles[(candles['ts_dt']>=pd.Timestamp(today.year,today.month,today.day,0,0,tz='UTC')) &
                          (candles['ts_dt']<pd.Timestamp(today.year,today.month,today.day,6,0,tz='UTC'))]
            if len(tok) >= 1:  # O: 1 bougie min
                r = candles.iloc[-1]; body = r['close'] - r['open']
                if abs(body) >= 1.0 * atr:
                    signals.append({'strat':'O','dir':'long' if body>0 else 'short'}); trig[k] = True

    # P: ORB NY 30min (break apres 15h00)
    if 15.0 <= hour < 21.5:
        k = str(today)+'_P'
        if k not in trig:
            # Calculer ORB = range des 6 premieres bougies NY (14:30-15:00)
            if 'P_high' not in ibs:
                orb = candles[(candles['ts_dt']>=pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC')) &
                              (candles['ts_dt']<pd.Timestamp(today.year,today.month,today.day,15,0,tz='UTC'))]
                if len(orb) >= 6:
                    ibs['P_high'] = float(orb['high'].max()); ibs['P_low'] = float(orb['low'].min())
            if 'P_high' in ibs:
                r = candles.iloc[-1]
                if r['close'] > ibs['P_high']:
                    signals.append({'strat':'P','dir':'long'}); trig[k] = True
                elif r['close'] < ibs['P_low']:
                    signals.append({'strat':'P','dir':'short'}); trig[k] = True

    # Q: Engulfing London (les 2 bougies doivent etre dans London)
    if 8.0 <= hour < 14.5 and len(candles) >= 3:
        k = str(today)+'_Q'
        if k not in trig:
            # Filtrer bougies London du jour
            lon = candles[(candles['ts_dt']>=pd.Timestamp(today.year,today.month,today.day,8,0,tz='UTC')) &
                          (candles['ts_dt']<pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC'))]
            if len(lon) >= 2:  # Q: 2 bougies min
                prev_b = lon.iloc[-2]; cur_b = lon.iloc[-1]
                # Bullish engulfing
                if (prev_b['close'] < prev_b['open'] and cur_b['close'] > cur_b['open'] and
                    cur_b['open'] <= prev_b['close'] and cur_b['close'] >= prev_b['open'] and
                    abs(cur_b['close']-cur_b['open']) >= 0.3*atr):
                    signals.append({'strat':'Q','dir':'long'}); trig[k] = True
                # Bearish engulfing
                elif (prev_b['close'] > prev_b['open'] and cur_b['close'] < cur_b['open'] and
                      cur_b['open'] >= prev_b['close'] and cur_b['close'] <= prev_b['open'] and
                      abs(cur_b['close']-cur_b['open']) >= 0.3*atr):
                    signals.append({'strat':'Q','dir':'short'}); trig[k] = True

    # R: 3 soldiers/crows Tokyo continuation (3 bougies dans Tokyo)
    if 0.0 <= hour < 6.0:
        k = str(today)+'_R'
        if k not in trig:
            tok = candles[(candles['ts_dt']>=pd.Timestamp(today.year,today.month,today.day,0,0,tz='UTC')) &
                          (candles['ts_dt']<pd.Timestamp(today.year,today.month,today.day,6,0,tz='UTC'))]
            if len(tok) >= 3:  # R: 3 bougies min
                c1 = tok.iloc[-3]; c2 = tok.iloc[-2]; c3 = tok.iloc[-1]
                b1 = c1['close']-c1['open']; b2 = c2['close']-c2['open']; b3 = c3['close']-c3['open']
                if b1*b2 > 0 and b2*b3 > 0 and min(abs(b1),abs(b2),abs(b3)) > 0.1*atr:
                    total = abs(b1+b2+b3)
                    if total >= 0.5*atr:
                        signals.append({'strat':'R','dir':'long' if b3>0 else 'short'}); trig[k] = True

    # S: 3 soldiers/crows London reversal (3 bougies dans London)
    if 8.0 <= hour < 14.5:
        k = str(today)+'_S'
        if k not in trig:
            lon = candles[(candles['ts_dt']>=pd.Timestamp(today.year,today.month,today.day,8,0,tz='UTC')) &
                          (candles['ts_dt']<pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC'))]
            if len(lon) >= 3:  # S: 3 bougies min
                c1 = lon.iloc[-3]; c2 = lon.iloc[-2]; c3 = lon.iloc[-1]
                b1 = c1['close']-c1['open']; b2 = c2['close']-c2['open']; b3 = c3['close']-c3['open']
                if b1*b2 > 0 and b2*b3 > 0 and min(abs(b1),abs(b2),abs(b3)) > 0.1*atr:
                    total = abs(b1+b2+b3)
                    if total >= 0.5*atr:
                        # Reversal = direction opposee
                        signals.append({'strat':'S','dir':'short' if b3>0 else 'long'}); trig[k] = True

    # V: Candle ratio 5/6 Tokyo → continuation
    if 0.0 <= hour < 6.0:
        k = str(today)+'_V'
        if k not in trig:
            tok = candles[(candles['ts_dt']>=pd.Timestamp(today.year,today.month,today.day,0,0,tz='UTC')) &
                          (candles['ts_dt']<pd.Timestamp(today.year,today.month,today.day,6,0,tz='UTC'))]
            if len(tok) >= 7:  # V: 7 bougies min
                last6 = tok.iloc[-6:]
                n_bull = (last6['close'] > last6['open']).sum()
                if n_bull >= 5:
                    signals.append({'strat':'V','dir':'long'}); trig[k] = True
                elif n_bull <= 1:
                    signals.append({'strat':'V','dir':'short'}); trig[k] = True

    # Z: 3 jours consecutifs meme sens → reversal London open
    if 8.0 <= hour < 8.1:
        k = str(today)+'_Z'
        if k not in trig:
            # Trouver les 3 jours precedents
            prev_days = []
            for c_date in sorted(set(candles['date'].unique()), reverse=True):
                if c_date < today:
                    prev_days.append(c_date)
                    if len(prev_days) == 3: break
            if len(prev_days) == 3:
                dirs = []
                for pd_z in prev_days:
                    dc = candles[candles['date'] == pd_z]
                    if len(dc) >= 10:
                        dirs.append(1 if dc.iloc[-1]['close'] > dc.iloc[0]['open'] else -1)
                if len(dirs) == 3 and len(set(dirs)) == 1:
                    signals.append({'strat':'Z','dir':'short' if dirs[0] > 0 else 'long'}); trig[k] = True

    # AA: Close near extreme London (close dans top/bottom 10% du range, body>0.2ATR)
    if 8.0 <= hour < 14.5:
        k = str(today)+'_AA'
        if k not in trig:
            lon = candles[(candles['ts_dt']>=pd.Timestamp(today.year,today.month,today.day,8,0,tz='UTC')) &
                          (candles['ts_dt']<pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC'))]
            if len(lon) >= 1:  # AA: 1 bougie min
                r = lon.iloc[-1]; rng = r['high'] - r['low']
                if rng >= 0.3*atr and abs(r['close']-r['open']) >= 0.2*atr:
                    pos_in_range = (r['close'] - r['low']) / rng
                    if pos_in_range >= 0.9:
                        signals.append({'strat':'AA','dir':'long'}); trig[k] = True
                    elif pos_in_range <= 0.1:
                        signals.append({'strat':'AA','dir':'short'}); trig[k] = True

    # AC: Absorption Tokyo (bougie couvre le range des 3 precedentes, body>0.5ATR)
    if 0.0 <= hour < 6.0:
        k = str(today)+'_AC'
        if k not in trig:
            tok = candles[(candles['ts_dt']>=pd.Timestamp(today.year,today.month,today.day,0,0,tz='UTC')) &
                          (candles['ts_dt']<pd.Timestamp(today.year,today.month,today.day,6,0,tz='UTC'))]
            if len(tok) >= 4:  # AC: 4 bougies min
                r = tok.iloc[-1]
                if len(tok) >= 4:
                    prev3_h = tok.iloc[-4:-1]['high'].max()
                    prev3_l = tok.iloc[-4:-1]['low'].min()
                    body = abs(r['close'] - r['open'])
                    if r['high'] >= prev3_h and r['low'] <= prev3_l and body >= 0.5*atr:
                        d = 'long' if r['close'] > r['open'] else 'short'
                        signals.append({'strat':'AC','dir':d}); trig[k] = True

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

            # Reset ib_levels au changement de jour
            if str(today) not in state.get('ib_levels', {}):
                state['ib_levels'] = {str(today): {}}

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
