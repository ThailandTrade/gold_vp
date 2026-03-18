"""
Exploration v4 — derniers concepts pas encore testes.
"""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd
from dotenv import load_dotenv
from datetime import datetime, timedelta
load_dotenv()
from phase1_poc_calculator import (
    get_conn, compute_atr, get_trading_days
)
from phase3_analyze import load_candles_5m

SLIPPAGE = 0.10

def sim_trail(cdf, pos, entry, d, sl, atr, mx, act, trail):
    best = entry
    stop = entry + sl*atr if d == 'short' else entry - sl*atr
    ta = False
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

def pr(trades, label, spread_rt=0.188):
    if len(trades) < 20:
        print("    {:60s}: n={:3d} --".format(label, len(trades)))
        return
    df = pd.DataFrame(trades).sort_values('date')
    n = len(df); mid = n // 2
    df['net'] = df['pnl_oz'] - spread_rt
    gp = df[df['net']>0]['net'].sum()
    gl = abs(df[df['net']<0]['net'].sum())+0.001
    pf = gp/gl; wr = (df['net']>0).mean()*100
    f1 = (df.iloc[:mid]['net']/df.iloc[:mid]['atr']).mean()
    f2 = (df.iloc[mid:]['net']/df.iloc[mid:]['atr']).mean()
    ok = "OK" if f1>0 and f2>0 else "!!" if f1<0 and f2<0 else "~ "
    flag = " ***" if pf >= 1.3 and f1>0 and f2>0 else ""
    print("    {:60s}: n={:4d} WR={:4.0f}% PF={:.2f} [{:+.3f}|{:+.3f}] {}{}".format(
        label, n, wr, pf, f1, f2, ok, flag))

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
SPREAD_RT = 2 * avg_sp

def prev_day(day):
    for di, d in enumerate(trading_days):
        if d >= day: return trading_days[di-1] if di > 0 else None
    return None

print("=" * 80)
print("EXPLORATION v4 (spread {:.3f} RT)".format(SPREAD_RT))
print("=" * 80)

# ══════════════════════════════════════════════════════
# 1. LONDON CLOSE (16h UTC) — derniere heure patterns
# ══════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("1. LONDON CLOSE — Fading le move de la session a 16h")
print("=" * 80)

for thresh in [1.0, 2.0, 3.0]:
    for sl, act, trail in [(0.75, 0.5, 0.3)]:
        trades = []
        for day in trading_days:
            pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
            if atr == 0: continue
            # Move London 8h-16h
            lon_s = pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')
            lon_16 = pd.Timestamp(day.year,day.month,day.day,16,0,tz='UTC')
            lon = candles[(candles['ts_dt'] >= lon_s) & (candles['ts_dt'] < lon_16)]
            if len(lon) < 20: continue
            lon_move = (lon.iloc[-1]['close'] - lon.iloc[0]['open']) / atr
            if abs(lon_move) < thresh: continue
            # Entrer a 16h dans le sens inverse
            post = candles[candles['ts_dt'] >= lon_16]
            if len(post) < 6: continue
            pi = candles.index.get_loc(post.index[0])
            entry = post.iloc[0]['open']
            d = 'short' if lon_move > 0 else 'long'
            bars, ex = sim_trail(candles, pi, entry, d, sl, atr, 24, act, trail)
            pnl = (ex-entry) if d == 'long' else (entry-ex)
            trades.append({'date': day, 'pnl_oz': pnl, 'atr': atr})
        pr(trades, "London close fade >{:.0f}ATR SL={}".format(thresh, sl))

# ══════════════════════════════════════════════════════
# 2. BREAKOUT RETEST — IB break, retour au niveau, puis continuation
# ══════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("2. BREAKOUT RETEST — Break IB, retour, puis re-break")
print("=" * 80)

for sess_name, sh, eh, ib_b in [('TOKYO', 0, 6, 12)]:
    for sl, act, trail in [(0.75, 0.5, 0.3)]:
        trades = []
        for day in trading_days:
            obs_s = pd.Timestamp(day.year,day.month,day.day,sh,0,tz='UTC')
            obs_e = pd.Timestamp(day.year,day.month,day.day,eh,0,tz='UTC')
            period = candles[(candles['ts_dt'] >= obs_s) & (candles['ts_dt'] < obs_e)]
            if len(period) < ib_b + 12: continue
            pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
            if atr == 0: continue
            ib_high = period.iloc[:ib_b]['high'].max()
            rest = period.iloc[ib_b:]
            # Phase 1: break UP
            broke = False; retested = False
            for i in range(len(rest)):
                r = rest.iloc[i]
                if not broke and r['close'] > ib_high:
                    broke = True; continue
                if broke and not retested:
                    # Retest: le prix revient toucher le IB high (support)
                    if r['low'] <= ib_high + 0.1*atr and r['close'] > ib_high:
                        retested = True
                        pi = candles.index.get_loc(rest.index[i])
                        entry = r['close']
                        bars, ex = sim_trail(candles, pi, entry, 'long', sl, atr, 24, act, trail)
                        trades.append({'date': day, 'pnl_oz': ex-entry, 'atr': atr})
                        break
                    # Si le prix casse sous le IB high, le retest a echoue
                    if r['close'] < ib_high - 0.25*atr:
                        break
        pr(trades, "{} retest UP SL={}".format(sess_name, sl))

# ══════════════════════════════════════════════════════
# 3. HIGHER TF ENGULFING — engulfing sur bougies 15min
# ══════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("3. ENGULFING 15min — bougies plus grandes = signal plus fort ?")
print("=" * 80)

# Creer des bougies 15min a partir des 5min
candles_15m = candles.copy()
candles_15m['ts_15m'] = (candles_15m['ts'] // (15*60*1000)) * (15*60*1000)
c15 = candles_15m.groupby('ts_15m').agg(
    open=('open', 'first'), high=('high', 'max'),
    low=('low', 'min'), close=('close', 'last'),
    ts_dt=('ts_dt', 'first'), date=('date', 'first')
).reset_index()

for sess_name, sh, eh in [('TOKYO', 0, 6), ('LONDON', 8, 14)]:
    for sl, act, trail in [(0.75, 0.5, 0.3), (1.0, 1.0, 0.5)]:
        trades = []
        for day in trading_days:
            obs_s = pd.Timestamp(day.year,day.month,day.day,sh,0,tz='UTC')
            obs_e = pd.Timestamp(day.year,day.month,day.day,eh,0,tz='UTC')
            period = c15[(c15['ts_dt'] >= obs_s) & (c15['ts_dt'] < obs_e)]
            if len(period) < 4: continue
            pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
            if atr == 0: continue
            for i in range(1, len(period)):
                pc = period.iloc[i-1]; cc = period.iloc[i]
                pb = abs(pc['close']-pc['open']); cb = abs(cc['close']-cc['open'])
                bull = (pc['close']<pc['open'] and cc['close']>cc['open'] and cb>pb and
                        cc['open']<=pc['close'] and cc['close']>=pc['open'])
                bear = (pc['close']>pc['open'] and cc['close']<cc['open'] and cb>pb and
                        cc['open']>=pc['close'] and cc['close']<=pc['open'])
                if bull or bear:
                    # Trouver l'index dans les candles 5m
                    cc_ts = cc['ts_15m']
                    idx_5m = candles[candles['ts'] >= cc_ts + 15*60*1000]
                    if len(idx_5m) < 6: break
                    pi = candles.index.get_loc(idx_5m.index[0])
                    entry = cc['close']; d = 'long' if bull else 'short'
                    bars, ex = sim_trail(candles, pi, entry, d, sl, atr, 24, act, trail)
                    pnl = (ex-entry) if d == 'long' else (entry-ex)
                    trades.append({'date': day, 'pnl_oz': pnl, 'atr': atr})
                    break
        pr(trades, "{} engulf 15m SL={} act={} trail={}".format(sess_name, sl, act, trail))

# ══════════════════════════════════════════════════════
# 4. NIVEAUX RONDS — le prix reagit-il a $XX00 ou $XX50 ?
# ══════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("4. NIVEAUX RONDS — reaction a $XX00 et $XX50")
print("=" * 80)

for level_mod in [100, 50]:
    for sl, act, trail in [(0.75, 0.5, 0.3)]:
        trades_bounce = []
        cooldown = -20
        for idx in range(1, len(candles) - 12):
            if idx - cooldown < 12: continue
            r = candles.iloc[idx]
            day = r['date']
            pd_ = prev_day(day)
            atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
            if atr == 0: continue
            price = r['close']
            # Nearest round level
            nearest = round(price / level_mod) * level_mod
            dist = abs(price - nearest) / atr
            if dist > 0.3: continue  # trop loin
            # Direction: le prix vient d'en haut ou d'en bas ?
            prev_price = candles.iloc[idx-1]['close']
            if prev_price > nearest and price <= nearest + 0.15*atr:
                # Vient d'en haut, touche le niveau -> bounce UP ?
                d = 'long'
            elif prev_price < nearest and price >= nearest - 0.15*atr:
                # Vient d'en bas, touche le niveau -> bounce DOWN ?
                d = 'short'
            else:
                continue
            pi = idx; entry = price
            bars, ex = sim_trail(candles, pi, entry, d, sl, atr, 12, act, trail)
            pnl = (ex-entry) if d == 'long' else (entry-ex)
            trades_bounce.append({'date': day, 'pnl_oz': pnl, 'atr': atr})
            cooldown = idx
        pr(trades_bounce, "Round ${} bounce SL={}".format(level_mod, sl))

# ══════════════════════════════════════════════════════
# 5. SESSION EXTREME REVERSAL — high/low de la session en cours
# ══════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("5. SESSION EXTREME — prix touche le running high/low puis reverse")
print("=" * 80)

for sess_name, sh, eh in [('TOKYO', 0, 6), ('LONDON', 8, 14)]:
    sm = 0; em = 30 if eh == 14 else 0
    for min_bars_before in [6, 12]:  # attendre au moins N bougies avant de chercher
        for sl, act, trail in [(0.75, 0.5, 0.3)]:
            trades = []
            for day in trading_days:
                obs_s = pd.Timestamp(day.year,day.month,day.day,sh,sm,tz='UTC')
                obs_e = pd.Timestamp(day.year,day.month,day.day,eh,em,tz='UTC')
                period = candles[(candles['ts_dt'] >= obs_s) & (candles['ts_dt'] < obs_e)]
                if len(period) < min_bars_before + 6: continue
                pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
                if atr == 0: continue
                traded = False
                for i in range(min_bars_before, len(period)):
                    if traded: break
                    r = period.iloc[i]
                    running_high = period.iloc[:i]['high'].max()
                    running_low = period.iloc[:i]['low'].min()
                    # Nouveau high suivi d'un close bearish = rejection
                    if r['high'] >= running_high and r['close'] < r['open']:
                        pi = candles.index.get_loc(period.index[i])
                        entry = r['close']
                        bars, ex = sim_trail(candles, pi, entry, 'short', sl, atr, 24, act, trail)
                        trades.append({'date': day, 'pnl_oz': entry-ex, 'atr': atr})
                        traded = True
                    # Nouveau low suivi d'un close bullish = rejection
                    elif r['low'] <= running_low and r['close'] > r['open']:
                        pi = candles.index.get_loc(period.index[i])
                        entry = r['close']
                        bars, ex = sim_trail(candles, pi, entry, 'long', sl, atr, 24, act, trail)
                        trades.append({'date': day, 'pnl_oz': ex-entry, 'atr': atr})
                        traded = True
            pr(trades, "{} extreme rev after {}b SL={}".format(sess_name, min_bars_before, sl))

# ══════════════════════════════════════════════════════
# 6. COMBO TEMPOREL — 2BAR + KZ le meme jour = double signal
# ══════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("6. ANALYSE : 2BAR matin predit-il la direction de KZ ?")
print("=" * 80)

twobar_dirs = {}
for day in trading_days:
    period = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,0,0,tz='UTC')) &
                     (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,6,0,tz='UTC'))]
    if len(period) < 8: continue
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    for i in range(1, len(period)):
        b1 = period.iloc[i-1]; b2 = period.iloc[i]
        b1b = b1['close']-b1['open']; b2b = b2['close']-b2['open']
        if abs(b1b) >= 0.5*atr and abs(b2b) >= 0.5*atr and b1b*b2b < 0 and abs(b2b) > abs(b1b):
            twobar_dirs[day] = 'long' if b2b > 0 else 'short'
            break

kz_dirs = {}
for day in trading_days:
    pd_ = prev_day(day); atr = daily_atr.get(pd_, global_atr) if pd_ else global_atr
    if atr == 0: continue
    kz = candles[(candles['ts_dt'] >= pd.Timestamp(day.year,day.month,day.day,8,0,tz='UTC')) &
                 (candles['ts_dt'] < pd.Timestamp(day.year,day.month,day.day,10,0,tz='UTC'))]
    if len(kz) < 20: continue
    kz_move = (kz.iloc[-1]['close'] - kz.iloc[0]['open']) / atr
    if abs(kz_move) >= 0.5:
        kz_dirs[day] = 'short' if kz_move > 0 else 'long'  # fade

both_days = set(twobar_dirs.keys()) & set(kz_dirs.keys())
agree = sum(1 for d in both_days if twobar_dirs[d] == kz_dirs[d])
disagree = len(both_days) - agree
print("  Jours avec 2BAR + KZ: {}".format(len(both_days)))
print("  Meme direction: {} ({:.0f}%)".format(agree, agree/max(len(both_days),1)*100))
print("  Direction opposee: {} ({:.0f}%)".format(disagree, disagree/max(len(both_days),1)*100))

conn.close()
print("\n" + "=" * 80)
print("FIN v4")
print("=" * 80)
