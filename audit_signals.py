"""Audit: compare signals from detect_all vs find_combo_greedy inline code."""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
from dotenv import load_dotenv; load_dotenv()
from phase1_poc_calculator import get_conn, compute_atr, get_trading_days
from phase3_analyze import load_candles_5m
from strats import compute_indicators, detect_all

conn = get_conn()
candles = load_candles_5m(conn)
daily_atr, global_atr = compute_atr(conn)
trading_days = get_trading_days(conn)
conn.close()

def prev_day(day):
    for di, d in enumerate(trading_days):
        if d >= day: return trading_days[di-1] if di > 0 else None
    return None

# === METHOD 1: via detect_all (strats.py) ===
c1 = candles.copy()
c1 = compute_indicators(c1)
S1 = {}
prev_d = None; trig = {}; day_atr = None; prev_day_data = None; prev2_day_data = None
for ci in range(200, len(c1)):
    row = c1.iloc[ci]; ct = row['ts_dt']; today = ct.date()
    hour = ct.hour + ct.minute / 60.0
    if today != prev_d:
        if prev_d:
            yc = c1[c1['date']==prev_d]
            if len(yc) > 0:
                prev2_day_data = prev_day_data
                prev_day_data = {'open':float(yc.iloc[0]['open']),'close':float(yc.iloc[-1]['close']),
                                 'high':float(yc['high'].max()),'low':float(yc['low'].min()),
                                 'range':float(yc['high'].max()-yc['low'].min()),
                                 'body':float(yc.iloc[-1]['close']-yc.iloc[0]['open'])}
        prev_d = today; trig = {}
        pd_ = prev_day(today); day_atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    atr = day_atr
    if atr == 0 or atr is None: continue
    ds = pd.Timestamp(today.year,today.month,today.day,0,0,tz='UTC')
    te = pd.Timestamp(today.year,today.month,today.day,6,0,tz='UTC')
    ls = pd.Timestamp(today.year,today.month,today.day,8,0,tz='UTC')
    ns = pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC')
    tv = c1[(c1['ts_dt']>=ds)&(c1['ts_dt']<=ct)]
    tok = tv[tv['ts_dt']<te]; lon = tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<ns)]
    def add1(sn, d, e):
        S1.setdefault(sn,[]).append({'ci':ci,'dir':d,'entry':e,'date':today})
    detect_all(c1, ci, row, ct, today, hour, atr, trig, tv, tok, lon, prev_day_data, add1, prev2_day_data)

# === METHOD 2: inline from find_combo_greedy.py (indicator strats only) ===
c2 = candles.copy()
c2['body'] = c2['close'] - c2['open']; c2['abs_body'] = abs(c2['body']); c2['range'] = c2['high'] - c2['low']
c2['mid'] = (c2['high']+c2['low'])/2
ef = c2['close'].ewm(span=8, adjust=False).mean(); es = c2['close'].ewm(span=17, adjust=False).mean()
c2['macd_med'] = ef - es; c2['macd_med_sig'] = c2['macd_med'].ewm(span=9, adjust=False).mean()
delta = c2['close'].diff(); gain = delta.clip(lower=0); loss = (-delta).clip(lower=0)
ag = gain.ewm(alpha=1.0/14, min_periods=14, adjust=False).mean()
al = loss.ewm(alpha=1.0/14, min_periods=14, adjust=False).mean()
c2['rsi14'] = 100 - 100/(1+ag/(al+1e-10))
c2['ema20'] = c2['close'].ewm(span=20, adjust=False).mean()
tr = np.maximum(c2['high']-c2['low'], np.maximum(abs(c2['high']-c2['close'].shift(1)), abs(c2['low']-c2['close'].shift(1))))
c2['atr14'] = tr.ewm(span=14, adjust=False).mean()
up2 = c2['mid'] - 2.0*c2['atr14']; dn2 = c2['mid'] + 2.0*c2['atr14']
st_dir = np.zeros(len(c2)); st_val = np.zeros(len(c2))
for i in range(1, len(c2)):
    if c2.iloc[i]['close'] > dn2.iloc[i-1]: st_dir[i]=1; st_val[i]=up2.iloc[i]
    elif c2.iloc[i]['close'] < up2.iloc[i-1]: st_dir[i]=-1; st_val[i]=dn2.iloc[i]
    else:
        st_dir[i]=st_dir[i-1]
        st_val[i]=max(up2.iloc[i],st_val[i-1]) if st_dir[i]==1 else min(dn2.iloc[i],st_val[i-1])
c2['psar_dir'] = st_dir

S2 = {}
prev_d2 = None; trig2 = {}; day_atr2 = None
for ci in range(200, len(c2)):
    row = c2.iloc[ci]; prev = c2.iloc[ci-1]; ct = row['ts_dt']; today = ct.date()
    hour = ct.hour + ct.minute / 60.0
    if today != prev_d2:
        prev_d2 = today; trig2 = {}
        pd_ = prev_day(today); day_atr2 = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    atr = day_atr2
    if atr == 0 or atr is None: continue
    ds = pd.Timestamp(today.year,today.month,today.day,0,0,tz='UTC')
    te = pd.Timestamp(today.year,today.month,today.day,6,0,tz='UTC')

    def add2(sn, d, e):
        S2.setdefault(sn,[]).append({'ci':ci,'dir':d,'entry':e,'date':today})

    # ALL_MACD_RSI (find_combo_greedy.py line 203-206)
    sn = 'ALL_MACD_RSI'
    if sn not in trig2 and pd.notna(row['macd_med']) and pd.notna(row['rsi14']):
        if prev['macd_med']<prev['macd_med_sig'] and row['macd_med']>row['macd_med_sig'] and row['rsi14']>50: add2(sn,'long',row['close']); trig2[sn]=True
        elif prev['macd_med']>prev['macd_med_sig'] and row['macd_med']<row['macd_med_sig'] and row['rsi14']<50: add2(sn,'short',row['close']); trig2[sn]=True

    # ALL_FVG_BULL (line 264-266)
    if ci>=3:
        sn = 'ALL_FVG_BULL'
        if sn not in trig2:
            if c2.iloc[ci-3]['high']<row['low'] and row['close']>row['open'] and row['abs_body']>=0.3*atr: add2(sn,'long',row['close']); trig2[sn]=True

    # ALL_CONSEC_REV (line 281-289)
    if ci>=6:
        sn = 'ALL_CONSEC_REV'
        if sn not in trig2:
            l5 = c2.iloc[ci-5:ci]
            ab = all(l5.iloc[j]['close']>l5.iloc[j]['open'] for j in range(5))
            ae = all(l5.iloc[j]['close']<l5.iloc[j]['open'] for j in range(5))
            tr_ = l5['high'].max()-l5['low'].min()
            if ab and tr_>=1.5*atr and row['close']<row['open'] and row['abs_body']>=0.3*atr: add2(sn,'short',row['close']); trig2[sn]=True
            elif ae and tr_>=1.5*atr and row['close']>row['open'] and row['abs_body']>=0.3*atr: add2(sn,'long',row['close']); trig2[sn]=True

    # ALL_FIB_618 (line 274-280)
    if ci>=30:
        sn = 'ALL_FIB_618'
        if sn not in trig2:
            l30 = c2.iloc[ci-30:ci]; sh = l30['high'].max(); sl_ = l30['low'].min(); sr = sh-sl_
            if sr>=2.0*atr:
                f618 = sh-0.618*sr
                if row['close']>sh-0.3*sr and prev['low']<=f618 and row['close']>f618 and row['close']>row['open']: add2(sn,'long',row['close']); trig2[sn]=True

    # ALL_3SOLDIERS (line 315-326)
    if ci>=3:
        sn = 'ALL_3SOLDIERS'
        if sn not in trig2:
            b1=c2.iloc[ci-2];b2=c2.iloc[ci-1];b3=row
            if (b1['close']>b1['open'] and b2['close']>b2['open'] and b3['close']>b3['open'] and
                b2['close']>b1['close'] and b3['close']>b2['close'] and
                min(abs(b1['body']),abs(b2['body']),abs(b3['body']))>=0.3*atr):
                add2(sn,'long',row['close']); trig2[sn]=True
            if (b1['close']<b1['open'] and b2['close']<b2['open'] and b3['close']<b3['open'] and
                b2['close']<b1['close'] and b3['close']<b2['close'] and
                min(abs(b1['body']),abs(b2['body']),abs(b3['body']))>=0.3*atr):
                add2(sn,'short',row['close']); trig2[sn]=True

    # ALL_PSAR_EMA (line 311-314)
    sn = 'ALL_PSAR_EMA'
    if sn not in trig2 and pd.notna(row['ema20']):
        if prev['psar_dir']==-1 and row['psar_dir']==1 and row['close']>row['ema20']: add2(sn,'long',row['close']); trig2[sn]=True
        elif prev['psar_dir']==1 and row['psar_dir']==-1 and row['close']<row['ema20']: add2(sn,'short',row['close']); trig2[sn]=True

    # PO3_SWEEP (line 328-333)
    if 7.0<=hour<9.0 and 'PO3_SWEEP' not in trig2:
        asian = c2[(c2['ts_dt']>=ds)&(c2['ts_dt']<te)]
        if len(asian)>=50:
            ah=asian['high'].max(); al_=asian['low'].min()
            if row['low']<al_ and row['close']>al_ and row['close']>row['open']: add2('PO3_SWEEP','long',row['close']); trig2['PO3_SWEEP']=True
            elif row['high']>ah and row['close']<ah and row['close']<row['open']: add2('PO3_SWEEP','short',row['close']); trig2['PO3_SWEEP']=True

# === COMPARE ===
target_strats = ['ALL_MACD_RSI','ALL_FVG_BULL','ALL_CONSEC_REV','ALL_FIB_618','ALL_3SOLDIERS','ALL_PSAR_EMA','PO3_SWEEP']
print(f"{'Strat':>22s} {'detect_all':>10s} {'greedy':>10s} {'Match':>10s}")
print('-'*60)
all_ok = True
for sn in target_strats:
    n1 = len(S1.get(sn,[])); n2 = len(S2.get(sn,[]))
    ok = n1 == n2
    # Also check each signal matches
    if ok and n1 > 0:
        for i in range(n1):
            t1 = S1[sn][i]; t2 = S2[sn][i]
            if t1['ci'] != t2['ci'] or t1['dir'] != t2['dir']:
                ok = False
                break
    if not ok: all_ok = False
    print(f"{sn:>22s} {n1:10d} {n2:10d} {'OK' if ok else 'MISMATCH':>10s}")
    if not ok and n1 > 0 and n2 > 0:
        # Find first diff
        i1 = 0; i2 = 0
        while i1 < n1 and i2 < n2:
            t1 = S1[sn][i1]; t2 = S2[sn][i2]
            if t1['ci'] == t2['ci'] and t1['dir'] == t2['dir']:
                i1 += 1; i2 += 1
            else:
                print(f"  First diff: detect_all[{i1}] ci={t1['ci']} {t1['dir']} date={t1['date']} vs greedy[{i2}] ci={t2['ci']} {t2['dir']} date={t2['date']}")
                break
        if n1 > n2:
            extra = S1[sn][n2]
            print(f"  Extra in detect_all: ci={extra['ci']} {extra['dir']} date={extra['date']}")
        elif n2 > n1:
            extra = S2[sn][n1]
            print(f"  Extra in greedy: ci={extra['ci']} {extra['dir']} date={extra['date']}")

print(f"\n{'ALL MATCH - detect_all is identical to greedy' if all_ok else 'MISMATCHES FOUND - FIX NEEDED'}")
