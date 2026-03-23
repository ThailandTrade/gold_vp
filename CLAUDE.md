# CLAUDE.md — VP Swing Explorer (XAUUSD 5m)

## Portfolio actif : Equilibre 10 strats (1%/trade, TPSL exits)

| Metrique | 1% risk |
|---|---|
| Rendement | +511% |
| Max DD | -15.4% |
| PF | 1.32 |
| WR | 72% |
| Trades | 2005 (~6.4/jour) |
| Mois positifs | 13/13 |
| Directions | Long + Short |
| Sessions | Tokyo + London + All |

## Strategies

| Strat | Description | SL | TP | PF | WR | Session |
|---|---|---|---|---|---|---|
| PO3_SWEEP | Asian sweep reversal at London open | 3.0 | 0.75 | 1.76 | 80% | London 7h-9h |
| ALL_3SOLDIERS | Three soldiers/crows pattern | 3.0 | 1.50 | 1.29 | 64% | All |
| LON_KZ | KZ London 8h-10h fade | 2.5 | 0.50 | 1.70 | 80% | London 10h |
| LON_TOKEND | 3 bougies Tokyo >1ATR continuation | 3.0 | 1.50 | 1.80 | 65% | London 8h |
| ALL_PSAR_EMA | Parabolic SAR flip + EMA20 | 3.0 | 1.00 | 1.29 | 72% | All |
| ALL_FVG_BULL | Fair Value Gap bullish | 2.5 | 0.75 | 1.45 | 70% | All |
| ALL_CONSEC_REV | 5-bar exhaustion reversal | 3.0 | 0.50 | 1.48 | 77% | All |
| ALL_MACD_RSI | MACD med cross + RSI>50 | 3.0 | 1.50 | 1.22 | 63% | All |
| ALL_FIB_618 | Fib 0.618 retracement bounce | 1.5 | 0.50 | 1.30 | 65% | All |
| TOK_BIG | Bougie Tokyo >1ATR continuation | 3.0 | 0.50 | 1.30 | 78% | Tokyo 0h-6h |
| TOK_2BAR | Two-bar reversal Tokyo | 3.0 | 1.50 | 1.57 | 67% | Tokyo 0h-6h |

### Regles
- Tous les exits sont TPSL (SL fixe + TP fixe, pas de trailing)
- Jamais 2 trades simultanes en sens opposes
- ATR du jour precedent
- Spread: 2x monthly avg dans backtest, bid/ask reel en live
- 1 trigger max par strat par jour
- Indicateurs precalcules: MACD(8,17,9), RSI(14), EMA(20), Parabolic SAR

### Horaires cles UTC
- 0h00: TOK_2BAR, TOK_BIG actifs
- 7h00-9h00: PO3_SWEEP actif
- 8h00: LON_TOKEND trigger
- 10h00: LON_KZ trigger
- ALL_* strats: actives toute la journee (sur bougie fermee)

## Scripts
| Script | Role |
|---|---|
| `strats.py` | Module commun: strategies, exit, indicateurs, noms |
| `strat_exits.py` | Config exit par strat (TPSL/TRAIL) |
| `config_icmarkets.py` | Portfolio Equilibre 10 strats |
| `live_paper_icmarkets.py` | Paper trading live |
| `dashboard.py` | Dashboard Streamlit |
| `build_combo_balanced.py` | Construction combo equilibre |
| `build_combo_high_wr.py` | Construction combo high WR |
| `find_combo_greedy.py` | Greedy combo builder |
| `results_log.md` | Log evolution resultats |

## Infrastructure
- PostgreSQL: `candles_mt5_xauusd_5m`, `market_ticks_xauusd`
- DST IC Markets: US (2eme dim mars, 1er dim nov)
- Connexion autocommit (pas de lock)
