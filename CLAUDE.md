# CLAUDE.md — VP Swing Explorer (XAUUSD 5m)

## Portfolio actif : 11 strats (1%/trade)

| Metrique | Valeur |
|---|---|
| Rendement | +27,559% |
| Max DD | -27.1% |
| Calmar | 1018 |
| PF | 1.51 |
| WR | 44% |
| Trades | 1895 (~6.0/jour) |
| Mois positifs | 13/13 |
| Directions | Long + Short |
| Sessions | Tokyo + London + New York |

## Strategies

| Strat | Description | Dir | PF | Session | Horaire |
|---|---|---|---|---|---|
| TOK_2BAR | Two-bar reversal Tokyo (body >0.5ATR, 2eme > 1ere) | L+S | 1.70 | Tokyo | 0h-6h |
| TOK_BIG | Bougie Tokyo >1ATR, continuation | L+S | 1.55 | Tokyo | 0h-6h |
| TOK_FADE | Fade previous day >1ATR at Tokyo open | L+S | 1.43 | Tokyo | 0h00 |
| LON_PIN | Pin bar London (close top/bottom 10% range) | L+S | 1.11 | London | 8h-14h30 |
| LON_GAP | Gap Tokyo close vs London open >0.5ATR, continuation | L+S | 1.74 | London | 8h |
| LON_KZ | London Kill Zone 8h-10h move >0.5ATR, fade a 10h | L+S | 1.58 | London | 10h |
| LON_TOKEND | 3 dernieres bougies Tokyo >1ATR, continuation London | L+S | 1.84 | London | 8h |
| LON_PREV | Previous day >1ATR, continuation London open | L+S | 1.43 | London | 8h |
| NY_GAP | Gap London close vs NY open >0.5ATR, continuation | L+S | 1.72 | NY | 14h30 |
| NY_LONEND | 3 dernieres bougies London >1ATR, continuation NY | L+S | 1.58 | NY | 14h30 |
| NY_LONMOM | 3 dernieres bougies London >0.5ATR, continuation NY | L+S | 1.47 | NY | 14h30 |

### Regles
- Jamais 2 trades simultanes en sens opposes
- ATR du jour precedent
- Trailing sur CLOSE: SL=1.0 ACT=0.5 TRAIL=0.75, pas de timeout (config unique)
- best = max(close) et non max(high) — coherence temporelle
- Apres trailing update, PAS de re-check low/high vs nouveau stop
- Seul re-check: close vs nouveau stop (MT5 ModifyPosition immediat)
- Spread: 2x monthly avg dans backtest, bid/ask reel en live
- 1 trigger max par strat par jour

### Horaires cles UTC
- 0h00: TOK_2BAR, TOK_BIG, TOK_FADE actifs
- 6h00: Tokyo close → reference pour LON_GAP, LON_TOKEND
- 8h00: London open → LON_GAP, LON_TOKEND, LON_PREV triggent, LON_PIN actif
- 10h00: LON_KZ trigger
- 14h30: NY open → NY_GAP, NY_LONEND, NY_LONMOM triggent, LON_PIN fin

## Scripts
| Script | Role |
|---|---|
| `strats.py` | Module commun: strategies, exit, noms |
| `simu_final.py` | Simulation mensuelle |
| `simu_detail.py` | Simulation detaillee mois par mois |
| `live_paper.py` | Paper trading live |
| `dashboard.py` | Dashboard Streamlit |
| `last100.py` | Stats et detail des 100 derniers trades |
| `explore_exits_v4.py` | Exploration exhaustive des exits |
| `explore_ny.py` | Exploration des strategies NY |
| `explore_v2.py` | Exploration v2 toutes sessions |

## Infrastructure
- PostgreSQL: `candles_mt5_xauusd_5m`, `market_ticks_xauusd`
- DST IC Markets: US (2eme dim mars, 1er dim nov)
- Connexion autocommit (pas de lock)
