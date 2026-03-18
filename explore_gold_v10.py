"""
Exploration v10 — 20 concepts supplementaires
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

# Pre-calcul
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

print("="*80)
print("EXPLORATION v10 — 20 concepts")
print("="*80)

# ── 1. ASIAN CLOSE LEVEL — prix de cloture Tokyo comme pivot ──
print("\n" + "="*80)
print("1. ASIAN CLOSE comme pivot — retest pendant London → rebond")
print("="*80)
trades = []
for day in trading_days:
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    tok = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(tok) < 10: continue
    tok_close = tok.iloc[-1]['close']
    tok_dir = 1 if tok.iloc[-1]['close'] > tok.iloc[0]['open'] else -1
    lon = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))]
    if len(lon) < 6: continue
    for i in range(len(lon)):
        r = lon.iloc[i]
        # Prix revient a tok_close depuis au-dessus → support
        if tok_dir > 0 and r['low'] <= tok_close + 0.1*atr and r['low'] >= tok_close - 0.2*atr and r['close'] > tok_close:
            pi = candles.index.get_loc(lon.index[i])
            b, ex = sim_trail(candles, pi, r['close'], 'long', SL, atr, 24, ACT, TRAIL)
            trades.append({'pnl':(ex-r['close'])-get_sp(day)}); break
        # Prix revient a tok_close depuis en dessous → resistance
        if tok_dir < 0 and r['high'] >= tok_close - 0.1*atr and r['high'] <= tok_close + 0.2*atr and r['close'] < tok_close:
            pi = candles.index.get_loc(lon.index[i])
            b, ex = sim_trail(candles, pi, r['close'], 'short', SL, atr, 24, ACT, TRAIL)
            trades.append({'pnl':(r['close']-ex)-get_sp(day)}); break
test_signal(trades, "Asian close retest → cont (London)")

# ── 2. TRAP CANDLE — faux break du high/low de session puis reverse ──
print("\n" + "="*80)
print("2. TRAP CANDLE — wick depasse le high/low session puis close inside")
print("="*80)
for sn, s_start, s_end in [('TOK',0,6),('LON',8,14.5),('NY',14.5,21.5)]:
    trades = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        sh=int(s_start);sm=int((s_start%1)*60);eh=int(s_end);em=int((s_end%1)*60)
        sess = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,sh,sm,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,eh,em,tz='UTC'))]
        if len(sess) < 8: continue
        run_high = sess.iloc[:3]['high'].max()
        run_low = sess.iloc[:3]['low'].min()
        for i in range(3, len(sess)):
            r = sess.iloc[i]
            # Trap high: wick au-dessus du run_high mais close en dessous
            if r['high'] > run_high + 0.1*atr and r['close'] < run_high and r['close'] < r['open']:
                pi = candles.index.get_loc(sess.index[i])
                b, ex = sim_trail(candles, pi, r['close'], 'short', SL, atr, 24, ACT, TRAIL)
                trades.append({'pnl':(r['close']-ex)-get_sp(day)}); break
            # Trap low
            if r['low'] < run_low - 0.1*atr and r['close'] > run_low and r['close'] > r['open']:
                pi = candles.index.get_loc(sess.index[i])
                b, ex = sim_trail(candles, pi, r['close'], 'long', SL, atr, 24, ACT, TRAIL)
                trades.append({'pnl':(ex-r['close'])-get_sp(day)}); break
            run_high = max(run_high, r['high'])
            run_low = min(run_low, r['low'])
    test_signal(trades, f"Trap candle ({sn})")

# ── 3. LONDON MOMENTUM SHIFT — 1ere heure London vs 2eme heure ──
print("\n" + "="*80)
print("3. LONDON SHIFT — 1h London up puis 2h London down → fade NY")
print("="*80)
for thresh in [0.3, 0.5]:
    trades = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        lon1 = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,9,0,tz='UTC'))]
        lon2 = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,9,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,10,0,tz='UTC'))]
        if len(lon1) < 10 or len(lon2) < 10: continue
        m1 = (lon1.iloc[-1]['close'] - lon1.iloc[0]['open']) / atr
        m2 = (lon2.iloc[-1]['close'] - lon2.iloc[0]['open']) / atr
        if abs(m1) < thresh or abs(m2) < thresh: continue
        if m1 * m2 >= 0: continue  # pas de shift
        # Fade la 2eme heure (continuation de la 1ere)
        post = candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,10,0,tz='UTC')]
        if len(post) < 6: continue
        pi = candles.index.get_loc(post.index[0]); e = post.iloc[0]['open']
        d = 'long' if m1 > 0 else 'short'  # continue la 1ere heure
        b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
        pnl = (ex-e) if d == 'long' else (e-ex)
        trades.append({'pnl':pnl-get_sp(day)})
    test_signal(trades, f"London shift (thresh={thresh}ATR) → cont 1h")

# ── 4. POWER HOUR — 1ere bougie apres gap de session (6h-8h gap) ──
print("\n" + "="*80)
print("4. POWER HOUR — 1ere bougie London forte (>0.5ATR) + Tokyo flat → cont")
print("="*80)
trades = []
for day in trading_days:
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    tok = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(tok) < 10: continue
    tok_range = (tok['high'].max() - tok['low'].min()) / atr
    if tok_range > 2.0: continue  # Tokyo pas flat
    lon = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))]
    if len(lon) < 6: continue
    body = lon.iloc[0]['close'] - lon.iloc[0]['open']
    if abs(body) < 0.5*atr: continue
    d = 'long' if body > 0 else 'short'
    if len(lon) < 2: continue
    pi = candles.index.get_loc(lon.index[1]); e = lon.iloc[1]['open']
    b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
    pnl = (ex-e) if d == 'long' else (e-ex)
    trades.append({'pnl':pnl-get_sp(day)})
test_signal(trades, "Power hour London (Tokyo flat + 1st candle >0.5ATR)")

# ── 5. HIGHER HIGH / LOWER LOW — 3 bougies avec HH ou LL ──
print("\n" + "="*80)
print("5. HH/LL structure — 3 bougies avec higher highs → continuation")
print("="*80)
for sn, s_start, s_end in [('TOK',0,6),('LON',8,14.5),('NY',14.5,21.5)]:
    trades = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        sh=int(s_start);sm=int((s_start%1)*60);eh=int(s_end);em=int((s_end%1)*60)
        sess = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,sh,sm,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,eh,em,tz='UTC'))]
        if len(sess) < 6: continue
        for i in range(2, len(sess)):
            c1=sess.iloc[i-2];c2=sess.iloc[i-1];c3=sess.iloc[i]
            # HH + HL = uptrend
            if c2['high']>c1['high'] and c3['high']>c2['high'] and c2['low']>c1['low'] and c3['low']>c2['low']:
                if (c3['high']-c1['low']) >= 0.5*atr:
                    pi = candles.index.get_loc(sess.index[i])
                    b, ex = sim_trail(candles, pi, c3['close'], 'long', SL, atr, 24, ACT, TRAIL)
                    trades.append({'pnl':(ex-c3['close'])-get_sp(day)}); break
            # LL + LH = downtrend
            if c2['low']<c1['low'] and c3['low']<c2['low'] and c2['high']<c1['high'] and c3['high']<c2['high']:
                if (c1['high']-c3['low']) >= 0.5*atr:
                    pi = candles.index.get_loc(sess.index[i])
                    b, ex = sim_trail(candles, pi, c3['close'], 'short', SL, atr, 24, ACT, TRAIL)
                    trades.append({'pnl':(c3['close']-ex)-get_sp(day)}); break
    test_signal(trades, f"HH/LL structure ({sn})")

# ── 6. ABSORPTION — grosse bougie qui absorbe les 3 precedentes ──
print("\n" + "="*80)
print("6. ABSORPTION — bougie couvre le range des 3 precedentes")
print("="*80)
for sn, s_start, s_end in [('TOK',0,6),('LON',8,14.5),('NY',14.5,21.5)]:
    trades = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        sh=int(s_start);sm=int((s_start%1)*60);eh=int(s_end);em=int((s_end%1)*60)
        sess = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,sh,sm,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,eh,em,tz='UTC'))]
        if len(sess) < 6: continue
        for i in range(3, len(sess)):
            prev3_h = sess.iloc[i-3:i]['high'].max()
            prev3_l = sess.iloc[i-3:i]['low'].min()
            r = sess.iloc[i]
            body = abs(r['close']-r['open'])
            if r['high'] >= prev3_h and r['low'] <= prev3_l and body >= 0.5*atr:
                d = 'long' if r['close'] > r['open'] else 'short'
                pi = candles.index.get_loc(sess.index[i])
                b, ex = sim_trail(candles, pi, r['close'], d, SL, atr, 24, ACT, TRAIL)
                pnl = (ex-r['close']) if d=='long' else (r['close']-ex)
                trades.append({'pnl':pnl-get_sp(day)}); break
    test_signal(trades, f"Absorption ({sn})")

# ── 7. BREAKAWAY GAP — London ouvre >0.5ATR au-dessus du high de Tokyo ──
print("\n" + "="*80)
print("7. BREAKAWAY — London open au-dessus/dessous du range Tokyo complet")
print("="*80)
trades = []
for day in trading_days:
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    tok = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(tok) < 10: continue
    tok_h = tok['high'].max(); tok_l = tok['low'].min()
    lon = candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
    if len(lon) < 6: continue
    lon_open = lon.iloc[0]['open']
    if lon_open > tok_h + 0.2*atr:
        pi = candles.index.get_loc(lon.index[0])
        b, ex = sim_trail(candles, pi, lon_open, 'long', SL, atr, 24, ACT, TRAIL)
        trades.append({'pnl':(ex-lon_open)-get_sp(day)})
    elif lon_open < tok_l - 0.2*atr:
        pi = candles.index.get_loc(lon.index[0])
        b, ex = sim_trail(candles, pi, lon_open, 'short', SL, atr, 24, ACT, TRAIL)
        trades.append({'pnl':(lon_open-ex)-get_sp(day)})
test_signal(trades, "Breakaway gap London (hors range Tokyo)")

# ── 8. MOMENTUM ACCELERATION — bougie actuelle > 2x bougie precedente ──
print("\n" + "="*80)
print("8. MOMENTUM ACCELERATION — body actuel > 2x body precedent, meme sens")
print("="*80)
for sn, s_start, s_end in [('TOK',0,6),('LON',8,14.5),('NY',14.5,21.5)]:
    trades = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        sh=int(s_start);sm=int((s_start%1)*60);eh=int(s_end);em=int((s_end%1)*60)
        sess = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,sh,sm,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,eh,em,tz='UTC'))]
        if len(sess) < 6: continue
        for i in range(1, len(sess)):
            b1 = sess.iloc[i-1]['close']-sess.iloc[i-1]['open']
            b2 = sess.iloc[i]['close']-sess.iloc[i]['open']
            if b1*b2 > 0 and abs(b2) >= 2*abs(b1) and abs(b1) >= 0.1*atr and abs(b2) >= 0.3*atr:
                d = 'long' if b2 > 0 else 'short'
                pi = candles.index.get_loc(sess.index[i]); e = sess.iloc[i]['close']
                b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
                pnl = (ex-e) if d=='long' else (e-ex)
                trades.append({'pnl':pnl-get_sp(day)}); break
    test_signal(trades, f"Momentum accel ({sn})")

# ── 9. FADE EXTREME MOVE — bougie >2ATR → fade ──
print("\n" + "="*80)
print("9. FADE EXTREME — bougie >2ATR → reversal")
print("="*80)
for sn, s_start, s_end in [('TOK',0,6),('LON',8,14.5),('NY',14.5,21.5)]:
    trades = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        sh=int(s_start);sm=int((s_start%1)*60);eh=int(s_end);em=int((s_end%1)*60)
        sess = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,sh,sm,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,eh,em,tz='UTC'))]
        if len(sess) < 6: continue
        for i in range(len(sess)):
            body = sess.iloc[i]['close'] - sess.iloc[i]['open']
            if abs(body) >= 2.0*atr:
                d = 'short' if body > 0 else 'long'
                pi = candles.index.get_loc(sess.index[i]); e = sess.iloc[i]['close']
                b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
                pnl = (ex-e) if d=='long' else (e-ex)
                trades.append({'pnl':pnl-get_sp(day)}); break
    test_signal(trades, f"Fade extreme >2ATR ({sn})")

# ── 10. RANGE MIDPOINT CROSS — prix croise le mid du range de session ──
print("\n" + "="*80)
print("10. SESSION RANGE MID — cross du mid en 2eme moitie de session → cont")
print("="*80)
for sn, s_start, s_end in [('LON',8,14.5),('NY',14.5,21.5)]:
    trades = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        sh=int(s_start);sm=int((s_start%1)*60);eh=int(s_end);em=int((s_end%1)*60)
        sess = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,sh,sm,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,eh,em,tz='UTC'))]
        if len(sess) < 20: continue
        mid_idx = len(sess)//2
        first_half = sess.iloc[:mid_idx]
        fh_mid = (first_half['high'].max() + first_half['low'].min()) / 2
        for i in range(mid_idx, len(sess)):
            r = sess.iloc[i]
            if r['close'] > fh_mid and sess.iloc[i-1]['close'] <= fh_mid:
                pi = candles.index.get_loc(sess.index[i])
                b, ex = sim_trail(candles, pi, r['close'], 'long', SL, atr, 24, ACT, TRAIL)
                trades.append({'pnl':(ex-r['close'])-get_sp(day)}); break
            if r['close'] < fh_mid and sess.iloc[i-1]['close'] >= fh_mid:
                pi = candles.index.get_loc(sess.index[i])
                b, ex = sim_trail(candles, pi, r['close'], 'short', SL, atr, 24, ACT, TRAIL)
                trades.append({'pnl':(r['close']-ex)-get_sp(day)}); break
    test_signal(trades, f"Mid cross 2nd half ({sn})")

# ── 11. CLOSE NEAR HIGH/LOW — bougie close dans le top/bottom 10% ──
print("\n" + "="*80)
print("11. CLOSE NEAR EXTREME — close dans top/bottom 10% du range → cont")
print("="*80)
for sn, s_start, s_end in [('TOK',0,6),('LON',8,14.5),('NY',14.5,21.5)]:
    trades = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        sh=int(s_start);sm=int((s_start%1)*60);eh=int(s_end);em=int((s_end%1)*60)
        sess = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,sh,sm,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,eh,em,tz='UTC'))]
        if len(sess) < 6: continue
        for i in range(len(sess)):
            r = sess.iloc[i]; rng = r['high']-r['low']
            if rng < 0.3*atr: continue
            pos_in_range = (r['close']-r['low'])/rng
            if pos_in_range >= 0.9 and abs(r['close']-r['open']) >= 0.2*atr:
                pi = candles.index.get_loc(sess.index[i])
                b, ex = sim_trail(candles, pi, r['close'], 'long', SL, atr, 24, ACT, TRAIL)
                trades.append({'pnl':(ex-r['close'])-get_sp(day)}); break
            if pos_in_range <= 0.1 and abs(r['close']-r['open']) >= 0.2*atr:
                pi = candles.index.get_loc(sess.index[i])
                b, ex = sim_trail(candles, pi, r['close'], 'short', SL, atr, 24, ACT, TRAIL)
                trades.append({'pnl':(r['close']-ex)-get_sp(day)}); break
    test_signal(trades, f"Close near extreme ({sn})")

# ── 12. TWIN CANDLES — 2 bougies quasi identiques → continuation ──
print("\n" + "="*80)
print("12. TWIN CANDLES — 2 bougies meme taille meme sens → continuation")
print("="*80)
for sn, s_start, s_end in [('TOK',0,6),('LON',8,14.5)]:
    trades = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        sh=int(s_start);sm=int((s_start%1)*60);eh=int(s_end);em=int((s_end%1)*60)
        sess = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,sh,sm,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,eh,em,tz='UTC'))]
        if len(sess) < 6: continue
        for i in range(1, len(sess)):
            b1 = sess.iloc[i-1]['close']-sess.iloc[i-1]['open']
            b2 = sess.iloc[i]['close']-sess.iloc[i]['open']
            if b1*b2 > 0 and abs(b1) >= 0.3*atr and abs(b2) >= 0.3*atr:
                ratio = abs(b1)/abs(b2) if abs(b2)>0 else 99
                if 0.7 <= ratio <= 1.3:  # quasi meme taille
                    d = 'long' if b2 > 0 else 'short'
                    pi = candles.index.get_loc(sess.index[i]); e = sess.iloc[i]['close']
                    b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
                    pnl = (ex-e) if d=='long' else (e-ex)
                    trades.append({'pnl':pnl-get_sp(day)}); break
    test_signal(trades, f"Twin candles ({sn})")

# ── 13. OPENING CANDLE BODY RATIO — body/range de la 1ere bougie ──
print("\n" + "="*80)
print("13. MARUBOZU OPEN — 1ere bougie body>80% range → strong continuation")
print("="*80)
for sn, s_start, s_end in [('LON',8,14.5),('NY',14.5,21.5)]:
    trades = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        sh=int(s_start);sm=int((s_start%1)*60);eh=int(s_end);em=int((s_end%1)*60)
        sess = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,sh,sm,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,eh,em,tz='UTC'))]
        if len(sess) < 6: continue
        first = sess.iloc[0]; body = abs(first['close']-first['open']); rng = first['high']-first['low']
        if rng < 0.3*atr or body/rng < 0.8: continue
        d = 'long' if first['close'] > first['open'] else 'short'
        if len(sess) < 2: continue
        pi = candles.index.get_loc(sess.index[1]); e = sess.iloc[1]['open']
        b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
        pnl = (ex-e) if d=='long' else (e-ex)
        trades.append({'pnl':pnl-get_sp(day)})
    test_signal(trades, f"Marubozu open ({sn})")

# ── 14. SQUEEZE BREAKOUT — 5 bougies <0.15ATR puis grosse ──
print("\n" + "="*80)
print("14. MICRO SQUEEZE — 3+ bougies <0.15ATR range puis break")
print("="*80)
for sn, s_start, s_end in [('TOK',0,6),('LON',8,14.5),('NY',14.5,21.5)]:
    trades = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        sh=int(s_start);sm=int((s_start%1)*60);eh=int(s_end);em=int((s_end%1)*60)
        sess = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,sh,sm,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,eh,em,tz='UTC'))]
        if len(sess) < 8: continue
        for i in range(3, len(sess)):
            # 3 bougies etroites
            narrow = all((sess.iloc[i-3+k]['high']-sess.iloc[i-3+k]['low']) < 0.15*atr for k in range(3))
            if not narrow: continue
            r = sess.iloc[i]; body = r['close']-r['open']
            if abs(body) < 0.3*atr: continue
            d = 'long' if body > 0 else 'short'
            pi = candles.index.get_loc(sess.index[i])
            b, ex = sim_trail(candles, pi, r['close'], d, SL, atr, 24, ACT, TRAIL)
            pnl = (ex-r['close']) if d=='long' else (r['close']-ex)
            trades.append({'pnl':pnl-get_sp(day)}); break
    test_signal(trades, f"Micro squeeze ({sn})")

# ── 15. NY LUNCH REVERSAL — 12h-13h UTC calme puis 13h-14:30 move ──
print("\n" + "="*80)
print("15. NY LUNCH → AFTERNOON — direction apres la pause dejeuner")
print("="*80)
for mode in ['cont', 'rev']:
    trades = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        morning = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,12,0,tz='UTC'))]
        if len(morning) < 20: continue
        m_move = (morning.iloc[-1]['close'] - morning.iloc[0]['open']) / atr
        if abs(m_move) < 0.5: continue
        afternoon = candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,13,0,tz='UTC')]
        if len(afternoon) < 6: continue
        pi = candles.index.get_loc(afternoon.index[0]); e = afternoon.iloc[0]['open']
        if mode == 'cont': d = 'long' if m_move > 0 else 'short'
        else: d = 'short' if m_move > 0 else 'long'
        b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
        pnl = (ex-e) if d == 'long' else (e-ex)
        trades.append({'pnl':pnl-get_sp(day)})
    test_signal(trades, f"Lunch break → {mode}")

# ── 16. ASIAN SESSION BODY — direction totale de Tokyo comme filtre ──
print("\n" + "="*80)
print("16. TOKYO BODY DIRECTION → London 1st candle filtre")
print("="*80)
trades = []
for day in trading_days:
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    tok = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(tok) < 10: continue
    tok_move = (tok.iloc[-1]['close'] - tok.iloc[0]['open']) / atr
    lon = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))]
    if len(lon) < 6: continue
    body = lon.iloc[0]['close'] - lon.iloc[0]['open']
    if abs(body) < 0.3*atr: continue
    lon_dir = 1 if body > 0 else -1
    # Ne prendre que quand Tokyo et London 1st sont dans le meme sens
    if (tok_move > 0.3 and lon_dir > 0) or (tok_move < -0.3 and lon_dir < 0):
        d = 'long' if lon_dir > 0 else 'short'
        if len(lon) < 2: continue
        pi = candles.index.get_loc(lon.index[1]); e = lon.iloc[1]['open']
        b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
        pnl = (ex-e) if d == 'long' else (e-ex)
        trades.append({'pnl':pnl-get_sp(day)})
test_signal(trades, "Tokyo+London1st aligned → cont")

# ── 17. REJECTION WICK RATIO — bougie avec meche >3x body ──
print("\n" + "="*80)
print("17. EXTREME REJECTION — wick >3x body → reversal")
print("="*80)
for sn, s_start, s_end in [('TOK',0,6),('LON',8,14.5),('NY',14.5,21.5)]:
    trades = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        sh=int(s_start);sm=int((s_start%1)*60);eh=int(s_end);em=int((s_end%1)*60)
        sess = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,sh,sm,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,eh,em,tz='UTC'))]
        if len(sess) < 6: continue
        for i in range(len(sess)):
            r = sess.iloc[i]; body = abs(r['close']-r['open']); rng = r['high']-r['low']
            if rng < 0.3*atr or body < 0.05*atr: continue
            wick = rng - body
            if wick < 3*body: continue
            lower = min(r['open'],r['close'])-r['low']; upper = r['high']-max(r['open'],r['close'])
            if lower > upper:  # grosse meche basse → bullish
                pi = candles.index.get_loc(sess.index[i])
                b, ex = sim_trail(candles, pi, r['close'], 'long', SL, atr, 24, ACT, TRAIL)
                trades.append({'pnl':(ex-r['close'])-get_sp(day)}); break
            else:  # grosse meche haute → bearish
                pi = candles.index.get_loc(sess.index[i])
                b, ex = sim_trail(candles, pi, r['close'], 'short', SL, atr, 24, ACT, TRAIL)
                trades.append({'pnl':(r['close']-ex)-get_sp(day)}); break
    test_signal(trades, f"Extreme rejection ({sn})")

# ── 18. REVERSAL AFTER 4+ CANDLES — 4 meme sens puis retournement ──
print("\n" + "="*80)
print("18. REVERSAL AFTER STREAK — 4+ bougies meme sens puis opposee")
print("="*80)
for sn, s_start, s_end in [('TOK',0,6),('LON',8,14.5),('NY',14.5,21.5)]:
    trades = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        sh=int(s_start);sm=int((s_start%1)*60);eh=int(s_end);em=int((s_end%1)*60)
        sess = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,sh,sm,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,eh,em,tz='UTC'))]
        if len(sess) < 8: continue
        for i in range(4, len(sess)):
            # 4 bougies meme sens
            bodies = [sess.iloc[i-4+k]['close']-sess.iloc[i-4+k]['open'] for k in range(4)]
            if not all(b > 0 for b in bodies) and not all(b < 0 for b in bodies): continue
            streak_dir = 1 if bodies[0] > 0 else -1
            # Bougie actuelle opposee
            cur_body = sess.iloc[i]['close']-sess.iloc[i]['open']
            if cur_body * streak_dir >= 0: continue
            if abs(cur_body) < 0.2*atr: continue
            d = 'long' if cur_body > 0 else 'short'
            pi = candles.index.get_loc(sess.index[i])
            b, ex = sim_trail(candles, pi, sess.iloc[i]['close'], d, SL, atr, 24, ACT, TRAIL)
            pnl = (ex-sess.iloc[i]['close']) if d=='long' else (sess.iloc[i]['close']-ex)
            trades.append({'pnl':pnl-get_sp(day)}); break
    test_signal(trades, f"Reversal after 4-streak ({sn})")

# ── 19. RANGE CONTRACTION → SESSION BREAK ──
print("\n" + "="*80)
print("19. RANGE CONTRACTION DAILY — jour <50% range veille → break")
print("="*80)
trades = []
for di, day in enumerate(trading_days):
    if di == 0: continue
    pd_ = trading_days[di-1]; atr = daily_atr.get(pd_, global_atr)
    if atr == 0 or pd_ not in daily_data or day not in daily_data: continue
    if daily_data[day]['range'] >= 0.5 * daily_data[pd_]['range']: continue
    # Jour etroit → chercher un break le JOUR SUIVANT
    if di+1 >= len(trading_days): continue
    next_day = trading_days[di+1]
    nd_atr = daily_atr.get(day, global_atr)
    if nd_atr == 0: continue
    day_h = daily_data[day]['high']; day_l = daily_data[day]['low']
    nd_c = candles[(candles['ts_dt']>=pd.Timestamp(next_day.year,next_day.month,next_day.day,8,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(next_day.year,next_day.month,next_day.day,14,30,tz='UTC'))]
    if len(nd_c) < 6: continue
    for i in range(len(nd_c)):
        r = nd_c.iloc[i]
        if r['close'] > day_h:
            pi = candles.index.get_loc(nd_c.index[i])
            b, ex = sim_trail(candles, pi, r['close'], 'long', SL, nd_atr, 24, ACT, TRAIL)
            trades.append({'pnl':(ex-r['close'])-get_sp(next_day)}); break
        if r['close'] < day_l:
            pi = candles.index.get_loc(nd_c.index[i])
            b, ex = sim_trail(candles, pi, r['close'], 'short', SL, nd_atr, 24, ACT, TRAIL)
            trades.append({'pnl':(r['close']-ex)-get_sp(next_day)}); break
test_signal(trades, "Narrow day → next day break London")

# ── 20. MULTI SESSION CONFIRMATION — Tokyo + London 1st hour meme sens → cont ──
print("\n" + "="*80)
print("20. MULTI SESSION CONF — Tokyo dir + KZ dir meme sens → cont apres 10h")
print("="*80)
for thresh in [0.3, 0.5]:
    trades = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        tok = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
        if len(tok) < 10: continue
        kz = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,10,0,tz='UTC'))]
        if len(kz) < 20: continue
        tok_m = (tok.iloc[-1]['close'] - tok.iloc[0]['open']) / atr
        kz_m = (kz.iloc[-1]['close'] - kz.iloc[0]['open']) / atr
        if abs(tok_m) < thresh or abs(kz_m) < thresh: continue
        if tok_m * kz_m <= 0: continue  # pas aligne
        post = candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,10,0,tz='UTC')]
        if len(post) < 6: continue
        pi = candles.index.get_loc(post.index[0]); e = post.iloc[0]['open']
        d = 'long' if tok_m > 0 else 'short'
        b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
        pnl = (ex-e) if d == 'long' else (e-ex)
        trades.append({'pnl':pnl-get_sp(day)})
    test_signal(trades, f"Tokyo+KZ aligned >{thresh}ATR → cont")

conn.close()
print("\n" + "="*80)
print("FIN v10")
print("="*80)
