"""
Optimisation des exits pour les 44 strats retenues.
Teste: TRAIL, TPSL, TIME pour chaque strat.
ZERO look-ahead, check_entry_candle pour strats open.
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

# ── EXIT FUNCTIONS ──
def exit_trail(cdf, pos, entry, d, atr, sl, act, trail, check_entry=False):
    best = entry; stop = entry + sl*atr if d == 'short' else entry - sl*atr; ta = False
    start = 0 if check_entry else 1
    for j in range(start, len(cdf)-pos):
        b = cdf.iloc[pos+j]
        if j == 0:
            if d == 'long' and b['low'] <= stop: return 0, stop
            if d == 'short' and b['high'] >= stop: return 0, stop
            continue
        if d == 'long':
            if b['low'] <= stop: return j, stop
            if b['close'] > best: best = b['close']
            if not ta and (best-entry) >= act*atr: ta = True
            if ta: stop = max(stop, best - trail*atr)
            if b['close'] < stop: return j, b['close']
        else:
            if b['high'] >= stop: return j, stop
            if b['close'] < best: best = b['close']
            if not ta and (entry-best) >= act*atr: ta = True
            if ta: stop = min(stop, best + trail*atr)
            if b['close'] > stop: return j, b['close']
    return 1, entry

def exit_tpsl(cdf, pos, entry, d, atr, sl, tp, check_entry=False):
    stop = entry + sl*atr if d == 'short' else entry - sl*atr
    target = entry + tp*atr if d == 'long' else entry - tp*atr
    start = 0 if check_entry else 1
    for j in range(start, len(cdf)-pos):
        b = cdf.iloc[pos+j]
        if j == 0:
            if d == 'long' and b['low'] <= stop: return 0, stop
            if d == 'short' and b['high'] >= stop: return 0, stop
            continue
        if d == 'long':
            if b['low'] <= stop: return j, stop
            if b['close'] >= target: return j, b['close']
        else:
            if b['high'] >= stop: return j, stop
            if b['close'] <= target: return j, b['close']
    n = min(288, len(cdf)-pos-1)
    if n > 0: return n, cdf.iloc[pos+n]['close']
    return 1, entry

# ── PRECALCUL INDICATEURS ──
print("Precalcul indicateurs...", flush=True)
c = candles.copy()
c['body'] = c['close'] - c['open']
c['range'] = c['high'] - c['low']
for p in [5,8,9,13,20,21,50,100,200]:
    c[f'ema{p}'] = c['close'].ewm(span=p, adjust=False).mean()
for p in [7,9,14]:
    delta = c['close'].diff(); gain = delta.clip(lower=0); loss = (-delta).clip(lower=0)
    ag = gain.ewm(alpha=1.0/p, min_periods=p, adjust=False).mean()
    al = loss.ewm(alpha=1.0/p, min_periods=p, adjust=False).mean()
    c[f'rsi{p}'] = 100 - 100/(1+ag/(al+1e-10))
for fast,slow,sig,name in [(12,26,9,'std'),(5,13,1,'fast'),(8,17,9,'med')]:
    ef = c['close'].ewm(span=fast, adjust=False).mean()
    es = c['close'].ewm(span=slow, adjust=False).mean()
    c[f'macd_{name}'] = ef - es
    c[f'macd_{name}_sig'] = c[f'macd_{name}'].ewm(span=max(sig,2), adjust=False).mean()
    c[f'macd_{name}_hist'] = c[f'macd_{name}'] - c[f'macd_{name}_sig']
c['bb_mid'] = c['close'].rolling(20).mean()
c['bb_std'] = c['close'].rolling(20).std()
c['bb_up'] = c['bb_mid'] + 2*c['bb_std']; c['bb_lo'] = c['bb_mid'] - 2*c['bb_std']
c['bb_w'] = (c['bb_up']-c['bb_lo'])/(c['bb_mid']+1e-10)
c['bb_t_mid'] = c['close'].rolling(10).mean(); c['bb_t_std'] = c['close'].rolling(10).std()
c['bb_t_up'] = c['bb_t_mid']+1.5*c['bb_t_std']; c['bb_t_lo'] = c['bb_t_mid']-1.5*c['bb_t_std']
for kp,nm in [(5,'f'),(9,'m'),(14,'s')]:
    c[f'sk{nm}_l'] = c['low'].rolling(kp).min(); c[f'sk{nm}_h'] = c['high'].rolling(kp).max()
    c[f'sk{nm}_k'] = 100*(c['close']-c[f'sk{nm}_l'])/(c[f'sk{nm}_h']-c[f'sk{nm}_l']+1e-10)
    c[f'sk{nm}_d'] = c[f'sk{nm}_k'].rolling(3).mean()
tr = np.maximum(c['high']-c['low'], np.maximum(abs(c['high']-c['close'].shift(1)), abs(c['low']-c['close'].shift(1))))
for p,nm in [(14,'s'),(7,'f')]:
    pdm = c['high'].diff().clip(lower=0); mdm = (-c['low'].diff()).clip(lower=0)
    mask = pdm > mdm; pdm = pdm.where(mask,0); mdm = mdm.where(~mask,0)
    atr_p = tr.ewm(span=p, adjust=False).mean()
    pdi = 100*pdm.ewm(span=p, adjust=False).mean()/(atr_p+1e-10)
    mdi = 100*mdm.ewm(span=p, adjust=False).mean()/(atr_p+1e-10)
    dx = 100*abs(pdi-mdi)/(pdi+mdi+1e-10)
    c[f'adx_{nm}'] = dx.ewm(span=p, adjust=False).mean()
    c[f'pdi_{nm}'] = pdi; c[f'mdi_{nm}'] = mdi
for p in [10,20,50]:
    c[f'dc{p}_h'] = c['high'].rolling(p).max(); c[f'dc{p}_l'] = c['low'].rolling(p).min()
c['kc_mid'] = c['ema20']; c['kc_atr'] = tr.ewm(span=14,adjust=False).mean()
c['kc_up'] = c['kc_mid']+1.5*c['kc_atr']; c['kc_lo'] = c['kc_mid']-1.5*c['kc_atr']
c['kc2_up'] = c['kc_mid']+2.0*c['kc_atr']; c['kc2_lo'] = c['kc_mid']-2.0*c['kc_atr']
# HMA
def wma(s,n):
    w = np.arange(1,n+1); return s.rolling(n).apply(lambda x: np.dot(x,w)/w.sum(), raw=True)
c['hma9'] = wma(2*wma(c['close'],4)-wma(c['close'],9),3)
c['hma21'] = wma(2*wma(c['close'],10)-wma(c['close'],21),4)
# Williams %R, CCI, Momentum
for p in [7,14]:
    hh = c['high'].rolling(p).max(); ll = c['low'].rolling(p).min()
    c[f'wr{p}'] = -100*(hh-c['close'])/(hh-ll+1e-10)
for p in [14,20]:
    tp = (c['high']+c['low']+c['close'])/3; sm = tp.rolling(p).mean()
    mad = tp.rolling(p).apply(lambda x: np.mean(np.abs(x-np.mean(x))), raw=True)
    c[f'cci{p}'] = (tp-sm)/(0.015*mad+1e-10)
for p in [5,10,14]:
    c[f'mom{p}'] = c['close']/c['close'].shift(p)*100 - 100
# Ichimoku
c['i_t'] = (c['high'].rolling(6).max()+c['low'].rolling(6).min())/2
c['i_k'] = (c['high'].rolling(13).max()+c['low'].rolling(13).min())/2
c['i_sa'] = ((c['i_t']+c['i_k'])/2).shift(13)
c['i_sb'] = ((c['high'].rolling(26).max()+c['low'].rolling(26).min())/2).shift(13)
c['bb_in_kc'] = (c['bb_up']<c['kc_up'])&(c['bb_lo']>c['kc_lo'])
c['ttm_m'] = c['close']-c['close'].rolling(20).mean()

# ── COLLECTE DES ENTREES ──
print("Collecte des entrees pour 44 strats...", flush=True)
OPEN_STRATS = {'TOK_FADE','TOK_PREVEXT','LON_GAP','LON_BIGGAP','LON_KZ','LON_TOKEND','LON_PREV','NY_GAP','NY_LONEND','NY_LONMOM','NY_DAYMOM'}
entries = {}  # {strat: [(ci, entry, dir, date, atr), ...]}

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

    def reg(sn, d, e):
        entries.setdefault(sn,[]).append((ci, e, d, today, atr))

    # ── PRICE ACTION (from strats.py detect_all) ──
    from strats import detect_all
    def add_pa(sn, d, e):
        reg(sn, d, e)
    detect_all(c, ci, row, ct, today, hour, atr, trig, tv, tok, lon, prev_day_data, add_pa, prev2_day_data)

    # ── INDICATORS (all "close" strats) ──
    # EMA crosses
    for fast,slow,nm in [(9,21,'921'),(5,13,'513'),(8,21,'821')]:
        sn = f'ALL_EMA_{nm}'
        if sn not in trig:
            ef,es = f'ema{fast}',f'ema{slow}'
            if pd.notna(row[ef]) and pd.notna(prev[ef]):
                if prev[ef]<prev[es] and row[ef]>row[es]: reg(sn,'long',row['close']); trig[sn]=True
                elif prev[ef]>prev[es] and row[ef]<row[es]: reg(sn,'short',row['close']); trig[sn]=True
    # MACD crosses
    for nm in ['std','fast','med']:
        sn = f'ALL_MACD_{nm.upper()}_SIG'
        mc,ms = f'macd_{nm}',f'macd_{nm}_sig'
        if sn not in trig and pd.notna(row[mc]):
            if prev[mc]<prev[ms] and row[mc]>row[ms]: reg(sn,'long',row['close']); trig[sn]=True
            elif prev[mc]>prev[ms] and row[mc]<row[ms]: reg(sn,'short',row['close']); trig[sn]=True
        sn2 = f'ALL_MACD_{nm.upper()}_ZERO'
        if sn2 not in trig and pd.notna(row[mc]):
            if prev[mc]<0 and row[mc]>=0: reg(sn2,'long',row['close']); trig[sn2]=True
            elif prev[mc]>0 and row[mc]<=0: reg(sn2,'short',row['close']); trig[sn2]=True
    # RSI
    sn = 'ALL_RSI_50'
    if sn not in trig and pd.notna(row['rsi14']):
        if prev['rsi14']<50 and row['rsi14']>=50: reg(sn,'long',row['close']); trig[sn]=True
        elif prev['rsi14']>50 and row['rsi14']<=50: reg(sn,'short',row['close']); trig[sn]=True
    # Donchian
    for p in [10,50]:
        sn = f'ALL_DC{p}'
        if sn not in trig and pd.notna(prev.get(f'dc{p}_h')):
            if row['close']>prev[f'dc{p}_h']: reg(sn,'long',row['close']); trig[sn]=True
            elif row['close']<prev[f'dc{p}_l']: reg(sn,'short',row['close']); trig[sn]=True
    # KC breakout
    sn = 'ALL_KC_BRK'
    if sn not in trig and pd.notna(row['kc_up']):
        if row['close']>row['kc_up'] and prev['close']<=prev['kc_up']: reg(sn,'long',row['close']); trig[sn]=True
        elif row['close']<row['kc_lo'] and prev['close']>=prev['kc_lo']: reg(sn,'short',row['close']); trig[sn]=True
    # MACD+ADX
    sn = 'ALL_MACD_ADX'
    if sn not in trig and pd.notna(row['macd_std']) and pd.notna(row['adx_s']):
        if row['adx_s']>25:
            if prev['macd_std']<prev['macd_std_sig'] and row['macd_std']>row['macd_std_sig']: reg(sn,'long',row['close']); trig[sn]=True
            elif prev['macd_std']>prev['macd_std_sig'] and row['macd_std']<row['macd_std_sig']: reg(sn,'short',row['close']); trig[sn]=True
    # ADX fast
    sn = 'ALL_ADX_FAST'
    if sn not in trig and pd.notna(row['adx_f']) and pd.notna(row['ema21']):
        if row['adx_f']>25 and row['pdi_f']>row['mdi_f'] and row['close']>row['ema21'] and not(prev['pdi_f']>prev['mdi_f']):
            reg(sn,'long',row['close']); trig[sn]=True
        elif row['adx_f']>25 and row['mdi_f']>row['pdi_f'] and row['close']<row['ema21'] and not(prev['mdi_f']>prev['pdi_f']):
            reg(sn,'short',row['close']); trig[sn]=True
    # RSI divergence
    sn = 'ALL_RSI_DIV'
    if sn not in trig and ci>=10 and pd.notna(row['rsi14']):
        l10 = c.iloc[ci-9:ci+1]
        if row['low']<l10.iloc[:-1]['low'].min() and row['rsi14']>l10.iloc[:-1]['rsi14'].min() and row['close']>row['open']:
            reg(sn,'long',row['close']); trig[sn]=True
        if row['high']>l10.iloc[:-1]['high'].max() and row['rsi14']<l10.iloc[:-1]['rsi14'].max() and row['close']<row['open']:
            reg(sn,'short',row['close']); trig[sn]=True
    # Ichimoku TK
    sn = 'ALL_ICHI_TK'
    if sn not in trig and pd.notna(row['i_t']):
        if prev['i_t']<prev['i_k'] and row['i_t']>row['i_k']:
            if pd.notna(row['i_sa']) and row['close']>max(row['i_sa'],row['i_sb']): reg(sn,'long',row['close']); trig[sn]=True
        elif prev['i_t']>prev['i_k'] and row['i_t']<row['i_k']:
            if pd.notna(row['i_sa']) and row['close']<min(row['i_sa'],row['i_sb']): reg(sn,'short',row['close']); trig[sn]=True
    # BB tight
    sn = 'ALL_BB_TIGHT'
    if sn not in trig and pd.notna(row['bb_t_up']):
        if row['close']>row['bb_t_up'] and prev['close']<=prev['bb_t_up']: reg(sn,'long',row['close']); trig[sn]=True
        elif row['close']<row['bb_t_lo'] and prev['close']>=prev['bb_t_lo']: reg(sn,'short',row['close']); trig[sn]=True
    # MACD_RSI combo
    sn = 'ALL_MACD_RSI'
    if sn not in trig and pd.notna(row['macd_med']) and pd.notna(row['rsi14']):
        if prev['macd_med']<prev['macd_med_sig'] and row['macd_med']>row['macd_med_sig'] and row['rsi14']>50:
            reg(sn,'long',row['close']); trig[sn]=True
        elif prev['macd_med']>prev['macd_med_sig'] and row['macd_med']<row['macd_med_sig'] and row['rsi14']<50:
            reg(sn,'short',row['close']); trig[sn]=True
    # Williams %R
    for p,nm in [(7,'7'),(14,'14')]:
        sn = f'ALL_WILLR_{nm}'
        if sn not in trig and pd.notna(row[f'wr{p}']):
            if prev[f'wr{p}']<-80 and row[f'wr{p}']>=-80: reg(sn,'long',row['close']); trig[sn]=True
            elif prev[f'wr{p}']>-20 and row[f'wr{p}']<=-20: reg(sn,'short',row['close']); trig[sn]=True
    # Momentum
    for p,nm in [(10,'10'),(14,'14')]:
        sn = f'ALL_MOM_{nm}'
        if sn not in trig and pd.notna(row[f'mom{p}']):
            if prev[f'mom{p}']<0 and row[f'mom{p}']>=0: reg(sn,'long',row['close']); trig[sn]=True
            elif prev[f'mom{p}']>0 and row[f'mom{p}']<=0: reg(sn,'short',row['close']); trig[sn]=True
    # HMA cross
    sn = 'ALL_HMA_CROSS'
    if sn not in trig and pd.notna(row['hma9']) and pd.notna(row['hma21']):
        if prev['hma9']<prev['hma21'] and row['hma9']>row['hma21']: reg(sn,'long',row['close']); trig[sn]=True
        elif prev['hma9']>prev['hma21'] and row['hma9']<row['hma21']: reg(sn,'short',row['close']); trig[sn]=True
    sn = 'ALL_HMA_DIR'
    if sn not in trig and ci>=3 and pd.notna(row['hma9']):
        h1,h2,h3 = c.iloc[ci-2]['hma9'],c.iloc[ci-1]['hma9'],row['hma9']
        if pd.notna(h1):
            if h1>h2 and h3>h2: reg(sn,'long',row['close']); trig[sn]=True
            elif h1<h2 and h3<h2: reg(sn,'short',row['close']); trig[sn]=True
    # DC10+EMA
    sn = 'ALL_DC10_EMA'
    if sn not in trig and pd.notna(prev.get('dc10_h')) and pd.notna(row['ema21']):
        if row['close']>prev['dc10_h'] and row['close']>row['ema21']: reg(sn,'long',row['close']); trig[sn]=True
        elif row['close']<prev['dc10_l'] and row['close']<row['ema21']: reg(sn,'short',row['close']); trig[sn]=True
    # EMA trend pullback
    sn = 'ALL_EMA_TREND_PB'
    if sn not in trig and pd.notna(row['ema50']) and pd.notna(row['ema200']):
        if row['ema50']>row['ema200'] and prev['low']<=prev['ema50'] and row['close']>row['ema50'] and row['close']>row['open']:
            reg(sn,'long',row['close']); trig[sn]=True
        elif row['ema50']<row['ema200'] and prev['high']>=prev['ema50'] and row['close']<row['ema50'] and row['close']<row['open']:
            reg(sn,'short',row['close']); trig[sn]=True
    # CCI zero
    for p,nm in [(14,'14'),(20,'20')]:
        sn = f'ALL_CCI_{nm}_ZERO'
        if sn not in trig and pd.notna(row[f'cci{p}']):
            if prev[f'cci{p}']<0 and row[f'cci{p}']>=0: reg(sn,'long',row['close']); trig[sn]=True
            elif prev[f'cci{p}']>0 and row[f'cci{p}']<=0: reg(sn,'short',row['close']); trig[sn]=True
    # Session-specific
    if 0.0<=hour<6.0:
        sn = 'TOK_MACD_MED'
        if sn not in trig and pd.notna(row['macd_med']):
            if prev['macd_med']<prev['macd_med_sig'] and row['macd_med']>row['macd_med_sig']: reg(sn,'long',row['close']); trig[sn]=True
            elif prev['macd_med']>prev['macd_med_sig'] and row['macd_med']<row['macd_med_sig']: reg(sn,'short',row['close']); trig[sn]=True
        sn = 'TOK_WILLR'
        if sn not in trig and pd.notna(row['wr14']):
            if prev['wr14']<-80 and row['wr14']>=-80: reg(sn,'long',row['close']); trig[sn]=True
            elif prev['wr14']>-20 and row['wr14']<=-20: reg(sn,'short',row['close']); trig[sn]=True
    if 8.0<=hour<14.5:
        sn = 'LON_DC10'
        if sn not in trig and pd.notna(prev.get('dc10_h')):
            if row['close']>prev['dc10_h']: reg(sn,'long',row['close']); trig[sn]=True
            elif row['close']<prev['dc10_l']: reg(sn,'short',row['close']); trig[sn]=True
        sn = 'LON_DC10_MOM'
        if sn not in trig and pd.notna(prev.get('dc10_h')) and pd.notna(row['mom5']):
            if row['close']>prev['dc10_h'] and row['mom5']>0: reg(sn,'long',row['close']); trig[sn]=True
            elif row['close']<prev['dc10_l'] and row['mom5']<0: reg(sn,'short',row['close']); trig[sn]=True
    if 14.5<=hour<21.0:
        sn = 'NY_HMA_CROSS'
        if sn not in trig and pd.notna(row['hma9']) and pd.notna(row['hma21']):
            if prev['hma9']<prev['hma21'] and row['hma9']>row['hma21']: reg(sn,'long',row['close']); trig[sn]=True
            elif prev['hma9']>prev['hma21'] and row['hma9']<row['hma21']: reg(sn,'short',row['close']); trig[sn]=True

print(f"Done. {len(entries)} strats collectees.", flush=True)

# ── GRILLE DE CONFIGS ──
SL_VALS = [0.5, 0.75, 1.0, 1.5, 2.0]
ACT_VALS = [0.3, 0.5, 0.75, 1.0]
TRAIL_VALS = [0.3, 0.5, 0.75, 1.0]
TP_VALS = [0.5, 1.0, 1.5, 2.0, 3.0]

configs_trail = []
for sl in SL_VALS:
    for act in ACT_VALS:
        for tr in TRAIL_VALS:
            if tr > sl: continue
            configs_trail.append(('TRAIL', sl, act, tr))
configs_tpsl = []
for sl in SL_VALS:
    for tp in TP_VALS:
        configs_tpsl.append(('TPSL', sl, tp))

print(f"  {len(configs_trail)} configs TRAIL, {len(configs_tpsl)} configs TPSL", flush=True)

# ── EVALUATION ──
def eval_config(sn, elist, cfg_type, p1, p2, p3=0):
    pnls = []
    is_open = sn in OPEN_STRATS
    for ci, entry, d, day, atr in elist:
        if cfg_type == 'TRAIL':
            _, ex = exit_trail(c, ci, entry, d, atr, p1, p2, p3, check_entry=is_open)
        else:
            _, ex = exit_tpsl(c, ci, entry, d, atr, p1, p2, check_entry=is_open)
        pnl = (ex-entry) if d=='long' else (entry-ex)
        pnls.append(pnl - get_sp(day))
    if len(pnls) < 20: return None
    n = len(pnls)
    gp = sum(p for p in pnls if p>0); gl = abs(sum(p for p in pnls if p<0))+0.001
    mid = n//2; f1 = np.mean(pnls[:mid]); f2 = np.mean(pnls[mid:])
    return {'pf': gp/gl, 'n': n, 'avg': np.mean(pnls), 'split': f1>0 and f2>0}

print("\nOptimisation des exits...", flush=True)
print("="*130)
print(f"{'Strat':>18s} | {'Best Type':>8s} {'SL':>5s} {'P2':>5s} {'P3':>5s} {'PF':>6s} {'n':>5s} {'Split':>5s} | {'Cur PF':>6s} {'Cur Split':>9s} | {'Delta':>6s}")
print("-"*130)

for sn in sorted(entries.keys()):
    elist = entries[sn]
    if len(elist) < 20: continue

    # Current config (TRAIL SL=1.0 ACT=0.5 TRAIL=0.75)
    cur = eval_config(sn, elist, 'TRAIL', 1.0, 0.5, 0.75)
    if cur is None: continue

    # Test all configs
    best = None; best_cfg = None
    for sl, act, tr in [(s,a,t) for s in SL_VALS for a in ACT_VALS for t in TRAIL_VALS if t<=s]:
        r = eval_config(sn, elist, 'TRAIL', sl, act, tr)
        if r and r['pf'] > 1.0 and r['split']:
            if best is None or r['pf'] > best['pf']:
                best = r; best_cfg = ('TRAIL', sl, act, tr)
    for sl in SL_VALS:
        for tp in TP_VALS:
            r = eval_config(sn, elist, 'TPSL', sl, tp)
            if r and r['pf'] > 1.0 and r['split']:
                if best is None or r['pf'] > best['pf']:
                    best = r; best_cfg = ('TPSL', sl, tp, 0)

    if best is None: best = cur; best_cfg = ('TRAIL', 1.0, 0.5, 0.75)
    typ, p1, p2, p3 = best_cfg
    cur_sp = 'OK' if cur['split'] else '!!'
    best_sp = 'OK' if best['split'] else '!!'
    delta = best['pf'] - cur['pf']
    marker = ' <<<' if delta > 0.1 else ''
    print(f"{sn:>18s} | {typ:>8s} {p1:5.2f} {p2:5.2f} {p3:5.2f} {best['pf']:6.2f} {best['n']:5d} {best_sp:>5s} | {cur['pf']:6.2f} {cur_sp:>9s} | {delta:+5.2f}{marker}")

print()
