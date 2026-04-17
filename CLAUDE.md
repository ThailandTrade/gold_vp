# CLAUDE.md — VP Swing (15m, multi-instrument)

## Etat au 2026-04-17 (branche cleanup-v2)

Branche de refactoring majeur: ménage du code, abandon du concept "combo", mutex LONG/SHORT supprimé, walk-forward OOS.

### Brokers actifs (15m)

| Broker | Capital | Risk | Instruments | Status |
|---|---|---|---|---|
| **FTMO** | $100k | 0.05% | XAUUSD, GER40.cash, US500.cash, US100.cash, US30.cash, JP225.cash | Live |
| **5ers** | $100k | 0.02% | DAX40, NAS100, SP500 | Live |
| **ICMarkets** | compte perso | 0.01% | 12 instruments (XAUUSD, US500, USTEC, DE40, JP225, AUS200, EURUSD, GBPUSD, AUDUSD, USDCAD, USDCHF, USDJPY) | Live |

### Modele v2 (cleanup en cours)

**Abandonne**:
- Concept "combo" (plus de Calmar 8 / Calmar 12 / etc.)
- `analyze_combos.py` supprime
- Mutex LONG/SHORT: les strats tradent sans aucune restriction inter-strats
- Backtests 5m (obsolete)

**Adopte**:
- Selection individuelle par (broker, instrument): les strats qui passent les criteres tradent toutes
- Walk-forward OOS: 10 mois rolling, step 1 mois
- Criteres de selection par strat: PF >= 1.30, WR >= 65% (ou PF >= 1.5 pour TPSL high-RR), n >= 200, M+ >= 10/13 sur IS, PF OOS >= 1.15

### Architecture cible

| Script | Role |
|---|---|
| `strats.py` | detect_all() + compute_indicators(). Source unique des signaux. |
| `strat_exits.py` | Config exit par (broker, instrument, strat) depuis pkl |
| `optimize_all.py` | Grille exits + filtre marge + walk-forward OOS |
| `bt_portfolio.py` | Backtest agrege multi-instrument, sans mutex LONG/SHORT |
| `live_mt5.py` | Execution live MT5 (tous comptes), sans conflict filter |
| `compare_today.py` | Compare BT vs live MT5 |
| `config_ftmo.py` / `config_5ers.py` / `config_icm.py` | Liste plate de strats par instrument |
| `api_server.py` + `dashboard_live.py` | Dashboard HTML |
| `vps_pusher.py` | Push etat MT5 -> API |
| `mt5_fetch_clean.py` | Fetch MT5 -> PostgreSQL |

### Regles fondamentales
- Candles en DB = UTC uniquement. JAMAIS heure systeme/broker
- Pas de strats "open" (detection sur ouverture de session)
- Broker obligatoire en arg sur tous les scripts
- Spread: 2x monthly avg dans backtest, bid/ask reel en live
- Pipeline: optimize -> filter -> walk-forward -> config -> bt -> audit -> live
- Les pkl doivent etre regeneres apres chaque update candles (verification hash a terme)

### Infrastructure
- PostgreSQL: `candles_mt5_*_5m` (MT5 + crypto via MT5)
- Connexion autocommit
- 2 machines: dev local + VPS live (meme schema, fetch independant)

### Source de verite
- **CLAUDE.md**: architecture et regles figees
- **results_log.md**: journal chronologique inverse des tests/resultats
- **project_live_status.md** (memory): snapshot de l'etat live
