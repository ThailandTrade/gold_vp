"""
Exploration V5 - SMC, Wyckoff, Fibonacci, Larry Williams, Raschke, NR4,
Supply/Demand, Order Blocks, Renko synthétique, PO3 Asian sweep,
ORB failure, candle patterns avancés.
Tout sur bougies FERMEES, ZERO look-ahead.
"""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
from dotenv import load_dotenv; load_dotenv()
from phase1_poc_calculator import get_conn, compute_atr, get_trading_days
from phase3_analyze import load_candles_5m
from strats import sim_exit_custom

conn = get_conn()
candles = load_candles_5m(conn)
daily_atr, global_atr = compute_atr(conn)
trading_days = get_trading_days(conn)
cur = conn.cursor()
cur.execute("""SELECT DATE_TRUNC('month', time), AVG(ask-bid) FROM market_ticks_xauusd WHERE ask>bid AND ask-bid<10 GROUP BY 1""")
monthly_spread = {r[0].strftime("%Y-%m"): float(r[1]) for r in cur.fetchall()}
cur.close(); conn.close()
avg_sp = np.mean(list(monthly_spread.values()))
def prev_day(day):
    for di, d in enumerate(trading_days):
        if d >= day: return trading_days[di-1] if di > 0 else None
    return None
def get_sp(day):
    return 2 * monthly_spread.get(str(day.year)+"-"+str(day.month).zfill(2), avg_sp)

print("Precalcul...", flush=True)
c = candles.copy()
c['body'] = c['close'] - c['open']
c['abs_body'] = abs(c['body'])
c['range'] = c['high'] - c['low']
c['upper_wick'] = c['high'] - c[['open','close']].max(axis=1)
c['lower_wick'] = c[['open','close']].min(axis=1) - c['low']

# EMAs
for p in [9,20,21,50]:
    c[f'ema{p}'] = c['close'].ewm(span=p, adjust=False).mean()

# ATR + ADX
tr = np.maximum(c['high']-c['low'], np.maximum(abs(c['high']-c['close'].shift(1)), abs(c['low']-c['close'].shift(1))))
c['atr14'] = tr.ewm(span=14, adjust=False).mean()
pdm = c['high'].diff().clip(lower=0); mdm = (-c['low'].diff()).clip(lower=0)
mask = pdm > mdm; pdm2 = pdm.where(mask,0); mdm2 = mdm.where(~mask,0)
atr_p = tr.ewm(span=14, adjust=False).mean()
pdi = 100*pdm2.ewm(span=14, adjust=False).mean()/(atr_p+1e-10)
mdi = 100*mdm2.ewm(span=14, adjust=False).mean()/(atr_p+1e-10)
dx = 100*abs(pdi-mdi)/(pdi+mdi+1e-10)
c['adx14'] = dx.ewm(span=14, adjust=False).mean()

# Pivot points
c['prev_h_d'] = np.nan; c['prev_l_d'] = np.nan; c['prev_c_d'] = np.nan; c['day_open'] = np.nan
dates = c['date'].unique()
for i in range(1, len(dates)):
    prev_dc = c[c['date']==dates[i-1]]
    today_mask = c['date']==dates[i]
    c.loc[today_mask,'prev_h_d'] = prev_dc['high'].max()
    c.loc[today_mask,'prev_l_d'] = prev_dc['low'].min()
    c.loc[today_mask,'prev_c_d'] = prev_dc.iloc[-1]['close']
    today_dc = c[c['date']==dates[i]]
    if len(today_dc)>0:
        c.loc[today_mask,'day_open'] = today_dc.iloc[0]['open']
c['pivot'] = (c['prev_h_d']+c['prev_l_d']+c['prev_c_d'])/3
c['s1'] = 2*c['pivot']-c['prev_h_d']; c['r1'] = 2*c['pivot']-c['prev_l_d']
c['s2'] = c['pivot']-(c['prev_h_d']-c['prev_l_d']); c['r2'] = c['pivot']+(c['prev_h_d']-c['prev_l_d'])
c['prev_day_range'] = c['prev_h_d'] - c['prev_l_d']

# Swing detection (simple: high > 2 neighbors each side)
c['swing_high'] = False; c['swing_low'] = False
for i in range(2, len(c)-2):
    if c.iloc[i]['high'] > max(c.iloc[i-1]['high'],c.iloc[i-2]['high'],c.iloc[i+1]['high'],c.iloc[i+2]['high']):
        c.iloc[i, c.columns.get_loc('swing_high')] = True
    if c.iloc[i]['low'] < min(c.iloc[i-1]['low'],c.iloc[i-2]['low'],c.iloc[i+1]['low'],c.iloc[i+2]['low']):
        c.iloc[i, c.columns.get_loc('swing_low')] = True

print("Collecte...", flush=True)
S = {}
prev_d = None; trig = {}; day_atr = None; prev_day_data = None

for ci in range(100, len(c)-3):
    row = c.iloc[ci]; prev = c.iloc[ci-1]; ct = row['ts_dt']; today = ct.date()
    hour = ct.hour + ct.minute / 60.0
    if today != prev_d:
        if prev_d:
            yc = c[c['date']==prev_d]
            if len(yc) > 0:
                prev_day_data = {'open':float(yc.iloc[0]['open']),'close':float(yc.iloc[-1]['close']),
                                 'high':float(yc['high'].max()),'low':float(yc['low'].min()),
                                 'range':float(yc['high'].max()-yc['low'].min()),
                                 'body':float(yc.iloc[-1]['close']-yc.iloc[0]['open'])}
        prev_d = today; trig = {}
        pd_ = prev_day(today); day_atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    atr = day_atr
    if atr == 0 or atr is None: continue

    def add(sn, d, e):
        b, ex = sim_exit_custom(c, ci, e, d, atr, 'TRAIL', 1.0, 0.5, 0.75, check_entry_candle=False)
        pnl = (ex-e) if d=='long' else (e-ex)
        S.setdefault(sn,[]).append({'date':today,'dir':d,'pnl_oz':pnl-get_sp(today)})

    ds = pd.Timestamp(today.year,today.month,today.day,0,0,tz='UTC')
    te = pd.Timestamp(today.year,today.month,today.day,6,0,tz='UTC')
    ls = pd.Timestamp(today.year,today.month,today.day,8,0,tz='UTC')
    ns = pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC')

    # ═══════════════════════════════════════════
    # RASCHKE HOLY GRAIL (ADX>30 + pullback EMA20)
    # ═══════════════════════════════════════════
    sn = 'ALL_HOLY_GRAIL'
    if sn not in trig and pd.notna(row['adx14']) and pd.notna(row['ema20']):
        if row['adx14'] > 30 and row['ema20'] > row['ema50']:
            if prev['low'] <= prev['ema20'] and row['close'] > row['ema20'] and row['close'] > row['open']:
                add(sn,'long',row['close']); trig[sn]=True
        if row['adx14'] > 30 and row['ema20'] < row['ema50']:
            if prev['high'] >= prev['ema20'] and row['close'] < row['ema20'] and row['close'] < row['open']:
                add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # NR4 BREAKOUT (narrow range 4)
    # ═══════════════════════════════════════════
    if ci >= 5:
        sn = 'ALL_NR4'
        if sn not in trig:
            ranges = [c.iloc[ci-j]['range'] for j in range(4)]
            if row['range'] == min(ranges) and row['range'] > 0:
                # Next candle breaks NR4 high/low — use current candle close direction
                if row['close'] > row['open'] and row['abs_body'] >= 0.1*atr:
                    add(sn,'long',row['close']); trig[sn]=True
                elif row['close'] < row['open'] and row['abs_body'] >= 0.1*atr:
                    add(sn,'short',row['close']); trig[sn]=True

    # NR4 + inside bar
    if ci >= 5:
        sn = 'ALL_NR4_IB'
        if sn not in trig:
            is_ib = row['high'] < prev['high'] and row['low'] > prev['low']
            ranges = [c.iloc[ci-j]['range'] for j in range(4)]
            if is_ib and row['range'] == min(ranges):
                if row['close'] > row['open']:
                    add(sn,'long',row['close']); trig[sn]=True
                elif row['close'] < row['open']:
                    add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # LARRY WILLIAMS VOLATILITY BREAKOUT
    # ═══════════════════════════════════════════
    if pd.notna(row['prev_day_range']) and pd.notna(row['day_open']):
        brk_dist = row['prev_day_range'] * 0.25
        sn = 'ALL_LW_VOLBRK'
        if sn not in trig and brk_dist > 0:
            if row['close'] > row['day_open'] + brk_dist and prev['close'] <= row['day_open'] + brk_dist:
                add(sn,'long',row['close']); trig[sn]=True
            elif row['close'] < row['day_open'] - brk_dist and prev['close'] >= row['day_open'] - brk_dist:
                add(sn,'short',row['close']); trig[sn]=True

        # LW with larger threshold
        brk_dist2 = row['prev_day_range'] * 0.5
        sn = 'ALL_LW_VOLBRK50'
        if sn not in trig and brk_dist2 > 0:
            if row['close'] > row['day_open'] + brk_dist2 and prev['close'] <= row['day_open'] + brk_dist2:
                add(sn,'long',row['close']); trig[sn]=True
            elif row['close'] < row['day_open'] - brk_dist2 and prev['close'] >= row['day_open'] - brk_dist2:
                add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # SUPPLY/DEMAND ZONES (base + impulse)
    # ═══════════════════════════════════════════
    if ci >= 8:
        sn = 'ALL_SD_ZONE'
        if sn not in trig:
            # Look for base (3 small candles) then impulse
            for k in range(3, 8):
                if ci-k-3 < 0: break
                base = c.iloc[ci-k-2:ci-k+1]
                impulse = c.iloc[ci-k+1]
                if len(base) >= 3:
                    all_small = all(abs(base.iloc[j]['body']) < 0.2*atr for j in range(len(base)))
                    if all_small and abs(impulse['body']) >= 1.0*atr:
                        zone_h = base['high'].max(); zone_l = base['low'].min()
                        if impulse['body'] > 0:  # demand zone (bullish impulse)
                            if row['low'] <= zone_h and row['close'] > zone_l and row['close'] > row['open']:
                                add(sn,'long',row['close']); trig[sn]=True; break
                        else:  # supply zone
                            if row['high'] >= zone_l and row['close'] < zone_h and row['close'] < row['open']:
                                add(sn,'short',row['close']); trig[sn]=True; break

    # ═══════════════════════════════════════════
    # ORDER BLOCK RETEST
    # ═══════════════════════════════════════════
    if ci >= 10:
        sn = 'ALL_OB_RETEST'
        if sn not in trig:
            # Find last bearish candle before 3+ bull candles (bullish OB)
            for k in range(3, 10):
                if ci-k < 0: break
                ob_candle = c.iloc[ci-k]
                if ob_candle['close'] < ob_candle['open']:  # bearish candle
                    # Check 3 next candles are bullish
                    next3 = c.iloc[ci-k+1:ci-k+4]
                    if len(next3) >= 3 and all(next3.iloc[j]['close'] > next3.iloc[j]['open'] for j in range(3)):
                        ob_high = max(ob_candle['open'], ob_candle['close'])
                        ob_low = ob_candle['low']
                        if row['low'] <= ob_high and row['close'] > ob_low and row['close'] > row['open']:
                            add(sn,'long',row['close']); trig[sn]=True; break
                elif ob_candle['close'] > ob_candle['open']:  # bullish candle (bearish OB)
                    next3 = c.iloc[ci-k+1:ci-k+4]
                    if len(next3) >= 3 and all(next3.iloc[j]['close'] < next3.iloc[j]['open'] for j in range(3)):
                        ob_low = min(ob_candle['open'], ob_candle['close'])
                        ob_high = ob_candle['high']
                        if row['high'] >= ob_low and row['close'] < ob_high and row['close'] < row['open']:
                            add(sn,'short',row['close']); trig[sn]=True; break

    # ═══════════════════════════════════════════
    # FIBONACCI RETRACEMENT (swing detection)
    # ═══════════════════════════════════════════
    if ci >= 30:
        sn = 'ALL_FIB_618'
        if sn not in trig:
            last30 = c.iloc[ci-30:ci]
            swing_h = last30['high'].max(); swing_l = last30['low'].min()
            swing_rng = swing_h - swing_l
            if swing_rng >= 2.0*atr:
                # Determine trend: if close is closer to high = uptrend, pullback to 61.8%
                fib_618 = swing_h - 0.618 * swing_rng
                fib_786 = swing_h - 0.786 * swing_rng
                if row['close'] > swing_h - 0.3*swing_rng:  # uptrend context
                    if prev['low'] <= fib_618 and row['close'] > fib_618 and row['close'] > row['open']:
                        add(sn,'long',row['close']); trig[sn]=True
                fib_618_s = swing_l + 0.618 * swing_rng
                if row['close'] < swing_l + 0.3*swing_rng:  # downtrend context
                    if prev['high'] >= fib_618_s and row['close'] < fib_618_s and row['close'] < row['open']:
                        add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # RENKO SYNTHETIQUE
    # ═══════════════════════════════════════════
    if 'renko_level' not in trig and atr > 0:
        trig['renko_level'] = row['close']
        trig['renko_dir'] = 0  # 0=neutral, 1=bull, -1=bear
        trig['renko_count'] = 0
    if 'renko_level' in trig:
        brick = atr * 0.5  # half ATR bricks
        level = trig['renko_level']
        if row['close'] > level + brick:
            if trig['renko_dir'] == -1:  # was bearish, now bullish = flip
                sn = 'ALL_RENKO_FLIP'
                if sn not in trig and trig['renko_count'] >= 2:
                    add(sn,'long',row['close']); trig[sn]=True
            trig['renko_level'] = level + brick
            if trig['renko_dir'] == 1: trig['renko_count'] += 1
            else: trig['renko_count'] = 1
            trig['renko_dir'] = 1
        elif row['close'] < level - brick:
            if trig['renko_dir'] == 1:
                sn = 'ALL_RENKO_FLIP'
                if sn not in trig and trig['renko_count'] >= 2:
                    add(sn,'short',row['close']); trig[sn]=True
            trig['renko_level'] = level - brick
            if trig['renko_dir'] == -1: trig['renko_count'] += 1
            else: trig['renko_count'] = 1
            trig['renko_dir'] = -1

    # ═══════════════════════════════════════════
    # PO3 ASIAN SWEEP REVERSAL at London
    # ═══════════════════════════════════════════
    if 7.0<=hour<9.0 and 'PO3_SWEEP' not in trig:
        asian = c[(c['ts_dt']>=ds)&(c['ts_dt']<te)]
        if len(asian) >= 50:
            asian_h = asian['high'].max(); asian_l = asian['low'].min()
            # Sweep below asian low then close above
            if row['low'] < asian_l and row['close'] > asian_l and row['close'] > row['open']:
                add('PO3_SWEEP','long',row['close']); trig['PO3_SWEEP']=True
            elif row['high'] > asian_h and row['close'] < asian_h and row['close'] < row['open']:
                add('PO3_SWEEP','short',row['close']); trig['PO3_SWEEP']=True

    # ═══════════════════════════════════════════
    # ORB FAILURE (fade)
    # ═══════════════════════════════════════════
    # London ORB failure
    if 8.5<=hour<14.5 and 'LON_ORB_FAIL' not in trig:
        if 'LON_ORB_d' not in trig:
            orb = c[(c['ts_dt']>=ls)&(c['ts_dt']<ls+pd.Timedelta(minutes=30))]
            if len(orb) >= 6:
                trig['LON_ORB_d']=True; trig['LON_ORB_h']=float(orb['high'].max()); trig['LON_ORB_l']=float(orb['low'].min())
        if 'LON_ORB_h' in trig:
            # Failed breakout above
            if prev['close'] > trig['LON_ORB_h'] and row['close'] < trig['LON_ORB_h'] and row['abs_body'] >= 0.2*atr:
                add('LON_ORB_FAIL','short',row['close']); trig['LON_ORB_FAIL']=True
            elif prev['close'] < trig['LON_ORB_l'] and row['close'] > trig['LON_ORB_l'] and row['abs_body'] >= 0.2*atr:
                add('LON_ORB_FAIL','long',row['close']); trig['LON_ORB_FAIL']=True

    # NY ORB failure
    if 14.75<=hour<21.0 and 'NY_ORB_FAIL' not in trig:
        if 'NY_ORB_d' not in trig:
            orb = c[(c['ts_dt']>=ns)&(c['ts_dt']<ns+pd.Timedelta(minutes=15))]
            if len(orb) >= 3:
                trig['NY_ORB_d']=True; trig['NY_ORB_h']=float(orb['high'].max()); trig['NY_ORB_l']=float(orb['low'].min())
        if 'NY_ORB_h' in trig:
            if prev['close'] > trig['NY_ORB_h'] and row['close'] < trig['NY_ORB_h'] and row['abs_body'] >= 0.2*atr:
                add('NY_ORB_FAIL','short',row['close']); trig['NY_ORB_FAIL']=True
            elif prev['close'] < trig['NY_ORB_l'] and row['close'] > trig['NY_ORB_l'] and row['abs_body'] >= 0.2*atr:
                add('NY_ORB_FAIL','long',row['close']); trig['NY_ORB_FAIL']=True

    # ═══════════════════════════════════════════
    # EQUAL HIGHS/LOWS SWEEP (liquidity)
    # ═══════════════════════════════════════════
    if ci >= 30:
        sn = 'ALL_EQ_SWEEP'
        if sn not in trig:
            # Find equal lows (2+ lows within 0.1 ATR of each other)
            last30_lows = [(c.iloc[j]['low'], j) for j in range(ci-30, ci) if c.iloc[j]['swing_low']]
            for i1 in range(len(last30_lows)):
                for i2 in range(i1+1, len(last30_lows)):
                    if abs(last30_lows[i1][0] - last30_lows[i2][0]) < 0.1*atr:
                        eq_level = min(last30_lows[i1][0], last30_lows[i2][0])
                        if row['low'] < eq_level and row['close'] > eq_level and row['close'] > row['open']:
                            add(sn,'long',row['close']); trig[sn]=True; break
                if sn in trig: break
            if sn not in trig:
                last30_highs = [(c.iloc[j]['high'], j) for j in range(ci-30, ci) if c.iloc[j]['swing_high']]
                for i1 in range(len(last30_highs)):
                    for i2 in range(i1+1, len(last30_highs)):
                        if abs(last30_highs[i1][0] - last30_highs[i2][0]) < 0.1*atr:
                            eq_level = max(last30_highs[i1][0], last30_highs[i2][0])
                            if row['high'] > eq_level and row['close'] < eq_level and row['close'] < row['open']:
                                add(sn,'short',row['close']); trig[sn]=True; break
                    if sn in trig: break

    # ═══════════════════════════════════════════
    # CONSECUTIVE EXHAUSTION REVERSAL (with range filter)
    # ═══════════════════════════════════════════
    if ci >= 6:
        sn = 'ALL_CONSEC_REV'
        if sn not in trig:
            # 5+ same dir, then reversal candle
            last5 = c.iloc[ci-5:ci]
            all_bull = all(last5.iloc[j]['close'] > last5.iloc[j]['open'] for j in range(5))
            all_bear = all(last5.iloc[j]['close'] < last5.iloc[j]['open'] for j in range(5))
            total_rng = c.iloc[ci-5:ci]['high'].max() - c.iloc[ci-5:ci]['low'].min()
            if all_bull and total_rng >= 1.5*atr and row['close'] < row['open'] and row['abs_body'] >= 0.3*atr:
                add(sn,'short',row['close']); trig[sn]=True
            elif all_bear and total_rng >= 1.5*atr and row['close'] > row['open'] and row['abs_body'] >= 0.3*atr:
                add(sn,'long',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # THREE BAR PLAY
    # ═══════════════════════════════════════════
    if ci >= 3:
        sn = 'ALL_3BAR_PLAY'
        if sn not in trig:
            b1 = c.iloc[ci-2]; b2 = c.iloc[ci-1]
            # Bull: big bull bar, small inside bar, then bull continuation
            if b1['body'] > 0.5*atr and b2['range'] < b1['range']*0.5 and b2['high']<=b1['high'] and b2['low']>=b1['low']:
                if row['close'] > b1['high'] and row['close'] > row['open']:
                    add(sn,'long',row['close']); trig[sn]=True
            if b1['body'] < -0.5*atr and b2['range'] < abs(b1['range'])*0.5 and b2['high']<=b1['high'] and b2['low']>=b1['low']:
                if row['close'] < b1['low'] and row['close'] < row['open']:
                    add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # PIVOT S2/R2 EXTREME BOUNCE
    # ═══════════════════════════════════════════
    if pd.notna(row.get('s2')) and pd.notna(row.get('r2')):
        sn = 'ALL_S2R2_BOUNCE'
        if sn not in trig:
            if row['low'] <= row['s2']*1.002 and row['close'] > row['s2'] and row['close'] > row['open']:
                add(sn,'long',row['close']); trig[sn]=True
            elif row['high'] >= row['r2']*0.998 and row['close'] < row['r2'] and row['close'] < row['open']:
                add(sn,'short',row['close']); trig[sn]=True

    # ═══════════════════════════════════════════
    # SESSION-SPECIFIC
    # ═══════════════════════════════════════════
    # Holy Grail at London
    sn = 'LON_HOLY_GRAIL'
    if 8.0<=hour<14.5 and sn not in trig and pd.notna(row['adx14']) and pd.notna(row['ema20']):
        if row['adx14']>30 and row['ema20']>row['ema50']:
            if prev['low']<=prev['ema20'] and row['close']>row['ema20'] and row['close']>row['open']:
                add(sn,'long',row['close']); trig[sn]=True
        if row['adx14']>30 and row['ema20']<row['ema50']:
            if prev['high']>=prev['ema20'] and row['close']<row['ema20'] and row['close']<row['open']:
                add(sn,'short',row['close']); trig[sn]=True

    # LW vol breakout at London
    if 8.0<=hour<14.5 and pd.notna(row.get('prev_day_range')) and pd.notna(row.get('day_open')):
        brk = row['prev_day_range'] * 0.25
        sn = 'LON_LW_VOLBRK'
        if sn not in trig and brk > 0:
            if row['close'] > row['day_open']+brk and prev['close'] <= row['day_open']+brk:
                add(sn,'long',row['close']); trig[sn]=True
            elif row['close'] < row['day_open']-brk and prev['close'] >= row['day_open']-brk:
                add(sn,'short',row['close']); trig[sn]=True

    # NR4 at Tokyo
    if 0.0<=hour<6.0 and ci>=5:
        sn = 'TOK_NR4'
        if sn not in trig:
            ranges = [c.iloc[ci-j]['range'] for j in range(4)]
            if row['range'] == min(ranges) and row['range'] > 0 and row['abs_body'] >= 0.1*atr:
                add(sn,'long' if row['body']>0 else 'short',row['close']); trig[sn]=True

    # Fibonacci at NY
    if 14.5<=hour<21.0 and ci>=30:
        sn = 'NY_FIB_618'
        if sn not in trig:
            last30 = c.iloc[ci-30:ci]
            sh = last30['high'].max(); sl_ = last30['low'].min(); sr = sh - sl_
            if sr >= 2.0*atr:
                f618 = sh - 0.618*sr
                if row['close'] > sh - 0.3*sr:
                    if prev['low'] <= f618 and row['close'] > f618 and row['close'] > row['open']:
                        add(sn,'long',row['close']); trig[sn]=True
                f618s = sl_ + 0.618*sr
                if row['close'] < sl_ + 0.3*sr:
                    if prev['high'] >= f618s and row['close'] < f618s and row['close'] < row['open']:
                        add(sn,'short',row['close']); trig[sn]=True

print(f"Done. {len(S)} strats.", flush=True)

# ── RESULTATS ──
print("\n" + "="*130)
print("EXPLORATION V5 - SMC, Wyckoff, Fibonacci, Larry Williams, Raschke, NR4, Supply/Demand")
print("="*130)
print(f"{'Strat':>18s} {'n':>5s} {'WR':>5s} {'PF':>6s} {'Avg':>8s} {'Total':>8s} {'[1st|2nd]':>18s} {'Split':>6s} {'Tiers':>5s}")
print("-"*130)

good = []
for sn in sorted(S.keys()):
    t = S[sn]
    if len(t) < 15: continue
    pnls = [x['pnl_oz'] for x in t]
    n = len(pnls)
    gp = sum(p for p in pnls if p>0); gl = abs(sum(p for p in pnls if p<0))+0.001
    wr = sum(1 for p in pnls if p>0)/n*100
    pf = gp/gl
    mid = n//2; f1 = np.mean(pnls[:mid]); f2 = np.mean(pnls[mid:])
    t1 = sum(pnls[:n//3]); t2 = sum(pnls[n//3:2*n//3]); t3 = sum(pnls[2*n//3:])
    tiers = sum(1 for x in [t1,t2,t3] if x>0)
    split = f1>0 and f2>0
    split_str = "OK" if split else "!!"
    marker = " <--" if pf > 1.2 and split else ""
    print(f"{sn:>18s} {n:5d} {wr:4.0f}% {pf:6.2f} {np.mean(pnls):+8.3f} {sum(pnls):+8.1f} [{f1:+7.3f}|{f2:+7.3f}] {split_str:>6s} {tiers:4d}/3{marker}")
    if pf > 1.2 and split:
        good.append(sn)

print(f"\n  Retenues (PF>1.2 + split OK): {', '.join(good) if good else 'aucune'}")
print()
