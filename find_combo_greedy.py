"""
Trouve le meilleur combo par approche greedy.
Commence par la meilleure strat, ajoute une a une.
Beaucoup plus rapide que brute force.
"""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
from dotenv import load_dotenv; load_dotenv()
from phase1_poc_calculator import get_conn, compute_atr, get_trading_days
from phase3_analyze import load_candles_5m
from strats import sim_exit_custom, detect_all
from strat_exits import STRAT_EXITS, DEFAULT_EXIT

conn = get_conn()
candles = load_candles_5m(conn)
daily_atr, global_atr = compute_atr(conn)
trading_days = get_trading_days(conn)
cur = conn.cursor()
cur.execute("""SELECT DATE_TRUNC('month', time), AVG(ask-bid) FROM market_ticks_xauusd WHERE ask>bid AND ask-bid<10 GROUP BY 1""")
monthly_spread = {r[0].strftime("%Y-%m"): float(r[1]) for r in cur.fetchall()}
cur.close(); conn.close()
avg_sp = np.mean(list(monthly_spread.values()))
n_td = len(set(candles['date'].unique()))
def prev_day(day):
    for di, d in enumerate(trading_days):
        if d >= day: return trading_days[di-1] if di > 0 else None
    return None
def get_sp(day):
    return 2 * monthly_spread.get(str(day.year)+"-"+str(day.month).zfill(2), avg_sp)

OPEN_STRATS = {'TOK_FADE','TOK_PREVEXT','LON_GAP','LON_BIGGAP','LON_KZ','LON_TOKEND','LON_PREV','NY_GAP','NY_LONEND','NY_LONMOM','NY_DAYMOM'}

# Precalcul + collecte (meme que find_best_combo mais avec V5-V7)
print("Precalcul...", flush=True)
c = candles.copy()
c['body'] = c['close'] - c['open']; c['abs_body'] = abs(c['body']); c['range'] = c['high'] - c['low']
c['mid'] = (c['high']+c['low'])/2
c['upper_wick'] = c['high'] - c[['open','close']].max(axis=1)
c['lower_wick'] = c[['open','close']].min(axis=1) - c['low']
for p in [5,8,9,13,20,21,50,100,200]:
    c[f'ema{p}'] = c['close'].ewm(span=p, adjust=False).mean()
for p in [7,9,14]:
    delta = c['close'].diff(); gain = delta.clip(lower=0); loss = (-delta).clip(lower=0)
    ag = gain.ewm(alpha=1.0/p, min_periods=p, adjust=False).mean()
    al = loss.ewm(alpha=1.0/p, min_periods=p, adjust=False).mean()
    c[f'rsi{p}'] = 100 - 100/(1+ag/(al+1e-10))
for fast,slow,sig,name in [(12,26,9,'std'),(5,13,1,'fast'),(8,17,9,'med')]:
    ef = c['close'].ewm(span=fast, adjust=False).mean(); es = c['close'].ewm(span=slow, adjust=False).mean()
    c[f'macd_{name}'] = ef - es; c[f'macd_{name}_sig'] = c[f'macd_{name}'].ewm(span=max(sig,2), adjust=False).mean()
tr = np.maximum(c['high']-c['low'], np.maximum(abs(c['high']-c['close'].shift(1)), abs(c['low']-c['close'].shift(1))))
c['atr14'] = tr.ewm(span=14, adjust=False).mean()
for p,nm in [(14,'s'),(7,'f')]:
    pdm = c['high'].diff().clip(lower=0); mdm = (-c['low'].diff()).clip(lower=0)
    mask = pdm > mdm; pdm2 = pdm.where(mask,0); mdm2 = mdm.where(~mask,0)
    atr_p = tr.ewm(span=p, adjust=False).mean()
    c[f'pdi_{nm}'] = 100*pdm2.ewm(span=p, adjust=False).mean()/(atr_p+1e-10)
    c[f'mdi_{nm}'] = 100*mdm2.ewm(span=p, adjust=False).mean()/(atr_p+1e-10)
    dx = 100*abs(c[f'pdi_{nm}']-c[f'mdi_{nm}'])/(c[f'pdi_{nm}']+c[f'mdi_{nm}']+1e-10)
    c[f'adx_{nm}'] = dx.ewm(span=p, adjust=False).mean()
for p in [10,20,50]:
    c[f'dc{p}_h'] = c['high'].rolling(p).max(); c[f'dc{p}_l'] = c['low'].rolling(p).min()
c['kc_up'] = c['ema20']+1.5*tr.ewm(span=14,adjust=False).mean()
c['kc_lo'] = c['ema20']-1.5*tr.ewm(span=14,adjust=False).mean()
def wma(s,n):
    w = np.arange(1,n+1); return s.rolling(n).apply(lambda x: np.dot(x,w)/w.sum(), raw=True)
c['hma9'] = wma(2*wma(c['close'],4)-wma(c['close'],9),3)
c['hma21'] = wma(2*wma(c['close'],10)-wma(c['close'],21),4)
for p in [7,14]:
    hh = c['high'].rolling(p).max(); ll = c['low'].rolling(p).min()
    c[f'wr{p}'] = -100*(hh-c['close'])/(hh-ll+1e-10)
for p in [14,20]:
    tp = (c['high']+c['low']+c['close'])/3; sm = tp.rolling(p).mean()
    mad = tp.rolling(p).apply(lambda x: np.mean(np.abs(x-np.mean(x))), raw=True)
    c[f'cci{p}'] = (tp-sm)/(0.015*mad+1e-10)
for p in [5,10,14]:
    c[f'mom{p}'] = c['close']/c['close'].shift(p)*100 - 100
c['i_t'] = (c['high'].rolling(6).max()+c['low'].rolling(6).min())/2
c['i_k'] = (c['high'].rolling(13).max()+c['low'].rolling(13).min())/2
c['i_sa'] = ((c['i_t']+c['i_k'])/2).shift(13)
c['i_sb'] = ((c['high'].rolling(26).max()+c['low'].rolling(26).min())/2).shift(13)
c['bb_t_mid'] = c['close'].rolling(10).mean(); c['bb_t_std'] = c['close'].rolling(10).std()
c['bb_t_up'] = c['bb_t_mid']+1.5*c['bb_t_std']; c['bb_t_lo'] = c['bb_t_mid']-1.5*c['bb_t_std']
# V5-V7 indicators
c['sma20'] = c['close'].rolling(20).mean()
# Pivot points
dates = c['date'].unique()
c['prev_h_d'] = np.nan; c['prev_l_d'] = np.nan; c['prev_c_d'] = np.nan
for i in range(1, len(dates)):
    prev_dc = c[c['date']==dates[i-1]]
    today_mask = c['date']==dates[i]
    c.loc[today_mask,'prev_h_d'] = prev_dc['high'].max()
    c.loc[today_mask,'prev_l_d'] = prev_dc['low'].min()
    c.loc[today_mask,'prev_c_d'] = prev_dc.iloc[-1]['close']
c['pivot'] = (c['prev_h_d']+c['prev_l_d']+c['prev_c_d'])/3
# Fisher, CMO
for p in [9]:
    hh = c['high'].rolling(p).max(); ll = c['low'].rolling(p).min()
    val = 2*((c['close']-ll)/(hh-ll+1e-10)-0.5); val = val.clip(-0.999,0.999)
    c[f'fisher{p}'] = (0.5*np.log((1+val)/(1-val+1e-10))).ewm(span=3,adjust=False).mean()
    c[f'fisher{p}_sig'] = c[f'fisher{p}'].shift(1)
for p in [9,14]:
    delta = c['close'].diff()
    su = delta.clip(lower=0).rolling(p).sum(); sd = (-delta.clip(upper=0)).rolling(p).sum()
    c[f'cmo{p}'] = 100*(su-sd)/(su+sd+1e-10)
c['dpo14'] = c['close'] - c['close'].rolling(14).mean().shift(8)
# AO
c['ao'] = c['mid'].rolling(5).mean() - c['mid'].rolling(34).mean()
# 1h proxy
c['high_1h'] = c['high'].rolling(12).max(); c['low_1h'] = c['low'].rolling(12).min()
# PSAR (simplified: use supertrend as proxy)
up2 = c['mid'] - 2.0*c['atr14']; dn2 = c['mid'] + 2.0*c['atr14']
st_dir = np.zeros(len(c)); st_val = np.zeros(len(c))
for i in range(1, len(c)):
    if c.iloc[i]['close'] > dn2.iloc[i-1]: st_dir[i]=1; st_val[i]=up2.iloc[i]
    elif c.iloc[i]['close'] < up2.iloc[i-1]: st_dir[i]=-1; st_val[i]=dn2.iloc[i]
    else:
        st_dir[i]=st_dir[i-1]
        st_val[i]=max(up2.iloc[i],st_val[i-1]) if st_dir[i]==1 else min(dn2.iloc[i],st_val[i-1])
c['psar_dir'] = st_dir

print("Collecte...", flush=True)
S = {}
prev_d = None; trig = {}; day_atr = None; prev_day_data = None; prev2_day_data = None
for ci in range(200, len(c)):
    row = c.iloc[ci]; prev = c.iloc[ci-1]; ct = row['ts_dt']; today = ct.date()
    hour = ct.hour + ct.minute / 60.0
    if today != prev_d:
        if prev_d:
            yc = c[c['date']==prev_d]
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
    tv = c[(c['ts_dt']>=ds)&(c['ts_dt']<=ct)]
    tok = tv[tv['ts_dt']<te]; lon = tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<ns)]

    def add(sn, d, e):
        is_open = sn in OPEN_STRATS
        exit_cfg = STRAT_EXITS.get(sn, DEFAULT_EXIT)
        etype, p1, p2, p3 = exit_cfg
        b, ex = sim_exit_custom(c, ci, e, d, atr, etype, p1, p2, p3, check_entry_candle=is_open)
        pnl = (ex-e) if d=='long' else (e-ex)
        S.setdefault(sn,[]).append({'date':today,'dir':d,'sl_atr':p1,'pnl_oz':pnl-get_sp(today),'atr':atr,'ei':ci,'xi':ci+b})

    # Price action
    detect_all(c, ci, row, ct, today, hour, atr, trig, tv, tok, lon, prev_day_data, add, prev2_day_data)

    # ALL indicators (from V1-V7) — only PF>1.3 strats
    # MACD crosses
    for nm in ['std','fast','med']:
        mc,ms = f'macd_{nm}',f'macd_{nm}_sig'
        sn = f'ALL_MACD_{nm.upper()}_SIG'
        if sn not in trig and pd.notna(row[mc]):
            if prev[mc]<prev[ms] and row[mc]>row[ms]: add(sn,'long',row['close']); trig[sn]=True
            elif prev[mc]>prev[ms] and row[mc]<row[ms]: add(sn,'short',row['close']); trig[sn]=True
    # RSI 50
    sn = 'ALL_RSI_50'
    if sn not in trig and pd.notna(row['rsi14']):
        if prev['rsi14']<50 and row['rsi14']>=50: add(sn,'long',row['close']); trig[sn]=True
        elif prev['rsi14']>50 and row['rsi14']<=50: add(sn,'short',row['close']); trig[sn]=True
    # Donchian
    for p in [10,50]:
        sn = f'ALL_DC{p}'
        if sn not in trig and pd.notna(prev.get(f'dc{p}_h')):
            if row['close']>prev[f'dc{p}_h']: add(sn,'long',row['close']); trig[sn]=True
            elif row['close']<prev[f'dc{p}_l']: add(sn,'short',row['close']); trig[sn]=True
    # KC
    sn = 'ALL_KC_BRK'
    if sn not in trig and pd.notna(row['kc_up']):
        if row['close']>row['kc_up'] and prev['close']<=prev['kc_up']: add(sn,'long',row['close']); trig[sn]=True
        elif row['close']<row['kc_lo'] and prev['close']>=prev['kc_lo']: add(sn,'short',row['close']); trig[sn]=True
    # MACD+ADX, ADX_FAST
    sn = 'ALL_MACD_ADX'
    if sn not in trig and pd.notna(row['macd_std']) and pd.notna(row['adx_s']):
        if row['adx_s']>25 and prev['macd_std']<prev['macd_std_sig'] and row['macd_std']>row['macd_std_sig']: add(sn,'long',row['close']); trig[sn]=True
        elif row['adx_s']>25 and prev['macd_std']>prev['macd_std_sig'] and row['macd_std']<row['macd_std_sig']: add(sn,'short',row['close']); trig[sn]=True
    sn = 'ALL_ADX_FAST'
    if sn not in trig and pd.notna(row['adx_f']) and pd.notna(row['ema21']):
        if row['adx_f']>25 and row['pdi_f']>row['mdi_f'] and row['close']>row['ema21'] and not(prev['pdi_f']>prev['mdi_f']): add(sn,'long',row['close']); trig[sn]=True
        elif row['adx_f']>25 and row['mdi_f']>row['pdi_f'] and row['close']<row['ema21'] and not(prev['mdi_f']>prev['pdi_f']): add(sn,'short',row['close']); trig[sn]=True
    # RSI div
    sn = 'ALL_RSI_DIV'
    if sn not in trig and ci>=10 and pd.notna(row['rsi14']):
        l10 = c.iloc[ci-9:ci+1]
        if row['low']<l10.iloc[:-1]['low'].min() and row['rsi14']>l10.iloc[:-1]['rsi14'].min() and row['close']>row['open']: add(sn,'long',row['close']); trig[sn]=True
        if row['high']>l10.iloc[:-1]['high'].max() and row['rsi14']<l10.iloc[:-1]['rsi14'].max() and row['close']<row['open']: add(sn,'short',row['close']); trig[sn]=True
    # Ichimoku TK, BB tight, MACD_RSI
    sn = 'ALL_ICHI_TK'
    if sn not in trig and pd.notna(row['i_t']):
        if prev['i_t']<prev['i_k'] and row['i_t']>row['i_k'] and pd.notna(row['i_sa']) and row['close']>max(row['i_sa'],row['i_sb']): add(sn,'long',row['close']); trig[sn]=True
        elif prev['i_t']>prev['i_k'] and row['i_t']<row['i_k'] and pd.notna(row['i_sa']) and row['close']<min(row['i_sa'],row['i_sb']): add(sn,'short',row['close']); trig[sn]=True
    sn = 'ALL_MACD_RSI'
    if sn not in trig and pd.notna(row['macd_med']) and pd.notna(row['rsi14']):
        if prev['macd_med']<prev['macd_med_sig'] and row['macd_med']>row['macd_med_sig'] and row['rsi14']>50: add(sn,'long',row['close']); trig[sn]=True
        elif prev['macd_med']>prev['macd_med_sig'] and row['macd_med']<row['macd_med_sig'] and row['rsi14']<50: add(sn,'short',row['close']); trig[sn]=True
    # Williams %R, Momentum, HMA, DC10+EMA, CCI, CMO, Fisher, DPO, AO saucer, MTF BRK
    for p,nm in [(7,'7'),(14,'14')]:
        sn = f'ALL_WILLR_{nm}'
        if sn not in trig and pd.notna(row[f'wr{p}']):
            if prev[f'wr{p}']<-80 and row[f'wr{p}']>=-80: add(sn,'long',row['close']); trig[sn]=True
            elif prev[f'wr{p}']>-20 and row[f'wr{p}']<=-20: add(sn,'short',row['close']); trig[sn]=True
    for p,nm in [(10,'10'),(14,'14')]:
        sn = f'ALL_MOM_{nm}'
        if sn not in trig and pd.notna(row[f'mom{p}']):
            if prev[f'mom{p}']<0 and row[f'mom{p}']>=0: add(sn,'long',row['close']); trig[sn]=True
            elif prev[f'mom{p}']>0 and row[f'mom{p}']<=0: add(sn,'short',row['close']); trig[sn]=True
    sn = 'ALL_HMA_CROSS'
    if sn not in trig and pd.notna(row['hma9']) and pd.notna(row['hma21']):
        if prev['hma9']<prev['hma21'] and row['hma9']>row['hma21']: add(sn,'long',row['close']); trig[sn]=True
        elif prev['hma9']>prev['hma21'] and row['hma9']<row['hma21']: add(sn,'short',row['close']); trig[sn]=True
    sn = 'ALL_DC10_EMA'
    if sn not in trig and pd.notna(prev.get('dc10_h')) and pd.notna(row['ema21']):
        if row['close']>prev['dc10_h'] and row['close']>row['ema21']: add(sn,'long',row['close']); trig[sn]=True
        elif row['close']<prev['dc10_l'] and row['close']<row['ema21']: add(sn,'short',row['close']); trig[sn]=True
    for p,nm in [(9,'9'),(14,'14')]:
        sn = f'ALL_CMO_{nm}'
        if sn not in trig and pd.notna(row[f'cmo{p}']):
            if prev[f'cmo{p}']<-50 and row[f'cmo{p}']>=-50: add(sn,'long',row['close']); trig[sn]=True
            elif prev[f'cmo{p}']>50 and row[f'cmo{p}']<=50: add(sn,'short',row['close']); trig[sn]=True
    sn = 'ALL_CMO_14_ZERO'
    if sn not in trig and pd.notna(row['cmo14']):
        if prev['cmo14']<0 and row['cmo14']>=0: add(sn,'long',row['close']); trig[sn]=True
        elif prev['cmo14']>0 and row['cmo14']<=0: add(sn,'short',row['close']); trig[sn]=True
    sn = 'ALL_FISHER_9'
    if sn not in trig and pd.notna(row['fisher9']):
        if prev['fisher9']<prev['fisher9_sig'] and row['fisher9']>row['fisher9_sig']: add(sn,'long',row['close']); trig[sn]=True
        elif prev['fisher9']>prev['fisher9_sig'] and row['fisher9']<row['fisher9_sig']: add(sn,'short',row['close']); trig[sn]=True
    sn = 'ALL_DPO_14'
    if sn not in trig and pd.notna(row['dpo14']):
        if prev['dpo14']<0 and row['dpo14']>=0: add(sn,'long',row['close']); trig[sn]=True
        elif prev['dpo14']>0 and row['dpo14']<=0: add(sn,'short',row['close']); trig[sn]=True
    sn = 'ALL_AO_SAUCER'
    if sn not in trig and ci>=4 and pd.notna(row['ao']):
        a = [c.iloc[ci-j]['ao'] for j in range(3,-1,-1)]
        if all(pd.notna(x) for x in a):
            if a[0]>0 and a[1]<a[0] and a[2]<a[1] and a[3]>a[2] and a[3]>0: add(sn,'long',row['close']); trig[sn]=True
            elif a[0]<0 and a[1]>a[0] and a[2]>a[1] and a[3]<a[2] and a[3]<0: add(sn,'short',row['close']); trig[sn]=True
    sn = 'ALL_MTF_BRK'
    if sn not in trig and pd.notna(row['high_1h']):
        if row['close']>prev['high_1h'] and prev['close']<=c.iloc[ci-2]['high_1h']: add(sn,'long',row['close']); trig[sn]=True
        elif row['close']<prev['low_1h'] and prev['close']>=c.iloc[ci-2]['low_1h']: add(sn,'short',row['close']); trig[sn]=True
    # V4: Pivot, FVG
    if pd.notna(row.get('pivot')):
        sn = 'ALL_PIVOT_BOUNCE'
        if sn not in trig:
            if prev['low']<=row['pivot']*1.001 and row['close']>row['pivot'] and row['close']>row['open']: add(sn,'long',row['close']); trig[sn]=True
            elif prev['high']>=row['pivot']*0.999 and row['close']<row['pivot'] and row['close']<row['open']: add(sn,'short',row['close']); trig[sn]=True
        sn = 'ALL_PIVOT_BRK'
        if sn not in trig:
            if prev['close']<row['pivot'] and row['close']>row['pivot'] and row['abs_body']>=0.2*atr: add(sn,'long',row['close']); trig[sn]=True
            elif prev['close']>row['pivot'] and row['close']<row['pivot'] and row['abs_body']>=0.2*atr: add(sn,'short',row['close']); trig[sn]=True
    if ci>=3:
        sn = 'ALL_FVG_BULL'
        if sn not in trig:
            if c.iloc[ci-3]['high']<row['low'] and row['close']>row['open'] and row['abs_body']>=0.3*atr: add(sn,'long',row['close']); trig[sn]=True
    # V5: NR4, FIB, PO3, CONSEC_REV
    if ci>=5:
        sn = 'ALL_NR4'
        if sn not in trig:
            ranges = [c.iloc[ci-j]['range'] for j in range(4)]
            if row['range']==min(ranges) and row['range']>0 and row['abs_body']>=0.1*atr:
                add(sn,'long' if row['body']>0 else 'short',row['close']); trig[sn]=True
    if ci>=30:
        sn = 'ALL_FIB_618'
        if sn not in trig:
            l30 = c.iloc[ci-30:ci]; sh = l30['high'].max(); sl_ = l30['low'].min(); sr = sh-sl_
            if sr>=2.0*atr:
                f618 = sh-0.618*sr
                if row['close']>sh-0.3*sr and prev['low']<=f618 and row['close']>f618 and row['close']>row['open']: add(sn,'long',row['close']); trig[sn]=True
    if ci>=6:
        sn = 'ALL_CONSEC_REV'
        if sn not in trig:
            l5 = c.iloc[ci-5:ci]
            ab = all(l5.iloc[j]['close']>l5.iloc[j]['open'] for j in range(5))
            ae = all(l5.iloc[j]['close']<l5.iloc[j]['open'] for j in range(5))
            tr_ = l5['high'].max()-l5['low'].min()
            if ab and tr_>=1.5*atr and row['close']<row['open'] and row['abs_body']>=0.3*atr: add(sn,'short',row['close']); trig[sn]=True
            elif ae and tr_>=1.5*atr and row['close']>row['open'] and row['abs_body']>=0.3*atr: add(sn,'long',row['close']); trig[sn]=True
    # V6: TOK_FISHER, TOK_WILLR, TOK_MACD_MED, TOK_NR4
    if 0.0<=hour<6.0:
        sn = 'TOK_FISHER'
        if sn not in trig and pd.notna(row['fisher9']):
            if prev['fisher9']<prev['fisher9_sig'] and row['fisher9']>row['fisher9_sig']: add(sn,'long',row['close']); trig[sn]=True
            elif prev['fisher9']>prev['fisher9_sig'] and row['fisher9']<row['fisher9_sig']: add(sn,'short',row['close']); trig[sn]=True
        sn = 'TOK_WILLR'
        if sn not in trig and pd.notna(row['wr14']):
            if prev['wr14']<-80 and row['wr14']>=-80: add(sn,'long',row['close']); trig[sn]=True
            elif prev['wr14']>-20 and row['wr14']<=-20: add(sn,'short',row['close']); trig[sn]=True
        sn = 'TOK_MACD_MED'
        if sn not in trig and pd.notna(row['macd_med']):
            if prev['macd_med']<prev['macd_med_sig'] and row['macd_med']>row['macd_med_sig']: add(sn,'long',row['close']); trig[sn]=True
            elif prev['macd_med']>prev['macd_med_sig'] and row['macd_med']<row['macd_med_sig']: add(sn,'short',row['close']); trig[sn]=True
        if ci>=5:
            sn = 'TOK_NR4'
            if sn not in trig:
                ranges = [c.iloc[ci-j]['range'] for j in range(4)]
                if row['range']==min(ranges) and row['range']>0 and row['abs_body']>=0.1*atr:
                    add(sn,'long' if row['body']>0 else 'short',row['close']); trig[sn]=True
    # V7: PSAR_EMA, 3SOLDIERS
    sn = 'ALL_PSAR_EMA'
    if sn not in trig and pd.notna(row['ema20']):
        if prev['psar_dir']==-1 and row['psar_dir']==1 and row['close']>row['ema20']: add(sn,'long',row['close']); trig[sn]=True
        elif prev['psar_dir']==1 and row['psar_dir']==-1 and row['close']<row['ema20']: add(sn,'short',row['close']); trig[sn]=True
    if ci>=3:
        sn = 'ALL_3SOLDIERS'
        if sn not in trig:
            b1=c.iloc[ci-2];b2=c.iloc[ci-1];b3=row
            if (b1['close']>b1['open'] and b2['close']>b2['open'] and b3['close']>b3['open'] and
                b2['close']>b1['close'] and b3['close']>b2['close'] and
                min(abs(b1['body']),abs(b2['body']),abs(b3['body']))>=0.3*atr):
                add(sn,'long',row['close']); trig[sn]=True
            if (b1['close']<b1['open'] and b2['close']<b2['open'] and b3['close']<b3['open'] and
                b2['close']<b1['close'] and b3['close']<b2['close'] and
                min(abs(b1['body']),abs(b2['body']),abs(b3['body']))>=0.3*atr):
                add(sn,'short',row['close']); trig[sn]=True
    # PO3 sweep
    if 7.0<=hour<9.0 and 'PO3_SWEEP' not in trig:
        asian = c[(c['ts_dt']>=ds)&(c['ts_dt']<te)]
        if len(asian)>=50:
            ah=asian['high'].max(); al_=asian['low'].min()
            if row['low']<al_ and row['close']>al_ and row['close']>row['open']: add('PO3_SWEEP','long',row['close']); trig['PO3_SWEEP']=True
            elif row['high']>ah and row['close']<ah and row['close']<row['open']: add('PO3_SWEEP','short',row['close']); trig['PO3_SWEEP']=True

print(f"Done. {len(S)} strats.", flush=True)

# ── STATS + GREEDY COMBO ──
print("\n  Stats individuelles (PF>1.3 + split OK):")
valid = []
for sn in sorted(S.keys()):
    t = S[sn]; n = len(t)
    if n < 20: continue
    pnls = [x['pnl_oz'] for x in t]
    gp = sum(p for p in pnls if p>0); gl = abs(sum(p for p in pnls if p<0))+0.001
    pf = gp/gl; wr = sum(1 for p in pnls if p>0)/n*100
    mid = n//2; f1 = np.mean(pnls[:mid]); f2 = np.mean(pnls[mid:])
    split = f1>0 and f2>0
    if pf > 1.3 and split:
        valid.append(sn)
        print(f"    {sn:22s} n={n:4d} PF={pf:.2f} WR={wr:.0f}%")

print(f"\n  {len(valid)} strats retenues (PF>1.3 + split OK)")

# Build arrays
strat_arrays = {}
for sn in valid:
    rows = []
    for t in S[sn]:
        di = 1 if t['dir']=='long' else -1
        mo = str(t['date'].year)+"-"+str(t['date'].month).zfill(2)
        rows.append((t['ei'], t['xi'], di, t['pnl_oz'], t['sl_atr'], t['atr'], mo, sn))
    strat_arrays[sn] = rows

def eval_combo(strats, capital=1000.0, risk=0.01):
    combined = []
    for sn in strats:
        if sn in strat_arrays: combined.extend(strat_arrays[sn])
    if len(combined) < 50: return None
    combined.sort(key=lambda x: (x[0], x[7]))
    active = []; accepted = []
    for ei, xi, di, pnl_oz, sl_atr, atr, mo, _sn in combined:
        active = [(axi, ad) for axi, ad in active if axi >= ei]
        if any(ad != di for _, ad in active): continue
        accepted.append((ei, xi, di, pnl_oz, sl_atr, atr, mo, _sn))
        active.append((xi, di))
    n = len(accepted)
    if n < 50: return None
    cap = capital; peak = cap; max_dd = 0; gp = 0; gl = 0; wins = 0; months = {}
    has_l = False; has_s = False; pnls = []
    for ei, xi, di, pnl_oz, sl_atr, atr, mo, _sn in accepted:
        pnl = pnl_oz * (cap * risk) / (sl_atr * atr)
        cap += pnl; pnls.append(pnl)
        if cap > peak: peak = cap
        dd = (cap - peak) / peak
        if dd < max_dd: max_dd = dd
        if pnl > 0: gp += pnl; wins += 1
        else: gl += abs(pnl)
        months[mo] = months.get(mo, 0.0) + pnl
        if di == 1: has_l = True;
        else: has_s = True
    mdd = max_dd * 100; ret = (cap - capital) / capital * 100
    mid = n // 2; p1 = sum(pnls[:mid]); p2 = sum(pnls[mid:])
    pm = sum(1 for v in months.values() if v > 0)
    return {'n': n, 'ret': ret, 'mdd': mdd, 'cal': ret / abs(mdd) if mdd < 0 else 0,
            'pf': gp / (gl + 0.01), 'wr': wins / n * 100, 'capital': cap,
            'split': p1 > 0 and p2 > 0, 'both': has_s and has_l, 'pm': pm, 'tm': len(months)}

# GREEDY: start with best single strat, add one at a time
print(f"\n{'='*130}")
print(f"GREEDY COMBO BUILDER")
print(f"{'='*130}")

# Rank by individual PF
ranked = sorted(valid, key=lambda sn: sum(p for p in [x['pnl_oz'] for x in S[sn]] if p>0)/(abs(sum(p for p in [x['pnl_oz'] for x in S[sn]] if p<0))+0.001), reverse=True)

combo = [ranked[0]]
remaining = set(ranked[1:])
print(f"\n  Start: {combo[0]}")
r = eval_combo(combo)
if r: print(f"    n={r['n']} PF={r['pf']:.2f} DD={r['mdd']:+.1f}% Rend={r['ret']:+.0f}% M+={r['pm']}/{r['tm']}")

for step in range(min(20, len(remaining))):
    best_add = None; best_cal = -1e9
    for sn in remaining:
        test = combo + [sn]
        r = eval_combo(test)
        if r and r['split'] and r['both']:
            if r['cal'] > best_cal:
                best_cal = r['cal']; best_add = sn; best_r = r
    if best_add is None: break
    combo.append(best_add); remaining.remove(best_add)
    r = best_r
    print(f"\n  +{best_add} ({len(combo)} strats)")
    print(f"    n={r['n']} PF={r['pf']:.2f} WR={r['wr']:.0f}% DD={r['mdd']:+.1f}% Cal={r['cal']:.1f} Rend={r['ret']:+.0f}% M+={r['pm']}/{r['tm']}")
    print(f"    Combo: {'+'.join(combo)}")

print(f"\n{'='*130}")
print(f"FINAL: {'+'.join(combo)}")
print(f"{'='*130}")
