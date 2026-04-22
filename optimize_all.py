"""
Optimisation complete: toutes les strats x tous les exits → meilleur combo.
1. Collecte signaux bruts (sans exit)
2. Grille SL/TP/TRAIL par strat
3. Best config par strat (PF + split)
4. Greedy combo builder
"""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
from dotenv import load_dotenv; load_dotenv()
from phase1_poc_calculator import get_conn, compute_atr, get_trading_days
from phase3_analyze import load_candles_5m
from strats import detect_all

# ── SYMBOL ──
import argparse as _ap
_p = _ap.ArgumentParser(); _p.add_argument('account')
_p.add_argument('--symbol', default='xauusd')
_p.add_argument('--tf', default='5m', help='Timeframe: 5m or 15m')
_p.add_argument('--spread', action='store_true', help='Modelise le spread (-0.1R par trade)')
_a = _p.parse_args()
SPREAD_R = 0.1 if _a.spread else 0.0
SYMBOL = _a.symbol.lower()
TF = _a.tf

# ── DATA ──
from backtest_engine import load_data as _be_load
print(f"Loading data ({SYMBOL} {TF})...", flush=True)
conn = get_conn()
candles, daily_atr, global_atr, trading_days = _be_load(conn, SYMBOL, tf=TF)
conn.close()
def prev_day(day):
    for di, d in enumerate(trading_days):
        if d >= day: return trading_days[di-1] if di > 0 else None
    return None

OPEN_STRATS = {'TOK_FADE','TOK_PREVEXT','LON_GAP','LON_BIGGAP','LON_KZ','LON_TOKEND','LON_PREV',
               'NY_GAP','NY_LONEND','NY_LONMOM','NY_DAYMOM'}

# Strats doublonnees (meme code, noms differents) — exclure pour eviter double exposition
DUPLICATE_STRATS = {
    'IDX_KC_BRK',    # doublon exact de ALL_KC_BRK
    'IDX_ENGULF',    # doublon exact de ALL_ENGULF (seuil 0.3*atr identique)
    'ALL_ROC_ZERO',  # doublon mathematique de ALL_MOM_10 (meme formule: (close/close[-10]-1)*100)
    'IDX_NR4',       # doublon exact de ALL_NR4 (range == candle_range, meme seuil 0.1*atr)
}

# ── PRECALCUL INDICATEURS ──
print("Precalcul indicateurs...", flush=True)
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
c['sma20'] = c['close'].rolling(20).mean()
dates = c['date'].unique()
c['prev_h_d'] = np.nan; c['prev_l_d'] = np.nan; c['prev_c_d'] = np.nan
for i in range(1, len(dates)):
    prev_dc = c[c['date']==dates[i-1]]
    today_mask = c['date']==dates[i]
    c.loc[today_mask,'prev_h_d'] = prev_dc['high'].max()
    c.loc[today_mask,'prev_l_d'] = prev_dc['low'].min()
    c.loc[today_mask,'prev_c_d'] = prev_dc.iloc[-1]['close']
c['pivot'] = (c['prev_h_d']+c['prev_l_d']+c['prev_c_d'])/3
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
c['ao'] = c['mid'].rolling(5).mean() - c['mid'].rolling(34).mean()
c['high_1h'] = c['high'].rolling(12).max(); c['low_1h'] = c['low'].rolling(12).min()
# PSAR (supertrend proxy)
up2 = c['mid'] - 2.0*c['atr14']; dn2 = c['mid'] + 2.0*c['atr14']
st_dir = np.zeros(len(c)); st_val = np.zeros(len(c))
for i in range(1, len(c)):
    if c.iloc[i]['close'] > dn2.iloc[i-1]: st_dir[i]=1; st_val[i]=up2.iloc[i]
    elif c.iloc[i]['close'] < up2.iloc[i-1]: st_dir[i]=-1; st_val[i]=dn2.iloc[i]
    else:
        st_dir[i]=st_dir[i-1]
        st_val[i]=max(up2.iloc[i],st_val[i-1]) if st_dir[i]==1 else min(dn2.iloc[i],st_val[i-1])
c['psar_dir'] = st_dir

# Complete with compute_indicators for new strats (BB, VWAP, candle_range, etc.)
from strats import compute_indicators as _ci
c = _ci(c)

# ── EXIT SIMULATION — meme fonction que backtest_engine/strats.py ──
from strats import sim_exit_custom as _sim_exit_custom

def sim_exit_unified(pos, entry, d, atr, etype, p1, p2, p3, check_entry):
    """Wrapper: appelle sim_exit_custom de strats.py (source unique)."""
    d_str = 'long' if d == 1 else 'short'
    etype_map = {0: 'TPSL', 1: 'TRAIL', 2: 'BE_TP'}
    exit_type = etype_map.get(etype, 'TRAIL')
    return _sim_exit_custom(c, pos, entry, d_str, atr, exit_type, p1, p2, p3, check_entry_candle=check_entry)

# ── SIGNAL COLLECTION ──
print("Collecte signaux...", flush=True)
SIG = {}  # strat -> [(ci, dir_int, entry, atr, date, spread), ...]
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
    sp = 0  # spread ignored (insignificant at PF>1.3)
    ds = pd.Timestamp(today.year,today.month,today.day,0,0,tz='UTC')
    te = pd.Timestamp(today.year,today.month,today.day,6,0,tz='UTC')
    ls = pd.Timestamp(today.year,today.month,today.day,8,0,tz='UTC')
    ns = pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC')
    tv = c[(c['ts_dt']>=ds)&(c['ts_dt']<=ct)]
    tok = tv[tv['ts_dt']<te]; lon = tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<ns)]

    def add_sig(sn, d, e):
        di = 1 if d == 'long' else -1
        SIG.setdefault(sn, []).append((ci, di, e, atr, today, sp))

    # Price action + indicator strats from detect_all
    detect_all(c, ci, row, ct, today, hour, atr, trig, tv, tok, lon, prev_day_data, add_sig, prev2_day_data)

    # ── ALL INDICATOR STRATS (from find_combo_greedy.py) ──
    # MACD crosses
    for nm in ['std','fast','med']:
        mc,ms = f'macd_{nm}',f'macd_{nm}_sig'
        sn = f'ALL_MACD_{nm.upper()}_SIG'
        if sn not in trig and pd.notna(row[mc]):
            if prev[mc]<prev[ms] and row[mc]>row[ms]: add_sig(sn,'long',row['close']); trig[sn]=True
            elif prev[mc]>prev[ms] and row[mc]<row[ms]: add_sig(sn,'short',row['close']); trig[sn]=True
    # RSI 50
    sn = 'ALL_RSI_50'
    if sn not in trig and pd.notna(row['rsi14']):
        if prev['rsi14']<50 and row['rsi14']>=50: add_sig(sn,'long',row['close']); trig[sn]=True
        elif prev['rsi14']>50 and row['rsi14']<=50: add_sig(sn,'short',row['close']); trig[sn]=True
    # Donchian
    for p in [10,50]:
        sn = f'ALL_DC{p}'
        if sn not in trig and pd.notna(prev.get(f'dc{p}_h')):
            if row['close']>prev[f'dc{p}_h']: add_sig(sn,'long',row['close']); trig[sn]=True
            elif row['close']<prev[f'dc{p}_l']: add_sig(sn,'short',row['close']); trig[sn]=True
    # KC
    sn = 'ALL_KC_BRK'
    if sn not in trig and pd.notna(row['kc_up']):
        if row['close']>row['kc_up'] and prev['close']<=prev['kc_up']: add_sig(sn,'long',row['close']); trig[sn]=True
        elif row['close']<row['kc_lo'] and prev['close']>=prev['kc_lo']: add_sig(sn,'short',row['close']); trig[sn]=True
    # MACD+ADX, ADX_FAST
    sn = 'ALL_MACD_ADX'
    if sn not in trig and pd.notna(row['macd_std']) and pd.notna(row['adx_s']):
        if row['adx_s']>25 and prev['macd_std']<prev['macd_std_sig'] and row['macd_std']>row['macd_std_sig']: add_sig(sn,'long',row['close']); trig[sn]=True
        elif row['adx_s']>25 and prev['macd_std']>prev['macd_std_sig'] and row['macd_std']<row['macd_std_sig']: add_sig(sn,'short',row['close']); trig[sn]=True
    sn = 'ALL_ADX_FAST'
    if sn not in trig and pd.notna(row['adx_f']) and pd.notna(row['ema21']):
        if row['adx_f']>25 and row['pdi_f']>row['mdi_f'] and row['close']>row['ema21'] and not(prev['pdi_f']>prev['mdi_f']): add_sig(sn,'long',row['close']); trig[sn]=True
        elif row['adx_f']>25 and row['mdi_f']>row['pdi_f'] and row['close']<row['ema21'] and not(prev['mdi_f']>prev['pdi_f']): add_sig(sn,'short',row['close']); trig[sn]=True
    # RSI div
    sn = 'ALL_RSI_DIV'
    if sn not in trig and ci>=10 and pd.notna(row['rsi14']):
        l10 = c.iloc[ci-9:ci+1]
        if row['low']<l10.iloc[:-1]['low'].min() and row['rsi14']>l10.iloc[:-1]['rsi14'].min() and row['close']>row['open']: add_sig(sn,'long',row['close']); trig[sn]=True
        if row['high']>l10.iloc[:-1]['high'].max() and row['rsi14']<l10.iloc[:-1]['rsi14'].max() and row['close']<row['open']: add_sig(sn,'short',row['close']); trig[sn]=True
    # Ichimoku TK
    sn = 'ALL_ICHI_TK'
    if sn not in trig and pd.notna(row['i_t']):
        if prev['i_t']<prev['i_k'] and row['i_t']>row['i_k'] and pd.notna(row['i_sa']) and row['close']>max(row['i_sa'],row['i_sb']): add_sig(sn,'long',row['close']); trig[sn]=True
        elif prev['i_t']>prev['i_k'] and row['i_t']<row['i_k'] and pd.notna(row['i_sa']) and row['close']<min(row['i_sa'],row['i_sb']): add_sig(sn,'short',row['close']); trig[sn]=True
    # MACD_RSI (already in detect_all but also here for completeness — trig prevents double)
    # Williams %R
    for p,nm in [(7,'7'),(14,'14')]:
        sn = f'ALL_WILLR_{nm}'
        if sn not in trig and pd.notna(row[f'wr{p}']):
            if prev[f'wr{p}']<-80 and row[f'wr{p}']>=-80: add_sig(sn,'long',row['close']); trig[sn]=True
            elif prev[f'wr{p}']>-20 and row[f'wr{p}']<=-20: add_sig(sn,'short',row['close']); trig[sn]=True
    # Momentum
    for p,nm in [(10,'10'),(14,'14')]:
        sn = f'ALL_MOM_{nm}'
        if sn not in trig and pd.notna(row[f'mom{p}']):
            if prev[f'mom{p}']<0 and row[f'mom{p}']>=0: add_sig(sn,'long',row['close']); trig[sn]=True
            elif prev[f'mom{p}']>0 and row[f'mom{p}']<=0: add_sig(sn,'short',row['close']); trig[sn]=True
    # HMA cross
    sn = 'ALL_HMA_CROSS'
    if sn not in trig and pd.notna(row['hma9']) and pd.notna(row['hma21']):
        if prev['hma9']<prev['hma21'] and row['hma9']>row['hma21']: add_sig(sn,'long',row['close']); trig[sn]=True
        elif prev['hma9']>prev['hma21'] and row['hma9']<row['hma21']: add_sig(sn,'short',row['close']); trig[sn]=True
    # DC10+EMA
    sn = 'ALL_DC10_EMA'
    if sn not in trig and pd.notna(prev.get('dc10_h')) and pd.notna(row['ema21']):
        if row['close']>prev['dc10_h'] and row['close']>row['ema21']: add_sig(sn,'long',row['close']); trig[sn]=True
        elif row['close']<prev['dc10_l'] and row['close']<row['ema21']: add_sig(sn,'short',row['close']); trig[sn]=True
    # CMO
    for p,nm in [(9,'9'),(14,'14')]:
        sn = f'ALL_CMO_{nm}'
        if sn not in trig and pd.notna(row[f'cmo{p}']):
            if prev[f'cmo{p}']<-50 and row[f'cmo{p}']>=-50: add_sig(sn,'long',row['close']); trig[sn]=True
            elif prev[f'cmo{p}']>50 and row[f'cmo{p}']<=50: add_sig(sn,'short',row['close']); trig[sn]=True
    sn = 'ALL_CMO_14_ZERO'
    if sn not in trig and pd.notna(row['cmo14']):
        if prev['cmo14']<0 and row['cmo14']>=0: add_sig(sn,'long',row['close']); trig[sn]=True
        elif prev['cmo14']>0 and row['cmo14']<=0: add_sig(sn,'short',row['close']); trig[sn]=True
    # Fisher
    sn = 'ALL_FISHER_9'
    if sn not in trig and pd.notna(row['fisher9']):
        if prev['fisher9']<prev['fisher9_sig'] and row['fisher9']>row['fisher9_sig']: add_sig(sn,'long',row['close']); trig[sn]=True
        elif prev['fisher9']>prev['fisher9_sig'] and row['fisher9']<row['fisher9_sig']: add_sig(sn,'short',row['close']); trig[sn]=True
    # DPO
    sn = 'ALL_DPO_14'
    if sn not in trig and pd.notna(row['dpo14']):
        if prev['dpo14']<0 and row['dpo14']>=0: add_sig(sn,'long',row['close']); trig[sn]=True
        elif prev['dpo14']>0 and row['dpo14']<=0: add_sig(sn,'short',row['close']); trig[sn]=True
    # AO saucer
    sn = 'ALL_AO_SAUCER'
    if sn not in trig and ci>=4 and pd.notna(row['ao']):
        a = [c.iloc[ci-j]['ao'] for j in range(3,-1,-1)]
        if all(pd.notna(x) for x in a):
            if a[0]>0 and a[1]<a[0] and a[2]<a[1] and a[3]>a[2] and a[3]>0: add_sig(sn,'long',row['close']); trig[sn]=True
            elif a[0]<0 and a[1]>a[0] and a[2]>a[1] and a[3]<a[2] and a[3]<0: add_sig(sn,'short',row['close']); trig[sn]=True
    # MTF breakout
    sn = 'ALL_MTF_BRK'
    if sn not in trig and pd.notna(row['high_1h']):
        if row['close']>prev['high_1h'] and prev['close']<=c.iloc[ci-2]['high_1h']: add_sig(sn,'long',row['close']); trig[sn]=True
        elif row['close']<prev['low_1h'] and prev['close']>=c.iloc[ci-2]['low_1h']: add_sig(sn,'short',row['close']); trig[sn]=True
    # Pivot
    if pd.notna(row.get('pivot')):
        sn = 'ALL_PIVOT_BOUNCE'
        if sn not in trig:
            if prev['low']<=row['pivot']*1.001 and row['close']>row['pivot'] and row['close']>row['open']: add_sig(sn,'long',row['close']); trig[sn]=True
            elif prev['high']>=row['pivot']*0.999 and row['close']<row['pivot'] and row['close']<row['open']: add_sig(sn,'short',row['close']); trig[sn]=True
        sn = 'ALL_PIVOT_BRK'
        if sn not in trig:
            if prev['close']<row['pivot'] and row['close']>row['pivot'] and row['abs_body']>=0.2*atr: add_sig(sn,'long',row['close']); trig[sn]=True
            elif prev['close']>row['pivot'] and row['close']<row['pivot'] and row['abs_body']>=0.2*atr: add_sig(sn,'short',row['close']); trig[sn]=True
    # FVG (already in detect_all)
    # NR4
    if ci>=5:
        sn = 'ALL_NR4'
        if sn not in trig:
            ranges = [c.iloc[ci-j]['range'] for j in range(4)]
            if row['range']==min(ranges) and row['range']>0 and row['abs_body']>=0.1*atr:
                add_sig(sn,'long' if row['body']>0 else 'short',row['close']); trig[sn]=True
    # Tokyo session indicators
    if 0.0<=hour<6.0:
        sn = 'TOK_FISHER'
        if sn not in trig and pd.notna(row['fisher9']):
            if prev['fisher9']<prev['fisher9_sig'] and row['fisher9']>row['fisher9_sig']: add_sig(sn,'long',row['close']); trig[sn]=True
            elif prev['fisher9']>prev['fisher9_sig'] and row['fisher9']<row['fisher9_sig']: add_sig(sn,'short',row['close']); trig[sn]=True
        sn = 'TOK_WILLR'
        if sn not in trig and pd.notna(row['wr14']):
            if prev['wr14']<-80 and row['wr14']>=-80: add_sig(sn,'long',row['close']); trig[sn]=True
            elif prev['wr14']>-20 and row['wr14']<=-20: add_sig(sn,'short',row['close']); trig[sn]=True
        sn = 'TOK_MACD_MED'
        if sn not in trig and pd.notna(row['macd_med']):
            if prev['macd_med']<prev['macd_med_sig'] and row['macd_med']>row['macd_med_sig']: add_sig(sn,'long',row['close']); trig[sn]=True
            elif prev['macd_med']>prev['macd_med_sig'] and row['macd_med']<row['macd_med_sig']: add_sig(sn,'short',row['close']); trig[sn]=True
        if ci>=5:
            sn = 'TOK_NR4'
            if sn not in trig:
                ranges = [c.iloc[ci-j]['range'] for j in range(4)]
                if row['range']==min(ranges) and row['range']>0 and row['abs_body']>=0.1*atr:
                    add_sig(sn,'long' if row['body']>0 else 'short',row['close']); trig[sn]=True
    # PSAR_EMA, 3SOLDIERS (already in detect_all)
    # PO3 (already in detect_all)

    # ── MISSING STRATS (13 from STRAT_EXITS) ──
    # ALL_EMA_513: EMA5 cross EMA13
    sn = 'ALL_EMA_513'
    if sn not in trig and pd.notna(row['ema5']) and pd.notna(row['ema13']):
        if prev['ema5']<prev['ema13'] and row['ema5']>row['ema13']: add_sig(sn,'long',row['close']); trig[sn]=True
        elif prev['ema5']>prev['ema13'] and row['ema5']<row['ema13']: add_sig(sn,'short',row['close']); trig[sn]=True
    # ALL_EMA_821: EMA8 cross EMA21
    sn = 'ALL_EMA_821'
    if sn not in trig and pd.notna(row['ema8']) and pd.notna(row['ema21']):
        if prev['ema8']<prev['ema21'] and row['ema8']>row['ema21']: add_sig(sn,'long',row['close']); trig[sn]=True
        elif prev['ema8']>prev['ema21'] and row['ema8']<row['ema21']: add_sig(sn,'short',row['close']); trig[sn]=True
    # ALL_EMA_921: EMA9 cross EMA21
    sn = 'ALL_EMA_921'
    if sn not in trig and pd.notna(row['ema9']) and pd.notna(row['ema21']):
        if prev['ema9']<prev['ema21'] and row['ema9']>row['ema21']: add_sig(sn,'long',row['close']); trig[sn]=True
        elif prev['ema9']>prev['ema21'] and row['ema9']<row['ema21']: add_sig(sn,'short',row['close']); trig[sn]=True
    # ALL_MACD_FAST_ZERO: MACD fast zero cross
    sn = 'ALL_MACD_FAST_ZERO'
    if sn not in trig and pd.notna(row['macd_fast']):
        if prev['macd_fast']<0 and row['macd_fast']>=0: add_sig(sn,'long',row['close']); trig[sn]=True
        elif prev['macd_fast']>0 and row['macd_fast']<=0: add_sig(sn,'short',row['close']); trig[sn]=True
    # ALL_MACD_SIG: = ALL_MACD_STD_SIG (already detected above as ALL_MACD_STD_SIG)
    # ALL_BB_TIGHT: Bollinger squeeze breakout
    sn = 'ALL_BB_TIGHT'
    if sn not in trig and pd.notna(row['bb_t_up']):
        if row['close']>row['bb_t_up'] and prev['close']<=prev['bb_t_up']: add_sig(sn,'long',row['close']); trig[sn]=True
        elif row['close']<row['bb_t_lo'] and prev['close']>=prev['bb_t_lo']: add_sig(sn,'short',row['close']); trig[sn]=True
    # ALL_CCI_14_ZERO: CCI14 zero cross
    sn = 'ALL_CCI_14_ZERO'
    if sn not in trig and pd.notna(row['cci14']):
        if prev['cci14']<0 and row['cci14']>=0: add_sig(sn,'long',row['close']); trig[sn]=True
        elif prev['cci14']>0 and row['cci14']<=0: add_sig(sn,'short',row['close']); trig[sn]=True
    # ALL_CCI_20_ZERO: CCI20 zero cross
    sn = 'ALL_CCI_20_ZERO'
    if sn not in trig and pd.notna(row['cci20']):
        if prev['cci20']<0 and row['cci20']>=0: add_sig(sn,'long',row['close']); trig[sn]=True
        elif prev['cci20']>0 and row['cci20']<=0: add_sig(sn,'short',row['close']); trig[sn]=True
    # ALL_HMA_DIR: HMA21 direction change
    sn = 'ALL_HMA_DIR'
    if sn not in trig and ci>=2 and pd.notna(row['hma21']):
        if c.iloc[ci-2]['hma21']>prev['hma21'] and prev['hma21']<row['hma21']: add_sig(sn,'long',row['close']); trig[sn]=True
        elif c.iloc[ci-2]['hma21']<prev['hma21'] and prev['hma21']>row['hma21']: add_sig(sn,'short',row['close']); trig[sn]=True
    # ALL_EMA_TREND_PB: EMA trend pullback (price above EMA50+EMA200 up, pullback to EMA20)
    sn = 'ALL_EMA_TREND_PB'
    if sn not in trig and pd.notna(row['ema50']) and pd.notna(row['ema200']) and pd.notna(row['ema20']):
        if row['ema50']>row['ema200'] and prev['low']<=prev['ema20'] and row['close']>row['ema20'] and row['close']>row['open']:
            add_sig(sn,'long',row['close']); trig[sn]=True
        elif row['ema50']<row['ema200'] and prev['high']>=prev['ema20'] and row['close']<row['ema20'] and row['close']<row['open']:
            add_sig(sn,'short',row['close']); trig[sn]=True
    # LON_DC10: London-only Donchian 10 breakout
    if 8.0<=hour<14.5:
        sn = 'LON_DC10'
        if sn not in trig and pd.notna(prev.get('dc10_h')):
            if row['close']>prev['dc10_h']: add_sig(sn,'long',row['close']); trig[sn]=True
            elif row['close']<prev['dc10_l']: add_sig(sn,'short',row['close']); trig[sn]=True
        # LON_DC10_MOM: London DC10 + momentum>0
        sn = 'LON_DC10_MOM'
        if sn not in trig and pd.notna(prev.get('dc10_h')) and pd.notna(row.get('mom10')):
            if row['close']>prev['dc10_h'] and row['mom10']>0: add_sig(sn,'long',row['close']); trig[sn]=True
            elif row['close']<prev['dc10_l'] and row['mom10']<0: add_sig(sn,'short',row['close']); trig[sn]=True
    # NY_HMA_CROSS: NY session HMA cross
    if 14.5<=hour<21.0:
        sn = 'NY_HMA_CROSS'
        if sn not in trig and pd.notna(row['hma9']) and pd.notna(row['hma21']):
            if prev['hma9']<prev['hma21'] and row['hma9']>row['hma21']: add_sig(sn,'long',row['close']); trig[sn]=True
            elif prev['hma9']>prev['hma21'] and row['hma9']<row['hma21']: add_sig(sn,'short',row['close']); trig[sn]=True

print(f"Done. {len(SIG)} strats, {sum(len(v) for v in SIG.values())} signaux total.", flush=True)

# ── EXIT OPTIMIZATION GRID ──
print("\nOptimisation exits...", flush=True)

# Grid configs — version ROBUSTE (2026-04-22)
# Objectif: distribution reguliere, zero dependance aux outliers, walk-forward valide
TPSL_GRID = [(sl, tp) for sl in [0.5, 1.0, 1.5, 2.0, 2.5, 3.0] for tp in [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]]
# TRAIL restreint: act/trail <= 0.5 (trailing serre, limite expo queue droite)
TRAIL_GRID = [(sl, act, trail) for sl in [0.5, 1.0, 1.5, 2.0, 3.0]
              for act in [0.3, 0.5] for trail in [0.3, 0.5]]
# BE_TP reintegre: move SL to BE a be_act (R), TP a p3 (R)
BE_TP_GRID = [(sl, be_act, tp) for sl in [1.0, 1.5, 2.0, 2.5, 3.0]
              for be_act in [0.3, 0.5, 0.75] for tp in [0.75, 1.0, 1.5, 2.0, 3.0]
              if be_act < tp]

# Filtres de robustesse
MIN_N = 80                 # echantillon minimum
MIN_PF_TRIMMED = 1.20      # PF sans 5% top + 5% bottom
MAX_PCT_ABOVE_3R = 1.0     # max 1% des trades au-dessus de 3R
MAX_NEG_MONTHS = 2         # max 2 mois negatifs sur la periode totale
MIN_TEST_PF = 1.0          # walk-forward OOS sanity

def _compute_pnls_R(signals, etype, p1, p2, p3):
    """Retourne (pnls_R numpy, dates list)."""
    pnls = []; dates = []
    for ci, di, entry, atr, date, sp in signals:
        b, ex = sim_exit_unified(ci, entry, di, atr, etype, p1, p2, p3, False)
        pnl_price = ((ex - entry) if di == 1 else (entry - ex)) - sp - SPREAD_R * p1 * atr
        risk = p1 * atr if (p1 * atr) > 0 else 1.0
        pnls.append(pnl_price / risk); dates.append(date)
    return np.array(pnls), dates

def _metrics(pnls_R, dates):
    n = len(pnls_R)
    if n < 10: return None
    wins = pnls_R[pnls_R > 0]; losses = pnls_R[pnls_R < 0]
    gp = float(wins.sum()); gl = abs(float(losses.sum())) + 1e-6
    pf = gp / gl
    wr = float((pnls_R > 0).mean() * 100)
    # Trimmed PF (5% top + 5% bottom)
    srt = np.sort(pnls_R); k5 = int(n * 0.05)
    trimmed = srt[k5:n-k5] if k5 > 0 and n > 2*k5 else srt
    tw = float(trimmed[trimmed > 0].sum()); tl = abs(float(trimmed[trimmed < 0].sum())) + 1e-6
    pf_trimmed = tw / tl
    # Outlier share: part du gain total venant du top 5% des winners
    pos_srt = np.sort(wins)[::-1] if len(wins) > 0 else np.array([])
    kp = max(1, int(len(pos_srt) * 0.05)) if len(pos_srt) > 0 else 0
    outlier_share = float(pos_srt[:kp].sum() / gp) if gp > 0 and kp > 0 else 1.0
    # % trades > 3R
    pct_above_3R = float((pnls_R > 3.0).mean() * 100)
    # Median
    median_R = float(np.median(pnls_R))
    # PnL mensuel
    months = {}
    for pn, d in zip(pnls_R, dates):
        mk = f"{d.year}-{d.month:02d}"
        months[mk] = months.get(mk, 0.0) + float(pn)
    m_neg = sum(1 for v in months.values() if v < 0)
    m_total = len(months)
    m_pos = sum(1 for v in months.values() if v > 0)
    return {'n': n, 'pf': pf, 'wr': wr, 'pf_trimmed': pf_trimmed,
            'outlier_share': outlier_share, 'pct_above_3R': pct_above_3R,
            'median_R': median_R, 'm_neg': m_neg, 'm_pos': m_pos, 'm_total': m_total,
            'pnls_R': pnls_R}

def _eval_full_and_split(signals, etype, p1, p2, p3):
    """Retourne (full_m, train_m, test_m). Split 70/30 par date."""
    sigs_sorted = sorted(signals, key=lambda s: s[4])
    k = int(len(sigs_sorted) * 0.70)
    train = sigs_sorted[:k]; test = sigs_sorted[k:]
    pnls_full, dates_full = _compute_pnls_R(sigs_sorted, etype, p1, p2, p3)
    pnls_train, dates_train = _compute_pnls_R(train, etype, p1, p2, p3)
    pnls_test, dates_test = _compute_pnls_R(test, etype, p1, p2, p3)
    return (_metrics(pnls_full, dates_full),
            _metrics(pnls_train, dates_train),
            _metrics(pnls_test, dates_test))

def _passes(full_m, train_m, test_m):
    if train_m is None: return False, 'train_none'
    if train_m['n'] < int(MIN_N * 0.7): return False, f"train_n={train_m['n']}"
    if full_m is None or full_m['n'] < MIN_N: return False, f"n={full_m['n'] if full_m else 0}<{MIN_N}"
    if train_m['pf_trimmed'] < MIN_PF_TRIMMED: return False, f"pf_trim={train_m['pf_trimmed']:.2f}"
    if train_m['median_R'] <= 0: return False, f"med_R={train_m['median_R']:.3f}"
    if train_m['pct_above_3R'] > MAX_PCT_ABOVE_3R: return False, f">3R={train_m['pct_above_3R']:.1f}%"
    if full_m['m_neg'] > MAX_NEG_MONTHS: return False, f"m_neg={full_m['m_neg']}"
    if test_m is None or test_m['pf'] < MIN_TEST_PF: return False, f"test_pf={test_m['pf']:.2f}" if test_m else 'test_none'
    return True, 'OK'

def _score(m):
    """Score = PF_trimmed × WR × (1 - outlier_share). Penalise la dependance aux outliers."""
    return m['pf_trimmed'] * (m['wr'] / 100.0) * max(0.0, 1.0 - m['outlier_share'])

best_configs = {}
rejected_reasons = {}
for sn in sorted(SIG.keys()):
    if sn in OPEN_STRATS:
        print(f"  {sn:22s} --- SKIP (open strat) ---")
        continue
    if sn in DUPLICATE_STRATS:
        print(f"  {sn:22s} --- SKIP (duplicate) ---")
        continue
    sigs = SIG[sn]
    if len(sigs) < MIN_N:
        print(f"  {sn:22s} --- SKIP n<{MIN_N} ({len(sigs)} signals) ---")
        continue

    best = None; best_score = -1e9; best_reason = 'none'
    # Grille combinee: (etype_int, etype_str, params_tuple)
    all_configs = ([(0, 'TPSL', (sl, tp, 0)) for sl, tp in TPSL_GRID]
                 + [(1, 'TRAIL', (sl, act, trail)) for sl, act, trail in TRAIL_GRID]
                 + [(2, 'BE_TP', (sl, be_act, tp)) for sl, be_act, tp in BE_TP_GRID])
    for etype_int, etype_str, params in all_configs:
        p1, p2, p3 = params
        full_m, train_m, test_m = _eval_full_and_split(sigs, etype_int, p1, p2, p3)
        ok, reason = _passes(full_m, train_m, test_m)
        if not ok:
            if best is None: best_reason = reason
            continue
        s = _score(train_m)
        if s > best_score:
            best_score = s; best = (etype_str, p1, p2, p3, full_m, train_m, test_m)

    if best:
        etype_str, p1, p2, p3, fm, trm, tem = best
        best_configs[sn] = {'type': etype_str, 'p1': p1, 'p2': p2, 'p3': p3,
                            'pf': fm['pf'], 'wr': fm['wr'], 'n': fm['n'],
                            'pf_trimmed': fm['pf_trimmed'], 'outlier_share': fm['outlier_share'],
                            'pct_above_3R': fm['pct_above_3R'], 'median_R': fm['median_R'],
                            'm_pos': fm['m_pos'], 'm_neg': fm['m_neg'], 'm_total': fm['m_total'],
                            'test_pf': tem['pf'] if tem else None,
                            'split': True}
        p2_label = 'TP' if etype_str=='TPSL' else ('ACT' if etype_str=='TRAIL' else 'BE')
        p3_label = '   ' if etype_str=='TPSL' else (f'TR={p3:.2f}' if etype_str=='TRAIL' else f'TP={p3:.2f}')
        print(f"  {sn:22s} {etype_str:5s} SL={p1:.1f} {p2_label}={p2:.2f} {p3_label} "
              f"PF={fm['pf']:.2f} PFt={fm['pf_trimmed']:.2f} WR={fm['wr']:.0f}% "
              f"OS={fm['outlier_share']*100:.0f}% >3R={fm['pct_above_3R']:.1f}% "
              f"M-={fm['m_neg']}/{fm['m_total']} tPF={tem['pf']:.2f} n={fm['n']}")
    else:
        rejected_reasons[sn] = best_reason
        print(f"  {sn:22s} --- REJETE ({best_reason}) ---")

print(f"\n  {len(best_configs)}/{len(SIG)} strats avec config robuste")
print(f"\n  Top raisons de rejet:")
from collections import Counter
cnt = Counter(rejected_reasons.values())
for r, n in cnt.most_common(10):
    print(f"    {r:25s} {n}")

# ── BUILD TRADE ARRAYS WITH BEST CONFIGS ──
print("\nConstruction arrays trades...", flush=True)
strat_arrays = {}
for sn in best_configs:
    cfg = best_configs[sn]
    etype = {'TPSL': 0, 'TRAIL': 1, 'BE_TP': 2}[cfg['type']]
    is_open = sn in OPEN_STRATS
    rows = []
    for ci, di, entry, atr, date, sp in SIG[sn]:
        b, ex = sim_exit_unified(ci, entry, di, atr, etype, cfg['p1'], cfg['p2'], cfg['p3'], is_open)
        pnl = ((ex - entry) if di == 1 else (entry - ex)) - sp - SPREAD_R * cfg['p1'] * atr
        mo = f"{date.year}-{str(date.month).zfill(2)}"
        rows.append((ci, ci + b, di, pnl, cfg['p1'], atr, mo, sn))
    strat_arrays[sn] = rows

# ── EVAL COMBO (event-based) ──
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
    events = []
    for idx, (ei, xi, di, pnl_oz, sl_atr, atr, mo, _sn) in enumerate(accepted):
        events.append((ei, 0, idx))
        events.append((xi, 1, idx))
    events.sort()
    cap = capital; peak = cap; max_dd = 0; gp = 0; gl = 0; wins = 0; months = {}
    has_l = False; has_s = False; entry_caps = {}; pnl_by_entry = []
    for bar, evt, idx in events:
        if evt == 0:
            entry_caps[idx] = cap
        else:
            ei, xi, di, pnl_oz, sl_atr, atr, mo, _sn = accepted[idx]
            pnl = pnl_oz * (entry_caps[idx] * risk) / (sl_atr * atr)
            cap += pnl; pnl_by_entry.append((ei, pnl))
            if cap > peak: peak = cap
            dd = (cap - peak) / peak
            if dd < max_dd: max_dd = dd
            if pnl > 0: gp += pnl; wins += 1
            else: gl += abs(pnl)
            months[mo] = months.get(mo, 0.0) + pnl
            if di == 1: has_l = True
            else: has_s = True
    mdd = max_dd * 100; ret = (cap - capital) / capital * 100
    pnl_by_entry.sort(); pnls = [p for _, p in pnl_by_entry]
    mid = n // 2; p1 = sum(pnls[:mid]); p2 = sum(pnls[mid:])
    pm = sum(1 for v in months.values() if v > 0)
    return {'n': n, 'ret': ret, 'mdd': mdd, 'cal': ret / abs(mdd) if mdd < 0 else 0,
            'pf': gp / (gl + 0.01), 'wr': wins / n * 100, 'capital': cap,
            'split': p1 > 0 and p2 > 0, 'both': has_s and has_l, 'pm': pm, 'tm': len(months)}

# ── GREEDY COMBO BUILDER ──
valid = list(best_configs.keys())
ranked = sorted(valid, key=lambda sn: best_configs[sn]['pf'], reverse=True)

if len(ranked) == 0:
    print("\nAucune strat safe. Arret.")
    import pickle, os
    import re
    _broker = _a.account
    _sym_san = re.sub(r"[^a-z0-9]+", "_", SYMBOL).strip("_")
    _dir = f'data/{_broker}/{_sym_san}'
    os.makedirs(_dir, exist_ok=True)
    with open(f'{_dir}/optim_data.pkl', 'wb') as f:
        pickle.dump({'strat_arrays': {}, 'best_configs': {}}, f)
    print(f"Saved {_dir}/optim_data.pkl (vide)")
    sys.exit(0)

print(f"\n{'='*130}")
print(f"GREEDY COMBO BUILDER ({len(valid)} strats)")
print(f"{'='*130}")

combo = [ranked[0]]; remaining = set(ranked[1:])
r = eval_combo(combo)
if r:
    print(f"\n  Start: {combo[0]}")
    print(f"    n={r['n']} PF={r['pf']:.2f} WR={r['wr']:.0f}% DD={r['mdd']:+.1f}% Rend={r['ret']:+.0f}% M+={r['pm']}/{r['tm']}")

# Track best combos at different sizes
checkpoints = {}
for step in range(min(30, len(remaining))):
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
    cfg = best_configs[best_add]
    print(f"\n  +{best_add:22s} ({len(combo):2d}) n={r['n']:5d} PF={r['pf']:.2f} WR={r['wr']:.0f}% "
          f"DD={r['mdd']:+.1f}% Rend={r['ret']:+.0f}% M+={r['pm']}/{r['tm']} "
          f"[{cfg['type']} SL={cfg['p1']:.1f} {cfg['p2']:.2f}/{cfg['p3']:.2f}]")
    checkpoints[len(combo)] = {'combo': list(combo), 'r': dict(r)}

# ── FINAL REPORT ──
print(f"\n{'='*130}")
print(f"RAPPORT FINAL")
print(f"{'='*130}")

print(f"\n  {'Combo':>20s}  {'Trades':>7s}  {'PF':>5s}  {'WR':>5s}  {'DD 1%':>8s}  {'Rend 1%':>12s}  {'M+':>6s}")
print(f"  {'-'*20}  {'-'*7}  {'-'*5}  {'-'*5}  {'-'*8}  {'-'*12}  {'-'*6}")
for sz in sorted(checkpoints.keys()):
    r = checkpoints[sz]['r']
    print(f"  {'Greedy '+str(sz):>20s}  {r['n']:7d}  {r['pf']:5.2f}  {r['wr']:4.0f}%  {r['mdd']:+7.1f}%  {r['ret']:+11.0f}%  {r['pm']:2d}/{r['tm']}")

# Print best configs for top combos
for sz in [5, 8, 10, 12, 15]:
    if sz in checkpoints:
        print(f"\n  Composition Greedy {sz}:")
        for sn in checkpoints[sz]['combo']:
            cfg = best_configs[sn]
            if cfg['type'] == 'TPSL':
                tp_str = f"TP={cfg['p2']:.2f}"
            elif cfg['type'] == 'TRAIL':
                tp_str = f"ACT={cfg['p2']:.2f} TR={cfg['p3']:.2f}"
            else:  # BE_TP
                tp_str = f"BE={cfg['p2']:.2f} TP={cfg['p3']:.2f}"
            print(f"    {sn:22s} {cfg['type']:5s} SL={cfg['p1']:.1f} {tp_str:20s} PF={cfg['pf']:.2f} WR={cfg['wr']:.0f}%")

print(f"\n{'='*130}")

# ── SAVE TO DISK ──
import pickle
save_data = {
    'strat_arrays': strat_arrays,
    'best_configs': best_configs,
    'OPEN_STRATS': list(OPEN_STRATS),
}
import os
import re as _re
_broker = _a.account
_sym_san = _re.sub(r"[^a-z0-9]+", "_", SYMBOL).strip("_")
_dir = f'data/{_broker}/{_sym_san}'
os.makedirs(_dir, exist_ok=True)
_pkl_file = f'{_dir}/optim_data.pkl'
with open(_pkl_file, 'wb') as f:
    pickle.dump(save_data, f)
print(f"Saved {_pkl_file}")
