"""
Exploration v5 — on cherche encore.
1. Three-bar pattern (1 grosse, 1 petite, 1 grosse dans le meme sens)
2. Opening candle direction (la 1ere bougie de chaque session predit la suite ?)
3. Range-based momentum (le range des N dernieres bougies comme filtre)
4. Sweep & reverse (le prix casse un high/low recent puis reverse immediatement)
5. London-NY overlap (14h30-16h = period de chevauchement = volatilite max)
6. Fading NY open (premier move de NY souvent faux ?)
7. Tokyo momentum into London (si Tokyo finit forte, London continue ?)
8. End-of-session scalp (dernieres 30 min de chaque session)
"""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
from dotenv import load_dotenv
from datetime import datetime, timedelta
load_dotenv()
from phase1_poc_calculator import get_conn, compute_atr, get_trading_days
from phase3_analyze import load_candles_5m

SLIPPAGE = 0.10

def sim_trail(cdf, pos, entry, d, sl, atr, mx, act, trail):
    best = entry
    stop = entry + sl*atr if d == 'short' else entry - sl*atr
    ta = False
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

def pr(trades, label, spread_rt=0.188):
    if len(trades) < 20:
        print("    {:60s}: n={:3d} --".format(label, len(trades)))
        return
    df = pd.DataFrame(trades).sort_values('date')
    n = len(df); mid = n // 2
    df['net'] = df['pnl_oz'] - spread_rt
    gp = df[df['net']>0]['net'].sum()
    gl = abs(df[df['net']<0]['net'].sum())+0.001
    pf = gp/gl; wr = (df['net']>0).mean()*100
    f1 = (df.iloc[:mid]['net']/df.iloc[:mid]['atr']).mean()
    f2 = (df.iloc[mid:]['net']/df.iloc[mid:]['atr']).mean()
    ok = "OK" if f1>0 and f2>0 else "!!" if f1<0 and f2<0 else "~ "
    flag = " ***" if pf >= 1.3 and f1>0 and f2>0 else ""
    print("    {:60s}: n={:4d} WR={:4.0f}% PF={:.2f} [{:+.3f}|{:+.3f}] {}{}".format(
        label, n, wr, pf, f1, f2, ok, flag))

conn = get_conn()
candles = load_candles_5m(conn)
daily_atr, global_atr = compute_atr(conn)
trading_days = get_trading_days(conn)

cur = conn.cursor()
cur.execute("""SELECT DATE_TRUNC('month', time), AVG(ask-bid)
    FROM market_ticks_xauusd WHERE ask>bid AND ask-bid<10 GROUP BY 1""")
monthly_spread = {r[0].strftime("%Y-%m"): float(r[1]) for r in cur.fetchall()}
cur.close()
SPREAD_RT = 2 * np.mean(list(monthly_spread.values()))

def prev_day(day):
    for di, d in enumerate(trading_days):
        if d >= day: return trading_days[di-1] if di > 0 else None
    return None

print("=" * 80)
print("EXPLORATION v5 (spread {:.3f} RT)".format(SPREAD_RT))
print("=" * 80)

# ══════════════════════════════════════════════════════
# 1. THREE-BAR PATTERN (grosse-petite-grosse dans le meme sens)
# ══════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("1. THREE-BAR — grosse, petite (inside), grosse continuation")
print("=" * 80)

for sess, sh, eh in [('TOK', 0, 6), ('LON', 8, 14)]:
    sm = 0; em = 30 if eh == 14 else 0
    for sl, act, trail in [(0.75, 0.5, 0.3)]:
        trades = []
        for day in trading_days:
            period = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,sh,sm,tz='UTC')) &
                             (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,eh,em,tz='UTC'))]
            if len(period) < 10: continue
            pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
            if atr == 0: continue
            for i in range(2, len(period)):
                c1 = period.iloc[i-2]; c2 = period.iloc[i-1]; c3 = period.iloc[i]
                b1 = abs(c1['close']-c1['open']); b2 = abs(c2['close']-c2['open']); b3 = abs(c3['close']-c3['open'])
                # c2 est inside (plus petit range)
                if not (c2['high'] <= c1['high'] and c2['low'] >= c1['low']): continue
                # c3 a un gros body dans le meme sens que c1
                if b3 < 0.3*atr: continue
                c1_dir = 1 if c1['close'] > c1['open'] else -1
                c3_dir = 1 if c3['close'] > c3['open'] else -1
                if c1_dir != c3_dir: continue
                d = 'long' if c3_dir > 0 else 'short'
                pi = candles.index.get_loc(period.index[i]); entry = c3['close']
                bars, ex = sim_trail(candles, pi, entry, d, sl, atr, 24, act, trail)
                pnl = (ex-entry) if d == 'long' else (entry-ex)
                trades.append({'date': day, 'pnl_oz': pnl, 'atr': atr}); break
        pr(trades, "{} 3bar SL={}".format(sess, sl))

# ══════════════════════════════════════════════════════
# 2. OPENING CANDLE — la 1ere bougie predit la direction ?
# ══════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("2. OPENING CANDLE — trader dans le sens de la 1ere bougie")
print("=" * 80)

for sess, sh, eh in [('TOK', 0, 6), ('LON', 8, 14), ('NY', 14, 21)]:
    sm = 30 if sh == 14 else 0; em = 30 if eh == 14 or eh == 21 else 0
    for min_body_atr in [0.2, 0.3, 0.5]:
        for sl, act, trail in [(0.75, 0.5, 0.3)]:
            trades = []
            for day in trading_days:
                period = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,sh,sm,tz='UTC')) &
                                 (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,eh,em,tz='UTC'))]
                if len(period) < 6: continue
                pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
                if atr == 0: continue
                first = period.iloc[0]
                body = first['close'] - first['open']
                if abs(body) < min_body_atr * atr: continue
                d = 'long' if body > 0 else 'short'
                # Entrer a la 2eme bougie
                if len(period) < 2: continue
                pi = candles.index.get_loc(period.index[1]); entry = period.iloc[1]['open']
                bars, ex = sim_trail(candles, pi, entry, d, sl, atr, 24, act, trail)
                pnl = (ex-entry) if d == 'long' else (entry-ex)
                trades.append({'date': day, 'pnl_oz': pnl, 'atr': atr})
            pr(trades, "{} 1st candle >{:.1f}ATR SL={}".format(sess, min_body_atr, sl))

# ══════════════════════════════════════════════════════
# 3. SWEEP & REVERSE — prix depasse un high/low recent puis reverse
# ══════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("3. SWEEP & REVERSE — liquidity grab puis retournement")
print("=" * 80)

for sess, sh, eh in [('TOK', 0, 6), ('LON', 8, 14)]:
    sm = 0; em = 30 if eh == 14 else 0
    for lookback in [6, 12]:
        for sl, act, trail in [(0.75, 0.5, 0.3)]:
            trades = []
            for day in trading_days:
                period = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,sh,sm,tz='UTC')) &
                                 (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,eh,em,tz='UTC'))]
                if len(period) < lookback + 6: continue
                pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
                if atr == 0: continue
                traded = False
                for i in range(lookback, len(period)):
                    if traded: break
                    r = period.iloc[i]
                    prev_high = period.iloc[i-lookback:i]['high'].max()
                    prev_low = period.iloc[i-lookback:i]['low'].min()
                    # Sweep high puis close bearish (sous le prev high)
                    if r['high'] > prev_high and r['close'] < prev_high and r['close'] < r['open']:
                        pi = candles.index.get_loc(period.index[i]); entry = r['close']
                        bars, ex = sim_trail(candles, pi, entry, 'short', sl, atr, 24, act, trail)
                        trades.append({'date': day, 'pnl_oz': entry-ex, 'atr': atr}); traded = True
                    # Sweep low puis close bullish
                    elif r['low'] < prev_low and r['close'] > prev_low and r['close'] > r['open']:
                        pi = candles.index.get_loc(period.index[i]); entry = r['close']
                        bars, ex = sim_trail(candles, pi, entry, 'long', sl, atr, 24, act, trail)
                        trades.append({'date': day, 'pnl_oz': ex-entry, 'atr': atr}); traded = True
            pr(trades, "{} sweep&rev lb={} SL={}".format(sess, lookback, sl))

# ══════════════════════════════════════════════════════
# 4. LONDON-NY OVERLAP (14h30-16h) — max volatilite
# ══════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("4. LONDON-NY OVERLAP — IB break 14h30-15h30 puis break")
print("=" * 80)

for direction in ['UP', 'DOWN']:
    for sl, act, trail in [(0.75, 0.5, 0.3), (1.0, 1.0, 0.5)]:
        trades = []
        for day in trading_days:
            obs_s = pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC')
            obs_e = pd.Timestamp(day.year,day.month,day.day,17,0,tz='UTC')
            period = candles[(candles['ts_dt'] >= obs_s) & (candles['ts_dt'] < obs_e)]
            if len(period) < 18: continue
            pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
            if atr == 0: continue
            ib = period.iloc[:12]
            lvl = ib['high'].max() if direction == 'UP' else ib['low'].min()
            rest = period.iloc[12:]
            for i in range(len(rest)):
                r = rest.iloc[i]
                trig = (direction == 'UP' and r['close'] > lvl) or (direction == 'DOWN' and r['close'] < lvl)
                if trig:
                    d = 'long' if direction == 'UP' else 'short'
                    pi = candles.index.get_loc(rest.index[i]); entry = r['close']
                    bars, ex = sim_trail(candles, pi, entry, d, sl, atr, 12, act, trail)
                    pnl = (ex-entry) if d == 'long' else (entry-ex)
                    trades.append({'date': day, 'pnl_oz': pnl, 'atr': atr}); break
        pr(trades, "Overlap {} SL={} act={} trail={}".format(direction, sl, act, trail))

# ══════════════════════════════════════════════════════
# 5. FADING NY OPEN (14h30-15h30 move -> inverse apres)
# ══════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("5. FADING NY OPEN — 1ere heure NY souvent faux move ?")
print("=" * 80)

for thresh in [0.5, 1.0, 1.5]:
    for sl, act, trail in [(0.75, 0.5, 0.3)]:
        trades = []
        for day in trading_days:
            pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
            if atr == 0: continue
            ny_s = pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC')
            ny_1h = pd.Timestamp(day.year,day.month,day.day,15,30,tz='UTC')
            ny_first = candles[(candles['ts_dt'] >= ny_s) & (candles['ts_dt'] < ny_1h)]
            if len(ny_first) < 10: continue
            ny_move = (ny_first.iloc[-1]['close'] - ny_first.iloc[0]['open']) / atr
            if abs(ny_move) < thresh: continue
            post = candles[candles['ts_dt'] >= ny_1h]
            if len(post) < 6: continue
            pi = candles.index.get_loc(post.index[0]); entry = post.iloc[0]['open']
            d = 'short' if ny_move > 0 else 'long'
            bars, ex = sim_trail(candles, pi, entry, d, sl, atr, 24, act, trail)
            pnl = (ex-entry) if d == 'long' else (entry-ex)
            trades.append({'date': day, 'pnl_oz': pnl, 'atr': atr})
        pr(trades, "Fade NY 1h >{:.1f}ATR SL={}".format(thresh, sl))

# ══════════════════════════════════════════════════════
# 6. TOKYO MOMENTUM INTO LONDON — si Tokyo finit forte, London continue ?
# ══════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("6. TOKYO END MOMENTUM — les 6 dernieres bougies de Tokyo fortes ?")
print("=" * 80)

for n_bars in [3, 6]:
    for min_move in [0.5, 1.0]:
        for sl, act, trail in [(0.75, 0.5, 0.3)]:
            trades = []
            for day in trading_days:
                pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
                if atr == 0: continue
                tok = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC')) &
                              (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
                if len(tok) < n_bars + 6: continue
                last_n = tok.iloc[-n_bars:]
                move = (last_n.iloc[-1]['close'] - last_n.iloc[0]['open']) / atr
                if abs(move) < min_move: continue
                lon = candles[candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
                if len(lon) < 6: continue
                pi = candles.index.get_loc(lon.index[0]); entry = lon.iloc[0]['open']
                d = 'long' if move > 0 else 'short'  # continuation
                bars, ex = sim_trail(candles, pi, entry, d, sl, atr, 24, act, trail)
                pnl = (ex-entry) if d == 'long' else (entry-ex)
                trades.append({'date': day, 'pnl_oz': pnl, 'atr': atr})
            pr(trades, "Tok end {}b >{:.1f}ATR cont SL={}".format(n_bars, min_move, sl))

# ══════════════════════════════════════════════════════
# 7. END-OF-SESSION SCALP — dernieres 30 min
# ══════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("7. END-OF-SESSION — 3 bougies bull/bear dans les 30 dernieres min")
print("=" * 80)

for sess, sh, eh in [('TOK', 5, 6), ('LON', 14, 14)]:
    sm = 0 if sess == 'TOK' else 0; em = 0 if sess == 'TOK' else 30
    for sl, act, trail in [(0.75, 0.5, 0.3)]:
        trades = []
        for day in trading_days:
            obs_s = pd.Timestamp(day.year,day.month,day.day,sh,sm,tz='UTC')
            obs_e = pd.Timestamp(day.year,day.month,day.day,eh,em,tz='UTC')
            period = candles[(candles['ts_dt'] >= obs_s) & (candles['ts_dt'] < obs_e)]
            if len(period) < 6: continue
            pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
            if atr == 0: continue
            last3 = period.iloc[-3:]
            all_bull = (last3['close'] > last3['open']).all()
            all_bear = (last3['close'] < last3['open']).all()
            if not all_bull and not all_bear: continue
            d = 'long' if all_bull else 'short'
            pi = candles.index.get_loc(period.index[-1]); entry = period.iloc[-1]['close']
            bars, ex = sim_trail(candles, pi, entry, d, sl, atr, 12, act, trail)
            pnl = (ex-entry) if d == 'long' else (entry-ex)
            trades.append({'date': day, 'pnl_oz': pnl, 'atr': atr})
        pr(trades, "{} end 3consec SL={}".format(sess, sl))

conn.close()
print("\n" + "=" * 80)
print("FIN v5")
print("=" * 80)
