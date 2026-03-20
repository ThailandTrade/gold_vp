# CLAUDE.md — VP Swing Explorer (XAUUSD 5m)

## Portfolio actif : AA+D+E+F+H+NY6+NY16+NY17+O (1%/trade)

| Metrique | Valeur |
|---|---|
| Rendement | +12,624% |
| Max DD | -26.2% |
| Calmar | 481.2 |
| PF | 1.54 |
| WR | 44% |
| Trades | 1637 (~5.2/jour) |
| Mois positifs | 12/13 |
| Directions | Long + Short |
| Sessions | Tokyo + London + New York |

## Strategies

| Lettre | Nom | Description | Dir | PF | Session | Horaire |
|---|---|---|---|---|---|---|
| AA | LON_pinbar | Close near extreme (top/bottom 10% range, body>0.2ATR) | L+S | 1.04 | London | 8h-14h30 |
| D | GAP_tok_lon | Gap Tokyo close vs London open >0.5ATR, continuation | L+S | 1.86 | London | 8h |
| E | KZ_lon_fade | London Kill Zone 8h-10h move >0.5ATR, fade a 10h | L+S | 1.56 | London | 10h |
| F | 2BAR_tok_rev | Two-bar reversal Tokyo (body >0.5ATR, 2eme > 1ere) | L+S | 1.63 | Tokyo | 0h-6h |
| H | TOKEND_3b | 3 dernieres bougies Tokyo >1ATR, continuation London | L+S | 1.86 | London | 8h |
| NY6 | GAP_lon_ny | Gap London close vs NY open >0.5ATR, continuation | L+S | 1.68 | NY | 14h30 |
| NY16 | LONEND_3b_ny | 3 dernieres bougies London >1ATR, continuation NY | L+S | 1.60 | NY | 14h30 |
| NY17 | LONEND_05_ny | 3 dernieres bougies London >0.5ATR, continuation NY | L+S | 1.49 | NY | 14h30 |
| O | BIG_tok | Bougie Tokyo >1ATR, continuation | L+S | 1.55 | Tokyo | 0h-6h |

### Regles
- Jamais 2 trades simultanes en sens opposes
- ATR du jour precedent
- Trailing sur CLOSE: SL=1.0 ACT=0.5 TRAIL=0.75, max 12 barres (config unique)
- best = max(close) et non max(high) — coherence temporelle
- Apres trailing update, PAS de re-check low/high vs nouveau stop
- Seul re-check: close vs nouveau stop (MT5 ModifyPosition immediat)
- Spread: 2x monthly avg dans backtest, bid/ask reel en live
- 1 trigger max par strat par jour

### Horaires cles UTC
- 0h00: 2BAR(F) et BigCandle(O) actifs
- 6h00: Tokyo close → reference pour GAP(D), TOKEND(H)
- 8h00: London open → GAP(D), TOKEND(H) triggent, AA actif
- 10h00: KZ(E) trigger
- 14h30: NY open → NY6, NY16, NY17 triggent, AA fin

## Scripts
| Script | Role |
|---|---|
| `find_best_v10.py` | Optimisation v10 (21 strats, trailing sur close, config unique) |
| `explore_exits_v4.py` | Exploration exhaustive des exits (TRAIL/TPSL/TIME/BE_TR) |
| `explore_ny.py` | Exploration des strategies NY (25 strats testees) |
| `simu_final.py` | Simulation mensuelle |
| `simu_detail.py` | Simulation detaillee mois par mois avec breakdown par strat |
| `live_paper.py` | Paper trading live |
| `dashboard.py` | Dashboard Streamlit |
| `last100.py` | Stats et detail des 100 derniers trades |

## Infrastructure
- PostgreSQL: `candles_mt5_xauusd_5m`, `market_ticks_xauusd`
- DST IC Markets: US (2eme dim mars, 1er dim nov)
- Connexion autocommit (pas de lock)
