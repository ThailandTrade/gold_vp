# CLAUDE.md — VP Swing Explorer (XAUUSD 5m)

## Portfolio actif : AA+D+E+F+H+O (1%/trade)

| Metrique | Valeur |
|---|---|
| Rendement | +3,393% |
| Max DD | -18.3% |
| Calmar | 185.3 |
| PF | 1.47 |
| WR | 45% |
| Trades | 1174 (~3.7/jour) |
| Mois positifs | 9/13 |
| Directions | Long (53%) + Short (47%) |

## Strategies (lettres = find_best_v10.py)

| Lettre | Nom | Description | Dir | PF | Session | Horaire |
|---|---|---|---|---|---|---|
| AA | LON_pinbar | Close near extreme (top/bottom 10% range, body>0.2ATR) | L+S | 1.20 | London | 8h-14h30 |
| D | GAP_tok_lon | Gap Tokyo close vs London open >0.5ATR, continuation | L+S | 2.45 | London | 8h |
| E | KZ_lon_fade | London Kill Zone 8h-10h move >0.5ATR, fade a 10h | L+S | 1.57 | London | 10h |
| F | 2BAR_tok_rev | Two-bar reversal Tokyo (body >0.5ATR, 2eme > 1ere) | L+S | 1.71 | Tokyo | 0h-6h |
| H | TOKEND_3b | 3 dernieres bougies Tokyo >1ATR, continuation London | L+S | 4.23 | London | 8h |
| O | BIG_tok | Bougie Tokyo >1ATR, continuation | L+S | 1.42 | Tokyo | 0h-6h |

### Strats eliminees (v10, trailing corrige sur CLOSE)
- A: PF 1.02 sans look-ahead
- AC: PF 1.52 mais split !! en config unique
- C: PF 1.05
- G: PF 1.23, split !!
- I: PF 1.02
- P: PF 1.25
- Q: PF 1.08
- R: PF 1.22, n'ameliore pas le Calmar
- S: PF 1.03
- V: PF 1.37, n'ameliore pas le Calmar

### Regles
- Jamais 2 trades simultanes en sens opposes
- ATR du jour precedent
- Trailing sur CLOSE: SL=1.0 ACT=0.5 TRAIL=0.75, max 12 barres (config unique)
- best = max(close) et non max(high) — coherence temporelle
- Apres trailing update, PAS de re-check low/high vs nouveau stop (temporellement incoherent)
- Seul re-check: close vs nouveau stop (MT5 ModifyPosition immediat)
- Spread: 2x monthly avg dans backtest, bid/ask reel en live
- 1 trigger max par strat par jour

### Horaires cles UTC
- 0h00: 2BAR(F) et BigCandle(O) actifs
- 6h00: Tokyo close → reference pour GAP(D), TOKEND(H)
- 8h00: London open → GAP(D), TOKEND(H) triggent, AA actif
- 10h00: KZ(E) trigger
- 14h30: AA fin

## Scripts
| Script | Role |
|---|---|
| `find_best_v10.py` | Optimisation v10 (15 strats, trailing sur close, config unique) |
| `explore_exits_v4.py` | Exploration exhaustive des exits (TRAIL/TPSL/TIME/BE_TR) |
| `simu_final.py` | Simulation mensuelle AA+D+E+F+H+O |
| `simu_detail.py` | Simulation detaillee mois par mois avec breakdown par strat |
| `live_paper.py` | Paper trading live |
| `dashboard.py` | Dashboard Streamlit |
| `last100.py` | Stats et detail des 100 derniers trades |

## Infrastructure
- PostgreSQL: `candles_mt5_xauusd_5m`, `market_ticks_xauusd`
- DST IC Markets: US (2eme dim mars, 1er dim nov)
- Connexion autocommit (pas de lock)
