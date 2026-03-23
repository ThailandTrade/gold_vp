"""Test: multi-trigger par jour (pas de limite 1/strat/jour)."""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
from dotenv import load_dotenv; load_dotenv()
from phase1_poc_calculator import get_conn, compute_atr, get_trading_days
from phase3_analyze import load_candles_5m
from strats import compute_indicators, detect_all, sim_exit_custom
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

def prev_day(day):
    for di, d in enumerate(trading_days):
        if d >= day: return trading_days[di-1] if di > 0 else None
    return None
def get_sp(day):
    return 2 * monthly_spread.get(str(day.year)+"-"+str(day.month).zfill(2), avg_sp)

OPEN_STRATS = {'TOK_FADE','TOK_PREVEXT','LON_GAP','LON_BIGGAP','LON_KZ','LON_TOKEND','LON_PREV','NY_GAP','NY_LONEND','NY_LONMOM','NY_DAYMOM'}
PORTFOLIO = ['PO3_SWEEP','ALL_3SOLDIERS','LON_KZ','LON_TOKEND','ALL_PSAR_EMA','ALL_FVG_BULL',
             'ALL_CONSEC_REV','ALL_MACD_RSI','ALL_FIB_618','TOK_BIG','TOK_2BAR']

c = candles.copy()
c = compute_indicators(c)

for mode_name, use_trig in [("1 TRIGGER/JOUR", True), ("MULTI TRIGGER", False)]:
    S = {}
    prev_d = None; trig = {}; day_atr = None; prev_day_data = None; prev2_day_data = None
    for ci in range(200, len(c)):
        row = c.iloc[ci]; ct = row['ts_dt']; today = ct.date()
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

        if use_trig:
            # Mode normal: 1 trigger par strat par jour
            local_trig = trig
        else:
            # Mode multi: reset trig a chaque bougie
            local_trig = {}

        def add(sn, d, e):
            if sn not in PORTFOLIO: return
            is_open = sn in OPEN_STRATS
            exit_cfg = STRAT_EXITS.get(sn, DEFAULT_EXIT)
            etype, p1, p2, p3 = exit_cfg
            b, ex = sim_exit_custom(c, ci, e, d, atr, etype, p1, p2, p3, check_entry_candle=is_open)
            pnl = (ex-e) if d=='long' else (e-ex)
            S.setdefault(sn,[]).append({'date':today,'dir':d,'sl_atr':p1,'pnl_oz':pnl-get_sp(today),'atr':atr,'ei':ci,'xi':ci+b})

        detect_all(c, ci, row, ct, today, hour, atr, local_trig, tv, tok, lon, prev_day_data, add, prev2_day_data)

    # Build arrays + eval combo
    strat_arrays = {}
    for sn in PORTFOLIO:
        if sn not in S: continue
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
        if len(combined) < 10: return None
        combined.sort(key=lambda x: (x[0], x[7]))
        active = []; accepted = []
        for ei, xi, di, pnl_oz, sl_atr, atr, mo, _sn in combined:
            active = [(axi, ad) for axi, ad in active if axi >= ei]
            if any(ad != di for _, ad in active): continue
            accepted.append((ei, xi, di, pnl_oz, sl_atr, atr, mo, _sn))
            active.append((xi, di))
        n = len(accepted)
        if n < 10: return None
        cap = capital; peak = cap; max_dd = 0; gp = 0; gl = 0; wins = 0; months = {}
        for ei, xi, di, pnl_oz, sl_atr, atr, mo, _sn in accepted:
            pnl = pnl_oz * (cap * risk) / (sl_atr * atr)
            cap += pnl
            if cap > peak: peak = cap
            dd = (cap - peak) / peak
            if dd < max_dd: max_dd = dd
            if pnl > 0: gp += pnl; wins += 1
            else: gl += abs(pnl)
            months[mo] = months.get(mo, 0.0) + pnl
        mdd = max_dd * 100; ret = (cap - capital) / capital * 100
        pm = sum(1 for v in months.values() if v > 0)
        return {'n': n, 'ret': ret, 'mdd': mdd, 'pf': gp/(gl+0.01), 'wr': wins/n*100, 'pm': pm, 'tm': len(months)}

    print(f"\n{'='*90}")
    print(f"  {mode_name}")
    print(f"{'='*90}")

    # Per-strat stats
    print(f"\n  {'Strat':>22s} {'n':>6s} {'PF':>6s} {'WR':>5s} {'Avg':>8s}")
    print(f"  {'-'*55}")
    total_trades = 0
    for sn in PORTFOLIO:
        if sn not in S: continue
        t = S[sn]; n = len(t); total_trades += n
        pnls = [x['pnl_oz'] for x in t]
        gp = sum(p for p in pnls if p>0); gl = abs(sum(p for p in pnls if p<0))+0.001
        wr = sum(1 for p in pnls if p>0)/n*100
        print(f"  {sn:>22s} {n:6d} {gp/gl:6.2f} {wr:4.0f}% {np.mean(pnls):+8.3f}")

    r = eval_combo(PORTFOLIO)
    if r:
        print(f"\n  COMBO: n={r['n']} PF={r['pf']:.2f} WR={r['wr']:.0f}% DD={r['mdd']:+.1f}% Rend={r['ret']:+.0f}% M+={r['pm']}/{r['tm']}")
        print(f"  Total signaux: {total_trades} | Acceptes apres filtre conflit: {r['n']}")
