"""
Moteur de backtest commun — utilise par simu_icmarkets.py et simu_ftmo.py.
"""
import numpy as np, pandas as pd
from strats import SL, ACT, TRAIL, sim_exit, detect_all

def run_backtest(candles, daily_atr, global_atr, trading_days, monthly_spread, portfolio, broker_name, capital=1000.0, risk=0.01, spread_override=None):
    avg_sp = np.mean(list(monthly_spread.values())) if monthly_spread else 0.10
    def prev_day(day):
        for di, d in enumerate(trading_days):
            if d >= day: return trading_days[di-1] if di > 0 else None
        return None
    def get_sp(day):
        if spread_override is not None: return spread_override
        return 2 * monthly_spread.get(str(day.year)+"-"+str(day.month).zfill(2), avg_sp)

    S = {}
    prev_d = None; trig = {}; day_atr = None; prev_day_data = None; prev2_day_data = None
    for ci in range(len(candles)):
        row = candles.iloc[ci]; ct = row['ts_dt']; today = ct.date()
        hour = ct.hour + ct.minute / 60.0
        if today != prev_d:
            if prev_d:
                yc = candles[candles['date']==prev_d]
                if len(yc) > 0:
                    prev2_day_data = prev_day_data
                    prev_day_data = {'open': float(yc.iloc[0]['open']), 'close': float(yc.iloc[-1]['close']),
                                     'high': float(yc['high'].max()), 'low': float(yc['low'].min()),
                                     'range': float(yc['high'].max()-yc['low'].min()),
                                     'body': float(yc.iloc[-1]['close']-yc.iloc[0]['open'])}
            prev_d = today; trig = {}
            pd_ = prev_day(today); day_atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
        atr = day_atr
        if atr == 0 or atr is None: continue
        ds = pd.Timestamp(today.year,today.month,today.day,0,0,tz='UTC')
        te = pd.Timestamp(today.year,today.month,today.day,6,0,tz='UTC')
        ls = pd.Timestamp(today.year,today.month,today.day,8,0,tz='UTC')
        ns = pd.Timestamp(today.year,today.month,today.day,14,30,tz='UTC')
        tv = candles[(candles['ts_dt']>=ds)&(candles['ts_dt']<=ct)]
        tok = tv[tv['ts_dt']<te]; lon = tv[(tv['ts_dt']>=ls)&(tv['ts_dt']<ns)]
        def add(sn, d, e):
            if sn not in portfolio: return
            b, ex = sim_exit(candles, ci, e, d, atr)
            pnl = (ex-e) if d=='long' else (e-ex)
            S.setdefault(sn,[]).append({'date':today,'dir':d,'sl_atr':SL,'pnl_oz':pnl-get_sp(today),'atr':atr,'ei':ci,'xi':ci+b})
        detect_all(candles, ci, row, ct, today, hour, atr, trig, tv, tok, lon, prev_day_data, add, prev2_day_data)

    # Combine et filtre conflits
    combined = []
    for sn in portfolio:
        for t in S.get(sn, []): combined.append({**t, 'strat': sn})
    combined.sort(key=lambda x: (x['ei'], x['strat']))
    al = []; acc = []
    for t in combined:
        al = [(xi, d) for xi, d in al if xi >= t['ei']]
        if any(d != t['dir'] for _, d in al): continue
        acc.append(t); al.append((t['xi'], t['dir']))

    # Simulation capital
    cap = capital; peak = cap; global_dd = 0; months = {}
    for t in acc:
        pnl = t['pnl_oz'] * (cap * risk) / (t['sl_atr'] * t['atr'])
        cap += pnl
        if cap > peak: peak = cap
        dd = (cap - peak) / peak * 100
        if dd < global_dd: global_dd = dd
        mo = str(t['date'].year)+"-"+str(t['date'].month).zfill(2)
        if mo not in months:
            months[mo] = {'cap_start': cap-pnl, 'cap_end': cap, 'n': 0, 'wins': 0,
                          'gp': 0, 'gl': 0, 'pnls': [], 'dd_worst': 0}
        m = months[mo]; m['cap_end'] = cap; m['n'] += 1; m['pnls'].append(pnl)
        if pnl > 0: m['wins'] += 1; m['gp'] += pnl
        else: m['gl'] += abs(pnl)
        if dd < m['dd_worst']: m['dd_worst'] = dd
        if cap > peak: peak = cap

    # Affichage
    print(f"\n{'='*110}")
    print(f"  {broker_name} — {len(portfolio)} strats — ${capital:,.0f}, Risk {risk*100:.1f}%")
    print(f"  Config: TRAIL SL={SL} ACT={ACT} TRAIL={TRAIL} (pas de timeout)")
    print(f"  {len(acc)} trades, Capital final ${cap:,.2f}, DD global {global_dd:.1f}%")
    print(f"{'='*110}")

    print(f"\n  Stats par strat:")
    print(f"  {'Strat':14s} {'n':>5s} {'WR':>5s} {'PF':>6s} {'Avg':>8s}")
    for sn in portfolio:
        sn_trades = [t for t in acc if t['strat']==sn]
        if not sn_trades: continue
        sn_pnls = [t['pnl_oz'] for t in sn_trades]
        gp = sum(p for p in sn_pnls if p>0); gl = abs(sum(p for p in sn_pnls if p<0))+0.001
        wr = sum(1 for p in sn_pnls if p>0)/len(sn_pnls)*100
        print(f"  {sn:14s} {len(sn_trades):5d} {wr:4.0f}% {gp/gl:6.2f} {np.mean(sn_pnls):+8.3f}")

    print(f"\n  {'Mois':8s} {'Trades':>7s} {'Wins':>5s} {'WR':>5s} {'PF':>6s} {'Capital':>14s} {'PnL $':>12s} {'PnL%':>8s} {'Max DD':>8s}")
    print(f"  {'-'*95}")
    for mo in sorted(months.keys()):
        m = months[mo]
        wr = m['wins']/m['n']*100 if m['n'] else 0
        pf = m['gp']/(m['gl']+0.01)
        pnl_total = sum(m['pnls'])
        pnl_pct = pnl_total / m['cap_start'] * 100 if m['cap_start'] > 0 else 0
        print(f"  {mo:8s} {m['n']:7d} {m['wins']:5d} {wr:4.0f}% {pf:6.2f} {m['cap_end']:14,.2f} {pnl_total:+12,.2f} {pnl_pct:+7.1f}% {m['dd_worst']:+7.1f}%")

    pm = sum(1 for m in months.values() if sum(m['pnls']) > 0)
    gp_all = sum(m['gp'] for m in months.values())
    gl_all = sum(m['gl'] for m in months.values()) + 0.01
    print(f"  {'-'*95}")
    print(f"  Capital: ${capital:,.0f} -> ${cap:,.2f} ({(cap-capital)/capital*100:+.1f}%)")
    print(f"  Trades: {len(acc)} | WR: {sum(m['wins'] for m in months.values())/len(acc)*100:.0f}% | PF: {gp_all/gl_all:.2f}")
    print(f"  Max DD: {global_dd:.1f}%")
    print(f"  Mois positifs: {pm}/{len(months)}")
    print(f"{'='*110}")
