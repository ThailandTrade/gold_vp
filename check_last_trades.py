"""
Verifie les derniers trades du backtest sur les 5 derniers jours
pour les 14 strats du portfolio champion.
"""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd, numpy as np
from dotenv import load_dotenv; load_dotenv()
from phase1_poc_calculator import get_conn, compute_atr, get_trading_days
from phase3_analyze import load_candles_5m

conn = get_conn()
candles = load_candles_5m(conn)
daily_atr, global_atr = compute_atr(conn)
trading_days = get_trading_days(conn)

cur = conn.cursor()
cur.execute("""SELECT DATE_TRUNC('month', time), AVG(ask-bid)
    FROM market_ticks_xauusd WHERE ask>bid AND ask-bid<10 GROUP BY 1""")
monthly_spread = {r[0].strftime('%Y-%m'): float(r[1]) for r in cur.fetchall()}
cur.close()
avg_sp = np.mean(list(monthly_spread.values()))

def prev_day(day):
    for di, d in enumerate(trading_days):
        if d >= day: return trading_days[di-1] if di > 0 else None
    return None
def get_sp(day):
    return 2 * monthly_spread.get(str(day.year)+"-"+str(day.month).zfill(2), avg_sp)

SL, ACT, TRAIL = 0.75, 0.5, 0.3
SLIPPAGE = 0.10

def sim_trail(cdf, pos, entry, d, sl, atr, mx, act, trail):
    best = entry; stop = entry + sl*atr if d == 'short' else entry - sl*atr; ta = False
    for j in range(1, mx+1):
        if pos+j >= len(cdf): break
        b = cdf.iloc[pos+j]
        if d == 'long':
            if b['low'] <= stop: return j, stop - SLIPPAGE
            if b['high'] > best: best = b['high']
            if not ta and (best-entry) >= act*atr: ta = True
            if ta: stop = max(stop, best - trail*atr)
        else:
            if b['high'] >= stop: return j, stop + SLIPPAGE
            if b['low'] < best: best = b['low']
            if not ta and (entry-best) >= act*atr: ta = True
            if ta: stop = min(stop, best + trail*atr)
    if pos+mx < len(cdf): return mx, cdf.iloc[pos+mx]['close']
    return mx, entry

print(f"Dernier jour: {trading_days[-1]}")
print(f"Derniere bougie: {candles.iloc[-1]['ts_dt']}")
print()

last_days = trading_days[-5:]
all_trades = []

for day in last_days:
    pd_ = prev_day(day)
    atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue

    def try_trade(name, d, e, pi):
        b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
        pnl = (ex-e) if d=='long' else (e-ex)
        reason = 'stop' if b < 24 else 'timeout'
        stop = e - SL*atr if d=='long' else e + SL*atr
        all_trades.append((day, name, d, e, ex, stop, pnl, b, reason, candles.iloc[pi]['ts_dt']))

    # A
    p = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(p) >= 18:
        lvl = p.iloc[:12]['high'].max()
        for i in range(12, len(p)):
            if p.iloc[i]['close'] > lvl:
                pi = candles.index.get_loc(p.index[i])
                try_trade('A', 'long', p.iloc[i]['close'], pi); break

    # C
    tok = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(tok) >= 10:
        m = (tok.iloc[-1]['close'] - tok.iloc[0]['open']) / atr
        if abs(m) >= 1.0:
            lon = candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
            if len(lon) >= 6:
                pi = candles.index.get_loc(lon.index[0])
                try_trade('C', 'short' if m>0 else 'long', lon.iloc[0]['open'], pi)

    # D
    tc = candles[candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC')]
    if len(tc) >= 5:
        lon = candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
        if len(lon) >= 6:
            gap = (lon.iloc[0]['open'] - tc.iloc[-1]['close']) / atr
            if abs(gap) >= 0.5:
                pi = candles.index.get_loc(lon.index[0])
                try_trade('D', 'long' if gap>0 else 'short', lon.iloc[0]['open'], pi)

    # E
    kz = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,10,0,tz='UTC'))]
    if len(kz) >= 20:
        m = (kz.iloc[-1]['close'] - kz.iloc[0]['open']) / atr
        if abs(m) >= 0.5:
            post = candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,10,0,tz='UTC')]
            if len(post) >= 6:
                pi = candles.index.get_loc(post.index[0])
                try_trade('E', 'short' if m>0 else 'long', post.iloc[0]['open'], pi)

    # F
    p = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(p) >= 8:
        for i in range(1, len(p)):
            b1b = p.iloc[i-1]['close']-p.iloc[i-1]['open']; b2b = p.iloc[i]['close']-p.iloc[i]['open']
            if abs(b1b)<0.5*atr or abs(b2b)<0.5*atr: continue
            if b1b*b2b >= 0 or abs(b2b) <= abs(b1b): continue
            pi = candles.index.get_loc(p.index[i])
            try_trade('F', 'long' if b2b>0 else 'short', p.iloc[i]['close'], pi); break

    # G
    p = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,21,30,tz='UTC'))]
    if len(p) >= 6:
        body = p.iloc[0]['close'] - p.iloc[0]['open']
        if abs(body) >= 0.3*atr and len(p) >= 2:
            pi = candles.index.get_loc(p.index[1])
            try_trade('G', 'long' if body>0 else 'short', p.iloc[1]['open'], pi)

    # H
    tok = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(tok) >= 9:
        last3 = tok.iloc[-3:]
        m = (last3.iloc[-1]['close'] - last3.iloc[0]['open']) / atr
        if abs(m) >= 1.0:
            lon = candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
            if len(lon) >= 6:
                pi = candles.index.get_loc(lon.index[0])
                try_trade('H', 'long' if m>0 else 'short', lon.iloc[0]['open'], pi)

    # I
    ny1 = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,15,30,tz='UTC'))]
    if len(ny1) >= 10:
        m = (ny1.iloc[-1]['close'] - ny1.iloc[0]['open']) / atr
        if abs(m) >= 1.0:
            post = candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,15,30,tz='UTC')]
            if len(post) >= 6:
                pi = candles.index.get_loc(post.index[0])
                try_trade('I', 'short' if m>0 else 'long', post.iloc[0]['open'], pi)

    # J
    p = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))]
    if len(p) >= 6:
        body = p.iloc[0]['close'] - p.iloc[0]['open']
        if abs(body) >= 0.3*atr and len(p) >= 2:
            pi = candles.index.get_loc(p.index[1])
            try_trade('J', 'long' if body>0 else 'short', p.iloc[1]['open'], pi)

    # O
    sess = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(sess) >= 6:
        for i in range(len(sess)):
            body = sess.iloc[i]['close'] - sess.iloc[i]['open']
            if abs(body) >= 1.0*atr:
                pi = candles.index.get_loc(sess.index[i])
                try_trade('O', 'long' if body>0 else 'short', sess.iloc[i]['close'], pi); break

    # P
    ny = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,21,30,tz='UTC'))]
    if len(ny) >= 12:
        orb_h = ny.iloc[:6]['high'].max(); orb_l = ny.iloc[:6]['low'].min()
        for i in range(6, len(ny)):
            r = ny.iloc[i]
            if r['close'] > orb_h:
                pi = candles.index.get_loc(ny.index[i])
                try_trade('P', 'long', r['close'], pi); break
            elif r['close'] < orb_l:
                pi = candles.index.get_loc(ny.index[i])
                try_trade('P', 'short', r['close'], pi); break

    # Q
    sess = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))]
    if len(sess) >= 6:
        for i in range(1, len(sess)):
            pb = sess.iloc[i-1]; cb = sess.iloc[i]
            if pb['close']<pb['open'] and cb['close']>cb['open'] and cb['open']<=pb['close'] and cb['close']>=pb['open'] and abs(cb['close']-cb['open'])>=0.3*atr:
                pi = candles.index.get_loc(sess.index[i])
                try_trade('Q', 'long', cb['close'], pi); break
            if pb['close']>pb['open'] and cb['close']<cb['open'] and cb['open']>=pb['close'] and cb['close']<=pb['open'] and abs(cb['close']-cb['open'])>=0.3*atr:
                pi = candles.index.get_loc(sess.index[i])
                try_trade('Q', 'short', cb['close'], pi); break

    # R
    sess = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(sess) >= 6:
        for i in range(2, len(sess)):
            c1=sess.iloc[i-2]; c2=sess.iloc[i-1]; c3=sess.iloc[i]
            b1=c1['close']-c1['open']; b2=c2['close']-c2['open']; b3=c3['close']-c3['open']
            if b1*b2>0 and b2*b3>0 and min(abs(b1),abs(b2),abs(b3))>0.1*atr and abs(b1+b2+b3)>=0.5*atr:
                pi = candles.index.get_loc(sess.index[i])
                try_trade('R', 'long' if b3>0 else 'short', c3['close'], pi); break

    # S
    sess = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))]
    if len(sess) >= 6:
        for i in range(2, len(sess)):
            c1=sess.iloc[i-2]; c2=sess.iloc[i-1]; c3=sess.iloc[i]
            b1=c1['close']-c1['open']; b2=c2['close']-c2['open']; b3=c3['close']-c3['open']
            if b1*b2>0 and b2*b3>0 and min(abs(b1),abs(b2),abs(b3))>0.1*atr and abs(b1+b2+b3)>=0.5*atr:
                pi = candles.index.get_loc(sess.index[i])
                try_trade('S', 'short' if b3>0 else 'long', c3['close'], pi); break

conn.close()

# Afficher
print("="*100)
print(f"  BACKTEST — 5 derniers jours ({last_days[0]} a {last_days[-1]})")
print("="*100)
print(f"  {'Date':12s} {'Strat':5s} {'Dir':5s} {'Heure':6s} {'Entry':>9s} {'Exit':>9s} {'Stop':>9s} {'PnL':>8s} {'Bars':>4s} {'Raison':>7s}")
for day, name, d, e, ex, stop, pnl, bars, reason, time in sorted(all_trades, key=lambda x: (x[0], x[9])):
    print(f"  {str(day):12s} {name:5s} {d:5s} {time.strftime('%H:%M'):6s} {e:9.2f} {ex:9.2f} {stop:9.2f} {pnl:+8.2f} {bars:4d} {reason:>7s}")
print(f"\n  Total: {len(all_trades)} trades")

# Comparer avec le paper trade du jour
print("\n" + "="*100)
print("  PAPER TRADES (live)")
print("="*100)
print(f"  {'Date':12s} {'Strat':5s} {'Dir':5s} {'Heure':6s} {'Entry':>9s} {'Exit':>9s} {'PnL_oz':>8s} {'Bars':>4s} {'Raison':>7s}")
import json
with open('paper_trades.json') as f:
    state = json.load(f)
for t in state['trades']:
    print(f"  {'2026-03-18':12s} {t['strat']:5s} {t['dir']:5s} {t['entry_time'][11:16]:6s} {t['entry']:9.2f} {t['exit']:9.2f} {t['pnl_oz']:+8.2f} {t['bars_held']:4d} {t['exit_reason']:>7s}")
print("="*100)
