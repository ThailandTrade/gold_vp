"""
Backtest complet d'un portfolio.
Usage:
  python bt_portfolio.py                        → ICM, $1000, 1%
  python bt_portfolio.py ftmo                   → FTMO, $1000, 0.5%
  python bt_portfolio.py 5ers                   → 5ers, $1000, 0.5%
  python bt_portfolio.py icm -c 100000 -r 2     → ICM, $100k, 2%
"""
import warnings; warnings.filterwarnings('ignore')
import sys, argparse; sys.stdout.reconfigure(encoding='utf-8')
import numpy as np, pandas as pd, pickle
from strat_exits import STRAT_EXITS, DEFAULT_EXIT

parser = argparse.ArgumentParser(description='Backtest portfolio')
parser.add_argument('account', nargs='?', default='icm', choices=['icm','ftmo','5ers'])
parser.add_argument('-c', '--capital', type=float, default=None, help='Capital initial (default: 1000)')
parser.add_argument('-r', '--risk', type=float, default=None, help='Risk %% par trade (ex: 1 pour 1%%)')
args = parser.parse_args()

if args.account == 'ftmo':
    from config_ftmo import PORTFOLIO, RISK_PCT, BROKER
elif args.account == '5ers':
    from config_5ers import PORTFOLIO, RISK_PCT, BROKER
else:
    from config_icm import PORTFOLIO, RISK_PCT, BROKER

CAPITAL = args.capital if args.capital else 1000.0
RISK = args.risk / 100 if args.risk else RISK_PCT

# ── LOAD DATA ──
try:
    pkl_file = f'optim_data_{args.account}.pkl'
    with open(pkl_file, 'rb') as f:
        data = pickle.load(f)
    strat_arrays = data['strat_arrays']
    print(f"Loaded {pkl_file}")
except FileNotFoundError:
    print(f"ERROR: {pkl_file} not found. Run: python optimize_all.py {args.account}")
    sys.exit(1)

missing = [s for s in PORTFOLIO if s not in strat_arrays]
if missing:
    print(f"WARNING: strats missing: {missing}")

# ── SIMULATE ──
combined = []
for sn in PORTFOLIO:
    if sn in strat_arrays: combined.extend(strat_arrays[sn])
combined.sort(key=lambda x: (x[0], x[7]))

# Conflict filter
active = []; accepted = []
for ei, xi, di, pnl_oz, sl_atr, atr, mo, _sn in combined:
    active = [(axi, ad) for axi, ad in active if axi >= ei]
    if any(ad != di for _, ad in active): continue
    accepted.append((ei, xi, di, pnl_oz, sl_atr, atr, mo, _sn))
    active.append((xi, di))

# Event-based PnL
events = []
for idx, (ei, xi, di, pnl_oz, sl_atr, atr, mo, _sn) in enumerate(accepted):
    events.append((ei, 0, idx))
    events.append((xi, 1, idx))
events.sort()

cap = CAPITAL; peak = cap; max_dd = 0
entry_caps = {}
trades = []  # full trade log

for bar, evt, idx in events:
    if evt == 0:
        entry_caps[idx] = cap
    else:
        ei, xi, di, pnl_oz, sl_atr, atr, mo, _sn = accepted[idx]
        entry_cap = entry_caps[idx]
        pnl = pnl_oz * (entry_cap * RISK) / (sl_atr * atr)
        cap += pnl
        if cap > peak: peak = cap
        dd = (cap - peak) / peak
        if dd < max_dd: max_dd = dd
        trades.append({
            'strat': _sn, 'dir': 'long' if di == 1 else 'short',
            'pnl': pnl, 'pnl_oz': pnl_oz, 'month': mo,
            'bars': xi - ei, 'cap_after': cap, 'dd': dd * 100,
            'entry_cap': entry_cap,
        })

df = pd.DataFrame(trades)
n = len(df)
wins = df[df['pnl'] > 0]; losses = df[df['pnl'] <= 0]
gp = wins['pnl'].sum() if len(wins) else 0
gl = abs(losses['pnl'].sum()) + 0.01
pf = gp / gl
wr = len(wins) / n * 100 if n > 0 else 0

# ══════════════════════════════════════════════════════════════════════
# REPORT
# ══════════════════════════════════════════════════════════════════════
W = 90
print(f"\n{'='*W}")
print(f"  BACKTEST {BROKER} — {len(PORTFOLIO)} strats @ {RISK*100:.1f}% risk — ${CAPITAL:,.0f}")
print(f"{'='*W}")

# ── RESUME ──
print(f"\n  {'Trades':.<20s} {n:,d} ({n/(df['month'].nunique()*20):.1f}/jour)")
print(f"  {'Profit Factor':.<20s} {pf:.2f}")
print(f"  {'Win Rate':.<20s} {wr:.0f}% ({len(wins)}W / {len(losses)}L)")
print(f"  {'Max Drawdown':.<20s} {max_dd*100:+.1f}%")
print(f"  {'Rendement':.<20s} {(cap-CAPITAL)/CAPITAL*100:+,.1f}%")
print(f"  {'Capital final':.<20s} ${cap:,.0f} (start ${CAPITAL:,.0f})")
mpos = sum(1 for m, g in df.groupby('month')['pnl'].sum().items() if g > 0)
mtot = df['month'].nunique()
print(f"  {'Mois positifs':.<20s} {mpos}/{mtot}")

if len(wins) > 0 and len(losses) > 0:
    print(f"  {'Avg win':.<20s} ${wins['pnl'].mean():+,.2f}")
    print(f"  {'Avg loss':.<20s} ${losses['pnl'].mean():+,.2f}")
    print(f"  {'Avg win/loss':.<20s} {abs(wins['pnl'].mean()/losses['pnl'].mean()):.2f}")
    print(f"  {'Bars moyen':.<20s} {df['bars'].mean():.1f} ({df['bars'].mean()*5:.0f}min)")

    # Streaks
    is_win = (df['pnl'] > 0).values
    max_ws = max_ls = cur = 0; last = None
    for w in is_win:
        if w == last: cur += 1
        else: cur = 1; last = w
        if w and cur > max_ws: max_ws = cur
        if not w and cur > max_ls: max_ls = cur
    print(f"  {'Max win streak':.<20s} {max_ws}")
    print(f"  {'Max loss streak':.<20s} {max_ls}")

    # Expectancy
    exp = df['pnl'].mean()
    print(f"  {'Expectancy/trade':.<20s} ${exp:+,.2f}")

# ── MOIS PAR MOIS ──
print(f"\n{'-'*W}")
print(f"  MOIS PAR MOIS")
print(f"{'-'*W}")
print(f"  {'Mois':>8s} {'Trades':>7s} {'Wins':>5s} {'WR':>5s} {'PF':>5s} {'PnL $':>12s} {'DD max':>8s} {'Capital':>12s}")
print(f"  {'-'*8} {'-'*7} {'-'*5} {'-'*5} {'-'*5} {'-'*12} {'-'*8} {'-'*12}")

monthly = df.groupby('month')
for mo in sorted(df['month'].unique()):
    mg = monthly.get_group(mo)
    mn = len(mg); mw = (mg['pnl'] > 0).sum()
    mgp = mg[mg['pnl']>0]['pnl'].sum(); mgl = abs(mg[mg['pnl']<0]['pnl'].sum()) + 0.01
    mpf = mgp / mgl
    mpnl = mg['pnl'].sum()
    mdd = mg['dd'].min()
    mcap = mg['cap_after'].iloc[-1]
    sign = '+' if mpnl >= 0 else ''
    print(f"  {mo:>8s} {mn:7d} {mw:5d} {mw/mn*100:4.0f}% {mpf:5.2f} ${mpnl:>+11,.0f} {mdd:+7.1f}% ${mcap:>11,.0f}")

# Totals
print(f"  {'-'*8} {'-'*7} {'-'*5} {'-'*5} {'-'*5} {'-'*12} {'-'*8} {'-'*12}")
print(f"  {'TOTAL':>8s} {n:7d} {len(wins):5d} {wr:4.0f}% {pf:5.2f} ${gp-gl:>+11,.0f} {max_dd*100:+7.1f}% ${cap:>11,.0f}")

# ── PAR STRAT ──
print(f"\n{'-'*W}")
print(f"  PAR STRATEGIE")
print(f"{'-'*W}")
print(f"  {'Strat':>22s} {'Type':>5s} {'SL':>4s} {'n':>5s} {'W':>4s} {'WR':>5s} {'PF':>5s} {'PnL $':>12s} {'Avg $':>9s} {'Bars':>5s}")
print(f"  {'-'*22} {'-'*5} {'-'*4} {'-'*5} {'-'*4} {'-'*5} {'-'*5} {'-'*12} {'-'*9} {'-'*5}")

strat_g = df.groupby('strat')
for sn in PORTFOLIO:
    cfg = STRAT_EXITS.get(sn, DEFAULT_EXIT)
    if sn in strat_g.groups:
        sg = strat_g.get_group(sn)
        sn_n = len(sg); sw = (sg['pnl']>0).sum()
        sgp = sg[sg['pnl']>0]['pnl'].sum(); sgl = abs(sg[sg['pnl']<0]['pnl'].sum()) + 0.01
        spf = sgp / sgl; swr = sw / sn_n * 100
        spnl = sg['pnl'].sum(); savg = sg['pnl'].mean(); sbars = sg['bars'].mean()
        print(f"  {sn:>22s} {cfg[0]:>5s} {cfg[1]:4.1f} {sn_n:5d} {sw:4d} {swr:4.0f}% {spf:5.2f} ${spnl:>+11,.0f} ${savg:>+8,.2f} {sbars:5.1f}")
    else:
        print(f"  {sn:>22s} {cfg[0]:>5s} {cfg[1]:4.1f}     0    0    —     —            $0     $0.00     —")

# ── PAR DIRECTION ──
print(f"\n{'-'*W}")
print(f"  PAR DIRECTION")
print(f"{'-'*W}")
for d in ['long', 'short']:
    dg = df[df['dir'] == d]
    if len(dg) == 0: continue
    dn = len(dg); dw = (dg['pnl']>0).sum()
    dgp = dg[dg['pnl']>0]['pnl'].sum(); dgl = abs(dg[dg['pnl']<0]['pnl'].sum()) + 0.01
    dpnl = dg['pnl'].sum()
    print(f"  {d.upper():>8s}  {dn:5d} trades  WR={dw/dn*100:.0f}%  PF={dgp/dgl:.2f}  PnL=${dpnl:+,.0f}")

# ── PAR SESSION ──
print(f"\n{'-'*W}")
print(f"  PAR SESSION")
print(f"{'-'*W}")
from strats import STRAT_SESSION
sessions = {}
for _, row in df.iterrows():
    s = STRAT_SESSION.get(row['strat'], 'All')
    sessions.setdefault(s, []).append(row['pnl'])

for sess in sorted(sessions.keys()):
    pnls = sessions[sess]
    sn = len(pnls); sw = sum(1 for p in pnls if p > 0)
    sgp = sum(p for p in pnls if p > 0); sgl = abs(sum(p for p in pnls if p < 0)) + 0.01
    spnl = sum(pnls)
    print(f"  {sess:>10s}  {sn:5d} trades  WR={sw/sn*100:.0f}%  PF={sgp/sgl:.2f}  PnL=${spnl:+,.0f}")

# ── DISTRIBUTION ──
print(f"\n{'-'*W}")
print(f"  DISTRIBUTION PnL")
print(f"{'-'*W}")
pnls = df['pnl'].values
pcts = [1, 5, 10, 25, 50, 75, 90, 95, 99]
vals = np.percentile(pnls, pcts)
for p, v in zip(pcts, vals):
    bar = '#' * int(max(0, (v - vals[0]) / (vals[-1] - vals[0] + 0.01) * 40))
    print(f"  P{p:02d}  ${v:>+10,.2f}  {bar}")

# ── EQUITY MENSUELLE (ASCII) ──
print(f"\n{'-'*W}")
print(f"  EQUITY MENSUELLE")
print(f"{'-'*W}")
bar_max = 50
caps_monthly = [CAPITAL]
for mo in sorted(df['month'].unique()):
    mg = monthly.get_group(mo)
    caps_monthly.append(mg['cap_after'].iloc[-1])

months_sorted = ['start'] + sorted(df['month'].unique())
max_cap = max(caps_monthly)
for i, (mo, c) in enumerate(zip(months_sorted, caps_monthly)):
    bar_len = int(c / max_cap * bar_max)
    pnl_mo = c - caps_monthly[i-1] if i > 0 else 0
    pnl_str = f"  ${pnl_mo:+,.0f}" if i > 0 else ""
    print(f"  {mo:>8s} ${c:>12,.0f} {'█' * bar_len}{pnl_str}")

print(f"\n{'='*W}")
