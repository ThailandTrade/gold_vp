"""
Exploration v7 — nouvelles idees
1. Asian range breakout à London (pas IB, le range complet Tokyo)
2. London close → NY continuation/reversal
3. Pre-NY momentum (13h-14h30 UTC) → NY direction
4. Double session fade (Tokyo ET London meme sens → fade NY)
5. Volume spike candle (bougie avec body >1ATR) → continuation
6. Inside bar breakout (pendant n'importe quelle session)
7. Previous day high/low touch → reversal
8. Opening range breakout London 30min
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
print("EXPLORATION v7")
print("="*80)

# ── 1. Asian range breakout a London ──
print("\n" + "="*80)
print("1. ASIAN RANGE BREAKOUT → London")
print("="*80)
for thresh in [0.0, 0.1]:
    for direction in ['break']:
        trades = []
        for day in trading_days:
            pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
            if atr == 0: continue
            tok = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC')) &
                          (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
            if len(tok) < 10: continue
            tok_high = tok['high'].max(); tok_low = tok['low'].min()
            tok_range = (tok_high - tok_low) / atr
            lon = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')) &
                          (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))]
            if len(lon) < 6: continue
            for i in range(len(lon)):
                r = lon.iloc[i]
                if r['close'] > tok_high + thresh*atr:
                    pi = candles.index.get_loc(lon.index[i]); e = r['close']
                    b, ex = sim_trail(candles, pi, e, 'long', SL, atr, 24, ACT, TRAIL)
                    trades.append({'pnl':(ex-e)-get_sp(day),'atr':atr}); break
                elif r['close'] < tok_low - thresh*atr:
                    pi = candles.index.get_loc(lon.index[i]); e = r['close']
                    b, ex = sim_trail(candles, pi, e, 'short', SL, atr, 24, ACT, TRAIL)
                    trades.append({'pnl':(e-ex)-get_sp(day),'atr':atr}); break
        test_signal(trades, f"Asian range break (thresh={thresh}ATR)")

# ── 2. London close → NY continuation ──
print("\n" + "="*80)
print("2. LONDON CLOSE MOMENTUM → NY")
print("="*80)
for thresh in [0.5, 1.0, 1.5]:
    for mode in ['cont', 'rev']:
        trades = []
        for day in trading_days:
            pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
            if atr == 0: continue
            lon = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')) &
                          (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))]
            if len(lon) < 20: continue
            # Derniere heure de London (13:30-14:30)
            lon_end = lon.iloc[-6:]
            m = (lon_end.iloc[-1]['close'] - lon_end.iloc[0]['open']) / atr
            if abs(m) < thresh: continue
            ny = candles[candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC')]
            if len(ny) < 6: continue
            pi = candles.index.get_loc(ny.index[0]); e = ny.iloc[0]['open']
            if mode == 'cont':
                d = 'long' if m > 0 else 'short'
            else:
                d = 'short' if m > 0 else 'long'
            b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
            pnl = (ex-e) if d == 'long' else (e-ex)
            trades.append({'pnl':pnl-get_sp(day),'atr':atr})
        test_signal(trades, f"London close {thresh}ATR → NY {mode}")

# ── 3. Pre-NY momentum (13h-14h30) ──
print("\n" + "="*80)
print("3. PRE-NY MOMENTUM (13h-14h30)")
print("="*80)
for thresh in [0.3, 0.5, 1.0]:
    for mode in ['cont', 'rev']:
        trades = []
        for day in trading_days:
            pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
            if atr == 0: continue
            pre = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,13,0,tz='UTC')) &
                          (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))]
            if len(pre) < 10: continue
            m = (pre.iloc[-1]['close'] - pre.iloc[0]['open']) / atr
            if abs(m) < thresh: continue
            ny = candles[candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC')]
            if len(ny) < 6: continue
            pi = candles.index.get_loc(ny.index[0]); e = ny.iloc[0]['open']
            if mode == 'cont':
                d = 'long' if m > 0 else 'short'
            else:
                d = 'short' if m > 0 else 'long'
            b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
            pnl = (ex-e) if d == 'long' else (e-ex)
            trades.append({'pnl':pnl-get_sp(day),'atr':atr})
        test_signal(trades, f"Pre-NY {thresh}ATR → {mode}")

# ── 4. Previous day high/low touch → reversal ──
print("\n" + "="*80)
print("4. PREVIOUS DAY HIGH/LOW → REVERSAL")
print("="*80)
for session_name, s_start, s_end in [('TOK', 0, 6), ('LON', 8, 14.5), ('NY', 14.5, 21.5)]:
    trades = []
    for di, day in enumerate(trading_days):
        if di == 0: continue
        pd_ = trading_days[di-1]
        atr = daily_atr.get(pd_, global_atr)
        if atr == 0: continue
        # Previous day high/low
        prev_c = candles[candles['date'] == pd_]
        if len(prev_c) < 10: continue
        prev_high = prev_c['high'].max()
        prev_low = prev_c['low'].min()
        # Current session
        sh = int(s_start); sm = int((s_start % 1) * 60)
        eh = int(s_end); em = int((s_end % 1) * 60)
        sess = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,sh,sm,tz='UTC')) &
                       (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,eh,em,tz='UTC'))]
        if len(sess) < 6: continue
        for i in range(len(sess)):
            r = sess.iloc[i]
            # Touch previous high → short
            if r['high'] >= prev_high and r['close'] < prev_high:
                pi = candles.index.get_loc(sess.index[i]); e = r['close']
                b, ex = sim_trail(candles, pi, e, 'short', SL, atr, 24, ACT, TRAIL)
                trades.append({'pnl':(e-ex)-get_sp(day),'atr':atr}); break
            # Touch previous low → long
            if r['low'] <= prev_low and r['close'] > prev_low:
                pi = candles.index.get_loc(sess.index[i]); e = r['close']
                b, ex = sim_trail(candles, pi, e, 'long', SL, atr, 24, ACT, TRAIL)
                trades.append({'pnl':(ex-e)-get_sp(day),'atr':atr}); break
    test_signal(trades, f"Prev day H/L touch → rev ({session_name})")

# ── 5. Volume spike candle continuation ──
print("\n" + "="*80)
print("5. GROSSE BOUGIE (body>1ATR) → CONTINUATION")
print("="*80)
for session_name, s_start, s_end in [('TOK', 0, 6), ('LON', 8, 14.5), ('NY', 14.5, 21.5)]:
    for thresh in [0.5, 1.0]:
        trades = []
        for day in trading_days:
            pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
            if atr == 0: continue
            sh = int(s_start); sm = int((s_start % 1) * 60)
            eh = int(s_end); em = int((s_end % 1) * 60)
            sess = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,sh,sm,tz='UTC')) &
                           (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,eh,em,tz='UTC'))]
            if len(sess) < 6: continue
            for i in range(len(sess)):
                r = sess.iloc[i]
                body = r['close'] - r['open']
                if abs(body) >= thresh*atr:
                    d = 'long' if body > 0 else 'short'
                    pi = candles.index.get_loc(sess.index[i]); e = r['close']
                    b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
                    pnl = (ex-e) if d == 'long' else (e-ex)
                    trades.append({'pnl':pnl-get_sp(day),'atr':atr}); break
        test_signal(trades, f"Big candle >{thresh}ATR cont ({session_name})")

# ── 6. Inside bar breakout ──
print("\n" + "="*80)
print("6. INSIDE BAR BREAKOUT")
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
            prev_bar = sess.iloc[i-1]; cur_bar = sess.iloc[i]
            # Inside bar = high <= prev high AND low >= prev low
            if cur_bar['high'] <= prev_bar['high'] and cur_bar['low'] >= prev_bar['low']:
                # Attendre le breakout
                for k in range(i+1, len(sess)):
                    nb = sess.iloc[k]
                    if nb['close'] > prev_bar['high']:
                        pi = candles.index.get_loc(sess.index[k]); e = nb['close']
                        b, ex = sim_trail(candles, pi, e, 'long', SL, atr, 24, ACT, TRAIL)
                        trades.append({'pnl':(ex-e)-get_sp(day),'atr':atr}); break
                    elif nb['close'] < prev_bar['low']:
                        pi = candles.index.get_loc(sess.index[k]); e = nb['close']
                        b, ex = sim_trail(candles, pi, e, 'short', SL, atr, 24, ACT, TRAIL)
                        trades.append({'pnl':(e-ex)-get_sp(day),'atr':atr}); break
                break
    test_signal(trades, f"Inside bar breakout ({session_name})")

# ── 7. Opening range breakout London 30min ──
print("\n" + "="*80)
print("7. OPENING RANGE BREAKOUT LONDON 30min")
print("="*80)
for orb_bars in [6, 12]:  # 30min = 6 bougies 5m, 60min = 12
    trades = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        lon = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')) &
                      (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))]
        if len(lon) < orb_bars + 6: continue
        orb_high = lon.iloc[:orb_bars]['high'].max()
        orb_low = lon.iloc[:orb_bars]['low'].min()
        for i in range(orb_bars, len(lon)):
            r = lon.iloc[i]
            if r['close'] > orb_high:
                pi = candles.index.get_loc(lon.index[i]); e = r['close']
                b, ex = sim_trail(candles, pi, e, 'long', SL, atr, 24, ACT, TRAIL)
                trades.append({'pnl':(ex-e)-get_sp(day),'atr':atr}); break
            elif r['close'] < orb_low:
                pi = candles.index.get_loc(lon.index[i]); e = r['close']
                b, ex = sim_trail(candles, pi, e, 'short', SL, atr, 24, ACT, TRAIL)
                trades.append({'pnl':(e-ex)-get_sp(day),'atr':atr}); break
    test_signal(trades, f"ORB London {orb_bars*5}min")

# ── 8. Opening range breakout NY 30min ──
print("\n" + "="*80)
print("8. OPENING RANGE BREAKOUT NY 30min")
print("="*80)
for orb_bars in [6, 12]:
    trades = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        ny = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC')) &
                     (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,21,30,tz='UTC'))]
        if len(ny) < orb_bars + 6: continue
        orb_high = ny.iloc[:orb_bars]['high'].max()
        orb_low = ny.iloc[:orb_bars]['low'].min()
        for i in range(orb_bars, len(ny)):
            r = ny.iloc[i]
            if r['close'] > orb_high:
                pi = candles.index.get_loc(ny.index[i]); e = r['close']
                b, ex = sim_trail(candles, pi, e, 'long', SL, atr, 24, ACT, TRAIL)
                trades.append({'pnl':(ex-e)-get_sp(day),'atr':atr}); break
            elif r['close'] < orb_low:
                pi = candles.index.get_loc(ny.index[i]); e = r['close']
                b, ex = sim_trail(candles, pi, e, 'short', SL, atr, 24, ACT, TRAIL)
                trades.append({'pnl':(e-ex)-get_sp(day),'atr':atr}); break
    test_signal(trades, f"ORB NY {orb_bars*5}min")

conn.close()
print("\n" + "="*80)
print("FIN v7")
print("="*80)
