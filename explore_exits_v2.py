"""
Exploration EXHAUSTIVE des sorties — v2
Chaque strat teste ~100 configs de sortie.
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

# ── EXIT METHODS ──
def exit_trail(cdf, pos, entry, d, sl, atr, mx, act, trail):
    best = entry; stop = entry + sl*atr if d == 'short' else entry - sl*atr; ta = False
    for j in range(1, mx+1):
        if pos+j >= len(cdf): break
        b = cdf.iloc[pos+j]
        if d == 'long':
            if b['low'] <= stop: return j, stop
            if b['high'] > best: best = b['high']
            if not ta and (best-entry) >= act*atr: ta = True
            if ta: stop = max(stop, best - trail*atr)
            if b['close'] < stop: return j, b['close']
        else:
            if b['high'] >= stop: return j, stop
            if b['low'] < best: best = b['low']
            if not ta and (entry-best) >= act*atr: ta = True
            if ta: stop = min(stop, best + trail*atr)
            if b['close'] > stop: return j, b['close']
    if pos+mx < len(cdf): return mx, cdf.iloc[pos+mx]['close']
    return mx, entry

def exit_sltp(cdf, pos, entry, d, sl_atr, tp_atr, atr, mx):
    sl = entry - sl_atr*atr if d == 'long' else entry + sl_atr*atr
    tp = entry + tp_atr*atr if d == 'long' else entry - tp_atr*atr
    for j in range(1, mx+1):
        if pos+j >= len(cdf): break
        b = cdf.iloc[pos+j]
        if d == 'long':
            if b['low'] <= sl: return j, sl
            if b['high'] >= tp: return j, tp
        else:
            if b['high'] >= sl: return j, sl
            if b['low'] <= tp: return j, tp
    if pos+mx < len(cdf): return mx, cdf.iloc[pos+mx]['close']
    return mx, entry

def exit_time(cdf, pos, entry, d, sl_atr, atr, n_bars):
    sl = entry - sl_atr*atr if d == 'long' else entry + sl_atr*atr
    for j in range(1, n_bars+1):
        if pos+j >= len(cdf): break
        b = cdf.iloc[pos+j]
        if d == 'long' and b['low'] <= sl: return j, sl
        if d == 'short' and b['high'] >= sl: return j, sl
    n = min(n_bars, len(cdf)-pos-1)
    if n > 0: return n, cdf.iloc[pos+n]['close']
    return 1, entry

def exit_be(cdf, pos, entry, d, sl_atr, atr, mx, be_trigger):
    """Breakeven: move stop to entry after be_trigger*ATR profit"""
    sl = entry - sl_atr*atr if d == 'long' else entry + sl_atr*atr
    stop = sl; be_done = False
    for j in range(1, mx+1):
        if pos+j >= len(cdf): break
        b = cdf.iloc[pos+j]
        if d == 'long':
            if b['low'] <= stop: return j, stop
            if not be_done and b['high'] >= entry + be_trigger*atr:
                stop = entry; be_done = True
            if be_done and b['close'] < stop: return j, b['close']
        else:
            if b['high'] >= stop: return j, stop
            if not be_done and b['low'] <= entry - be_trigger*atr:
                stop = entry; be_done = True
            if be_done and b['close'] > stop: return j, b['close']
    if pos+mx < len(cdf): return mx, cdf.iloc[pos+mx]['close']
    return mx, entry

def exit_nosl(cdf, pos, entry, d, n_bars):
    """Pas de stop, juste time exit"""
    n = min(n_bars, len(cdf)-pos-1)
    if n > 0: return n, cdf.iloc[pos+n]['close']
    return 1, entry

# ── SIGNAUX ──
print("Collecte signaux...", flush=True)
signals = {}
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
    le = pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC')
    ns = pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC')
    tv = candles[(candles['ts_dt']>=ds)&(candles['ts_dt']<=ct)]
    tok = tv[tv['ts_dt']<te]; lon = tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<le)]
    def sig(sn, d, e): signals.setdefault(sn,[]).append((ci, d, e, atr, today))

    if 8.0<=hour<8.1 and 'C' not in trig and len(tok)>=10:
        m=(tok.iloc[-1]['close']-tok.iloc[0]['open'])/atr
        if abs(m)>=1.0: sig('C','short' if m>0 else 'long',row['open']); trig['C']=True
    if 8.0<=hour<8.1 and 'D' not in trig:
        tc=candles[(candles['ts_dt']<te)&(candles['ts_dt']<=ct)]
        if len(tc)>=5:
            gap=(row['open']-tc.iloc[-1]['close'])/atr
            if abs(gap)>=0.5: sig('D','long' if gap>0 else 'short',row['open']); trig['D']=True
    if 10.0<=hour<10.1 and 'E' not in trig:
        kz=tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<pd.Timestamp(today.year,today.month,today.day,10,0,tz='UTC'))]
        if len(kz)>=20:
            m=(kz.iloc[-1]['close']-kz.iloc[0]['open'])/atr
            if abs(m)>=0.5: sig('E','short' if m>0 else 'long',row['open']); trig['E']=True
    if 0.0<=hour<6.0 and 'F' not in trig and len(tok)>=2:
        b1=tok.iloc[-2];b2=tok.iloc[-1]
        b1b=b1['close']-b1['open'];b2b=b2['close']-b2['open']
        if abs(b1b)>=0.5*atr and abs(b2b)>=0.5*atr and b1b*b2b<0 and abs(b2b)>abs(b1b):
            sig('F','long' if b2b>0 else 'short',b2['close']); trig['F']=True
    if 14.5<=hour<14.6 and 'G' not in trig:
        body=row['close']-row['open']
        if abs(body)>=0.3*atr: sig('G','long' if body>0 else 'short',row['close']); trig['G']=True
    if 8.0<=hour<8.1 and 'H' not in trig and len(tok)>=9:
        l3=tok.iloc[-3:]; m=(l3.iloc[-1]['close']-l3.iloc[0]['open'])/atr
        if abs(m)>=1.0: sig('H','long' if m>0 else 'short',row['open']); trig['H']=True
    if 15.5<=hour<15.6 and 'I' not in trig:
        ny1=tv[(tv['ts_dt']>=ns)&(tv['ts_dt']<pd.Timestamp(today.year,today.month,today.day,15,30,tz='UTC'))]
        if len(ny1)>=10:
            m=(ny1.iloc[-1]['close']-ny1.iloc[0]['open'])/atr
            if abs(m)>=1.0: sig('I','short' if m>0 else 'long',row['open']); trig['I']=True
    if 8.0<=hour<8.1 and 'J' not in trig:
        body=row['close']-row['open']
        if abs(body)>=0.3*atr: sig('J','long' if body>0 else 'short',row['close']); trig['J']=True
    if 0.0<=hour<6.0 and 'O' not in trig:
        body=row['close']-row['open']
        if abs(body)>=1.0*atr: sig('O','long' if body>0 else 'short',row['close']); trig['O']=True
    if 15.0<=hour<21.5 and 'P' not in trig:
        if 'P_h' not in trig:
            orb=tv[(tv['ts_dt']>=ns)&(tv['ts_dt']<pd.Timestamp(today.year,today.month,today.day,15,0,tz='UTC'))]
            if len(orb)>=6: trig['P_h']=float(orb['high'].max()); trig['P_l']=float(orb['low'].min())
        if 'P_h' in trig:
            if row['close']>trig['P_h']: sig('P','long',row['close']); trig['P']=True
            elif row['close']<trig['P_l']: sig('P','short',row['close']); trig['P']=True
    if 8.0<=hour<14.5 and 'Q' not in trig and len(lon)>=2:
        pb=lon.iloc[-2];cb=lon.iloc[-1]
        if pb['close']<pb['open'] and cb['close']>cb['open'] and cb['open']<=pb['close'] and cb['close']>=pb['open'] and abs(cb['close']-cb['open'])>=0.3*atr:
            sig('Q','long',cb['close']); trig['Q']=True
        elif pb['close']>pb['open'] and cb['close']<cb['open'] and cb['open']>=pb['close'] and cb['close']<=pb['open'] and abs(cb['close']-cb['open'])>=0.3*atr:
            sig('Q','short',cb['close']); trig['Q']=True
    if 0.0<=hour<6.0 and 'R' not in trig and len(tok)>=3:
        c1=tok.iloc[-3];c2=tok.iloc[-2];c3=tok.iloc[-1]
        b1=c1['close']-c1['open'];b2=c2['close']-c2['open'];b3=c3['close']-c3['open']
        if b1*b2>0 and b2*b3>0 and min(abs(b1),abs(b2),abs(b3))>0.1*atr and abs(b1+b2+b3)>=0.5*atr:
            sig('R','long' if b3>0 else 'short',c3['close']); trig['R']=True
    if 8.0<=hour<14.5 and 'S' not in trig and len(lon)>=3:
        c1=lon.iloc[-3];c2=lon.iloc[-2];c3=lon.iloc[-1]
        b1=c1['close']-c1['open'];b2=c2['close']-c2['open'];b3=c3['close']-c3['open']
        if b1*b2>0 and b2*b3>0 and min(abs(b1),abs(b2),abs(b3))>0.1*atr and abs(b1+b2+b3)>=0.5*atr:
            sig('S','short' if b3>0 else 'long',c3['close']); trig['S']=True
    if 0.0<=hour<6.0 and 'V' not in trig and len(tok)>=7:
        last6=tok.iloc[-6:]; n_bull=(last6['close']>last6['open']).sum()
        if n_bull>=5: sig('V','long',row['close']); trig['V']=True
        elif n_bull<=1: sig('V','short',row['close']); trig['V']=True
    if 8.0<=hour<14.5 and 'AA' not in trig:
        rng=row['high']-row['low']
        if rng>=0.3*atr and abs(row['close']-row['open'])>=0.2*atr:
            pir=(row['close']-row['low'])/rng
            if pir>=0.9: sig('AA','long',row['close']); trig['AA']=True
            elif pir<=0.1: sig('AA','short',row['close']); trig['AA']=True
    if 0.0<=hour<6.0 and 'AC' not in trig and len(tok)>=4:
        prev3_h=tok.iloc[-4:-1]['high'].max();prev3_l=tok.iloc[-4:-1]['low'].min()
        body=abs(row['close']-row['open'])
        if row['high']>=prev3_h and row['low']<=prev3_l and body>=0.5*atr:
            sig('AC','long' if row['close']>row['open'] else 'short',row['close']); trig['AC']=True

print("Done.", flush=True)

# ── BUILD ALL CONFIGS ──
configs = []
# SL/TP fixe
for sl in [0.25, 0.3, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0]:
    for tp_r in [0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0]:
        tp = sl * tp_r
        for mx in [12, 24, 48]:
            configs.append((f"SL{sl} TP{tp_r}R T{mx}", lambda ci,d,e,atr,day,_sl=sl,_tp=tp,_mx=mx: exit_sltp(candles,ci,e,d,_sl,_tp,atr,_mx)))
# Time-based
for sl in [0.5, 0.75, 1.0, 1.5]:
    for t in [3, 4, 6, 8, 12, 18, 24, 36, 48]:
        configs.append((f"SL{sl} T{t}b", lambda ci,d,e,atr,day,_sl=sl,_t=t: exit_time(candles,ci,e,d,_sl,atr,_t)))
# Trailing corrige
for sl in [0.3, 0.5, 0.75, 1.0, 1.5]:
    for act in [0.2, 0.3, 0.5, 0.75, 1.0]:
        for trail in [0.15, 0.2, 0.3, 0.5, 0.75]:
            if trail >= sl: continue  # trail doit etre < sl
            for mx in [12, 24, 48]:
                configs.append((f"TR s{sl} a{act} t{trail} T{mx}", lambda ci,d,e,atr,day,_sl=sl,_a=act,_t=trail,_mx=mx: exit_trail(candles,ci,e,d,_sl,atr,_mx,_a,_t)))
# Breakeven
for sl in [0.5, 0.75, 1.0]:
    for be in [0.3, 0.5, 0.75, 1.0]:
        for mx in [12, 24, 48]:
            configs.append((f"BE s{sl} be{be} T{mx}", lambda ci,d,e,atr,day,_sl=sl,_be=be,_mx=mx: exit_be(candles,ci,e,d,_sl,atr,_mx,_be)))
# No stop
for t in [3, 6, 12, 24]:
    configs.append((f"NOSL T{t}b", lambda ci,d,e,atr,day,_t=t: exit_nosl(candles,ci,e,d,_t)))

print(f"{len(configs)} configs a tester par strat", flush=True)

# ── TEST ──
STRATS = sorted(signals.keys())
print(f"\n{'='*100}")
print(f"EXPLORATION EXHAUSTIVE — {len(STRATS)} strats x {len(configs)} configs = {len(STRATS)*len(configs)} tests")
print(f"{'='*100}")

for sn in STRATS:
    sigs = signals[sn]
    if len(sigs) < 20: continue

    results = []
    for config_name, exit_fn in configs:
        pnls = []
        for ci, d, e, atr, day in sigs:
            bars, ex = exit_fn(ci, d, e, atr, day)
            pnl = (ex-e) if d=='long' else (e-ex)
            pnls.append(pnl - get_sp(day))
        pnls = np.array(pnls)
        n = len(pnls); gp = pnls[pnls>0].sum(); gl = abs(pnls[pnls<0].sum())+0.001
        pf = gp/gl; wr = (pnls>0).mean()*100
        mid = n//2; f1 = pnls[:mid].mean(); f2 = pnls[mid:].mean()
        ok = f1>0 and f2>0
        results.append((config_name, n, wr, pf, pnls.mean(), ok))

    # Top 10 par PF (split OK)
    valid = [r for r in results if r[5] and r[3] >= 1.0]
    valid.sort(key=lambda x: -x[3])

    print(f"\n  {sn} ({len(sigs)} trades) — Top 10 (split OK):")
    print(f"    {'Config':35s} {'n':>4s} {'WR':>5s} {'PF':>6s} {'Avg':>8s}")
    for config_name, n, wr, pf, avg, ok in valid[:10]:
        marker = " ***" if pf >= 1.3 else ""
        print(f"    {config_name:35s} {n:4d} {wr:4.0f}% {pf:6.2f} {avg:+8.3f}{marker}")

    if not valid:
        print(f"    AUCUNE config avec split OK et PF >= 1.0")

print(f"\n{'='*100}")
