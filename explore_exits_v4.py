"""
Exploration exhaustive des exits — toutes strats, tous types de sortie.
Trailing sur CLOSE (pas high/low), temporellement coherent.

Types de sortie:
  TRAIL: SL + trailing (activation + trail distance) + timeout
  TPSL:  TP fixe + SL fixe + timeout
  TIME:  SL + timeout (pas de trailing, pas de TP)
  BE_TR: Breakeven puis trailing (SL -> entry apres activation, puis trail)

Tous les paramètres en multiples d'ATR.
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

# ── EXIT FUNCTIONS (toutes sur CLOSE, temporellement coherentes) ──

def exit_trail(cdf, pos, entry, d, atr, sl, act, trail, mx):
    """Trailing sur close: SL check sur low/high, best/trail sur close."""
    best = entry; stop = entry + sl*atr if d == 'short' else entry - sl*atr; ta = False
    for j in range(1, mx+1):
        if pos+j >= len(cdf): break
        b = cdf.iloc[pos+j]
        if d == 'long':
            if b['low'] <= stop: return j, stop, 'stop'
            if b['close'] > best: best = b['close']
            if not ta and (best-entry) >= act*atr: ta = True
            if ta: stop = max(stop, best - trail*atr)
            if b['close'] < stop: return j, b['close'], 'trail'
        else:
            if b['high'] >= stop: return j, stop, 'stop'
            if b['close'] < best: best = b['close']
            if not ta and (entry-best) >= act*atr: ta = True
            if ta: stop = min(stop, best + trail*atr)
            if b['close'] > stop: return j, b['close'], 'trail'
    n = min(mx, len(cdf)-pos-1)
    if n > 0: return n, cdf.iloc[pos+n]['close'], 'timeout'
    return 1, entry, 'timeout'

def exit_tpsl(cdf, pos, entry, d, atr, sl, tp, mx):
    """TP/SL fixes. SL sur low/high, TP sur close."""
    stop = entry + sl*atr if d == 'short' else entry - sl*atr
    target = entry + tp*atr if d == 'long' else entry - tp*atr
    for j in range(1, mx+1):
        if pos+j >= len(cdf): break
        b = cdf.iloc[pos+j]
        if d == 'long':
            if b['low'] <= stop: return j, stop, 'stop'
            if b['close'] >= target: return j, b['close'], 'tp'
        else:
            if b['high'] >= stop: return j, stop, 'stop'
            if b['close'] <= target: return j, b['close'], 'tp'
    n = min(mx, len(cdf)-pos-1)
    if n > 0: return n, cdf.iloc[pos+n]['close'], 'timeout'
    return 1, entry, 'timeout'

def exit_time(cdf, pos, entry, d, atr, sl, mx):
    """SL + timeout seulement. Pas de trailing, pas de TP."""
    stop = entry + sl*atr if d == 'short' else entry - sl*atr
    for j in range(1, mx+1):
        if pos+j >= len(cdf): break
        b = cdf.iloc[pos+j]
        if d == 'long' and b['low'] <= stop: return j, stop, 'stop'
        if d == 'short' and b['high'] >= stop: return j, stop, 'stop'
    n = min(mx, len(cdf)-pos-1)
    if n > 0: return n, cdf.iloc[pos+n]['close'], 'timeout'
    return 1, entry, 'timeout'

def exit_be_trail(cdf, pos, entry, d, atr, sl, act, trail, mx):
    """Breakeven + trailing: apres activation, SL -> entry, puis trail depuis close."""
    best = entry; stop = entry + sl*atr if d == 'short' else entry - sl*atr; ta = False
    for j in range(1, mx+1):
        if pos+j >= len(cdf): break
        b = cdf.iloc[pos+j]
        if d == 'long':
            if b['low'] <= stop: return j, stop, 'stop'
            if b['close'] > best: best = b['close']
            if not ta and (best-entry) >= act*atr:
                ta = True; stop = max(stop, entry)  # BE
            if ta: stop = max(stop, best - trail*atr)
            if b['close'] < stop: return j, b['close'], 'be_trail'
        else:
            if b['high'] >= stop: return j, stop, 'stop'
            if b['close'] < best: best = b['close']
            if not ta and (entry-best) >= act*atr:
                ta = True; stop = min(stop, entry)  # BE
            if ta: stop = min(stop, best + trail*atr)
            if b['close'] > stop: return j, b['close'], 'be_trail'
    n = min(mx, len(cdf)-pos-1)
    if n > 0: return n, cdf.iloc[pos+n]['close'], 'timeout'
    return 1, entry, 'timeout'

# ── COLLECTE DES ENTREES (meme logique que find_best_v10) ──

print("Collecte des entrees...", flush=True)
entries = {}  # {strat: [(ci, entry_price, direction, date, atr), ...]}
prev_d = None; trig = {}; day_atr = None
for ci in range(len(candles)):
    row = candles.iloc[ci]; ct = row['ts_dt']; today = ct.date()
    hour = ct.hour + ct.minute / 60.0
    if today != prev_d:
        prev_d = today; trig = {}
        pd_ = prev_day(today); day_atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    atr = day_atr
    if atr == 0 or atr is None: continue
    ds = pd.Timestamp(today.year,today.month,today.day,0,0,tz='UTC')
    te = pd.Timestamp(today.year,today.month,today.day,6,0,tz='UTC')
    ls = pd.Timestamp(today.year,today.month,today.day,8,0,tz='UTC')
    tv = candles[(candles['ts_dt']>=ds)&(candles['ts_dt']<=ct)]
    tok = tv[tv['ts_dt']<te]

    def reg(sn, d, e):
        entries.setdefault(sn, []).append((ci, e, d, today, atr))

    if 8.0<=hour<14.5 and 'AA' not in trig:
        rng=row['high']-row['low']
        if rng>=0.3*atr and abs(row['close']-row['open'])>=0.2*atr:
            pir=(row['close']-row['low'])/rng
            if pir>=0.9: reg('AA','long',row['close']); trig['AA']=True
            elif pir<=0.1: reg('AA','short',row['close']); trig['AA']=True
    if 8.0<=hour<8.1 and 'C' not in trig and len(tok)>=10:
        m=(tok.iloc[-1]['close']-tok.iloc[0]['open'])/atr
        if abs(m)>=1.0: reg('C','short' if m>0 else 'long',row['open']); trig['C']=True
    if 8.0<=hour<8.1 and 'D' not in trig:
        tc=candles[(candles['ts_dt']<te)&(candles['ts_dt']<=ct)]
        if len(tc)>=5:
            gap=(row['open']-tc.iloc[-1]['close'])/atr
            if abs(gap)>=0.5: reg('D','long' if gap>0 else 'short',row['open']); trig['D']=True
    if 10.0<=hour<10.1 and 'E' not in trig:
        kz=tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<pd.Timestamp(today.year,today.month,today.day,10,0,tz='UTC'))]
        if len(kz)>=20:
            m=(kz.iloc[-1]['close']-kz.iloc[0]['open'])/atr
            if abs(m)>=0.5: reg('E','short' if m>0 else 'long',row['open']); trig['E']=True
    if 0.0<=hour<6.0 and 'F' not in trig and len(tok)>=2:
        b1=tok.iloc[-2];b2=tok.iloc[-1];b1b=b1['close']-b1['open'];b2b=b2['close']-b2['open']
        if abs(b1b)>=0.5*atr and abs(b2b)>=0.5*atr and b1b*b2b<0 and abs(b2b)>abs(b1b):
            reg('F','long' if b2b>0 else 'short',b2['close']); trig['F']=True
    if 14.5<=hour<14.6 and 'G' not in trig:
        body=row['close']-row['open']
        if abs(body)>=0.3*atr: reg('G','long' if body>0 else 'short',row['close']); trig['G']=True
    if 8.0<=hour<8.1 and 'H' not in trig and len(tok)>=9:
        l3=tok.iloc[-3:]; m=(l3.iloc[-1]['close']-l3.iloc[0]['open'])/atr
        if abs(m)>=1.0: reg('H','long' if m>0 else 'short',row['open']); trig['H']=True
    if 15.5<=hour<15.6 and 'I' not in trig:
        ny1=tv[(tv['ts_dt']>=pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC'))&
               (tv['ts_dt']<pd.Timestamp(today.year,today.month,today.day,15,30,tz='UTC'))]
        if len(ny1)>=10:
            m=(ny1.iloc[-1]['close']-ny1.iloc[0]['open'])/atr
            if abs(m)>=1.0: reg('I','short' if m>0 else 'long',row['open']); trig['I']=True
    if 0.0<=hour<6.0 and 'O' not in trig:
        body=row['close']-row['open']
        if abs(body)>=1.0*atr: reg('O','long' if body>0 else 'short',row['close']); trig['O']=True
    if 15.0<=hour<21.5 and 'P' not in trig:
        if 'P_h' not in trig:
            orb=tv[(tv['ts_dt']>=pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC'))&
                   (tv['ts_dt']<pd.Timestamp(today.year,today.month,today.day,15,0,tz='UTC'))]
            if len(orb)>=6: trig['P_h']=float(orb['high'].max()); trig['P_l']=float(orb['low'].min())
        if 'P_h' in trig:
            if row['close']>trig['P_h']: reg('P','long',row['close']); trig['P']=True
            elif row['close']<trig['P_l']: reg('P','short',row['close']); trig['P']=True
    if 8.0<=hour<14.5 and 'Q' not in trig:
        lon = tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC'))]
        if len(lon)>=2:
            pb=lon.iloc[-2];cb=lon.iloc[-1]
            if pb['close']<pb['open'] and cb['close']>cb['open'] and cb['open']<=pb['close'] and cb['close']>=pb['open'] and abs(cb['close']-cb['open'])>=0.3*atr:
                reg('Q','long',cb['close']); trig['Q']=True
            elif pb['close']>pb['open'] and cb['close']<cb['open'] and cb['open']>=pb['close'] and cb['close']<=pb['open'] and abs(cb['close']-cb['open'])>=0.3*atr:
                reg('Q','short',cb['close']); trig['Q']=True
    if 0.0<=hour<6.0 and 'R' not in trig and len(tok)>=3:
        c1=tok.iloc[-3];c2=tok.iloc[-2];c3=tok.iloc[-1];b1=c1['close']-c1['open'];b2=c2['close']-c2['open'];b3=c3['close']-c3['open']
        if b1*b2>0 and b2*b3>0 and min(abs(b1),abs(b2),abs(b3))>0.1*atr and abs(b1+b2+b3)>=0.5*atr:
            reg('R','long' if b3>0 else 'short',c3['close']); trig['R']=True
    if 8.0<=hour<14.5 and 'S' not in trig:
        lon = tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC'))]
        if len(lon)>=3:
            c1=lon.iloc[-3];c2=lon.iloc[-2];c3=lon.iloc[-1];b1=c1['close']-c1['open'];b2=c2['close']-c2['open'];b3=c3['close']-c3['open']
            if b1*b2>0 and b2*b3>0 and min(abs(b1),abs(b2),abs(b3))>0.1*atr and abs(b1+b2+b3)>=0.5*atr:
                reg('S','short' if b3>0 else 'long',c3['close']); trig['S']=True
    if 0.0<=hour<6.0 and 'V' not in trig and len(tok)>=7:
        last6=tok.iloc[-6:]; n_bull=(last6['close']>last6['open']).sum()
        if n_bull>=5: reg('V','long',row['close']); trig['V']=True
        elif n_bull<=1: reg('V','short',row['close']); trig['V']=True
    if 0.0<=hour<6.0 and 'AC' not in trig and len(tok)>=4:
        prev3_h=tok.iloc[-4:-1]['high'].max();prev3_l=tok.iloc[-4:-1]['low'].min()
        body=abs(row['close']-row['open'])
        if row['high']>=prev3_h and row['low']<=prev3_l and body>=0.5*atr:
            reg('AC','long' if row['close']>row['open'] else 'short',row['close']); trig['AC']=True

print(f"  {sum(len(v) for v in entries.values())} entrees pour {len(entries)} strats", flush=True)

# ── GRILLE DE CONFIGS ──

SL_VALS = [0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
ACT_VALS = [0.3, 0.5, 0.75, 1.0, 1.5]
TRAIL_VALS = [0.3, 0.5, 0.75, 1.0, 1.5]
TP_VALS = [0.5, 1.0, 1.5, 2.0, 3.0, 5.0]
MX_VALS = [4, 6, 12, 24, 48]

configs = []
# TRAIL: sl × act × trail × mx
for sl in SL_VALS:
    for act in ACT_VALS:
        for tr in TRAIL_VALS:
            if tr > sl: continue  # trail > SL n'a pas de sens
            for mx in MX_VALS:
                configs.append(('TRAIL', sl, act, tr, mx, 0))
# TPSL: sl × tp × mx
for sl in SL_VALS:
    for tp in TP_VALS:
        for mx in MX_VALS:
            configs.append(('TPSL', sl, 0, 0, mx, tp))
# TIME: sl × mx
for sl in SL_VALS:
    for mx in MX_VALS:
        configs.append(('TIME', sl, 0, 0, mx, 0))
# BE_TRAIL: sl × act × trail × mx
for sl in SL_VALS:
    for act in ACT_VALS:
        for tr in TRAIL_VALS:
            if tr > sl: continue
            for mx in MX_VALS:
                configs.append(('BE_TR', sl, act, tr, mx, 0))

print(f"  {len(configs)} configs a tester", flush=True)

# ── EVALUATION ──

def eval_strat_config(sn, cfg):
    typ, sl, act, tr, mx, tp = cfg
    elist = entries.get(sn, [])
    if len(elist) < 20: return None
    pnls = []
    for ci, entry, d, day, atr in elist:
        if typ == 'TRAIL':
            bars, ex, reason = exit_trail(candles, ci, entry, d, atr, sl, act, tr, mx)
        elif typ == 'TPSL':
            bars, ex, reason = exit_tpsl(candles, ci, entry, d, atr, sl, tp, mx)
        elif typ == 'TIME':
            bars, ex, reason = exit_time(candles, ci, entry, d, atr, sl, mx)
        elif typ == 'BE_TR':
            bars, ex, reason = exit_be_trail(candles, ci, entry, d, atr, sl, act, tr, mx)
        pnl = (ex-entry) if d=='long' else (entry-ex)
        pnls.append(pnl - get_sp(day))
    n = len(pnls)
    wins = [p for p in pnls if p > 0]
    gp = sum(wins); gl = abs(sum(p for p in pnls if p < 0)) + 0.001
    wr = len(wins)/n*100
    pf = gp/gl
    avg = np.mean(pnls)
    mid = n//2
    f1 = np.mean(pnls[:mid]); f2 = np.mean(pnls[mid:])
    t1 = sum(pnls[:n//3]); t2 = sum(pnls[n//3:2*n//3]); t3 = sum(pnls[2*n//3:])
    tiers = sum(1 for x in [t1, t2, t3] if x > 0)
    split = f1 > 0 and f2 > 0
    return {'n': n, 'wr': wr, 'pf': pf, 'avg': avg, 'total': sum(pnls),
            'split': split, 'tiers': tiers, 'f1': f1, 'f2': f2}

print("\nEvaluation...", flush=True)

# Pour chaque strat, trouver les meilleures configs
all_results = {}
for sn in sorted(entries.keys()):
    n_entries = len(entries[sn])
    if n_entries < 20: continue
    results = []
    for i, cfg in enumerate(configs):
        if i % 200 == 0: print(f"\r  {sn}: {i*100//len(configs)}%   ", end='', flush=True)
        r = eval_strat_config(sn, cfg)
        if r and r['pf'] > 0.5:
            results.append((cfg, r))
    all_results[sn] = results
    # Best par type
    print(f"\r  {sn}: {n_entries} trades, {len(results)} configs evaluees")

# ── RESULTATS ──

print("\n" + "="*130)
print("MEILLEURE CONFIG PAR STRAT ET PAR TYPE DE SORTIE (PF, split OK)")
print("="*130)
print(f"{'Strat':>4s} {'Type':>6s} {'SL':>4s} {'ACT':>5s} {'TR':>4s} {'TP':>4s} {'MX':>3s} {'n':>5s} {'WR':>5s} {'PF':>6s} {'Avg':>8s} {'Total':>8s} {'Split':>6s} {'Tiers':>5s}")
print("-"*130)

for sn in sorted(all_results.keys()):
    results = all_results[sn]
    if not results: continue

    for typ in ['TRAIL', 'TPSL', 'TIME', 'BE_TR']:
        typ_results = [(c, r) for c, r in results if c[0] == typ and r['pf'] > 1.0]
        if not typ_results: continue
        # Tri par PF
        typ_results.sort(key=lambda x: x[1]['pf'], reverse=True)
        cfg, r = typ_results[0]
        _, sl, act, tr, mx, tp = cfg
        split_str = "OK" if r['split'] else "!!"
        act_str = f"{act:.2f}" if act > 0 else "—"
        tr_str = f"{tr:.1f}" if tr > 0 else "—"
        tp_str = f"{tp:.1f}" if tp > 0 else "—"
        print(f"{sn:>4s} {typ:>6s} {sl:4.1f} {act_str:>5s} {tr_str:>4s} {tp_str:>4s} {mx:3d} {r['n']:5d} {r['wr']:4.0f}% {r['pf']:6.2f} {r['avg']:+8.3f} {r['total']:+8.1f} {split_str:>6s} {r['tiers']:4d}/3")

# Top 5 configs par strat (tous types confondus, PF)
print("\n" + "="*130)
print("TOP 5 PAR STRAT (PF, n>=20)")
print("="*130)
for sn in sorted(all_results.keys()):
    results = all_results[sn]
    if not results: continue
    valid = [(c, r) for c, r in results if r['pf'] > 1.0]
    valid.sort(key=lambda x: x[1]['pf'], reverse=True)
    print(f"\n  {sn} ({len(entries[sn])} trades):")
    print(f"  {'Type':>6s} {'SL':>4s} {'ACT':>5s} {'TR':>4s} {'TP':>4s} {'MX':>3s} {'n':>5s} {'WR':>5s} {'PF':>6s} {'Avg':>8s} {'Total':>8s} {'Split':>6s} {'Tiers':>5s}")
    for cfg, r in valid[:5]:
        _, sl, act, tr, mx, tp = cfg
        split_str = "OK" if r['split'] else "!!"
        act_str = f"{act:.2f}" if act > 0 else "—"
        tr_str = f"{tr:.1f}" if tr > 0 else "—"
        tp_str = f"{tp:.1f}" if tp > 0 else "—"
        print(f"  {cfg[0]:>6s} {sl:4.1f} {act_str:>5s} {tr_str:>4s} {tp_str:>4s} {mx:3d} {r['n']:5d} {r['wr']:4.0f}% {r['pf']:6.2f} {r['avg']:+8.3f} {r['total']:+8.1f} {split_str:>6s} {r['tiers']:4d}/3")

# Config unique: quelle config est la meilleure sur TOUTES les strats combinées?
print("\n" + "="*130)
print("MEILLEURE CONFIG UNIQUE (somme des PnL de toutes les strats)")
print("="*130)

cfg_scores = []
for i, cfg in enumerate(configs):
    total_pnl = 0; total_n = 0; all_split = True; min_pf = 999
    strat_pfs = {}
    for sn in sorted(entries.keys()):
        r = eval_strat_config(sn, cfg)
        if r is None: continue
        total_pnl += r['total']; total_n += r['n']
        if not r['split']: all_split = False
        strat_pfs[sn] = r['pf']
        if r['pf'] < min_pf: min_pf = r['pf']
    if total_n < 100: continue
    # Nombre de strats avec PF > 1.0
    n_good = sum(1 for pf in strat_pfs.values() if pf > 1.0)
    n_great = sum(1 for pf in strat_pfs.values() if pf > 1.2)
    cfg_scores.append((cfg, total_pnl, total_n, n_good, n_great, strat_pfs))

cfg_scores.sort(key=lambda x: x[1], reverse=True)

print(f"\n  TOP 30 par PnL total (toutes strats):")
print(f"  {'Type':>6s} {'SL':>4s} {'ACT':>5s} {'TR':>4s} {'TP':>4s} {'MX':>3s} {'Total PnL':>10s} {'n':>6s} {'Good':>5s} {'Great':>5s}")
for cfg, pnl, n, ng, ngr, _ in cfg_scores[:30]:
    _, sl, act, tr, mx, tp = cfg
    act_str = f"{act:.2f}" if act > 0 else "—"
    tr_str = f"{tr:.1f}" if tr > 0 else "—"
    tp_str = f"{tp:.1f}" if tp > 0 else "—"
    print(f"  {cfg[0]:>6s} {sl:4.1f} {act_str:>5s} {tr_str:>4s} {tp_str:>4s} {mx:3d} {pnl:+10.1f} {n:6d} {ng:4d}/15 {ngr:4d}/15")

# Detail de la meilleure config unique
if cfg_scores:
    best_cfg, best_pnl, best_n, _, _, best_pfs = cfg_scores[0]
    print(f"\n  MEILLEURE CONFIG: {best_cfg[0]} SL={best_cfg[1]} ACT={best_cfg[2]} TRAIL={best_cfg[3]} MX={best_cfg[4]} TP={best_cfg[5]}")
    print(f"  PnL total: {best_pnl:+.1f} oz sur {best_n} trades")
    print(f"\n  {'Strat':>4s} {'PF':>6s} {'Verdict':>8s}")
    for sn in sorted(best_pfs.keys()):
        pf = best_pfs[sn]
        v = "GOOD" if pf > 1.2 else "ok" if pf > 1.0 else "WEAK" if pf > 0.8 else "BAD"
        print(f"  {sn:>4s} {pf:6.2f} {v:>8s}")

print()
