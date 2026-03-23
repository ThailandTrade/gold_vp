# CLAUDE.md — VP Swing Explorer (XAUUSD 5m)

## Portfolios actifs (optimises 2026-03-23)

| Compte | Combo | Risk | PF | WR | DD | Rend | M+ |
|---|---|---|---|---|---|---|---|
| **ICM** | Calmar 12 | 1.0% | 1.62 | 72% | -12.5% | +3523% | 13/13 |
| **FTMO** | Calmar 8 | 0.5% | 1.65 | 73% | -6.0% | +743% | 13/13 |
| **5ers** | MinDD 5 | 0.5% | 1.62 | 82% | -2.5% | +83% | 12/13 |

## ICM Calmar 12 (compte propre)

| Strat | Exit | SL | ACT/TP | TRAIL | PF | WR | Session |
|---|---|---|---|---|---|---|---|
| PO3_SWEEP | TRAIL | 3.0 | 0.75 | 0.75 | 2.46 | 79% | London 7h-9h |
| LON_PREV | TRAIL | 2.0 | 0.75 | 0.75 | 1.19 | 63% | London 8h |
| TOK_2BAR | TRAIL | 3.0 | 0.50 | 0.50 | 1.61 | 75% | Tokyo 0h-6h |
| LON_KZ | TRAIL | 3.0 | 0.50 | 0.30 | 1.80 | 82% | London 10h |
| ALL_KC_BRK | TRAIL | 3.0 | 1.00 | 0.75 | 1.20 | 69% | All |
| ALL_3SOLDIERS | TPSL | 3.0 | 2.00 | — | 1.34 | 67% | All |
| ALL_FVG_BULL | TRAIL | 3.0 | 1.00 | 0.75 | 1.63 | 70% | All |
| LON_BIGGAP | TRAIL | 3.0 | 0.75 | 0.50 | 1.70 | 74% | London 8h |
| ALL_MACD_RSI | TRAIL | 1.5 | 0.50 | 0.50 | 1.67 | 60% | All |
| TOK_BIG | TRAIL | 3.0 | 0.30 | 0.30 | 1.57 | 76% | Tokyo 0h-6h |
| TOK_PREVEXT | TRAIL | 1.5 | 0.75 | 1.00 | 1.53 | 51% | Tokyo 0h |
| LON_TOKEND | TRAIL | 3.0 | 0.30 | 0.30 | 1.81 | 68% | London 8h |

### Regles
- Exits TRAIL majoritaires (11/12 strats), 1 TPSL (ALL_3SOLDIERS)
- Jamais 2 trades simultanes en sens opposes
- ATR du jour precedent
- Spread: 2x monthly avg dans backtest, bid/ask reel en live
- 1 trigger max par strat par jour
- Indicateurs precalcules: MACD(8,17,9), RSI(14), EMA(20), Parabolic SAR, Keltner Channels

## Nomenclature fichiers

### Core
| Script | Role |
|---|---|
| `strats.py` | Module commun: detect_all(), sim_exit_custom(), compute_indicators() |
| `strat_exits.py` | Config exit optimale par strat (65 strats, optimise 2026-03-23) |

### Configs par compte
| Script | Role |
|---|---|
| `config_icm.py` | ICMarkets Calmar 12 (1% risk) |
| `config_ftmo.py` | FTMO Calmar 8 (0.5% risk) |
| `config_5ers.py` | 5ers MinDD 5 (0.5% risk) |

### Live paper trading
| Script | Role |
|---|---|
| `live_paper_icmarkets.py` | Paper trading ICM (importe config_icm.py) |

### Backtest / optimisation
| Script | Role |
|---|---|
| `optimize_all.py` | Optimisation complete: 65 strats x 122 exits → best configs |
| `analyze_combos.py` | Analyse combinatoire: 6 criteres, pairwise, profils risque |
| `find_combo_greedy.py` | Legacy greedy builder (remplace par optimize_all.py) |

### Data / logs
| Fichier | Role |
|---|---|
| `results_log.md` | Log detaille de toutes les iterations et decisions |
| `LOOK_AHEAD_CHECKLIST.md` | Checklist anti look-ahead |
| `optim_data.pkl` | Trades precomputes (reload rapide pour analyze_combos.py) |
| `combo_results.json` | Resultats tous criteres/tailles |

## Infrastructure
- PostgreSQL: `candles_mt5_xauusd_5m`, `market_ticks_xauusd`
- DST IC Markets: US (2eme dim mars, 1er dim nov)
- Connexion autocommit (pas de lock)
