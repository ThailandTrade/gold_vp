"""
Test : toutes les strats SANS cooldown (plusieurs trades par strat par jour)
vs avec cooldown (1 trade/strat/jour comme le backtest actuel)
"""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
from dotenv import load_dotenv; load_dotenv()
from phase1_poc_calculator import get_conn, compute_atr, get_trading_days
from phase3_analyze import load_candles_5m

SLIPPAGE = 0.10
def sim_trail(cdf, pos, entry, d, sl, atr, mx, act, trail):
    best = entry; stop = entry + sl*atr if d == 'short' else entry - sl*atr; ta = False
    for j in range(1, mx+1):
        if pos+j >= len(cdf): break
        b = cdf.iloc[pos+j]
        if d == 'long':
            if b['low'] <= stop: return j, stop - SLIPPAGE
            if b['high'] > best: best = b['high']
            if not ta and (best-entry) >= act*atr: ta = True
            if ta: stop = max(stop, best - trail*atr)
        else:
            if b['high'] >= stop: return j, stop + SLIPPAGE
            if b['low'] < best: best = b['low']
            if not ta and (entry-best) >= act*atr: ta = True
            if ta: stop = min(stop, best + trail*atr)
    if pos+mx < len(cdf): return mx, cdf.iloc[pos+mx]['close']
    return mx, entry

conn = get_conn()
candles = load_candles_5m(conn)
daily_atr, global_atr = compute_atr(conn)
trading_days = get_trading_days(conn)
cur = conn.cursor()
cur.execute("""SELECT DATE_TRUNC('month', time), AVG(ask-bid)
    FROM market_ticks_xauusd WHERE ask>bid AND ask-bid<10 GROUP BY 1""")
monthly_spread = {r[0].strftime("%Y-%m"): float(r[1]) for r in cur.fetchall()}
cur.close()
avg_sp = np.mean(list(monthly_spread.values()))

def prev_day(day):
    for di, d in enumerate(trading_days):
        if d >= day: return trading_days[di-1] if di > 0 else None
    return None
def get_sp(day):
    return 2 * monthly_spread.get(str(day.year)+"-"+str(day.month).zfill(2), avg_sp)
n_td = len(set(candles['date'].unique()))
SL, ACT, TRAIL = 0.75, 0.5, 0.3

def collect_trades(cooldown=True):
    """Collecte tous les trades. cooldown=True = 1/strat/jour, False = illimite"""
    S = {}

    # ── Strats iteratives (F, O, Q, R, S) — avec ou sans break ──

    # F: 2BAR Tokyo
    t = []
    for day in trading_days:
        p = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
        if len(p) < 8: continue
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        for i in range(1, len(p)):
            b1b = p.iloc[i-1]['close']-p.iloc[i-1]['open']; b2b = p.iloc[i]['close']-p.iloc[i]['open']
            if abs(b1b)<0.5*atr or abs(b2b)<0.5*atr: continue
            if b1b*b2b >= 0 or abs(b2b) <= abs(b1b): continue
            pi = candles.index.get_loc(p.index[i]); e = p.iloc[i]['close']
            d = 'long' if b2b > 0 else 'short'
            b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
            pnl = (ex-e) if d == 'long' else (e-ex)
            t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b})
            if cooldown: break
    S['F'] = t

    # O: Big candle >1ATR Tokyo
    t = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        sess = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
        if len(sess) < 6: continue
        for i in range(len(sess)):
            r = sess.iloc[i]; body = r['close'] - r['open']
            if abs(body) >= 1.0*atr:
                d = 'long' if body > 0 else 'short'
                pi = candles.index.get_loc(sess.index[i]); e = r['close']
                b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
                pnl = (ex-e) if d == 'long' else (e-ex)
                t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b})
                if cooldown: break
    S['O'] = t

    # Q: Engulfing London
    t = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        sess = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))]
        if len(sess) < 6: continue
        for i in range(1, len(sess)):
            pb = sess.iloc[i-1]; cb = sess.iloc[i]; triggered = False
            if pb['close']<pb['open'] and cb['close']>cb['open'] and cb['open']<=pb['close'] and cb['close']>=pb['open'] and abs(cb['close']-cb['open'])>=0.3*atr:
                pi = candles.index.get_loc(sess.index[i]); e = cb['close']
                b, ex = sim_trail(candles, pi, e, 'long', SL, atr, 24, ACT, TRAIL)
                t.append({'date':day,'dir':'long','sl_atr':SL,'pnl_oz':(ex-e)-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b}); triggered = True
            if not triggered and pb['close']>pb['open'] and cb['close']<cb['open'] and cb['open']>=pb['close'] and cb['close']<=pb['open'] and abs(cb['close']-cb['open'])>=0.3*atr:
                pi = candles.index.get_loc(sess.index[i]); e = cb['close']
                b, ex = sim_trail(candles, pi, e, 'short', SL, atr, 24, ACT, TRAIL)
                t.append({'date':day,'dir':'short','sl_atr':SL,'pnl_oz':(e-ex)-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b}); triggered = True
            if triggered and cooldown: break
    S['Q'] = t

    # R: 3 soldiers Tokyo cont
    t = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        sess = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
        if len(sess) < 6: continue
        for i in range(2, len(sess)):
            c1=sess.iloc[i-2]; c2=sess.iloc[i-1]; c3=sess.iloc[i]
            b1=c1['close']-c1['open']; b2=c2['close']-c2['open']; b3=c3['close']-c3['open']
            if b1*b2>0 and b2*b3>0 and min(abs(b1),abs(b2),abs(b3))>0.1*atr and abs(b1+b2+b3)>=0.5*atr:
                d = 'long' if b3>0 else 'short'
                pi = candles.index.get_loc(sess.index[i]); e = c3['close']
                b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
                pnl = (ex-e) if d == 'long' else (e-ex)
                t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b})
                if cooldown: break
    S['R'] = t

    # S: 3 soldiers London reversal
    t = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        sess = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))]
        if len(sess) < 6: continue
        for i in range(2, len(sess)):
            c1=sess.iloc[i-2]; c2=sess.iloc[i-1]; c3=sess.iloc[i]
            b1=c1['close']-c1['open']; b2=c2['close']-c2['open']; b3=c3['close']-c3['open']
            if b1*b2>0 and b2*b3>0 and min(abs(b1),abs(b2),abs(b3))>0.1*atr and abs(b1+b2+b3)>=0.5*atr:
                d = 'short' if b3>0 else 'long'
                pi = candles.index.get_loc(sess.index[i]); e = c3['close']
                b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
                pnl = (ex-e) if d == 'long' else (e-ex)
                t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b})
                if cooldown: break
    S['S'] = t

    # ── Strats a horaire fixe (A, C, D, E, G, H, I, J) — 1 signal/jour par nature ──
    # A: IB Tokyo
    t = []
    for day in trading_days:
        p = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
        if len(p) < 18: continue
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        lvl = p.iloc[:12]['high'].max()
        for i in range(12, len(p)):
            if p.iloc[i]['close'] > lvl:
                pi = candles.index.get_loc(p.index[i]); e = p.iloc[i]['close']
                b, ex = sim_trail(candles, pi, e, 'long', SL, atr, 24, ACT, TRAIL)
                t.append({'date':day,'dir':'long','sl_atr':SL,'pnl_oz':(ex-e)-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b}); break
    S['A'] = t

    # C
    t = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        tok = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
        if len(tok) < 10: continue
        m = (tok.iloc[-1]['close'] - tok.iloc[0]['open']) / atr
        if abs(m) < 1.0: continue
        lon = candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
        if len(lon) < 6: continue
        pi = candles.index.get_loc(lon.index[0]); e = lon.iloc[0]['open']
        d = 'short' if m > 0 else 'long'
        b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
        pnl = (ex-e) if d == 'long' else (e-ex)
        t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b})
    S['C'] = t

    # D
    t = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        tc = candles[candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC')]
        if len(tc) < 5: continue
        lon = candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
        if len(lon) < 6: continue
        gap = (lon.iloc[0]['open'] - tc.iloc[-1]['close']) / atr
        if abs(gap) < 0.5: continue
        pi = candles.index.get_loc(lon.index[0]); e = lon.iloc[0]['open']
        d = 'long' if gap > 0 else 'short'
        b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
        pnl = (ex-e) if d == 'long' else (e-ex)
        t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b})
    S['D'] = t

    # E
    t = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        kz = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,10,0,tz='UTC'))]
        if len(kz) < 20: continue
        m = (kz.iloc[-1]['close'] - kz.iloc[0]['open']) / atr
        if abs(m) < 0.5: continue
        post = candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,10,0,tz='UTC')]
        if len(post) < 6: continue
        pi = candles.index.get_loc(post.index[0]); e = post.iloc[0]['open']
        d = 'short' if m > 0 else 'long'
        b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
        pnl = (ex-e) if d == 'long' else (e-ex)
        t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b})
    S['E'] = t

    # G
    t = []
    for day in trading_days:
        p = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,21,30,tz='UTC'))]
        if len(p) < 6: continue
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        body = p.iloc[0]['close'] - p.iloc[0]['open']
        if abs(body) < 0.3*atr or len(p) < 2: continue
        d = 'long' if body > 0 else 'short'
        pi = candles.index.get_loc(p.index[1]); e = p.iloc[1]['open']
        b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
        pnl = (ex-e) if d == 'long' else (e-ex)
        t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b})
    S['G'] = t

    # H
    t = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        tok = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
        if len(tok) < 9: continue
        last3 = tok.iloc[-3:]
        m = (last3.iloc[-1]['close'] - last3.iloc[0]['open']) / atr
        if abs(m) < 1.0: continue
        lon = candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')]
        if len(lon) < 6: continue
        pi = candles.index.get_loc(lon.index[0]); e = lon.iloc[0]['open']
        d = 'long' if m > 0 else 'short'
        b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
        pnl = (ex-e) if d == 'long' else (e-ex)
        t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b})
    S['H'] = t

    # I
    t = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        ny1 = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,15,30,tz='UTC'))]
        if len(ny1) < 10: continue
        m = (ny1.iloc[-1]['close'] - ny1.iloc[0]['open']) / atr
        if abs(m) < 1.0: continue
        post = candles[candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,15,30,tz='UTC')]
        if len(post) < 6: continue
        pi = candles.index.get_loc(post.index[0]); e = post.iloc[0]['open']
        d = 'short' if m > 0 else 'long'
        b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
        pnl = (ex-e) if d == 'long' else (e-ex)
        t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b})
    S['I'] = t

    # J
    t = []
    for day in trading_days:
        p = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))]
        if len(p) < 6: continue
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        body = p.iloc[0]['close'] - p.iloc[0]['open']
        if abs(body) < 0.3*atr or len(p) < 2: continue
        d = 'long' if body > 0 else 'short'
        pi = candles.index.get_loc(p.index[1]); e = p.iloc[1]['open']
        b, ex = sim_trail(candles, pi, e, d, SL, atr, 24, ACT, TRAIL)
        pnl = (ex-e) if d == 'long' else (e-ex)
        t.append({'date':day,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b})
    S['J'] = t

    # P: ORB NY 30min
    t = []
    for day in trading_days:
        pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        if atr == 0: continue
        ny = candles[(candles['ts_dt']>=pd.Timestamp(day.year,day.month,day.day,14,30,tz='UTC'))&(candles['ts_dt']<pd.Timestamp(day.year,day.month,day.day,21,30,tz='UTC'))]
        if len(ny) < 12: continue
        orb_h = ny.iloc[:6]['high'].max(); orb_l = ny.iloc[:6]['low'].min()
        for i in range(6, len(ny)):
            r = ny.iloc[i]
            if r['close'] > orb_h:
                pi = candles.index.get_loc(ny.index[i]); e = r['close']
                b, ex = sim_trail(candles, pi, e, 'long', SL, atr, 24, ACT, TRAIL)
                t.append({'date':day,'dir':'long','sl_atr':SL,'pnl_oz':(ex-e)-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b})
                if cooldown: break
            elif r['close'] < orb_l:
                pi = candles.index.get_loc(ny.index[i]); e = r['close']
                b, ex = sim_trail(candles, pi, e, 'short', SL, atr, 24, ACT, TRAIL)
                t.append({'date':day,'dir':'short','sl_atr':SL,'pnl_oz':(e-ex)-get_sp(day),'atr':atr,'ei':pi,'xi':pi+b})
                if cooldown: break
    S['P'] = t

    return S

def eval_portfolio(S, strats, label, capital=1000.0, risk=0.01):
    combined = []
    for sn in strats:
        for t in S[sn]: combined.append({**t, 'strat': sn})
    if len(combined) < 10: return None
    combined.sort(key=lambda x: (x['ei'], x['strat']))
    # Conflict resolution
    al = []; acc = []
    for t in combined:
        al = [(xi, d) for xi, d in al if xi >= t['ei']]
        if any(d != t['dir'] for _, d in al): continue
        acc.append(t); al.append((t['xi'], t['dir']))
    if len(acc) < 10: return None
    cap = capital; peak = cap; max_dd = 0; gp = 0; gl = 0; wins = 0; months = {}
    for t in acc:
        pnl = t['pnl_oz'] * (cap * risk) / (t['sl_atr'] * t['atr'])
        cap += pnl
        if cap > peak: peak = cap
        dd = (cap - peak) / peak
        if dd < max_dd: max_dd = dd
        if pnl > 0: gp += pnl; wins += 1
        else: gl += abs(pnl)
        mo = str(t['date'].year)+"-"+str(t['date'].month).zfill(2)
        months[mo] = months.get(mo, 0) + pnl
    n = len(acc)
    ret = (cap - capital) / capital * 100
    mdd = max_dd * 100
    pf = gp / (gl + 0.01)
    wr = wins / n * 100
    pm = sum(1 for v in months.values() if v > 0)
    tm = len(months)
    return {'label': label, 'n': n, 'tpd': n/n_td, 'capital': cap,
            'ret': ret, 'mdd': mdd, 'cal': ret/abs(mdd) if mdd < 0 else 0,
            'pf': pf, 'wr': wr, 'pm': pm, 'tm': tm}

strats = ['A','C','D','E','F','G','H','I','J','O','P','Q','R','S']

print("Calcul avec cooldown (1/strat/jour)...", flush=True)
S_cd = collect_trades(cooldown=True)
print("Calcul SANS cooldown (multi/strat/jour)...", flush=True)
S_nocd = collect_trades(cooldown=False)

conn.close()

# Stats individuelles
print("\n" + "="*80)
print("TRADES PAR STRAT — cooldown vs no-cooldown")
print("="*80)
print(f"  {'Strat':5s} {'CD n':>6s} {'noCD n':>6s} {'CD PF':>6s} {'noCD PF':>7s}")
for sn in sorted(strats):
    cd = pd.DataFrame(S_cd[sn]); nocd = pd.DataFrame(S_nocd[sn])
    cd_pf = cd[cd['pnl_oz']>0]['pnl_oz'].sum() / (abs(cd[cd['pnl_oz']<0]['pnl_oz'].sum())+0.001) if len(cd)>0 else 0
    nocd_pf = nocd[nocd['pnl_oz']>0]['pnl_oz'].sum() / (abs(nocd[nocd['pnl_oz']<0]['pnl_oz'].sum())+0.001) if len(nocd)>0 else 0
    print(f"  {sn:5s} {len(cd):6d} {len(nocd):6d} {cd_pf:6.2f} {nocd_pf:7.2f}")

# Portfolio
print("\n" + "="*80)
print("PORTFOLIO — $1000, Risk 1%")
print("="*80)
print(f"  {'Label':40s} {'n':>5s} {'t/j':>5s} {'Capital':>12s} {'Rend%':>8s} {'DD%':>7s} {'Cal':>7s} {'PF':>5s} {'WR%':>4s} {'M+':>5s}")

for label, S_data in [("AVEC cooldown (1/strat/jour)", S_cd), ("SANS cooldown (multi/strat/jour)", S_nocd)]:
    r = eval_portfolio(S_data, strats, label)
    if r:
        print(f"  {r['label']:40s} {r['n']:5d} {r['tpd']:5.1f} {r['capital']:12,.0f}$ {r['ret']:+7.0f}% {r['mdd']:+6.1f}% {r['cal']:7.1f} {r['pf']:.2f} {r['wr']:3.0f}% {r['pm']:2.0f}/{r['tm']:.0f}")

print("="*80)
