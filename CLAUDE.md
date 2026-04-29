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
- ATR du jour precedent
- Spread: 2x monthly avg dans backtest, bid/ask reel en live
- 1 trigger max par strat par jour
- Indicateurs precalcules: MACD(8,17,9), RSI(14), EMA(20), Parabolic SAR, Keltner Channels
- (Filtre anti-conflit SHORT/LONG retire 2026-04-29 — directions opposees autorisees simultanement)

## Architecture

### Core (agnostique plateforme)
| Script | Role |
|---|---|
| `strats.py` | 110 strats: detect_all(), sim_exit_custom(), compute_indicators() |
| `strat_exits.py` | Config exit par (broker, instrument, strat) — regenere depuis pkl |
| `optimize_all.py` | Optimisation: 110 strats x exits, filtre marge >= 8% |
| `analyze_combos.py` | Combinatoire: 6 criteres, pairwise, profils risque |
| `bt_portfolio.py` | Backtest agrege multi-instrument (ALL_INSTRUMENTS) |

### MT5 — Propfirm + Perso
| Script | Role |
|---|---|
| `config_5ers.py` | 5ers: 6 instruments, Calmar 9 XAUUSD (0.05% risk) |
| `config_ftmo.py` | FTMO: 3 instruments, Calmar 17 XAUUSD (0.05% risk) |
| `config_icm.py` | ICMarkets: compte perso |
| `live_mt5.py` | Execution live MT5 (tous comptes) |
| `compare_today.py` | Compare BT vs live MT5 |
| `dashboard.py` | Dashboard Streamlit MT5 |
| `mt5_fetch_clean.py` | Fetch MT5 -> PostgreSQL (drop last candle) |
| `data/5ers/` | pkl + combos 5ers (XAUUSD, indices) |
| `data/ftmo/` | pkl + combos FTMO (XAUUSD, indices) |

### Hyperliquid — Crypto
| Script | Role |
|---|---|
| `config_crypto.py` | 12 cryptos, 0.2% risk |
| `live_hyperliquid.py` | Execution Hyperliquid (a creer) |
| `compare_today_hl.py` | Compare BT vs Hyperliquid (a creer) |
| `dashboard_hl.py` | Dashboard Hyperliquid (a creer) |
| `hl_fetch.py` | Fetch Hyperliquid API -> PostgreSQL (a creer) |
| `data/crypto/` | pkl + combos crypto |

### Regles
- Candles en DB = UTC uniquement. JAMAIS heure systeme ou broker
- Marge WR >= 8% obligatoire
- PAS de strats open (timing non reproductible)
- Pipeline: optimize -> strat_exits -> combos -> config -> bt -> audit -> live

## Infrastructure
- PostgreSQL: candles_mt5_*_5m (MT5 + crypto via MT5)
- Connexion autocommit (pas de lock)
- 2 machines: dev local + VPS live (meme DB schema, fetch independant)
