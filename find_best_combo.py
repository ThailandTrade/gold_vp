"""
Trouve le meilleur combo parmi les 47 strats (price action + indicators).
Exits par strat (strat_exits.py). Check entry candle.
"""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
from itertools import combinations
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

# ── PRECALCUL INDICATEURS ──
print("Precalcul...", flush=True)
c = candles.copy()
c['body'] = c['close'] - c['open']; c['range'] = c['high'] - c['low']
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
c['bb_t_mid'] = c['close'].rolling(10).mean(); c['bb_t_std'] = c['close'].rolling(10).std()
c['bb_t_up'] = c['bb_t_mid']+1.5*c['bb_t_std']; c['bb_t_lo'] = c['bb_t_mid']-1.5*c['bb_t_std']
tr = np.maximum(c['high']-c['low'], np.maximum(abs(c['high']-c['close'].shift(1)), abs(c['low']-c['close'].shift(1))))
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
c['kc_up'] = c['ema20']+1.5*tr.ewm(span=14,adjust=False).mean(); c['kc_lo'] = c['ema20']-1.5*tr.ewm(span=14,adjust=False).mean()
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

# ── COLLECTE ──
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

    # Indicators (all close strats)
    for fast,slow,nm in [(9,21,'921'),(5,13,'513'),(8,21,'821')]:
        sn = f'ALL_EMA_{nm}'
        if sn not in trig and pd.notna(row[f'ema{fast}']) and pd.notna(prev[f'ema{fast}']):
            if prev[f'ema{fast}']<prev[f'ema{slow}'] and row[f'ema{fast}']>row[f'ema{slow}']: add(sn,'long',row['close']); trig[sn]=True
            elif prev[f'ema{fast}']>prev[f'ema{slow}'] and row[f'ema{fast}']<row[f'ema{slow}']: add(sn,'short',row['close']); trig[sn]=True
    for nm in ['std','fast','med']:
        mc,ms = f'macd_{nm}',f'macd_{nm}_sig'
        sn = f'ALL_MACD_{nm.upper()}_SIG'
        if sn not in trig and pd.notna(row[mc]):
            if prev[mc]<prev[ms] and row[mc]>row[ms]: add(sn,'long',row['close']); trig[sn]=True
            elif prev[mc]>prev[ms] and row[mc]<row[ms]: add(sn,'short',row['close']); trig[sn]=True
    sn = 'ALL_RSI_50'
    if sn not in trig and pd.notna(row['rsi14']):
        if prev['rsi14']<50 and row['rsi14']>=50: add(sn,'long',row['close']); trig[sn]=True
        elif prev['rsi14']>50 and row['rsi14']<=50: add(sn,'short',row['close']); trig[sn]=True
    for p in [10,50]:
        sn = f'ALL_DC{p}'
        if sn not in trig and pd.notna(prev.get(f'dc{p}_h')):
            if row['close']>prev[f'dc{p}_h']: add(sn,'long',row['close']); trig[sn]=True
            elif row['close']<prev[f'dc{p}_l']: add(sn,'short',row['close']); trig[sn]=True
    sn = 'ALL_KC_BRK'
    if sn not in trig and pd.notna(row['kc_up']):
        if row['close']>row['kc_up'] and prev['close']<=prev['kc_up']: add(sn,'long',row['close']); trig[sn]=True
        elif row['close']<row['kc_lo'] and prev['close']>=prev['kc_lo']: add(sn,'short',row['close']); trig[sn]=True
    sn = 'ALL_MACD_ADX'
    if sn not in trig and pd.notna(row['macd_std']) and pd.notna(row['adx_s']):
        if row['adx_s']>25 and prev['macd_std']<prev['macd_std_sig'] and row['macd_std']>row['macd_std_sig']: add(sn,'long',row['close']); trig[sn]=True
        elif row['adx_s']>25 and prev['macd_std']>prev['macd_std_sig'] and row['macd_std']<row['macd_std_sig']: add(sn,'short',row['close']); trig[sn]=True
    sn = 'ALL_ADX_FAST'
    if sn not in trig and pd.notna(row['adx_f']) and pd.notna(row['ema21']):
        if row['adx_f']>25 and row['pdi_f']>row['mdi_f'] and row['close']>row['ema21'] and not(prev['pdi_f']>prev['mdi_f']): add(sn,'long',row['close']); trig[sn]=True
        elif row['adx_f']>25 and row['mdi_f']>row['pdi_f'] and row['close']<row['ema21'] and not(prev['mdi_f']>prev['pdi_f']): add(sn,'short',row['close']); trig[sn]=True
    sn = 'ALL_RSI_DIV'
    if sn not in trig and ci>=10 and pd.notna(row['rsi14']):
        l10 = c.iloc[ci-9:ci+1]
        if row['low']<l10.iloc[:-1]['low'].min() and row['rsi14']>l10.iloc[:-1]['rsi14'].min() and row['close']>row['open']: add(sn,'long',row['close']); trig[sn]=True
        if row['high']>l10.iloc[:-1]['high'].max() and row['rsi14']<l10.iloc[:-1]['rsi14'].max() and row['close']<row['open']: add(sn,'short',row['close']); trig[sn]=True
    sn = 'ALL_ICHI_TK'
    if sn not in trig and pd.notna(row['i_t']):
        if prev['i_t']<prev['i_k'] and row['i_t']>row['i_k'] and pd.notna(row['i_sa']) and row['close']>max(row['i_sa'],row['i_sb']): add(sn,'long',row['close']); trig[sn]=True
        elif prev['i_t']>prev['i_k'] and row['i_t']<row['i_k'] and pd.notna(row['i_sa']) and row['close']<min(row['i_sa'],row['i_sb']): add(sn,'short',row['close']); trig[sn]=True
    sn = 'ALL_BB_TIGHT'
    if sn not in trig and pd.notna(row['bb_t_up']):
        if row['close']>row['bb_t_up'] and prev['close']<=prev['bb_t_up']: add(sn,'long',row['close']); trig[sn]=True
        elif row['close']<row['bb_t_lo'] and prev['close']>=prev['bb_t_lo']: add(sn,'short',row['close']); trig[sn]=True
    sn = 'ALL_MACD_RSI'
    if sn not in trig and pd.notna(row['macd_med']) and pd.notna(row['rsi14']):
        if prev['macd_med']<prev['macd_med_sig'] and row['macd_med']>row['macd_med_sig'] and row['rsi14']>50: add(sn,'long',row['close']); trig[sn]=True
        elif prev['macd_med']>prev['macd_med_sig'] and row['macd_med']<row['macd_med_sig'] and row['rsi14']<50: add(sn,'short',row['close']); trig[sn]=True
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
    sn = 'ALL_HMA_DIR'
    if sn not in trig and ci>=3 and pd.notna(row['hma9']):
        h1,h2,h3 = c.iloc[ci-2]['hma9'],c.iloc[ci-1]['hma9'],row['hma9']
        if pd.notna(h1):
            if h1>h2 and h3>h2: add(sn,'long',row['close']); trig[sn]=True
            elif h1<h2 and h3<h2: add(sn,'short',row['close']); trig[sn]=True
    sn = 'ALL_DC10_EMA'
    if sn not in trig and pd.notna(prev.get('dc10_h')) and pd.notna(row['ema21']):
        if row['close']>prev['dc10_h'] and row['close']>row['ema21']: add(sn,'long',row['close']); trig[sn]=True
        elif row['close']<prev['dc10_l'] and row['close']<row['ema21']: add(sn,'short',row['close']); trig[sn]=True
    sn = 'ALL_EMA_TREND_PB'
    if sn not in trig and pd.notna(row['ema50']) and pd.notna(row['ema200']):
        if row['ema50']>row['ema200'] and prev['low']<=prev['ema50'] and row['close']>row['ema50'] and row['close']>row['open']: add(sn,'long',row['close']); trig[sn]=True
        elif row['ema50']<row['ema200'] and prev['high']>=prev['ema50'] and row['close']<row['ema50'] and row['close']<row['open']: add(sn,'short',row['close']); trig[sn]=True
    for p,nm in [(14,'14'),(20,'20')]:
        sn = f'ALL_CCI_{nm}_ZERO'
        if sn not in trig and pd.notna(row[f'cci{p}']):
            if prev[f'cci{p}']<0 and row[f'cci{p}']>=0: add(sn,'long',row['close']); trig[sn]=True
            elif prev[f'cci{p}']>0 and row[f'cci{p}']<=0: add(sn,'short',row['close']); trig[sn]=True
    if 0.0<=hour<6.0:
        sn = 'TOK_MACD_MED'
        if sn not in trig and pd.notna(row['macd_med']):
            if prev['macd_med']<prev['macd_med_sig'] and row['macd_med']>row['macd_med_sig']: add(sn,'long',row['close']); trig[sn]=True
            elif prev['macd_med']>prev['macd_med_sig'] and row['macd_med']<row['macd_med_sig']: add(sn,'short',row['close']); trig[sn]=True
        sn = 'TOK_WILLR'
        if sn not in trig and pd.notna(row['wr14']):
            if prev['wr14']<-80 and row['wr14']>=-80: add(sn,'long',row['close']); trig[sn]=True
            elif prev['wr14']>-20 and row['wr14']<=-20: add(sn,'short',row['close']); trig[sn]=True
    if 8.0<=hour<14.5:
        sn = 'LON_DC10'
        if sn not in trig and pd.notna(prev.get('dc10_h')):
            if row['close']>prev['dc10_h']: add(sn,'long',row['close']); trig[sn]=True
            elif row['close']<prev['dc10_l']: add(sn,'short',row['close']); trig[sn]=True
        sn = 'LON_DC10_MOM'
        if sn not in trig and pd.notna(prev.get('dc10_h')) and pd.notna(row.get('mom5')):
            if row['close']>prev['dc10_h'] and row['mom5']>0: add(sn,'long',row['close']); trig[sn]=True
            elif row['close']<prev['dc10_l'] and row['mom5']<0: add(sn,'short',row['close']); trig[sn]=True
    if 14.5<=hour<21.0:
        sn = 'NY_HMA_CROSS'
        if sn not in trig and pd.notna(row['hma9']) and pd.notna(row['hma21']):
            if prev['hma9']<prev['hma21'] and row['hma9']>row['hma21']: add(sn,'long',row['close']); trig[sn]=True
            elif prev['hma9']>prev['hma21'] and row['hma9']<row['hma21']: add(sn,'short',row['close']); trig[sn]=True

print(f"Done. {len(S)} strats.", flush=True)

# ── STATS INDIVIDUELLES ──
print("\n" + "="*130)
print("STATS INDIVIDUELLES (exits par strat)")
print("="*130)
print(f"{'Strat':>22s} {'Exit':>5s} {'n':>5s} {'WR':>5s} {'PF':>6s} {'Avg':>8s} {'Split':>6s} {'T':>3s}")
print("-"*100)
valid = []
for sn in sorted(S.keys()):
    t = S[sn]; n = len(t)
    if n < 20: continue
    pnls = [x['pnl_oz'] for x in t]
    gp = sum(p for p in pnls if p>0); gl = abs(sum(p for p in pnls if p<0))+0.001
    pf = gp/gl; wr = sum(1 for p in pnls if p>0)/n*100
    mid = n//2; f1 = np.mean(pnls[:mid]); f2 = np.mean(pnls[mid:])
    split = f1>0 and f2>0; split_str = 'OK' if split else '!!'
    t1 = sum(pnls[:n//3]); t2 = sum(pnls[n//3:2*n//3]); t3 = sum(pnls[2*n//3:])
    tiers = sum(1 for x in [t1,t2,t3] if x>0)
    etype = STRAT_EXITS.get(sn, DEFAULT_EXIT)[0]
    marker = ' <--' if pf > 1.2 and split else ''
    print(f"{sn:>22s} {etype:>5s} {n:5d} {wr:4.0f}% {pf:6.2f} {np.mean(pnls):+8.3f} {split_str:>6s} {tiers}/3{marker}")
    if pf > 1.2 and split:
        valid.append(sn)

print(f"\n  {len(valid)} strats retenues (PF>1.2 + split OK)")

# ── COMBOS ──
if len(valid) < 3:
    print("Pas assez de strats pour les combos"); sys.exit()

strat_arrays = {}
for sn in valid:
    rows = []
    for t in S[sn]:
        di = 1 if t['dir']=='long' else -1
        mo = str(t['date'].year)+"-"+str(t['date'].month).zfill(2)
        rows.append((t['ei'], t['xi'], di, t['pnl_oz'], t['sl_atr'], t['atr'], mo, sn))
    strat_arrays[sn] = rows

def eval_combo(combo, capital=1000.0, risk=0.01):
    combined = []
    for sn in combo:
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
        if di == 1: has_l = True
        else: has_s = True
    mdd = max_dd * 100; ret = (cap - capital) / capital * 100
    mid = n // 2; p1 = sum(pnls[:mid]); p2 = sum(pnls[mid:])
    t1 = sum(pnls[:n//3]); t2 = sum(pnls[n//3:2*n//3]); t3 = sum(pnls[2*n//3:])
    pm = sum(1 for v in months.values() if v > 0)
    return {
        'combo': '+'.join(combo), 'ns': len(combo), 'n': n,
        'ret': ret, 'mdd': mdd, 'cal': ret / abs(mdd) if mdd < 0 else 0,
        'pf': gp / (gl + 0.01), 'wr': wins / n * 100, 'capital': cap,
        'split': p1 > 0 and p2 > 0,
        'tiers': sum(1 for x in [t1, t2, t3] if x > 0),
        'both': has_s and has_l, 'pm': pm, 'tm': len(months),
    }

print(f"\n{'='*130}")
print(f"MEILLEUR COMBO PAR TAILLE (Calmar, split OK, L+S)")
print(f"{'='*130}")
for sz in range(3, min(len(valid)+1, 15)):
    best = None; count = 0
    for combo in combinations(valid, sz):
        count += 1
        if count > 50000: break  # limiter pour les grandes tailles
        r = eval_combo(combo)
        if r and r['split'] and r['tiers']>=2 and r['both']:
            if best is None or r['cal'] > best['cal']:
                best = r
    if best:
        print(f"  {sz:2d} strats: {best['combo'][:80]:80s} n={best['n']:5.0f} PF={best['pf']:.2f} WR={best['wr']:.0f}% DD={best['mdd']:+.1f}% Cal={best['cal']:.1f} Rend={best['ret']:+.0f}% M+={best['pm']:.0f}/{best['tm']:.0f}")
    else:
        if sz <= 5: print(f"  {sz:2d} strats: aucun combo valide")

print()
