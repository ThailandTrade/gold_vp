"""
Optimise les exits pour maximiser le WR (>60%) tout en gardant PF>1.1.
Strategie: SL large + TP court = WR eleve.
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
def get_sp(day):
    return 2 * monthly_spread.get(str(day.year)+"-"+str(day.month).zfill(2), avg_sp)

# Reuse collection from greedy
exec(open('find_combo_greedy.py').read().split('# GREEDY')[0])

OPEN_SET = {'TOK_FADE','TOK_PREVEXT','LON_GAP','LON_BIGGAP','LON_KZ','LON_TOKEND','LON_PREV','NY_GAP','NY_LONEND','NY_LONMOM','NY_DAYMOM'}

# For each strat, test configs aiming for WR > 60%
# High WR = large SL (room to breathe) + small TP (take profit quickly)
SL_VALS = [1.0, 1.5, 2.0, 3.0]
TP_VALS = [0.3, 0.5, 0.75, 1.0]
ACT_VALS = [0.3, 0.5]
TRAIL_VALS = [0.3, 0.5, 0.75]

print("="*100)
print("OPTIMISATION HIGH WR (>60%) — SL large + TP court")
print("="*100)
print(f"{'Strat':>22s} {'Type':>6s} {'SL':>5s} {'P2':>5s} {'P3':>5s} {'PF':>6s} {'WR':>5s} {'n':>5s} {'Split':>5s}")
print("-"*100)

good_hw = []
hw_configs = {}

for sn in sorted(S.keys()):
    trades = S[sn]
    if len(trades) < 20: continue
    is_open = sn in OPEN_SET
    best = None

    for sl in SL_VALS:
        for tp in TP_VALS:
            pnls = []; wins = 0; n = 0
            for t in trades:
                ci = t.get('ei')
                if ci is None or ci >= len(c)-5: continue
                d = t['dir']; atr = t.get('atr', 1.0)
                if atr == 0: continue
                entry = c.iloc[ci]['close']
                stop = entry - sl*atr if d=='long' else entry + sl*atr
                target = entry + tp*atr if d=='long' else entry - tp*atr
                spread = get_sp(t['date'])
                exited = False
                start = 0 if is_open else 1
                for j in range(start, min(100, len(c)-ci)):
                    b = c.iloc[ci+j]
                    if j == 0 and is_open:
                        if d=='long' and b['low']<=stop: pnls.append(stop-entry-spread); exited=True; break
                        if d=='short' and b['high']>=stop: pnls.append(entry-stop-spread); exited=True; break
                        continue
                    if d=='long':
                        if b['low']<=stop: pnls.append(stop-entry-spread); exited=True; break
                        if b['close']>=target: pnls.append(b['close']-entry-spread); wins+=1; exited=True; break
                    else:
                        if b['high']>=stop: pnls.append(entry-stop-spread); exited=True; break
                        if b['close']<=target: pnls.append(entry-b['close']-spread); wins+=1; exited=True; break
                if not exited:
                    nb = min(100, len(c)-ci-1)
                    if nb > 0:
                        ex = c.iloc[ci+nb]['close']
                        pnl = (ex-entry-spread) if d=='long' else (entry-ex-spread)
                        pnls.append(pnl)
                        if pnl > 0: wins += 1
                n += 1

            if len(pnls) < 20: continue
            wr = wins/len(pnls)*100
            if wr < 55: continue
            gp = sum(p for p in pnls if p>0); gl = abs(sum(p for p in pnls if p<0))+0.001
            pf = gp/gl
            mid = len(pnls)//2; f1 = np.mean(pnls[:mid]); f2 = np.mean(pnls[mid:])
            split = f1>0 and f2>0
            if pf >= 1.1 and split:
                score = wr * pf  # optimize for both WR and PF
                if best is None or score > best['score']:
                    best = {'type':'TPSL','sl':sl,'p2':tp,'p3':0,'pf':pf,'wr':wr,'n':len(pnls),'split':split,'score':score}

    for sl in SL_VALS:
        for act in ACT_VALS:
            for trail in TRAIL_VALS:
                if trail > sl: continue
                pnls = []; wins = 0
                for t in trades:
                    ci = t.get('ei')
                    if ci is None or ci >= len(c)-5: continue
                    d = t['dir']; atr = t.get('atr', 1.0)
                    if atr == 0: continue
                    entry = c.iloc[ci]['close']
                    spread = get_sp(t['date'])
                    best_p = entry; stop = entry-sl*atr if d=='long' else entry+sl*atr; ta = False
                    exited = False
                    start = 0 if is_open else 1
                    for j in range(start, min(50, len(c)-ci)):
                        b = c.iloc[ci+j]
                        if j == 0 and is_open:
                            if d=='long' and b['low']<=stop: pnls.append(stop-entry-spread); exited=True; break
                            if d=='short' and b['high']>=stop: pnls.append(entry-stop-spread); exited=True; break
                            continue
                        if d=='long':
                            if b['low']<=stop: pnls.append(stop-entry-spread); exited=True; break
                            if b['close']>best_p: best_p=b['close']
                            if not ta and (best_p-entry)>=act*atr: ta=True
                            if ta: stop=max(stop,best_p-trail*atr)
                            if b['close']<stop:
                                pnl = b['close']-entry-spread; pnls.append(pnl)
                                if pnl>0: wins+=1
                                exited=True; break
                        else:
                            if b['high']>=stop: pnls.append(entry-stop-spread); exited=True; break
                            if b['close']<best_p: best_p=b['close']
                            if not ta and (entry-best_p)>=act*atr: ta=True
                            if ta: stop=min(stop,best_p+trail*atr)
                            if b['close']>stop:
                                pnl = entry-b['close']-spread; pnls.append(pnl)
                                if pnl>0: wins+=1
                                exited=True; break
                    if not exited:
                        nb = min(50, len(c)-ci-1)
                        if nb > 0:
                            ex = c.iloc[ci+nb]['close']
                            pnl = (ex-entry-spread) if d=='long' else (entry-ex-spread)
                            pnls.append(pnl)
                            if pnl > 0: wins += 1

                if len(pnls) < 20: continue
                wr = wins/len(pnls)*100
                if wr < 55: continue
                gp = sum(p for p in pnls if p>0); gl = abs(sum(p for p in pnls if p<0))+0.001
                pf = gp/gl
                mid = len(pnls)//2; f1 = np.mean(pnls[:mid]); f2 = np.mean(pnls[mid:])
                split = f1>0 and f2>0
                if pf >= 1.1 and split:
                    score = wr * pf
                    if best is None or score > best['score']:
                        best = {'type':'TRAIL','sl':sl,'p2':act,'p3':trail,'pf':pf,'wr':wr,'n':len(pnls),'split':split,'score':score}

    if best and best['wr'] >= 55:
        sp = 'OK' if best['split'] else '!!'
        marker = ' <--' if best['wr'] >= 65 and best['pf'] >= 1.15 else ' *' if best['wr'] >= 60 else ''
        print(f"{sn:>22s} {best['type']:>6s} {best['sl']:5.2f} {best['p2']:5.2f} {best['p3']:5.2f} {best['pf']:6.2f} {best['wr']:4.0f}% {best['n']:5d} {sp:>5s}{marker}")
        if best['wr'] >= 60 and best['pf'] >= 1.1 and best['split']:
            good_hw.append(sn)
            hw_configs[sn] = best

print(f"\n  {len(good_hw)} strats avec WR>=60% + PF>=1.1 + split OK")
if good_hw:
    print(f"\n  WR>=65% + PF>=1.15:")
    for sn in good_hw:
        cfg = hw_configs[sn]
        if cfg['wr'] >= 65 and cfg['pf'] >= 1.15:
            print(f"    {sn:22s} WR={cfg['wr']:.0f}% PF={cfg['pf']:.2f} {cfg['type']} SL={cfg['sl']}")
print()
