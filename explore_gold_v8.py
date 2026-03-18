"""
Exploration v8 — nouvelles idees
1. Engulfing pattern (bougie qui englobe la precedente) par session
2. Three white soldiers / three black crows (3 bougies consecutives meme sens)
3. Gap fill (gap Tokyo-London, fade vers le fill)
4. Session high/low dans les N premieres bougies → continuation
5. Hammer/shooting star (longue meche, petit body) → reversal
6. Range contraction → expansion (2 bougies etroites puis grosse)
7. London breakout failure (break Asian range puis echec)
8. NY afternoon reversal (16h-18h reverse de 14:30-16h)
9. Double top/bottom intra-session
10. Momentum exhaustion (3+ bougies meme sens puis ralentissement)
"""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
from dotenv import load_dotenv
load_dotenv()
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
cur.close()
avg_sp = np.mean(list(monthly_spread.values()))

def prev_day(day):
    for di, d in enumerate(trading_days):
        if d >= day: return trading_days[di-1] if di > 0 else None
    return None
def get_sp(day):
    return 2 * monthly_spread.get(str(day.year)+"-"+str(day.month).zfill(2), avg_sp)
n_td = len(set(candles['date'].unique()))
SL, ACT, TRAIL = 0.75, 0.5, 0.3

def sim_trail(cdf, pos, entry, d, sl, atr, mx, act, trail):
    best = entry
    stop = entry + sl*atr if d == 'short' else entry - sl*atr
    ta = False
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

def test_signal(trades, label):
    if len(trades) < 20:
        print(f"    {label:60s}: n={len(trades):4d} -- trop peu")
        return
    df = pd.DataFrame(trades)
    gp = df[df['pnl']>0]['pnl'].sum(); gl = abs(df[df['pnl']<0]['pnl'].sum())+0.001
    wr = (df['pnl']>0).mean()*100
    mid = len(df)//2
    f1 = df.iloc[:mid]['pnl'].mean(); f2 = df.iloc[mid:]['pnl'].mean()
    ok = "OK" if f1>0 and f2>0 else "~"
    star = " ***" if gp/gl >= 1.3 and f1>0 and f2>0 else ""
    print(f"    {label:60s}: n={len(df):4d} WR={wr:3.0f}% PF={gp/gl:.2f} [{f1:+.3f}|{f2:+.3f}] {ok}{star}")

print("="*80)
print("EXPLORATION v8")
print("="*80)

# ── 1. Engulfing pattern ──
print("\n" + "="*80)
print("1. ENGULFING PATTERN → continuation")
print("="*80)
for session_name, s_start, s_end in [('TOK', 0, 6), ('LON', 8, 14.5), ('NY', 14.5, 21.5)]:
    trades = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        sh = int(s_start); sm = int((s_start % 1) * 60)
        eh = int(s_end); em = int((s_end % 1) * 60)
        sess = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,sh,sm,tz='UTC')) &
                       (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,eh,em,tz='UTC'))]
        if len(sess) < 6: continue
        for i in range(1, len(sess)):
            prev_b = sess.iloc[i-1]; cur_b = sess.iloc[i]
            # Bullish engulfing
            if (prev_b['close'] < prev_b['open'] and  # prev bearish
                cur_b['close'] > cur_b['open'] and  # curr bullish
                cur_b['open'] <= prev_b['close'] and  # open <= prev close
                cur_b['close'] >= prev_b['open'] and  # close >= prev open
                abs(cur_b['close']-cur_b['open']) >= 0.3*atr):  # significant
                pi = candles.index.get_loc(sess.index[i]); e = cur_b['close']
                b, ex = sim_trail(candles, pi, e, 'long', SL, atr, 24, ACT, TRAIL)
                trades.append({'pnl':(ex-e)-get_sp(day)}); break
            # Bearish engulfing
            if (prev_b['close'] > prev_b['open'] and
                cur_b['close'] < cur_b['open'] and
                cur_b['open'] >= prev_b['close'] and
                cur_b['close'] <= prev_b['open'] and
                abs(cur_b['close']-cur_b['open']) >= 0.3*atr):
                pi = candles.index.get_loc(sess.index[i]); e = cur_b['close']
                b, ex = sim_trail(candles, pi, e, 'short', SL, atr, 24, ACT, TRAIL)
                trades.append({'pnl':(e-ex)-get_sp(day)}); break
    test_signal(trades, f"Engulfing ({session_name})")

# ── 2. Three soldiers/crows ──
print("\n" + "="*80)
print("2. THREE SOLDIERS / CROWS")
print("="*80)
for session_name, s_start, s_end in [('TOK', 0, 6), ('LON', 8, 14.5), ('NY', 14.5, 21.5)]:
    for mode in ['cont', 'rev']:
        trades = []
        for day in trading_days:
            pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
            if atr == 0: continue
            sh = int(s_start); sm = int((s_start % 1) * 60)
            eh = int(s_end); em = int((s_end % 1) * 60)
            sess = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,sh,sm,tz='UTC')) &
                           (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,eh,em,tz='UTC'))]
            if len(sess) < 6: continue
            for i in range(2, len(sess)):
                c1 = sess.iloc[i-2]; c2 = sess.iloc[i-1]; c3 = sess.iloc[i]
                b1 = c1['close']-c1['open']; b2 = c2['close']-c2['open']; b3 = c3['close']-c3['open']
                # 3 meme sens, chaque body > 0.1 ATR
                if b1*b2 > 0 and b2*b3 > 0 and min(abs(b1),abs(b2),abs(b3)) > 0.1*atr:
                    total = abs(b1+b2+b3)
                    if total < 0.5*atr: continue
                    if mode == 'cont':
                        d = 'long' if b3 > 0 else 'short'
                    else:
                        d = 'short' if b3 > 0 else 'long'
                    pi = candles.index.get_loc(sess.index[i]); e = c3['close']
                    b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
                    pnl = (ex-e) if d == 'long' else (e-ex)
                    trades.append({'pnl':pnl-get_sp(day)}); break
        test_signal(trades, f"3 soldiers/crows {mode} ({session_name})")

# ── 3. Gap fill (fade gap Tokyo-London) ──
print("\n" + "="*80)
print("3. GAP FILL (fade gap Tokyo-London)")
print("="*80)
for thresh in [0.3, 0.5]:
    trades = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        tc = candles[candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC')]
        if len(tc) < 5: continue
        tok_close = tc.iloc[-1]['close']
        lon = candles[candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
        if len(lon) < 6: continue
        lon_open = lon.iloc[0]['open']
        gap = (lon_open - tok_close) / atr
        if abs(gap) < thresh: continue
        pi = candles.index.get_loc(lon.index[0]); e = lon_open
        # FADE = direction opposee au gap (vers le fill)
        d = 'short' if gap > 0 else 'long'
        b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
        pnl = (ex-e) if d == 'long' else (e-ex)
        trades.append({'pnl':pnl-get_sp(day)})
    test_signal(trades, f"Gap fill (fade) thresh={thresh}ATR")

# ── 4. Hammer / shooting star ──
print("\n" + "="*80)
print("4. HAMMER / SHOOTING STAR → reversal")
print("="*80)
for session_name, s_start, s_end in [('TOK', 0, 6), ('LON', 8, 14.5), ('NY', 14.5, 21.5)]:
    trades = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        sh = int(s_start); sm = int((s_start % 1) * 60)
        eh = int(s_end); em = int((s_end % 1) * 60)
        sess = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,sh,sm,tz='UTC')) &
                       (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,eh,em,tz='UTC'))]
        if len(sess) < 6: continue
        for i in range(1, len(sess)):
            r = sess.iloc[i]
            body = abs(r['close']-r['open']); rng = r['high']-r['low']
            if rng < 0.3*atr or body == 0: continue
            upper_wick = r['high'] - max(r['open'],r['close'])
            lower_wick = min(r['open'],r['close']) - r['low']
            # Hammer = longue meche basse, petit body en haut → bullish
            if lower_wick >= 2*body and upper_wick <= body:
                # Confirmer tendance baissiere avant
                if i >= 2:
                    prev_move = sess.iloc[i-2]['close'] - sess.iloc[i]['low']
                    if prev_move < -0.2*atr:
                        pi = candles.index.get_loc(sess.index[i]); e = r['close']
                        b, ex = sim_trail(candles, pi, e, 'long', SL, atr, 24, ACT, TRAIL)
                        trades.append({'pnl':(ex-e)-get_sp(day)}); break
            # Shooting star = longue meche haute, petit body en bas → bearish
            if upper_wick >= 2*body and lower_wick <= body:
                if i >= 2:
                    prev_move = sess.iloc[i]['high'] - sess.iloc[i-2]['close']
                    if prev_move > 0.2*atr:
                        pi = candles.index.get_loc(sess.index[i]); e = r['close']
                        b, ex = sim_trail(candles, pi, e, 'short', SL, atr, 24, ACT, TRAIL)
                        trades.append({'pnl':(e-ex)-get_sp(day)}); break
    test_signal(trades, f"Hammer/ShootingStar ({session_name})")

# ── 5. Range contraction → expansion ──
print("\n" + "="*80)
print("5. RANGE CONTRACTION → EXPANSION")
print("="*80)
for session_name, s_start, s_end in [('TOK', 0, 6), ('LON', 8, 14.5), ('NY', 14.5, 21.5)]:
    trades = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        sh = int(s_start); sm = int((s_start % 1) * 60)
        eh = int(s_end); em = int((s_end % 1) * 60)
        sess = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,sh,sm,tz='UTC')) &
                       (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,eh,em,tz='UTC'))]
        if len(sess) < 6: continue
        for i in range(2, len(sess)):
            c1 = sess.iloc[i-2]; c2 = sess.iloc[i-1]; c3 = sess.iloc[i]
            r1 = c1['high']-c1['low']; r2 = c2['high']-c2['low']; r3 = c3['high']-c3['low']
            # 2 bougies etroites puis grosse
            if r1 < 0.2*atr and r2 < 0.2*atr and r3 > 0.4*atr:
                body3 = c3['close'] - c3['open']
                if abs(body3) < 0.2*atr: continue
                d = 'long' if body3 > 0 else 'short'
                pi = candles.index.get_loc(sess.index[i]); e = c3['close']
                b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
                pnl = (ex-e) if d == 'long' else (e-ex)
                trades.append({'pnl':pnl-get_sp(day)}); break
    test_signal(trades, f"Contraction→Expansion ({session_name})")

# ── 6. London breakout failure (Asian range) ──
print("\n" + "="*80)
print("6. LONDON BREAKOUT FAILURE (Asian range break puis retour)")
print("="*80)
trades = []
for day in trading_days:
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    tok = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC')) &
                  (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(tok) < 10: continue
    tok_high = tok['high'].max(); tok_low = tok['low'].min()
    lon = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')) &
                  (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))]
    if len(lon) < 10: continue
    for i in range(len(lon)):
        r = lon.iloc[i]
        # Break UP puis retour
        if r['high'] > tok_high and r['close'] < tok_high:
            pi = candles.index.get_loc(lon.index[i]); e = r['close']
            b, ex = sim_trail(candles, pi, e, 'short', SL, atr, 24, ACT, TRAIL)
            trades.append({'pnl':(e-ex)-get_sp(day)}); break
        # Break DOWN puis retour
        if r['low'] < tok_low and r['close'] > tok_low:
            pi = candles.index.get_loc(lon.index[i]); e = r['close']
            b, ex = sim_trail(candles, pi, e, 'long', SL, atr, 24, ACT, TRAIL)
            trades.append({'pnl':(ex-e)-get_sp(day)}); break
test_signal(trades, "London failed Asian break")

# ── 7. NY afternoon reversal ──
print("\n" + "="*80)
print("7. NY AFTERNOON REVERSAL (16h-18h fade 14:30-16h)")
print("="*80)
for thresh in [0.5, 1.0]:
    trades = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        ny_early = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC')) &
                           (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,16,0,tz='UTC'))]
        if len(ny_early) < 10: continue
        m = (ny_early.iloc[-1]['close'] - ny_early.iloc[0]['open']) / atr
        if abs(m) < thresh: continue
        ny_late = candles[candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,16,0,tz='UTC')]
        if len(ny_late) < 6: continue
        pi = candles.index.get_loc(ny_late.index[0]); e = ny_late.iloc[0]['open']
        d = 'short' if m > 0 else 'long'
        b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
        pnl = (ex-e) if d == 'long' else (e-ex)
        trades.append({'pnl':pnl-get_sp(day)})
    test_signal(trades, f"NY afternoon reversal (thresh={thresh}ATR)")

# ── 8. Momentum exhaustion ──
print("\n" + "="*80)
print("8. MOMENTUM EXHAUSTION (3+ bougies meme sens, derniere plus petite)")
print("="*80)
for session_name, s_start, s_end in [('TOK', 0, 6), ('LON', 8, 14.5), ('NY', 14.5, 21.5)]:
    trades = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        sh = int(s_start); sm = int((s_start % 1) * 60)
        eh = int(s_end); em = int((s_end % 1) * 60)
        sess = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,sh,sm,tz='UTC')) &
                       (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,eh,em,tz='UTC'))]
        if len(sess) < 6: continue
        for i in range(3, len(sess)):
            c1 = sess.iloc[i-3]; c2 = sess.iloc[i-2]; c3 = sess.iloc[i-1]; c4 = sess.iloc[i]
            b1 = c1['close']-c1['open']; b2 = c2['close']-c2['open']
            b3 = c3['close']-c3['open']; b4 = c4['close']-c4['open']
            # 3 meme sens, 4eme meme sens mais plus petit
            if b1*b2 > 0 and b2*b3 > 0 and b3*b4 > 0:
                if abs(b4) < abs(b3) and abs(b3) > 0.1*atr:
                    total = abs(b1+b2+b3+b4)
                    if total < 0.5*atr: continue
                    # Reversal
                    d = 'short' if b4 > 0 else 'long'
                    pi = candles.index.get_loc(sess.index[i]); e = c4['close']
                    b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
                    pnl = (ex-e) if d == 'long' else (e-ex)
                    trades.append({'pnl':pnl-get_sp(day)}); break
    test_signal(trades, f"Momentum exhaustion rev ({session_name})")

# ── 9. Session open drive (1ere bougie = la plus forte des N premieres) ──
print("\n" + "="*80)
print("9. SESSION OPEN DRIVE (1ere bougie dominante sur les 6 premieres)")
print("="*80)
for session_name, s_start, s_end in [('TOK', 0, 6), ('LON', 8, 14.5), ('NY', 14.5, 21.5)]:
    trades = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        sh = int(s_start); sm = int((s_start % 1) * 60)
        eh = int(s_end); em = int((s_end % 1) * 60)
        sess = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,sh,sm,tz='UTC')) &
                       (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,eh,em,tz='UTC'))]
        if len(sess) < 12: continue
        first6 = sess.iloc[:6]
        bodies = [(abs(first6.iloc[j]['close']-first6.iloc[j]['open']), j) for j in range(6)]
        max_body, max_idx = max(bodies)
        if max_idx != 0: continue  # 1ere bougie doit etre la plus forte
        if max_body < 0.3*atr: continue
        first = sess.iloc[0]
        body = first['close'] - first['open']
        d = 'long' if body > 0 else 'short'
        # Entree apres 6eme bougie
        pi = candles.index.get_loc(sess.index[6]); e = sess.iloc[6]['open']
        b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
        pnl = (ex-e) if d == 'long' else (e-ex)
        trades.append({'pnl':pnl-get_sp(day)})
    test_signal(trades, f"Open drive ({session_name})")

# ── 10. Faux breakout intra-session (nouveau high puis close sous previous close) ──
print("\n" + "="*80)
print("10. FAUX BREAKOUT INTRA-SESSION")
print("="*80)
for session_name, s_start, s_end in [('TOK', 0, 6), ('LON', 8, 14.5), ('NY', 14.5, 21.5)]:
    trades = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        sh = int(s_start); sm = int((s_start % 1) * 60)
        eh = int(s_end); em = int((s_end % 1) * 60)
        sess = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,sh,sm,tz='UTC')) &
                       (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,eh,em,tz='UTC'))]
        if len(sess) < 6: continue
        run_high = sess.iloc[0]['high']
        run_low = sess.iloc[0]['low']
        for i in range(1, len(sess)):
            r = sess.iloc[i]
            # Nouveau high mais close sous le close precedent
            if r['high'] > run_high and r['close'] < sess.iloc[i-1]['close']:
                if (r['high'] - run_high) > 0.1*atr:
                    pi = candles.index.get_loc(sess.index[i]); e = r['close']
                    b, ex = sim_trail(candles, pi, e, 'short', SL, atr, 24, ACT, TRAIL)
                    trades.append({'pnl':(e-ex)-get_sp(day)}); break
            # Nouveau low mais close au-dessus du close precedent
            if r['low'] < run_low and r['close'] > sess.iloc[i-1]['close']:
                if (run_low - r['low']) > 0.1*atr:
                    pi = candles.index.get_loc(sess.index[i]); e = r['close']
                    b, ex = sim_trail(candles, pi, e, 'long', SL, atr, 24, ACT, TRAIL)
                    trades.append({'pnl':(ex-e)-get_sp(day)}); break
            run_high = max(run_high, r['high'])
            run_low = min(run_low, r['low'])
    test_signal(trades, f"Faux breakout intra ({session_name})")

conn.close()
print("\n" + "="*80)
print("FIN v8")
print("="*80)
