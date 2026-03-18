"""
Exploration v6 — derniers concepts.
"""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
from dotenv import load_dotenv
from datetime import datetime, timedelta
load_dotenv()
from phase1_poc_calculator import get_conn, compute_atr, get_trading_days
from phase3_analyze import load_candles_5m

SLIPPAGE = 0.0  # pas de slippage fixe

def sim_trail(cdf, pos, entry, d, sl, atr, mx, act=0.5, trail=0.3):
    best = entry
    stop = entry + sl*atr if d == 'short' else entry - sl*atr
    ta = False
    for j in range(1, mx+1):
        if pos+j >= len(cdf): break
        b = cdf.iloc[pos+j]
        if d == 'long':
            if b['low'] <= stop: return j, stop
            if b['high'] > best: best = b['high']
            if not ta and (best-entry) >= act*atr: ta = True
            if ta: stop = max(stop, best - trail*atr)
        else:
            if b['high'] >= stop: return j, stop
            if b['low'] < best: best = b['low']
            if not ta and (entry-best) >= act*atr: ta = True
            if ta: stop = min(stop, best + trail*atr)
    if pos+mx < len(cdf): return mx, cdf.iloc[pos+mx]['close']
    return mx, entry

def pr(trades, label, spread_rt=0.188):
    if len(trades) < 20:
        print("    {:60s}: n={:3d} --".format(label, len(trades))); return
    df = pd.DataFrame(trades).sort_values('date')
    n = len(df); mid = n // 2
    df['net'] = df['pnl_oz'] - spread_rt
    gp = df[df['net']>0]['net'].sum(); gl = abs(df[df['net']<0]['net'].sum())+0.001
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

def get_sp(day):
    return 2 * monthly_spread.get(str(day.year)+"-"+str(day.month).zfill(2), SPREAD_RT/2)

print("=" * 80)
print("EXPLORATION v6 (spread {:.3f} RT, no slippage)".format(SPREAD_RT))
print("=" * 80)

# ══════════════════════════════════════════════════════
# 1. SESSION ALIGNMENT — Tokyo + London meme sens → NY continue ?
# ══════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("1. SESSION ALIGNMENT — Tok+Lon meme sens -> NY ?")
print("=" * 80)

for min_move in [0.5, 1.0]:
    for sl in [0.75]:
        trades_cont = []; trades_rev = []
        for day in trading_days:
            pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
            if atr == 0: continue
            tok = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC')) &
                          (candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
            lon = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')) &
                          (candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))]
            if len(tok) < 10 or len(lon) < 10: continue
            tok_m = (tok.iloc[-1]['close'] - tok.iloc[0]['open']) / atr
            lon_m = (lon.iloc[-1]['close'] - lon.iloc[0]['open']) / atr
            if abs(tok_m) < min_move or abs(lon_m) < min_move: continue
            if (tok_m > 0) != (lon_m > 0): continue  # pas aligne
            ny = candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC')]
            if len(ny) < 6: continue
            pi = candles.index.get_loc(ny.index[0]); entry = ny.iloc[0]['open']
            # Continuation
            d = 'long' if tok_m > 0 else 'short'
            b, ex = sim_trail(candles, pi, entry, d, sl, atr, 24)
            pnl = (ex-entry) if d == 'long' else (entry-ex)
            trades_cont.append({'date': day, 'pnl_oz': pnl, 'atr': atr})
            # Reversion
            d2 = 'short' if tok_m > 0 else 'long'
            b2, ex2 = sim_trail(candles, pi, entry, d2, sl, atr, 24)
            pnl2 = (ex2-entry) if d2 == 'long' else (entry-ex2)
            trades_rev.append({'date': day, 'pnl_oz': pnl2, 'atr': atr})
        pr(trades_cont, "Tok+Lon>{:.1f}ATR aligned -> NY CONT".format(min_move))
        pr(trades_rev, "Tok+Lon>{:.1f}ATR aligned -> NY REV".format(min_move))

# ══════════════════════════════════════════════════════
# 2. FAILED IB BREAK → REVERSE
# ══════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("2. FAILED IB BREAK — break UP puis echec → SHORT")
print("=" * 80)

for sess, sh, eh, ib_b in [('TOK', 0, 6, 12)]:
    for sl in [0.75]:
        trades = []
        for day in trading_days:
            p = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,sh,0,tz='UTC')) &
                        (candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,eh,0,tz='UTC'))]
            if len(p) < ib_b + 12: continue
            pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
            if atr == 0: continue
            ib_high = p.iloc[:ib_b]['high'].max()
            ib_low = p.iloc[:ib_b]['low'].min()
            rest = p.iloc[ib_b:]
            broke_up = False; broke_down = False
            for i in range(len(rest)):
                r = rest.iloc[i]
                if not broke_up and r['close'] > ib_high:
                    broke_up = True; continue
                if broke_up and r['close'] < ib_high:
                    # Failed break UP → SHORT
                    pi = candles.index.get_loc(rest.index[i]); entry = r['close']
                    b, ex = sim_trail(candles, pi, entry, 'short', sl, atr, 24)
                    trades.append({'date': day, 'pnl_oz': entry-ex, 'atr': atr}); break
                if not broke_down and r['close'] < ib_low:
                    broke_down = True; continue
                if broke_down and r['close'] > ib_low:
                    # Failed break DOWN → LONG
                    pi = candles.index.get_loc(rest.index[i]); entry = r['close']
                    b, ex = sim_trail(candles, pi, entry, 'long', sl, atr, 24)
                    trades.append({'date': day, 'pnl_oz': ex-entry, 'atr': atr}); break
        pr(trades, "{} failed IB break -> reverse SL={}".format(sess, sl))

# ══════════════════════════════════════════════════════
# 3. INTRA-SESSION REVERSAL — 1ere moitie vs 2eme moitie
# ══════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("3. INTRA-SESSION REVERSAL — 1ere moitie predit reversion 2eme ?")
print("=" * 80)

for sess, sh, mid_h, eh in [('TOK', 0, 3, 6), ('LON', 8, 11, 14)]:
    em = 30 if eh == 14 else 0
    for min_move in [0.5, 1.0, 1.5]:
        for sl in [0.75]:
            trades = []
            for day in trading_days:
                pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
                if atr == 0: continue
                first_half = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,sh,0,tz='UTC')) &
                                     (candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,mid_h,0,tz='UTC'))]
                if len(first_half) < 10: continue
                m = (first_half.iloc[-1]['close'] - first_half.iloc[0]['open']) / atr
                if abs(m) < min_move: continue
                second_start = candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,mid_h,0,tz='UTC')]
                if len(second_start) < 6: continue
                pi = candles.index.get_loc(second_start.index[0]); entry = second_start.iloc[0]['open']
                d = 'short' if m > 0 else 'long'  # reversion
                b, ex = sim_trail(candles, pi, entry, d, sl, atr, 24)
                pnl = (ex-entry) if d == 'long' else (entry-ex)
                trades.append({'date': day, 'pnl_oz': pnl, 'atr': atr})
            pr(trades, "{} 1st half >{:.1f}ATR -> 2nd REV SL={}".format(sess, min_move, sl))

# ══════════════════════════════════════════════════════
# 4. NARROW DAY → EXPANSION
# ══════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("4. NARROW DAY — jour etroit → break le lendemain")
print("=" * 80)

# Calculer le range journalier
daily_ranges = {}
for day in trading_days:
    dc = candles[candles['date'] == day]
    if len(dc) < 20: continue
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    daily_ranges[day] = (dc['high'].max() - dc['low'].min()) / atr

if daily_ranges:
    range_vals = list(daily_ranges.values())
    range_med = np.median(range_vals)
    range_q25 = np.percentile(range_vals, 25)
    print("  Range journalier: Q25={:.2f} Med={:.2f}".format(range_q25, range_med))

    for max_range in [range_q25, range_med * 0.5]:
        for sl in [0.75]:
            trades = []
            for day_idx in range(1, len(trading_days)):
                prev_d = trading_days[day_idx - 1]
                curr_d = trading_days[day_idx]
                if prev_d not in daily_ranges: continue
                if daily_ranges[prev_d] > max_range: continue
                atr = daily_atr.get(prev_d, global_atr)
                if atr == 0: continue
                # Premier break de Tokyo le lendemain
                tok = candles[(candles['ts_dt']>=pd.Timestamp(curr_d.year,curr_d.month,curr_d.day,0,0,tz='UTC')) &
                              (candles['ts_dt']<pd.Timestamp(curr_d.year,curr_d.month,curr_d.day,6,0,tz='UTC'))]
                if len(tok) < 18: continue
                ib = tok.iloc[:12]; ib_h = ib['high'].max(); ib_l = ib['low'].min()
                rest = tok.iloc[12:]
                for i in range(len(rest)):
                    r = rest.iloc[i]
                    if r['close'] > ib_h:
                        pi = candles.index.get_loc(rest.index[i]); entry = r['close']
                        b, ex = sim_trail(candles, pi, entry, 'long', sl, atr, 24)
                        trades.append({'date': curr_d, 'pnl_oz': ex-entry, 'atr': atr}); break
                    elif r['close'] < ib_l:
                        pi = candles.index.get_loc(rest.index[i]); entry = r['close']
                        b, ex = sim_trail(candles, pi, entry, 'short', sl, atr, 24)
                        trades.append({'date': curr_d, 'pnl_oz': entry-ex, 'atr': atr}); break
            pr(trades, "Narrow day <{:.1f}ATR -> next break SL={}".format(max_range, sl))

# ══════════════════════════════════════════════════════
# 5. MULTI-DAY MOMENTUM — 2 jours consec bullish/bearish
# ══════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("5. MULTI-DAY — 2 jours consecutifs meme sens → 3eme jour ?")
print("=" * 80)

for min_move in [0.5, 1.0]:
    for sl in [0.75]:
        trades_cont = []; trades_rev = []
        for day_idx in range(2, len(trading_days)):
            d1 = trading_days[day_idx - 2]; d2 = trading_days[day_idx - 1]; d3 = trading_days[day_idx]
            atr = daily_atr.get(d2, global_atr)
            if atr == 0: continue
            c1 = candles[candles['date'] == d1]; c2 = candles[candles['date'] == d2]
            if len(c1) < 20 or len(c2) < 20: continue
            m1 = (c1.iloc[-1]['close'] - c1.iloc[0]['open']) / atr
            m2 = (c2.iloc[-1]['close'] - c2.iloc[0]['open']) / atr
            if abs(m1) < min_move or abs(m2) < min_move: continue
            if (m1 > 0) != (m2 > 0): continue
            c3 = candles[(candles['ts_dt']>=pd.Timestamp(d3.year,d3.month,d3.day,0,0,tz='UTC'))]
            if len(c3) < 6: continue
            pi = candles.index.get_loc(c3.index[0]); entry = c3.iloc[0]['open']
            d = 'long' if m1 > 0 else 'short'
            b, ex = sim_trail(candles, pi, entry, d, sl, atr, 48)
            pnl = (ex-entry) if d == 'long' else (entry-ex)
            trades_cont.append({'date': d3, 'pnl_oz': pnl, 'atr': atr})
            d2r = 'short' if m1 > 0 else 'long'
            b2, ex2 = sim_trail(candles, pi, entry, d2r, sl, atr, 48)
            pnl2 = (ex2-entry) if d2r == 'long' else (entry-ex2)
            trades_rev.append({'date': d3, 'pnl_oz': pnl2, 'atr': atr})
        pr(trades_cont, "2day >{:.1f}ATR aligned -> CONT".format(min_move))
        pr(trades_rev, "2day >{:.1f}ATR aligned -> REV".format(min_move))

# ══════════════════════════════════════════════════════
# 6. WICK RATIO FILTER on NY1st (le plus fort signal)
# ══════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("6. WICK RATIO — NY1st avec peu de meche = plus fiable ?")
print("=" * 80)

for max_wick_pct in [0.3, 0.5, 1.0]:
    for sl in [0.75]:
        trades = []
        for day in trading_days:
            p = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC')) &
                        (candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,21,30,tz='UTC'))]
            if len(p) < 6: continue
            pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
            if atr == 0: continue
            first = p.iloc[0]
            body = abs(first['close'] - first['open'])
            if body < 0.3 * atr: continue
            rng = first['high'] - first['low']
            wick = rng - body if rng > 0 else 0
            wick_ratio = wick / body if body > 0 else 999
            if wick_ratio > max_wick_pct: continue
            d = 'long' if first['close'] > first['open'] else 'short'
            if len(p) < 2: continue
            pi = candles.index.get_loc(p.index[1]); entry = p.iloc[1]['open']
            b, ex = sim_trail(candles, pi, entry, d, sl, atr, 24)
            pnl = (ex-entry) if d == 'long' else (entry-ex)
            trades.append({'date': day, 'pnl_oz': pnl, 'atr': atr})
        pr(trades, "NY1st wick<{:.0f}% SL={}".format(max_wick_pct*100, sl))

conn.close()
print("\n" + "=" * 80)
print("FIN v6")
print("=" * 80)
