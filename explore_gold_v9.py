"""
Exploration v9 — 20 nouveaux concepts
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

def test_signal(trades, label):
    if len(trades) < 20:
        print(f"    {label:65s}: n={len(trades):4d} -- trop peu"); return
    df = pd.DataFrame(trades)
    gp = df[df['pnl']>0]['pnl'].sum(); gl = abs(df[df['pnl']<0]['pnl'].sum())+0.001
    wr = (df['pnl']>0).mean()*100; mid = len(df)//2
    f1 = df.iloc[:mid]['pnl'].mean(); f2 = df.iloc[mid:]['pnl'].mean()
    ok = "OK" if f1>0 and f2>0 else "~"
    star = " ***" if gp/gl >= 1.3 and f1>0 and f2>0 else ""
    print(f"    {label:65s}: n={len(df):4d} WR={wr:3.0f}% PF={gp/gl:.2f} [{f1:+.3f}|{f2:+.3f}] {ok}{star}")

# Pre-calcul : range et direction par jour
daily_data = {}
for di, day in enumerate(trading_days):
    dc = candles[candles['date'] == day]
    if len(dc) < 10: continue
    daily_data[day] = {
        'high': dc['high'].max(), 'low': dc['low'].min(),
        'open': dc.iloc[0]['open'], 'close': dc.iloc[-1]['close'],
        'range': dc['high'].max() - dc['low'].min(),
        'dir': 1 if dc.iloc[-1]['close'] > dc.iloc[0]['open'] else -1,
        'dow': day.weekday()  # 0=lundi, 4=vendredi
    }

print("="*80)
print("EXPLORATION v9 — 20 concepts")
print("="*80)

# ── 1. JOUR DE LA SEMAINE — filtre sur les strats existantes ──
print("\n" + "="*80)
print("1. JOUR DE LA SEMAINE — NY1st (strat G) par jour")
print("="*80)
for dow, dow_name in [(0,'Lun'),(1,'Mar'),(2,'Mer'),(3,'Jeu'),(4,'Ven')]:
    trades = []
    for day in trading_days:
        if day.weekday() != dow: continue
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        p = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,21,30,tz='UTC'))]
        if len(p) < 6: continue
        body = p.iloc[0]['close'] - p.iloc[0]['open']
        if abs(body) < 0.3*atr or len(p) < 2: continue
        d = 'long' if body > 0 else 'short'
        pi = candles.index.get_loc(p.index[1]); e = p.iloc[1]['open']
        b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
        pnl = (ex-e) if d == 'long' else (e-ex)
        trades.append({'pnl':pnl-get_sp(day)})
    test_signal(trades, f"NY1st {dow_name}")

# ── 2. REGIME ATR — high vol vs low vol ──
print("\n" + "="*80)
print("2. REGIME ATR — strats en high vol vs low vol")
print("="*80)
atr_values = sorted([v for v in daily_atr.values() if v > 0])
atr_med = np.median(atr_values)
for regime, label in [('high', f'ATR > median ({atr_med:.2f})'), ('low', f'ATR < median ({atr_med:.2f})')]:
    trades = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        if regime == 'high' and atr < atr_med: continue
        if regime == 'low' and atr >= atr_med: continue
        p = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,21,30,tz='UTC'))]
        if len(p) < 6: continue
        body = p.iloc[0]['close'] - p.iloc[0]['open']
        if abs(body) < 0.3*atr or len(p) < 2: continue
        d = 'long' if body > 0 else 'short'
        pi = candles.index.get_loc(p.index[1]); e = p.iloc[1]['open']
        b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
        pnl = (ex-e) if d == 'long' else (e-ex)
        trades.append({'pnl':pnl-get_sp(day)})
    test_signal(trades, f"NY1st {label}")

# ── 3. DIRECTION VEILLE — continuation ou reversal ──
print("\n" + "="*80)
print("3. DIRECTION VEILLE → today continuation/reversal")
print("="*80)
for mode in ['cont', 'rev']:
    trades = []
    for di, day in enumerate(trading_days):
        if di == 0: continue
        pd_ = trading_days[di-1]; atr = daily_atr.get(pd_, global_atr)
        if atr == 0 or pd_ not in daily_data: continue
        prev_dir = daily_data[pd_]['dir']
        lon = candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
        if len(lon) < 6: continue
        pi = candles.index.get_loc(lon.index[0]); e = lon.iloc[0]['open']
        if mode == 'cont': d = 'long' if prev_dir > 0 else 'short'
        else: d = 'short' if prev_dir > 0 else 'long'
        b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
        pnl = (ex-e) if d == 'long' else (e-ex)
        trades.append({'pnl':pnl-get_sp(day)})
    test_signal(trades, f"Prev day dir → {mode} at London open")

# ── 4. RANGE VEILLE — breakout du high/low de D-1 ──
print("\n" + "="*80)
print("4. RANGE VEILLE — breakout D-1 high/low pendant London")
print("="*80)
trades = []
for di, day in enumerate(trading_days):
    if di == 0: continue
    pd_ = trading_days[di-1]; atr = daily_atr.get(pd_, global_atr)
    if atr == 0 or pd_ not in daily_data: continue
    prev_h = daily_data[pd_]['high']; prev_l = daily_data[pd_]['low']
    lon = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))]
    if len(lon) < 6: continue
    for i in range(len(lon)):
        r = lon.iloc[i]
        if r['close'] > prev_h:
            pi = candles.index.get_loc(lon.index[i])
            b, ex = sim_trail(candles, pi, r['close'], 'long', SL, atr, 24, ACT, TRAIL)
            trades.append({'pnl':(ex-r['close'])-get_sp(day)}); break
        if r['close'] < prev_l:
            pi = candles.index.get_loc(lon.index[i])
            b, ex = sim_trail(candles, pi, r['close'], 'short', SL, atr, 24, ACT, TRAIL)
            trades.append({'pnl':(r['close']-ex)-get_sp(day)}); break
test_signal(trades, "D-1 range breakout (London)")

trades = []
for di, day in enumerate(trading_days):
    if di == 0: continue
    pd_ = trading_days[di-1]; atr = daily_atr.get(pd_, global_atr)
    if atr == 0 or pd_ not in daily_data: continue
    prev_h = daily_data[pd_]['high']; prev_l = daily_data[pd_]['low']
    ny = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,21,30,tz='UTC'))]
    if len(ny) < 6: continue
    for i in range(len(ny)):
        r = ny.iloc[i]
        if r['close'] > prev_h:
            pi = candles.index.get_loc(ny.index[i])
            b, ex = sim_trail(candles, pi, r['close'], 'long', SL, atr, 24, ACT, TRAIL)
            trades.append({'pnl':(ex-r['close'])-get_sp(day)}); break
        if r['close'] < prev_l:
            pi = candles.index.get_loc(ny.index[i])
            b, ex = sim_trail(candles, pi, r['close'], 'short', SL, atr, 24, ACT, TRAIL)
            trades.append({'pnl':(r['close']-ex)-get_sp(day)}); break
test_signal(trades, "D-1 range breakout (NY)")

# ── 5. DOJI → breakout bougie suivante ──
print("\n" + "="*80)
print("5. DOJI (body<10% range) → breakout next candle")
print("="*80)
for sn, s_start, s_end in [('TOK',0,6),('LON',8,14.5),('NY',14.5,21.5)]:
    trades = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        sh=int(s_start); sm=int((s_start%1)*60); eh=int(s_end); em=int((s_end%1)*60)
        sess = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,sh,sm,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,eh,em,tz='UTC'))]
        if len(sess) < 6: continue
        for i in range(len(sess)-1):
            r = sess.iloc[i]; rng = r['high']-r['low']
            if rng < 0.2*atr: continue
            body = abs(r['close']-r['open'])
            if body/rng > 0.1: continue  # pas un doji
            # Bougie suivante = breakout
            nb = sess.iloc[i+1]; nb_body = nb['close']-nb['open']
            if abs(nb_body) < 0.3*atr: continue
            d = 'long' if nb_body > 0 else 'short'
            pi = candles.index.get_loc(sess.index[i+1]); e = nb['close']
            b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
            pnl = (ex-e) if d == 'long' else (e-ex)
            trades.append({'pnl':pnl-get_sp(day)}); break
    test_signal(trades, f"Doji→breakout ({sn})")

# ── 6. PIN BAR (meche >2x body, rejet d'un niveau) ──
print("\n" + "="*80)
print("6. PIN BAR rejection → continuation meche")
print("="*80)
for sn, s_start, s_end in [('TOK',0,6),('LON',8,14.5),('NY',14.5,21.5)]:
    trades = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        sh=int(s_start); sm=int((s_start%1)*60); eh=int(s_end); em=int((s_end%1)*60)
        sess = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,sh,sm,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,eh,em,tz='UTC'))]
        if len(sess) < 6: continue
        for i in range(len(sess)):
            r = sess.iloc[i]; body = abs(r['close']-r['open']); rng = r['high']-r['low']
            if rng < 0.3*atr or body == 0: continue
            upper = r['high']-max(r['open'],r['close']); lower = min(r['open'],r['close'])-r['low']
            # Pin bar bas = longue meche basse → bullish
            if lower > 2*body and upper < 0.5*body:
                pi = candles.index.get_loc(sess.index[i]); e = r['close']
                b, ex = sim_trail(candles, pi, e, 'long', SL, atr, 24, ACT, TRAIL)
                trades.append({'pnl':(ex-e)-get_sp(day)}); break
            # Pin bar haut = longue meche haute → bearish
            if upper > 2*body and lower < 0.5*body:
                pi = candles.index.get_loc(sess.index[i]); e = r['close']
                b, ex = sim_trail(candles, pi, e, 'short', SL, atr, 24, ACT, TRAIL)
                trades.append({'pnl':(e-ex)-get_sp(day)}); break
    test_signal(trades, f"Pin bar ({sn})")

# ── 7. DOUBLE INSIDE BAR → explosion ──
print("\n" + "="*80)
print("7. DOUBLE INSIDE BAR → breakout")
print("="*80)
for sn, s_start, s_end in [('TOK',0,6),('LON',8,14.5),('NY',14.5,21.5)]:
    trades = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        sh=int(s_start); sm=int((s_start%1)*60); eh=int(s_end); em=int((s_end%1)*60)
        sess = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,sh,sm,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,eh,em,tz='UTC'))]
        if len(sess) < 6: continue
        for i in range(2, len(sess)):
            c0=sess.iloc[i-2]; c1=sess.iloc[i-1]; c2=sess.iloc[i]
            # c1 inside c0, c2 breaks out
            if c1['high']<=c0['high'] and c1['low']>=c0['low']:
                if c2['close'] > c0['high']:
                    pi = candles.index.get_loc(sess.index[i])
                    b, ex = sim_trail(candles, pi, c2['close'], 'long', SL, atr, 24, ACT, TRAIL)
                    trades.append({'pnl':(ex-c2['close'])-get_sp(day)}); break
                elif c2['close'] < c0['low']:
                    pi = candles.index.get_loc(sess.index[i])
                    b, ex = sim_trail(candles, pi, c2['close'], 'short', SL, atr, 24, ACT, TRAIL)
                    trades.append({'pnl':(c2['close']-ex)-get_sp(day)}); break
    test_signal(trades, f"Double inside bar ({sn})")

# ── 8. PREVIOUS SESSION HIGH/LOW comme S/R ──
print("\n" + "="*80)
print("8. PREV SESSION HIGH/LOW → reversal")
print("="*80)
# Tokyo H/L → reversal pendant London
trades = []
for day in trading_days:
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    tok = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(tok) < 10: continue
    tok_h = tok['high'].max(); tok_l = tok['low'].min()
    lon = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))]
    if len(lon) < 6: continue
    for i in range(len(lon)):
        r = lon.iloc[i]
        if r['high'] >= tok_h and r['close'] < tok_h:
            pi = candles.index.get_loc(lon.index[i])
            b, ex = sim_trail(candles, pi, r['close'], 'short', SL, atr, 24, ACT, TRAIL)
            trades.append({'pnl':(r['close']-ex)-get_sp(day)}); break
        if r['low'] <= tok_l and r['close'] > tok_l:
            pi = candles.index.get_loc(lon.index[i])
            b, ex = sim_trail(candles, pi, r['close'], 'long', SL, atr, 24, ACT, TRAIL)
            trades.append({'pnl':(ex-r['close'])-get_sp(day)}); break
test_signal(trades, "Tokyo H/L → reversal London")

# London H/L → reversal pendant NY
trades = []
for day in trading_days:
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    lon = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))]
    if len(lon) < 10: continue
    lon_h = lon['high'].max(); lon_l = lon['low'].min()
    ny = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,21,30,tz='UTC'))]
    if len(ny) < 6: continue
    for i in range(len(ny)):
        r = ny.iloc[i]
        if r['high'] >= lon_h and r['close'] < lon_h:
            pi = candles.index.get_loc(ny.index[i])
            b, ex = sim_trail(candles, pi, r['close'], 'short', SL, atr, 24, ACT, TRAIL)
            trades.append({'pnl':(r['close']-ex)-get_sp(day)}); break
        if r['low'] <= lon_l and r['close'] > lon_l:
            pi = candles.index.get_loc(ny.index[i])
            b, ex = sim_trail(candles, pi, r['close'], 'long', SL, atr, 24, ACT, TRAIL)
            trades.append({'pnl':(ex-r['close'])-get_sp(day)}); break
test_signal(trades, "London H/L → reversal NY")

# ── 9. FIRST PULLBACK — momentum puis retrace puis continuation ──
print("\n" + "="*80)
print("9. FIRST PULLBACK — apres move >1ATR, 1er retrace >0.3ATR → cont")
print("="*80)
for sn, s_start, s_end in [('LON',8,14.5),('NY',14.5,21.5)]:
    trades = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        sh=int(s_start); sm=int((s_start%1)*60); eh=int(s_end); em=int((s_end%1)*60)
        sess = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,sh,sm,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,eh,em,tz='UTC'))]
        if len(sess) < 12: continue
        # Chercher un move >1ATR dans les 6 premieres bougies
        move = sess.iloc[5]['close'] - sess.iloc[0]['open']
        if abs(move) < 1.0*atr: continue
        move_dir = 1 if move > 0 else -1
        # Chercher un pullback >0.3ATR dans les bougies suivantes
        for i in range(6, len(sess)):
            r = sess.iloc[i]
            pb = r['close'] - sess.iloc[i-1]['close']
            if move_dir > 0 and pb < -0.3*atr:  # pullback baissier dans un move haussier
                pi = candles.index.get_loc(sess.index[i]); e = r['close']
                b, ex = sim_trail(candles, pi, e, 'long', SL, atr, 24, ACT, TRAIL)
                trades.append({'pnl':(ex-e)-get_sp(day)}); break
            if move_dir < 0 and pb > 0.3*atr:
                pi = candles.index.get_loc(sess.index[i]); e = r['close']
                b, ex = sim_trail(candles, pi, e, 'short', SL, atr, 24, ACT, TRAIL)
                trades.append({'pnl':(e-ex)-get_sp(day)}); break
    test_signal(trades, f"First pullback ({sn})")

# ── 10. MEAN REVERSION apres move extreme (>3ATR jour) ──
print("\n" + "="*80)
print("10. MEAN REVERSION — jour >3ATR → fade le lendemain London")
print("="*80)
for thresh in [2.0, 3.0, 4.0]:
    trades = []
    for di, day in enumerate(trading_days):
        if di == 0: continue
        pd_ = trading_days[di-1]; atr = daily_atr.get(pd_, global_atr)
        if atr == 0 or pd_ not in daily_data: continue
        prev_range = daily_data[pd_]['range']
        if prev_range < thresh * atr: continue
        prev_dir = daily_data[pd_]['dir']
        lon = candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
        if len(lon) < 6: continue
        pi = candles.index.get_loc(lon.index[0]); e = lon.iloc[0]['open']
        d = 'short' if prev_dir > 0 else 'long'
        b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
        pnl = (ex-e) if d == 'long' else (e-ex)
        trades.append({'pnl':pnl-get_sp(day)})
    test_signal(trades, f"Mean rev apres jour >{thresh}ATR")

# ── 11. WEEKLY OPEN BREAKOUT ──
print("\n" + "="*80)
print("11. WEEKLY OPEN BREAKOUT — break du range des 2 premieres heures du lundi")
print("="*80)
trades = []
for day in trading_days:
    if day.weekday() != 0: continue  # lundi
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    first2h = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,2,0,tz='UTC'))]
    if len(first2h) < 20: continue
    wk_h = first2h['high'].max(); wk_l = first2h['low'].min()
    rest = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,2,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,21,30,tz='UTC'))]
    if len(rest) < 6: continue
    for i in range(len(rest)):
        r = rest.iloc[i]
        if r['close'] > wk_h:
            pi = candles.index.get_loc(rest.index[i])
            b, ex = sim_trail(candles, pi, r['close'], 'long', SL, atr, 24, ACT, TRAIL)
            trades.append({'pnl':(ex-r['close'])-get_sp(day)}); break
        if r['close'] < wk_l:
            pi = candles.index.get_loc(rest.index[i])
            b, ex = sim_trail(candles, pi, r['close'], 'short', SL, atr, 24, ACT, TRAIL)
            trades.append({'pnl':(r['close']-ex)-get_sp(day)}); break
test_signal(trades, "Weekly open breakout (lundi)")

# ── 12. CONSECUTIVE LOSING DAYS → reversal ──
print("\n" + "="*80)
print("12. CONSECUTIVE DAYS meme sens → reversal le jour suivant")
print("="*80)
for n_days in [2, 3]:
    trades = []
    for di, day in enumerate(trading_days):
        if di < n_days: continue
        atr = daily_atr.get(trading_days[di-1], global_atr)
        if atr == 0: continue
        dirs = []
        for k in range(n_days):
            dk = trading_days[di-n_days+k]
            if dk in daily_data: dirs.append(daily_data[dk]['dir'])
        if len(dirs) < n_days or len(set(dirs)) > 1: continue
        lon = candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
        if len(lon) < 6: continue
        pi = candles.index.get_loc(lon.index[0]); e = lon.iloc[0]['open']
        d = 'short' if dirs[0] > 0 else 'long'
        b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
        pnl = (ex-e) if d == 'long' else (e-ex)
        trades.append({'pnl':pnl-get_sp(day)})
    test_signal(trades, f"{n_days} jours meme sens → reversal London")

# ── 13. PRE-MARKET SQUEEZE — range Tokyo <0.5ATR → break London ──
print("\n" + "="*80)
print("13. PRE-MARKET SQUEEZE — Tokyo range etroit → break London")
print("="*80)
for thresh in [0.5, 1.0]:
    trades = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        tok = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
        if len(tok) < 10: continue
        tok_range = (tok['high'].max() - tok['low'].min()) / atr
        if tok_range >= thresh: continue
        lon = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))]
        if len(lon) < 6: continue
        tok_h = tok['high'].max(); tok_l = tok['low'].min()
        for i in range(len(lon)):
            r = lon.iloc[i]
            if r['close'] > tok_h:
                pi = candles.index.get_loc(lon.index[i])
                b, ex = sim_trail(candles, pi, r['close'], 'long', SL, atr, 24, ACT, TRAIL)
                trades.append({'pnl':(ex-r['close'])-get_sp(day)}); break
            if r['close'] < tok_l:
                pi = candles.index.get_loc(lon.index[i])
                b, ex = sim_trail(candles, pi, r['close'], 'short', SL, atr, 24, ACT, TRAIL)
                trades.append({'pnl':(r['close']-ex)-get_sp(day)}); break
    test_signal(trades, f"Tokyo squeeze <{thresh}ATR → London break")

# ── 14. LAST HOUR REVERSAL — derniere heure de session inverse ──
print("\n" + "="*80)
print("14. LAST HOUR REVERSAL — derniere heure de London reverse le move")
print("="*80)
for thresh in [0.5, 1.0]:
    trades = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        lon = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))]
        if len(lon) < 24: continue
        last_h = lon.iloc[-6:]  # derniere heure
        m = (last_h.iloc[-1]['close'] - last_h.iloc[0]['open']) / atr
        main_move = (lon.iloc[-7]['close'] - lon.iloc[0]['open']) / atr
        if abs(main_move) < thresh: continue
        # Reversal = derniere heure opposee au move principal
        if main_move > 0 and m < -0.3:
            ny = candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC')]
            if len(ny) < 6: continue
            pi = candles.index.get_loc(ny.index[0]); e = ny.iloc[0]['open']
            b, ex = sim_trail(candles, pi, e, 'short', SL, atr, 24, ACT, TRAIL)
            trades.append({'pnl':(e-ex)-get_sp(day)})
        elif main_move < 0 and m > 0.3:
            ny = candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC')]
            if len(ny) < 6: continue
            pi = candles.index.get_loc(ny.index[0]); e = ny.iloc[0]['open']
            b, ex = sim_trail(candles, pi, e, 'long', SL, atr, 24, ACT, TRAIL)
            trades.append({'pnl':(ex-e)-get_sp(day)})
    test_signal(trades, f"London last hour reversal (main>{thresh}ATR)")

# ── 15. SESSION MIDPOINT RETEST ──
print("\n" + "="*80)
print("15. SESSION MIDPOINT — prix revient au mid de Tokyo pendant London")
print("="*80)
trades = []
for day in trading_days:
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    tok = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(tok) < 10: continue
    tok_mid = (tok['high'].max() + tok['low'].min()) / 2
    tok_dir = 1 if tok.iloc[-1]['close'] > tok.iloc[0]['open'] else -1
    lon = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))]
    if len(lon) < 6: continue
    for i in range(len(lon)):
        r = lon.iloc[i]
        # Prix touche le mid → rebond dans la direction de Tokyo
        if tok_dir > 0 and r['low'] <= tok_mid and r['close'] > tok_mid:
            pi = candles.index.get_loc(lon.index[i])
            b, ex = sim_trail(candles, pi, r['close'], 'long', SL, atr, 24, ACT, TRAIL)
            trades.append({'pnl':(ex-r['close'])-get_sp(day)}); break
        if tok_dir < 0 and r['high'] >= tok_mid and r['close'] < tok_mid:
            pi = candles.index.get_loc(lon.index[i])
            b, ex = sim_trail(candles, pi, r['close'], 'short', SL, atr, 24, ACT, TRAIL)
            trades.append({'pnl':(r['close']-ex)-get_sp(day)}); break
test_signal(trades, "Tokyo midpoint retest → cont (London)")

# ── 16. CANDLE RATIO — % bullish dans les 6 dernieres bougies ──
print("\n" + "="*80)
print("16. CANDLE RATIO — 5/6 ou 6/6 bougies meme sens → continuation")
print("="*80)
for sn, s_start, s_end in [('TOK',0,6),('LON',8,14.5)]:
    trades = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        sh=int(s_start); sm=int((s_start%1)*60); eh=int(s_end); em=int((s_end%1)*60)
        sess = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,sh,sm,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,eh,em,tz='UTC'))]
        if len(sess) < 12: continue
        for i in range(6, len(sess)):
            last6 = sess.iloc[i-6:i]
            n_bull = (last6['close'] > last6['open']).sum()
            if n_bull >= 5:
                pi = candles.index.get_loc(sess.index[i]); e = sess.iloc[i]['open']
                b, ex = sim_trail(candles, pi, e, 'long', SL, atr, 24, ACT, TRAIL)
                trades.append({'pnl':(ex-e)-get_sp(day)}); break
            elif n_bull <= 1:
                pi = candles.index.get_loc(sess.index[i]); e = sess.iloc[i]['open']
                b, ex = sim_trail(candles, pi, e, 'short', SL, atr, 24, ACT, TRAIL)
                trades.append({'pnl':(e-ex)-get_sp(day)}); break
    test_signal(trades, f"Candle ratio 5/6+ ({sn}) → cont")

# ── 17. GAP INTRADAY — gap entre sessions (Tok close vs Tok open) ──
print("\n" + "="*80)
print("17. GAP INTRADAY — gap a l'ouverture du jour (open vs prev close)")
print("="*80)
for mode in ['cont', 'fill']:
    trades = []
    for di, day in enumerate(trading_days):
        if di == 0: continue
        pd_ = trading_days[di-1]; atr = daily_atr.get(pd_, global_atr)
        if atr == 0: continue
        today_c = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC'))]
        prev_c = candles[candles['date']==pd_]
        if len(today_c) < 6 or len(prev_c) < 5: continue
        gap = (today_c.iloc[0]['open'] - prev_c.iloc[-1]['close']) / atr
        if abs(gap) < 0.3: continue
        pi = candles.index.get_loc(today_c.index[0]); e = today_c.iloc[0]['open']
        if mode == 'cont': d = 'long' if gap > 0 else 'short'
        else: d = 'short' if gap > 0 else 'long'
        b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
        pnl = (ex-e) if d == 'long' else (e-ex)
        trades.append({'pnl':pnl-get_sp(day)})
    test_signal(trades, f"Day gap >0.3ATR → {mode}")

# ── 18. EMA CROSS sur 5min ──
print("\n" + "="*80)
print("18. EMA CROSS — EMA8 croise EMA21 pendant session")
print("="*80)
candles['ema8'] = candles['close'].ewm(span=8, adjust=False).mean()
candles['ema21'] = candles['close'].ewm(span=21, adjust=False).mean()
for sn, s_start, s_end in [('TOK',0,6),('LON',8,14.5),('NY',14.5,21.5)]:
    trades = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        sh=int(s_start); sm=int((s_start%1)*60); eh=int(s_end); em=int((s_end%1)*60)
        sess = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,sh,sm,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,eh,em,tz='UTC'))]
        if len(sess) < 10: continue
        for i in range(1, len(sess)):
            prev_diff = sess.iloc[i-1]['ema8'] - sess.iloc[i-1]['ema21']
            curr_diff = sess.iloc[i]['ema8'] - sess.iloc[i]['ema21']
            if prev_diff <= 0 and curr_diff > 0 and abs(curr_diff) > 0.1*atr:
                pi = candles.index.get_loc(sess.index[i])
                b, ex = sim_trail(candles, pi, sess.iloc[i]['close'], 'long', SL, atr, 24, ACT, TRAIL)
                trades.append({'pnl':(ex-sess.iloc[i]['close'])-get_sp(day)}); break
            if prev_diff >= 0 and curr_diff < 0 and abs(curr_diff) > 0.1*atr:
                pi = candles.index.get_loc(sess.index[i])
                b, ex = sim_trail(candles, pi, sess.iloc[i]['close'], 'short', SL, atr, 24, ACT, TRAIL)
                trades.append({'pnl':(sess.iloc[i]['close']-ex)-get_sp(day)}); break
    test_signal(trades, f"EMA8x21 cross ({sn})")

# ── 19. RANGE EXPANSION FILTER — today range > yesterday ──
print("\n" + "="*80)
print("19. RANGE EXPANSION — Tokyo range > prev Tokyo range → break London")
print("="*80)
trades = []
for di, day in enumerate(trading_days):
    if di == 0: continue
    pd_ = trading_days[di-1]; atr = daily_atr.get(pd_, global_atr)
    if atr == 0: continue
    tok_today = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    tok_prev = candles[(candles['ts_dt']>=pd.Timestamp(pd_.year,pd_.month,pd_.day,0,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(pd_.year,pd_.month,pd_.day,6,0,tz='UTC'))]
    if len(tok_today) < 10 or len(tok_prev) < 10: continue
    r_today = tok_today['high'].max() - tok_today['low'].min()
    r_prev = tok_prev['high'].max() - tok_prev['low'].min()
    if r_today <= r_prev: continue
    tok_dir = 1 if tok_today.iloc[-1]['close'] > tok_today.iloc[0]['open'] else -1
    lon = candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
    if len(lon) < 6: continue
    pi = candles.index.get_loc(lon.index[0]); e = lon.iloc[0]['open']
    d = 'long' if tok_dir > 0 else 'short'
    b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
    pnl = (ex-e) if d == 'long' else (e-ex)
    trades.append({'pnl':pnl-get_sp(day)})
test_signal(trades, "Tokyo range expansion → cont London")

# ── 20. LONDON OPEN REJECTION — 1ere bougie London rejetee → inverse ──
print("\n" + "="*80)
print("20. LONDON OPEN REJECTION — 1ere bougie forte, 2eme inverse → fade")
print("="*80)
trades = []
for day in trading_days:
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    lon = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))]
    if len(lon) < 6: continue
    b1 = lon.iloc[0]['close'] - lon.iloc[0]['open']
    b2 = lon.iloc[1]['close'] - lon.iloc[1]['open']
    if abs(b1) < 0.3*atr: continue
    if b1*b2 >= 0: continue  # pas de rejection
    if abs(b2) < abs(b1)*0.5: continue  # rejection trop faible
    d = 'long' if b2 > 0 else 'short'
    pi = candles.index.get_loc(lon.index[1]); e = lon.iloc[1]['close']
    b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
    pnl = (ex-e) if d == 'long' else (e-ex)
    trades.append({'pnl':pnl-get_sp(day)})
test_signal(trades, "London open rejection → fade")

conn.close()
print("\n" + "="*80)
print("FIN v9")
print("="*80)
