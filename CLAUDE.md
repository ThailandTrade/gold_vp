# CLAUDE.md — VP Swing Explorer (multi-instrument 15m)

## Portfolios actifs

| Compte | Approche | Instruments | Risk | Note |
|---|---|---|---|---|
| **FTMO** | reactive XAUUSD | 6 | 0.5% | 37 strats |
| **5ers** | XAUUSD + indices | 6 | 0.5% | combos beam search |
| **Pepperstone** | find_winners | 20 | 0.5% | 78 strats, compte propre $200 |

## Pipeline pepperstone (find_winners)

Filtres absolus par strat individuelle (pas de cherry-pick par combo):
- n >= 80, avg_R >= 0.05, avg_R_trim > 0, median_R > 0
- outlier_share < 30%, M+ >= 7/12
- walk-forward h1 > 0 et h2 > 0

## Architecture

### Core (agnostique plateforme)
| Script | Role |
|---|---|
| `strats.py` | 110 strats: detect_all(), sim_exit_custom(), compute_indicators() |
| `strat_exits.py` | Config exit par (broker, instrument, strat) — regenere depuis pkl |
| `optimize_all.py` | Optimisation: 110 strats x exits, filtre marge >= 8% |
| `find_winners.py` | Selection mecanique strats gagnantes (filtres absolus) |
| `analyze_combos.py` | Combinatoire beam search (legacy) |
| `bt_portfolio.py` | Backtest agrege multi-instrument |

### MT5 — Propfirm + Perso
| Script | Role |
|---|---|
| `config_5ers.py` | 5ers |
| `config_ftmo.py` | FTMO |
| `config_pepperstone.py` | Pepperstone (compte propre, $200, UTC+3) |
| `live_mt5.py` | Execution live MT5 (tous comptes) |
| `compare_today.py` | Compare BT vs live MT5 |
| `dashboard.py` | Dashboard Streamlit MT5 |
| `mt5_fetch_clean.py` | Fetch MT5 -> PostgreSQL |

### Hyperliquid — Crypto
| Script | Role |
|---|---|
| `config_crypto.py` | 12 cryptos, 0.2% risk |
| `live_hyperliquid.py` | Execution Hyperliquid (a creer) |

### Regles
- Candles en DB = UTC uniquement. JAMAIS heure systeme ou broker
- Marge WR >= 8% obligatoire (pour combos legacy)
- PAS de strats open (timing non reproductible)
- PAS de strats LON_/NY_ (DST, horaires variables) — seules TOK_ acceptables
- Filtre anti-conflit SHORT/LONG retire 2026-04-29 — directions opposees autorisees simultanement
- Pipeline find_winners: optimize -> find_winners -> config -> bt -> audit -> live
- Pipeline combos (legacy): optimize -> strat_exits -> analyze_combos -> config -> bt -> audit -> live

## Infrastructure
- PostgreSQL: candles_mt5_*_<tf> (MT5 + crypto via MT5)
- Connexion autocommit (pas de lock)
- 2 machines: dev local + VPS live (meme DB schema, fetch independant)
