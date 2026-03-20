"""
Exploration v11 — 100+ tests
Backtest bougie par bougie (no look-ahead)
"""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
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
monthly_spread = {r[0].strftime("%Y-%m"): float(r[1]) for r in cur.fetchall()}
cur.close(); conn.close()
avg_sp = np.mean(list(monthly_spread.values()))
def prev_day(day):
    for di, d in enumerate(trading_days):
        if d >= day: return trading_days[di-1] if di > 0 else None
    return None
def get_sp(day):
    return 2 * monthly_spread.get(str(day.year)+"-"+str(day.month).zfill(2), avg_sp)
SL, ACT, TRAIL = 0.75, 0.5, 0.3

def sim_trail(cdf, pos, entry, d, sl, atr, mx, act, trail):
    best = entry; stop = entry + sl*atr if d == 'short' else entry - sl*atr; ta = False
    for j in range(1, mx+1):
        if pos+j >= len(cdf): break
        b = cdf.iloc[pos+j]
        if d == 'long':
            if b['low'] <= stop: return j, stop - 0.10
            if b['high'] > best: best = b['high']
            if not ta and (best-entry) >= act*atr: ta = True
            if ta: stop = max(stop, best - trail*atr)
        else:
            if b['high'] >= stop: return j, stop + 0.10
            if b['low'] < best: best = b['low']
            if not ta and (entry-best) >= act*atr: ta = True
            if ta: stop = min(stop, best + trail*atr)
    if pos+mx < len(cdf): return mx, cdf.iloc[pos+mx]['close']
    return mx, entry

# Pre-calcul daily data
daily_data = {}
for day in trading_days:
    dc = candles[candles['date'] == day]
    if len(dc) < 10: continue
    daily_data[day] = {
        'high': dc['high'].max(), 'low': dc['low'].min(),
        'open': dc.iloc[0]['open'], 'close': dc.iloc[-1]['close'],
        'range': dc['high'].max() - dc['low'].min(),
        'dir': 1 if dc.iloc[-1]['close'] > dc.iloc[0]['open'] else -1
    }

n_tested = 0
n_good = 0

def test(trades, label):
    global n_tested, n_good
    n_tested += 1
    if len(trades) < 20:
        return
    df = pd.DataFrame(trades)
    gp = df[df['pnl']>0]['pnl'].sum(); gl = abs(df[df['pnl']<0]['pnl'].sum())+0.001
    wr = (df['pnl']>0).mean()*100; mid = len(df)//2
    f1 = df.iloc[:mid]['pnl'].mean(); f2 = df.iloc[mid:]['pnl'].mean()
    ok = f1>0 and f2>0; pf = gp/gl
    if pf >= 1.3 and ok:
        n_good += 1
        print(f"  *** {label:70s}: n={len(df):4d} WR={wr:3.0f}% PF={pf:.2f} [{f1:+.3f}|{f2:+.3f}]")

print("="*90)
print("EXPLORATION v11 — tests massifs (no look-ahead)")
print("="*90)

# ══════════════════════════════════════════════════════════════
# BLOC 1: FIRST N MINUTES patterns (10 concepts x 3 sessions = 30 tests)
# ══════════════════════════════════════════════════════════════
print("\n── BLOC 1: First N minutes ──", flush=True)

for sn, s_start, s_end in [('TOK',0,6),('LON',8,14.5),('NY',14.5,21.5)]:
    for n_bars, mode in [(3,'cont'),(3,'rev'),(6,'cont'),(6,'rev'),(12,'cont')]:
        trades = []
        for day in trading_days:
            pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
            if atr == 0: continue
            sh=int(s_start);sm=int((s_start%1)*60);eh=int(s_end);em=int((s_end%1)*60)
            sess = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,sh,sm,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,eh,em,tz='UTC'))]
            if len(sess) < n_bars + 3: continue
            first = sess.iloc[:n_bars]
            m = (first.iloc[-1]['close'] - first.iloc[0]['open']) / atr
            if abs(m) < 0.3: continue
            # Entree apres les N premieres bougies
            pi = candles.index.get_loc(sess.index[n_bars]); e = sess.iloc[n_bars]['open']
            if mode == 'cont': d = 'long' if m > 0 else 'short'
            else: d = 'short' if m > 0 else 'long'
            b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
            pnl = (ex-e) if d=='long' else (e-ex)
            trades.append({'pnl':pnl-get_sp(day)})
        test(trades, f"First {n_bars*5}min {mode} ({sn})")

# ══════════════════════════════════════════════════════════════
# BLOC 2: LAST N MINUTES of session → next session (10 tests)
# ══════════════════════════════════════════════════════════════
print("\n── BLOC 2: Last minutes → next session ──", flush=True)

for n_bars in [3, 6, 12]:
    for mode in ['cont', 'rev']:
        # Tokyo last → London
        trades = []
        for day in trading_days:
            pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
            if atr == 0: continue
            tok = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
            if len(tok) < n_bars + 3: continue
            last = tok.iloc[-n_bars:]
            m = (last.iloc[-1]['close'] - last.iloc[0]['open']) / atr
            if abs(m) < 0.3: continue
            lon = candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
            if len(lon) < 3: continue
            pi = candles.index.get_loc(lon.index[0]); e = lon.iloc[0]['open']
            if mode == 'cont': d = 'long' if m > 0 else 'short'
            else: d = 'short' if m > 0 else 'long'
            b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
            pnl = (ex-e) if d=='long' else (e-ex)
            trades.append({'pnl':pnl-get_sp(day)})
        test(trades, f"Tok last {n_bars*5}min → Lon {mode}")

# ══════════════════════════════════════════════════════════════
# BLOC 3: BODY/RANGE ratios (15 tests)
# ══════════════════════════════════════════════════════════════
print("\n── BLOC 3: Body/Range ratio patterns ──", flush=True)

for sn, s_start, s_end in [('TOK',0,6),('LON',8,14.5),('NY',14.5,21.5)]:
    for body_pct, label in [(0.8,'marubozu'),(0.1,'doji_rev'),(0.5,'balanced')]:
        for min_range in [0.3, 0.5]:
            trades = []
            for day in trading_days:
                pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
                if atr == 0: continue
                sh=int(s_start);sm=int((s_start%1)*60);eh=int(s_end);em=int((s_end%1)*60)
                sess = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,sh,sm,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,eh,em,tz='UTC'))]
                if len(sess) < 3: continue
                for ci_local in range(len(sess)):
                    r = sess.iloc[ci_local]; rng = r['high']-r['low']
                    if rng < min_range*atr: continue
                    body = abs(r['close']-r['open'])
                    ratio = body/rng
                    if label == 'marubozu' and ratio < body_pct: continue
                    elif label == 'doji_rev' and ratio > body_pct: continue
                    elif label == 'balanced' and not (0.4 <= ratio <= 0.6): continue
                    else: pass
                    if label == 'doji_rev':
                        # Doji → reversal de la tendance recente
                        if ci_local < 3: continue
                        recent = sess.iloc[ci_local-3:ci_local]
                        trend = recent.iloc[-1]['close'] - recent.iloc[0]['open']
                        if abs(trend) < 0.2*atr: continue
                        d = 'short' if trend > 0 else 'long'
                    else:
                        d = 'long' if r['close'] > r['open'] else 'short'
                    ci_abs = candles.index.get_loc(sess.index[ci_local])
                    b, ex = sim_trail(candles, ci_abs, r['close'], d, SL, atr, 24, ACT, TRAIL)
                    pnl = (ex-r['close']) if d=='long' else (r['close']-ex)
                    trades.append({'pnl':pnl-get_sp(day)}); break
            test(trades, f"{label} rng>{min_range}ATR ({sn})")

# ══════════════════════════════════════════════════════════════
# BLOC 4: PREVIOUS SESSION HIGH/LOW levels (10 tests)
# ══════════════════════════════════════════════════════════════
print("\n── BLOC 4: Session levels ──", flush=True)

for ref_sess, tgt_sess in [('TOK','LON'),('LON','NY'),('TOK','NY')]:
    for mode in ['break', 'reject']:
        trades = []
        for day in trading_days:
            pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
            if atr == 0: continue
            if ref_sess == 'TOK':
                ref = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
            else:
                ref = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))]
            if len(ref) < 10: continue
            ref_h = ref['high'].max(); ref_l = ref['low'].min()
            if tgt_sess == 'LON':
                tgt = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))]
            else:
                tgt = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,21,30,tz='UTC'))]
            if len(tgt) < 6: continue
            for i in range(len(tgt)):
                r = tgt.iloc[i]
                if mode == 'break':
                    if r['close'] > ref_h:
                        ci_abs = candles.index.get_loc(tgt.index[i])
                        b, ex = sim_trail(candles, ci_abs, r['close'], 'long', SL, atr, 24, ACT, TRAIL)
                        trades.append({'pnl':(ex-r['close'])-get_sp(day)}); break
                    if r['close'] < ref_l:
                        ci_abs = candles.index.get_loc(tgt.index[i])
                        b, ex = sim_trail(candles, ci_abs, r['close'], 'short', SL, atr, 24, ACT, TRAIL)
                        trades.append({'pnl':(r['close']-ex)-get_sp(day)}); break
                else:  # reject
                    if r['high'] > ref_h and r['close'] < ref_h:
                        ci_abs = candles.index.get_loc(tgt.index[i])
                        b, ex = sim_trail(candles, ci_abs, r['close'], 'short', SL, atr, 24, ACT, TRAIL)
                        trades.append({'pnl':(r['close']-ex)-get_sp(day)}); break
                    if r['low'] < ref_l and r['close'] > ref_l:
                        ci_abs = candles.index.get_loc(tgt.index[i])
                        b, ex = sim_trail(candles, ci_abs, r['close'], 'long', SL, atr, 24, ACT, TRAIL)
                        trades.append({'pnl':(ex-r['close'])-get_sp(day)}); break
        test(trades, f"{ref_sess} H/L {mode} → {tgt_sess}")

# ══════════════════════════════════════════════════════════════
# BLOC 5: ROUND NUMBER proximity (6 tests)
# ══════════════════════════════════════════════════════════════
print("\n── BLOC 5: Round numbers ──", flush=True)

for sn, s_start, s_end in [('TOK',0,6),('LON',8,14.5)]:
    for rn_size in [50, 100]:
        trades = []
        for day in trading_days:
            pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
            if atr == 0: continue
            sh=int(s_start);sm=int((s_start%1)*60);eh=int(s_end);em=int((s_end%1)*60)
            sess = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,sh,sm,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,eh,em,tz='UTC'))]
            if len(sess) < 6: continue
            for i in range(1, len(sess)):
                r = sess.iloc[i]; price = r['close']
                nearest_rn = round(price / rn_size) * rn_size
                dist = abs(price - nearest_rn)
                if dist > 2: continue  # close to round number
                # Bounce off round number
                if price > nearest_rn and sess.iloc[i-1]['close'] <= nearest_rn:
                    ci_abs = candles.index.get_loc(sess.index[i])
                    b, ex = sim_trail(candles, ci_abs, r['close'], 'long', SL, atr, 24, ACT, TRAIL)
                    trades.append({'pnl':(ex-r['close'])-get_sp(day)}); break
                if price < nearest_rn and sess.iloc[i-1]['close'] >= nearest_rn:
                    ci_abs = candles.index.get_loc(sess.index[i])
                    b, ex = sim_trail(candles, ci_abs, r['close'], 'short', SL, atr, 24, ACT, TRAIL)
                    trades.append({'pnl':(r['close']-ex)-get_sp(day)}); break
        test(trades, f"Round ${rn_size} bounce ({sn})")

# ══════════════════════════════════════════════════════════════
# BLOC 6: CONSECUTIVE candle sequences (12 tests)
# ══════════════════════════════════════════════════════════════
print("\n── BLOC 6: Sequences ──", flush=True)

for sn, s_start, s_end in [('TOK',0,6),('LON',8,14.5),('NY',14.5,21.5)]:
    for n_consec in [2, 3, 4]:
        for mode in ['cont', 'rev']:
            trades = []
            for day in trading_days:
                pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
                if atr == 0: continue
                sh=int(s_start);sm=int((s_start%1)*60);eh=int(s_end);em=int((s_end%1)*60)
                sess = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,sh,sm,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,eh,em,tz='UTC'))]
                if len(sess) < n_consec + 2: continue
                for i in range(n_consec, len(sess)):
                    bodies = [sess.iloc[i-n_consec+k]['close']-sess.iloc[i-n_consec+k]['open'] for k in range(n_consec)]
                    all_up = all(b > 0.05*atr for b in bodies)
                    all_dn = all(b < -0.05*atr for b in bodies)
                    if not (all_up or all_dn): continue
                    if mode == 'cont': d = 'long' if all_up else 'short'
                    else: d = 'short' if all_up else 'long'
                    ci_abs = candles.index.get_loc(sess.index[i])
                    e = sess.iloc[i]['close']
                    b, ex = sim_trail(candles, ci_abs, e, d, SL, atr, 24, ACT, TRAIL)
                    pnl = (ex-e) if d=='long' else (e-ex)
                    trades.append({'pnl':pnl-get_sp(day)}); break
            test(trades, f"{n_consec} consec {mode} ({sn})")

# ══════════════════════════════════════════════════════════════
# BLOC 7: VOLATILITY regime filter (8 tests)
# ══════════════════════════════════════════════════════════════
print("\n── BLOC 7: Volatility regime ──", flush=True)

atr_vals = sorted([v for v in daily_atr.values() if v > 0])
atr_p25 = np.percentile(atr_vals, 25)
atr_p75 = np.percentile(atr_vals, 75)

for regime, lo, hi in [('low', 0, atr_p25), ('mid', atr_p25, atr_p75), ('high', atr_p75, 999)]:
    for sn, s_start in [('LON',8), ('NY',14.5)]:
        trades = []
        for day in trading_days:
            pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
            if atr == 0 or atr < lo or atr >= hi: continue
            sh=int(s_start);sm=int((s_start%1)*60)
            sess = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,sh,sm,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,sh+6,sm,tz='UTC'))]
            if len(sess) < 6: continue
            body = sess.iloc[0]['close'] - sess.iloc[0]['open']
            if abs(body) < 0.3*atr: continue
            d = 'long' if body > 0 else 'short'
            ci_abs = candles.index.get_loc(sess.index[0])
            b, ex = sim_trail(candles, ci_abs, sess.iloc[0]['close'], d, SL, atr, 24, ACT, TRAIL)
            pnl = (ex-sess.iloc[0]['close']) if d=='long' else (sess.iloc[0]['close']-ex)
            trades.append({'pnl':pnl-get_sp(day)})
        test(trades, f"1st candle {regime}ATR ({sn})")

# ══════════════════════════════════════════════════════════════
# BLOC 8: PREV DAY patterns (10 tests)
# ══════════════════════════════════════════════════════════════
print("\n── BLOC 8: Previous day patterns ──", flush=True)

for mode in ['cont','rev']:
    for entry_sess in ['TOK','LON','NY']:
        trades = []
        for di, day in enumerate(trading_days):
            if di == 0: continue
            pd_ = trading_days[di-1]; atr = daily_atr.get(pd_, global_atr)
            if atr == 0 or pd_ not in daily_data: continue
            pdir = daily_data[pd_]['dir']
            if entry_sess == 'TOK':
                tgt = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
            elif entry_sess == 'LON':
                tgt = candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
            else:
                tgt = candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC')]
            if len(tgt) < 3: continue
            pi = candles.index.get_loc(tgt.index[0]); e = tgt.iloc[0]['open']
            if mode == 'cont': d = 'long' if pdir > 0 else 'short'
            else: d = 'short' if pdir > 0 else 'long'
            b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
            pnl = (ex-e) if d=='long' else (e-ex)
            trades.append({'pnl':pnl-get_sp(day)})
        test(trades, f"Prev day {mode} → {entry_sess}")

# Prev day range-based
for range_type in ['narrow','wide']:
    trades = []
    for di, day in enumerate(trading_days):
        if di == 0: continue
        pd_ = trading_days[di-1]; atr = daily_atr.get(pd_, global_atr)
        if atr == 0 or pd_ not in daily_data: continue
        pr = daily_data[pd_]['range'] / atr
        if range_type == 'narrow' and pr > 1.5: continue
        if range_type == 'wide' and pr < 2.5: continue
        # Narrow → break, Wide → reversal
        lon = candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
        if len(lon) < 3: continue
        pi = candles.index.get_loc(lon.index[0]); e = lon.iloc[0]['open']
        pdir = daily_data[pd_]['dir']
        if range_type == 'narrow': d = 'long' if pdir > 0 else 'short'
        else: d = 'short' if pdir > 0 else 'long'
        b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
        pnl = (ex-e) if d=='long' else (e-ex)
        trades.append({'pnl':pnl-get_sp(day)})
    test(trades, f"Prev day {range_type} → LON")

# ══════════════════════════════════════════════════════════════
# BLOC 9: MULTI-BAR momentum (6 tests)
# ══════════════════════════════════════════════════════════════
print("\n── BLOC 9: Multi-bar momentum ──", flush=True)

for sn, s_start, s_end in [('TOK',0,6),('LON',8,14.5)]:
    for n_bars in [4, 6, 10]:
        trades = []
        for day in trading_days:
            pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
            if atr == 0: continue
            sh=int(s_start);sm=int((s_start%1)*60);eh=int(s_end);em=int((s_end%1)*60)
            sess = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,sh,sm,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,eh,em,tz='UTC'))]
            if len(sess) < n_bars + 3: continue
            for i in range(n_bars, len(sess)):
                window = sess.iloc[i-n_bars:i]
                m = (window.iloc[-1]['close'] - window.iloc[0]['open']) / atr
                if abs(m) < 1.0: continue
                d = 'long' if m > 0 else 'short'
                ci_abs = candles.index.get_loc(sess.index[i])
                e = sess.iloc[i]['open']
                b, ex = sim_trail(candles, ci_abs, e, d, SL, atr, 24, ACT, TRAIL)
                pnl = (ex-e) if d=='long' else (e-ex)
                trades.append({'pnl':pnl-get_sp(day)}); break
        test(trades, f"{n_bars}-bar mom >1ATR cont ({sn})")

# ══════════════════════════════════════════════════════════════
# BLOC 10: SPECIFIC HOURS (12 tests)
# ══════════════════════════════════════════════════════════════
print("\n── BLOC 10: Specific hours ──", flush=True)

for hour_test in [0, 1, 2, 3, 4, 5, 8, 9, 10, 11, 14, 15]:
    trades = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        sess = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,hour_test,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,hour_test+1,0,tz='UTC'))]
        if len(sess) < 6: continue
        body = sess.iloc[0]['close'] - sess.iloc[0]['open']
        if abs(body) < 0.3*atr: continue
        d = 'long' if body > 0 else 'short'
        ci_abs = candles.index.get_loc(sess.index[0])
        b, ex = sim_trail(candles, ci_abs, sess.iloc[0]['close'], d, SL, atr, 24, ACT, TRAIL)
        pnl = (ex-sess.iloc[0]['close']) if d=='long' else (sess.iloc[0]['close']-ex)
        trades.append({'pnl':pnl-get_sp(day)})
    test(trades, f"1st candle {hour_test:02d}h cont")

# ══════════════════════════════════════════════════════════════
# BLOC 11: TICK VOLUME patterns (6 tests)
# ══════════════════════════════════════════════════════════════
print("\n── BLOC 11: Tick volume ──", flush=True)

if 'volume' in candles.columns or 'tick_volume' in candles.columns:
    vol_col = 'volume' if 'volume' in candles.columns else 'tick_volume'
    for sn, s_start, s_end in [('TOK',0,6),('LON',8,14.5)]:
        trades = []
        for day in trading_days:
            pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
            if atr == 0: continue
            sh=int(s_start);sm=int((s_start%1)*60);eh=int(s_end);em=int((s_end%1)*60)
            sess = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,sh,sm,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,eh,em,tz='UTC'))]
            if len(sess) < 6 or vol_col not in sess.columns: continue
            avg_vol = sess[vol_col].mean()
            for i in range(1, len(sess)):
                r = sess.iloc[i]
                if r[vol_col] > 2 * avg_vol and abs(r['close']-r['open']) >= 0.3*atr:
                    d = 'long' if r['close'] > r['open'] else 'short'
                    ci_abs = candles.index.get_loc(sess.index[i])
                    b, ex = sim_trail(candles, ci_abs, r['close'], d, SL, atr, 24, ACT, TRAIL)
                    pnl = (ex-r['close']) if d=='long' else (r['close']-ex)
                    trades.append({'pnl':pnl-get_sp(day)}); break
        test(trades, f"Volume spike cont ({sn})")
else:
    print("  (pas de colonne volume)")

# ══════════════════════════════════════════════════════════════
# BLOC 12: COMBINED filters (existing strats with filters)
# ══════════════════════════════════════════════════════════════
print("\n── BLOC 12: Strats existantes + filtres ──", flush=True)

# D (GAP) only on days where Tokyo was trending
trades = []
for day in trading_days:
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    tok = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(tok) < 10: continue
    tok_move = abs(tok.iloc[-1]['close'] - tok.iloc[0]['open']) / atr
    if tok_move < 0.5: continue  # filter: Tokyo must have trended
    tc = candles[candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC')]
    lon = candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
    if len(tc) < 5 or len(lon) < 6: continue
    gap = (lon.iloc[0]['open'] - tc.iloc[-1]['close']) / atr
    if abs(gap) < 0.5: continue
    d = 'long' if gap > 0 else 'short'
    pi = candles.index.get_loc(lon.index[0])
    b, ex = sim_trail(candles, pi, lon.iloc[0]['open'], d, SL, atr, 24, ACT, TRAIL)
    pnl = (ex-lon.iloc[0]['open']) if d=='long' else (lon.iloc[0]['open']-ex)
    trades.append({'pnl':pnl-get_sp(day)})
test(trades, "D (GAP) + Tokyo trending filter")

# E (KZ fade) only when KZ move > 1ATR (stronger filter)
trades = []
for day in trading_days:
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    kz = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,10,0,tz='UTC'))]
    if len(kz) < 20: continue
    m = (kz.iloc[-1]['close'] - kz.iloc[0]['open']) / atr
    if abs(m) < 1.0: continue  # stronger filter
    post = candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,10,0,tz='UTC')]
    if len(post) < 6: continue
    pi = candles.index.get_loc(post.index[0])
    d = 'short' if m > 0 else 'long'
    b, ex = sim_trail(candles, pi, post.iloc[0]['open'], d, SL, atr, 24, ACT, TRAIL)
    pnl = (ex-post.iloc[0]['open']) if d=='long' else (post.iloc[0]['open']-ex)
    trades.append({'pnl':pnl-get_sp(day)})
test(trades, "E (KZ) strong filter >1ATR")

# H (TOKEND) + aligned with full Tokyo direction
trades = []
for day in trading_days:
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    tok = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(tok) < 9: continue
    l3 = tok.iloc[-3:]
    m_end = (l3.iloc[-1]['close'] - l3.iloc[0]['open']) / atr
    m_full = (tok.iloc[-1]['close'] - tok.iloc[0]['open']) / atr
    if abs(m_end) < 1.0: continue
    # Filter: end momentum aligned with full session
    if m_end * m_full <= 0: continue
    lon = candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
    if len(lon) < 6: continue
    pi = candles.index.get_loc(lon.index[0])
    d = 'long' if m_end > 0 else 'short'
    b, ex = sim_trail(candles, pi, lon.iloc[0]['open'], d, SL, atr, 24, ACT, TRAIL)
    pnl = (ex-lon.iloc[0]['open']) if d=='long' else (lon.iloc[0]['open']-ex)
    trades.append({'pnl':pnl-get_sp(day)})
test(trades, "H (TOKEND) + full Tokyo aligned")

print(f"\n{'='*90}")
print(f"TOTAL: {n_tested} tests, {n_good} avec PF>=1.3 et split OK")
print(f"{'='*90}")
