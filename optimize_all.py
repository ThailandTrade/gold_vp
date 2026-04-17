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

print(f"Done. {len(SIG)} strats, {sum(len(v) for v in SIG.values())} signaux total.", flush=True)

# ── EXIT OPTIMIZATION GRID ──
print("\nOptimisation exits...", flush=True)

# Grid configs (+ TP=2.5 pour completer RR=1 sur toutes les bornes SL)
TP_VALS = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0]
SL_VALS = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
TPSL_GRID = [(sl, tp) for sl in SL_VALS for tp in TP_VALS]
TRAIL_GRID = [(sl, act, trail) for sl in [0.5, 1.0, 1.5, 2.0, 3.0]
              for act in [0.3, 0.5, 0.75, 1.0] for trail in [0.3, 0.5, 0.75, 1.0]]
# BE_TP_GRID retire definitivement cleanup-v2

# Walk-forward OOS parameters
IS_MONTHS = 6
OOS_MONTHS = 1
STEP = 1
MIN_N_TRADES = 30
MIN_MEDIAN_PF_OOS = 1.20
MIN_PCT_PROFITABLE_OOS = 0.70
MIN_PF_RECENT = 1.20  # la config finale doit tenir sur 6 ET 12 derniers mois
RECENT_SHORT = 6  # mois
RECENT_LONG = 12  # mois

# Exits structurels: SL au swing low/high des N bars, TP = distance * RR
STRUCT_N = [5, 10, 20]
STRUCT_RR = [1.0]  # RR=1 anti-overfit
STRUCT_SL_BUFFER = 0.1  # ATR au-dela du swing (anti-wick)
STRUCT_SL_MIN = 0.3    # sl_atr min (sinon trop serre)
STRUCT_SL_MAX = 3.0    # sl_atr max (sinon trop lache)

def eval_config(signals, etype, p1, p2, p3):
    """Evaluate one exit config on all signals for a strat."""
    pnls = []
    for ci, di, entry, atr, date, sp in signals:
        is_open = False  # will be set per-strat later
        d_str = 'long' if di == 1 else 'short'
        b, ex = sim_exit_unified(ci, entry, di, atr, etype, p1, p2, p3, is_open)
        pnl = (ex - entry) if di == 1 else (entry - ex)
        pnls.append(pnl - sp - SPREAD_R * p1 * atr)
    n = len(pnls)
    if n < 10: return None
    gp = sum(p for p in pnls if p > 0); gl = abs(sum(p for p in pnls if p < 0)) + 0.001
    pf = gp / gl; wr = sum(1 for p in pnls if p > 0) / n * 100
    mid = n // 2; f1 = np.mean(pnls[:mid]); f2 = np.mean(pnls[mid:])
    split = f1 > 0 and f2 > 0
    avg_pnl = np.mean(pnls)
    return {'pf': pf, 'wr': wr, 'n': n, 'split': split, 'avg': avg_pnl, 'pnls': pnls}

# ── WALK-FORWARD OOS VALIDATION ──
# Construire les mois presents dans les donnees
all_months = sorted(set((d.year, d.month) for strat_sigs in SIG.values() for (_, _, _, _, d, _) in strat_sigs))
print(f"\nData span: {len(all_months)} mois ({all_months[0]} -> {all_months[-1]})")

# Fenetres walk-forward: IS 10 mois + OOS 1 mois, step 1 mois
wf_windows = []
for i in range(0, len(all_months) - IS_MONTHS - OOS_MONTHS + 1, STEP):
    is_set = set(all_months[i : i + IS_MONTHS])
    oos_set = set(all_months[i + IS_MONTHS : i + IS_MONTHS + OOS_MONTHS])
    wf_windows.append((is_set, oos_set))
print(f"Walk-forward: {len(wf_windows)} fenetres (IS={IS_MONTHS}m, OOS={OOS_MONTHS}m, step={STEP}m)")
print(f"Criteres: n_total >= {MIN_N_TRADES}, median(PF_OOS) >= {MIN_MEDIAN_PF_OOS}, pct profitable >= {MIN_PCT_PROFITABLE_OOS:.0%}")

# Sets de mois pour PF recent (6 et 12 derniers mois)
recent_6_set = set(all_months[-RECENT_SHORT:]) if len(all_months) >= RECENT_SHORT else set(all_months)
recent_12_set = set(all_months[-RECENT_LONG:]) if len(all_months) >= RECENT_LONG else set(all_months)
print(f"Validation periodes: PF {RECENT_SHORT}m >= {MIN_PF_RECENT} ET PF {RECENT_LONG}m >= {MIN_PF_RECENT}\n")

def _pnl_from_signals(sigs, etype, p1, p2, p3, is_open):
    """Calcule les pnls (avec dates) pour une config donnee. Retourne [(pnl, date, sl_atr), ...]"""
    out = []
    for ci, di, entry, atr, date, sp in sigs:
        b, ex = sim_exit_unified(ci, entry, di, atr, etype, p1, p2, p3, is_open)
        pnl = ((ex - entry) if di == 1 else (entry - ex)) - sp - SPREAD_R * p1 * atr
        out.append((pnl, date, p1))
    return out

def _pnl_from_struct(sigs, N, rr):
    """STRUCT_RR: SL au swing des N dernieres bars, TP = distance * rr. sl_atr dynamique par trade."""
    out = []
    for ci, di, entry, atr, date, sp in sigs:
        if ci < N:
            continue
        # Swing sur les N bars precedentes (pas inclure la bougie du signal)
        if di == 1:
            swing = float(c.iloc[ci-N:ci]['low'].min())
            distance = entry - swing + STRUCT_SL_BUFFER * atr
        else:
            swing = float(c.iloc[ci-N:ci]['high'].max())
            distance = swing - entry + STRUCT_SL_BUFFER * atr
        if distance <= 0:
            continue
        sl_atr_dyn = distance / atr
        if sl_atr_dyn < STRUCT_SL_MIN or sl_atr_dyn > STRUCT_SL_MAX:
            continue
        tp_atr_dyn = sl_atr_dyn * rr
        b, ex = sim_exit_unified(ci, entry, di, atr, 0, sl_atr_dyn, tp_atr_dyn, 0, False)
        pnl = ((ex - entry) if di == 1 else (entry - ex)) - sp - SPREAD_R * sl_atr_dyn * atr
        out.append((pnl, date, sl_atr_dyn))
    return out

def _pf_of(pnls):
    """Calcule PF d'une liste de pnls (cap a 10 pour eviter artifacts quand gl~=0)."""
    gp = sum(p for p in pnls if p > 0)
    gl = abs(sum(p for p in pnls if p < 0))
    if gl < 0.001:
        return 10.0 if gp > 0 else 0.0
    pf = gp / gl
    return min(pf, 10.0)

def _window_pnls(pnls_dates, month_set):
    """Extrait les pnls dont la date appartient au set de mois. Accepte tuples (pnl, date, sl_atr)."""
    return [t[0] for t in pnls_dates if (t[1].year, t[1].month) in month_set]

def _is_rr1_cfg(cfg):
    """True si la config TPSL a TP=SL (RR=1)."""
    return cfg[0] == 'TPSL' and abs(cfg[1] - cfg[2]) < 0.01

def _is_struct_cfg(cfg):
    return cfg[0] == 'STRUCT'

best_configs = {}
for sn in sorted(SIG.keys()):
    if sn in OPEN_STRATS:
        print(f"  {sn:22s} --- SKIP (open strat)")
        continue
    sigs = SIG[sn]
    if len(sigs) < MIN_N_TRADES:
        print(f"  {sn:22s} --- SKIP (n={len(sigs)} < {MIN_N_TRADES})")
        continue

    # Pre-calcul: pnls pour chaque config (TPSL + TRAIL + STRUCT)
    config_pnls = {}
    for sl, tp in TPSL_GRID:
        config_pnls[('TPSL', sl, tp, 0)] = _pnl_from_signals(sigs, 0, sl, tp, 0, False)
    for sl, act, trail in TRAIL_GRID:
        config_pnls[('TRAIL', sl, act, trail)] = _pnl_from_signals(sigs, 1, sl, act, trail, False)
    for N in STRUCT_N:
        for rr in STRUCT_RR:
            config_pnls[('STRUCT', N, rr, 0)] = _pnl_from_struct(sigs, N, rr)

    # Pour chaque fenetre: trouver best config IS, mesurer PF_OOS
    pf_oos_list = []
    for (is_set, oos_set) in wf_windows:
        best_is_pf = -1; best_is_cfg = None
        for cfg, pnls_dates in config_pnls.items():
            is_pnls = _window_pnls(pnls_dates, is_set)
            if len(is_pnls) < 10:
                continue
            pf_is = _pf_of(is_pnls)
            if pf_is > best_is_pf:
                best_is_pf = pf_is; best_is_cfg = cfg
        if best_is_cfg is None:
            continue
        oos_pnls = _window_pnls(config_pnls[best_is_cfg], oos_set)
        if len(oos_pnls) < 3:
            continue
        pf_oos_list.append(_pf_of(oos_pnls))

    if len(pf_oos_list) < len(wf_windows):
        print(f"  {sn:22s} --- SKIP (WF incomplet {len(pf_oos_list)}/{len(wf_windows)})")
        continue

    # Validation walk-forward
    import statistics
    median_pf_oos = statistics.median(pf_oos_list)
    pct_profitable = sum(1 for p in pf_oos_list if p > 1.0) / len(pf_oos_list)

    if median_pf_oos < MIN_MEDIAN_PF_OOS or pct_profitable < MIN_PCT_PROFITABLE_OOS:
        print(f"  {sn:22s} FAIL WF  median={median_pf_oos:.2f}  pct={pct_profitable:.0%}  ({len(pf_oos_list)}w)")
        continue

    # Config finale: meilleure sur full period (parmi configs avec n >= MIN_N_TRADES)
    def _score_cfg(cfg, pnls_dates):
        pnls = [t[0] for t in pnls_dates]
        if len(pnls) < MIN_N_TRADES:
            return None
        pf = _pf_of(pnls); wr = sum(1 for p in pnls if p > 0) / len(pnls) * 100
        return (pf * (wr / 100), pf, wr, len(pnls))

    best_full = None; best_full_score = -1
    best_rr1 = None; best_rr1_score = -1
    for cfg, pnls_dates in config_pnls.items():
        r = _score_cfg(cfg, pnls_dates)
        if r is None: continue
        score, pf, wr, n = r
        if score > best_full_score:
            best_full_score = score; best_full = (cfg, pf, wr, n)
        if (_is_rr1_cfg(cfg) or _is_struct_cfg(cfg)) and score > best_rr1_score:
            best_rr1_score = score; best_rr1 = (cfg, pf, wr, n)

    if best_full is None:
        print(f"  {sn:22s} --- SKIP (aucune config n >= {MIN_N_TRADES})")
        continue

    (etype, p1, p2, p3), pf, wr, n = best_full

    # Double validation: PF sur 6 derniers mois ET sur 12 derniers mois
    final_pnls_dates = config_pnls[(etype, p1, p2, p3)]
    pnls_6m = _window_pnls(final_pnls_dates, recent_6_set)
    pnls_12m = _window_pnls(final_pnls_dates, recent_12_set)
    pf_6m = _pf_of(pnls_6m) if pnls_6m else 0
    pf_12m = _pf_of(pnls_12m) if pnls_12m else 0
    n_6m = len(pnls_6m)
    n_12m = len(pnls_12m)

    if pf_6m < MIN_PF_RECENT or pf_12m < MIN_PF_RECENT:
        print(f"  {sn:22s} FAIL recent  PF 6m={pf_6m:.2f} (n={n_6m})  PF 12m={pf_12m:.2f} (n={n_12m})")
        continue

    # Stats sl_atr pour STRUCT (dynamique)
    avg_sl_atr = p1
    if etype == 'STRUCT':
        sl_atrs = [t[2] for t in config_pnls[(etype, p1, p2, p3)]]
        avg_sl_atr = sum(sl_atrs) / len(sl_atrs) if sl_atrs else p1

    best_configs[sn] = {
        'type': etype, 'p1': p1, 'p2': p2, 'p3': p3,
        'pf': pf, 'wr': wr, 'n': n,
        'pf_6m': pf_6m, 'n_6m': n_6m,
        'pf_12m': pf_12m, 'n_12m': n_12m,
        'median_pf_oos': median_pf_oos,
        'pct_profitable_oos': pct_profitable,
        'wf_windows': len(pf_oos_list),
        'avg_sl_atr': avg_sl_atr,
        'rr1_alt': best_rr1,
    }

    # Affichage
    if etype == 'STRUCT':
        main_str = f"STRUCT N={p1} RR={p2} avg_sl_atr={avg_sl_atr:.2f}"
    elif etype == 'TPSL':
        rr_tag = ' [RR=1]' if abs(p1 - p2) < 0.01 else ''
        main_str = f"TPSL SL={p1:.1f} TP={p2:.2f}{rr_tag}"
    else:
        main_str = f"TRAIL SL={p1:.1f} ACT={p2:.2f} TR={p3:.2f}"

    rr1_str = ''
    if best_rr1 and best_rr1[0] != best_full[0]:
        (rcfg, rpf, rwr, rn) = best_rr1
        rr1_type = rcfg[0]
        rr1_str = f"  [alt RR1/STRUCT: {rr1_type} PF={rpf:.2f} WR={rwr:.0f}%]"

    print(f"  {sn:22s} {main_str:40s} | PF={pf:.2f} WR={wr:.0f}% n={n:4d} | OOS med={median_pf_oos:.2f} pct={pct_profitable:.0%} | 6m={pf_6m:.2f}(n={n_6m}) 12m={pf_12m:.2f}(n={n_12m}){rr1_str}")

print(f"\n  {len(best_configs)}/{len(SIG)} strats validees walk-forward")

# ── BUILD TRADE ARRAYS WITH BEST CONFIGS ──
strat_arrays = {}
for sn, cfg in best_configs.items():
    rows = []
    if cfg['type'] == 'STRUCT':
        N = int(cfg['p1']); rr = cfg['p2']
        for ci, di, entry, atr, date, sp in SIG[sn]:
            if ci < N: continue
            if di == 1:
                swing = float(c.iloc[ci-N:ci]['low'].min())
                distance = entry - swing + STRUCT_SL_BUFFER * atr
            else:
                swing = float(c.iloc[ci-N:ci]['high'].max())
                distance = swing - entry + STRUCT_SL_BUFFER * atr
            if distance <= 0: continue
            sl_atr_dyn = distance / atr
            if sl_atr_dyn < STRUCT_SL_MIN or sl_atr_dyn > STRUCT_SL_MAX: continue
            tp_atr_dyn = sl_atr_dyn * rr
            b, ex = sim_exit_unified(ci, entry, di, atr, 0, sl_atr_dyn, tp_atr_dyn, 0, False)
            pnl = ((ex - entry) if di == 1 else (entry - ex)) - sp - SPREAD_R * sl_atr_dyn * atr
            mo = f"{date.year}-{str(date.month).zfill(2)}"
            rows.append((ci, ci + b, di, pnl, sl_atr_dyn, atr, mo, sn))
    else:
        etype = 0 if cfg['type'] == 'TPSL' else 1
        for ci, di, entry, atr, date, sp in SIG[sn]:
            b, ex = sim_exit_unified(ci, entry, di, atr, etype, cfg['p1'], cfg['p2'], cfg['p3'], False)
            pnl = ((ex - entry) if di == 1 else (entry - ex)) - sp - SPREAD_R * cfg['p1'] * atr
            mo = f"{date.year}-{str(date.month).zfill(2)}"
            rows.append((ci, ci + b, di, pnl, cfg['p1'], atr, mo, sn))
    strat_arrays[sn] = rows

# ── SUMMARY ──
print("\n" + "=" * 115)
print(f"  {len(best_configs)} strats validees (WF 6M/1M + PF 6m >= {MIN_PF_RECENT} + PF 12m >= {MIN_PF_RECENT})")
print("=" * 115)
n_tpsl = sum(1 for c in best_configs.values() if c['type'] == 'TPSL')
n_trail = sum(1 for c in best_configs.values() if c['type'] == 'TRAIL')
n_struct = sum(1 for c in best_configs.values() if c['type'] == 'STRUCT')
n_rr1 = sum(1 for c in best_configs.values() if _is_rr1_cfg((c['type'], c['p1'], c['p2'], c['p3'])))
print(f"  Repartition: {n_tpsl} TPSL ({n_rr1} RR=1) | {n_trail} TRAIL | {n_struct} STRUCT")
print()
print(f"  {'STRAT':<22} {'TYPE':<6} {'P1':>5} {'P2':>5} {'P3':>5} | {'PF':>5} {'WR':>4} {'n':>5} | {'PF6m':>5} {'n6':>4} | {'PF12m':>6} {'n12':>4} | {'OOS.med':>7} {'OOS.pct':>7}")
for sn in sorted(best_configs.keys(), key=lambda x: -best_configs[x]['pf_6m']):
    cfg = best_configs[sn]
    p3 = cfg['p3'] if cfg['type'] == 'TRAIL' else 0
    tag = ''
    if cfg['type'] == 'STRUCT': tag = 'S'
    elif _is_rr1_cfg((cfg['type'], cfg['p1'], cfg['p2'], cfg['p3'])): tag = 'R'
    print(f"  {sn:<22} {cfg['type']:<6} {cfg['p1']:>5.1f} {cfg['p2']:>5.2f} {p3:>5.2f} | {cfg['pf']:>5.2f} {cfg['wr']:>3.0f}% {cfg['n']:>5d} | {cfg['pf_6m']:>5.2f} {cfg['n_6m']:>4d} | {cfg['pf_12m']:>6.2f} {cfg['n_12m']:>4d} | {cfg['median_pf_oos']:>7.2f} {cfg['pct_profitable_oos']:>7.0%} {tag}")


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
