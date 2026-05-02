# CLAUDE.md — VP Swing Explorer (multi-instrument multi-TF)

## Etat actuel (2026-05-02)

| Compte | TF live | Instruments | Strats | Risk | Methode |
|---|---|---|---|---|---|
| **Pepperstone** | 1h | 24 | 98 | 0.5% | find_winners |
| **5ers** | 1h | 6 (sans metaux) | 26 | 0.01% | find_winners |
| **FTMO** | 1h | 11 (toutes) | 49 | 0.04% | find_winners |

ICM supprime (2026-05-01, compte non actif).

## Architecture multi-TF

- Schema configs: `ALL_INSTRUMENTS[sym][tf] = {risk_pct, portfolio}`
- `LIVE_TIMEFRAMES = ['1h']` filtre runtime (modifiable sans toucher au code pour activer 4h, 15m, etc.)
- Magic numbers: `broker_base + sym_id*1000 + tf_id*200 + strat_id` (TF_ID = {5m:0, 15m:1, 1h:2, 4h:3, 1d:4})
- Pkl: `data/<broker>/<sym>/<tf>/optim_data.pkl`
- STRAT_EXITS key: `(broker, sym, tf)`
- Tuple trade: `(ci, xi, di, pnl_oz, sl_atr, atr, mo, sn, tf)` (9 elements)

## Methode find_winners (defaut)

Filtres absolus par strat individuelle (pas cherry-pick combinatoire):
- `n >= 80` (15m), `60` (1h), `40` (4h)
- `avg_R >= 0.05`
- `avg_R_trim > 0` (5% top + 5% bottom retires)
- `median_R > 0`
- `outlier_share < 30%` (top 5% wins < 30% gross profit)
- `M+ >= 7/12` mois positifs
- `h1 > 0` ET `h2 > 0` (walk-forward 50/50)

Pourquoi pas analyze_combos: optim ensembliste = cherry-pick par construction (multiple testing). find_winners = walk-forward par strat = robustesse OOS verifiee.

## Pipeline (etapes)

1. `find_winners.py <broker> --tf <tf> --n-min <N>`
2. Script temp/compile_<broker>_<tf>.py: merge dans config + strat_exits
3. `bt_portfolio.py <broker> --tf <tf>` validation
4. compare_today.py audit live vs BT
5. Activer LIVE_TIMEFRAMES + redeployer VPS (git pull, kill processes, optionnel rm state.json, relancer)

## Live MT5 architecture

- **Mutex magic retire** (2026-05-02): plusieurs positions same (sym, strat, tf) autorisees. Trail/BE_TP keyed par ticket = isole nativement.
- **Sizing sur equity** (pas balance): `mt5_equity()` dans `open_position`. Reflet capital reel + dynamic risk reduction en DD latent.
- **Dedup 1/strat/sym/jour** garantie par `_triggered_close` dans state per_unit (3 couches: detect_all > state JSON > rebuild from MT5 positions au boot).
- **Comment MT5**: `"STRAT|TF"` (pour decode si magic non resolu).
- **Source temps**: `ts_dt` UTC des candles DB. Jamais horloge systeme/broker.

## Regles strats (intransigeantes)

- **PAS de strats LON_/NY_** (DST, retirees 2026-04-29). Seules TOK_ acceptables.
- **PAS de strats open** (timing non reproductible).
- **Filtre conflit SHORT/LONG retire** (2026-04-29) — directions opposees autorisees.
- ATR fige a l'entree (chaque position garde son ATR du jour precedent toute sa vie).
- 1 trigger max par strat/sym/jour direction-blind (premier qui fire gagne).

## Cost-r dans BT

- 0.05R uniforme dans bt_portfolio --cost-r 0.05.
- Pessimiste sur 1h (~0.02R reel) et 4h (~0.008R reel).
- Calibration via differentiel live apres quelques semaines de trading.

## Swap

- Pas modelise dans le BT (formule MQL5 forum incomplete: conversions FX cachees pour profit_currency=JPY, contract_size>1 sur metaux).
- Verification empirique 2026-05-02: ratio formule/reel = 0.06 sur JPN225/JPY pairs (= 17x trop eleve dans la formule).
- Decision: **mesurer differentiel live via mt5.history_deals_get** apres quelques semaines, pas de modelisation theorique.

## Infrastructure

- PostgreSQL: `candles_mt5_<sym>_<tf>` (multi-TF natif via mt5_fetch_clean.py + timeframes.txt)
- **NE JAMAIS modifier mt5_fetch_clean.py** (gere deja multi-tf, prod stable)
- Fuseaux: laptop UTC+7, VPS UTC+2, brokers UTC+3 → toujours convertir via BROKER_OFFSET (broker_offsets.json)
- 2 machines: dev local + VPS live (meme DB schema, fetch independant)

## Discipline log + push

- Apres CHAQUE commit: log dans `results_log.md` + push, immediat. Pas en batch.
- results_log.md anti-chronologique (plus recentes en haut).
- Recidive chronique cette regle, pattern documente dans memory/feedback_log_after_every_commit.md.

## Files cles

| Script | Role |
|---|---|
| `strats.py` | 110 strats: detect_all, sim_exit_custom, compute_indicators, make_magic, decode_magic |
| `strat_exits.py` | Configs exit par (broker, sym, tf) |
| `config_helpers.py` | iter_sym_tf, list_timeframes, get_inst_config |
| `find_winners.py` | Selection mecanique par strat (filtres absolus) |
| `optimize_all.py` | Optimisation 110 strats x exits, marge >= 8% |
| `analyze_combos.py` | LEGACY: beam search ensembliste |
| `bt_portfolio.py` | Backtest agrege multi-instrument multi-TF |
| `compare_today.py` | BT vs live (N-to-N matching UTC) |
| `live_mt5.py` | Execution live MT5 (3 brokers, multi-TF) |
| `mt5_fetch_clean.py` | Fetch DB (multi-TF via timeframes.txt) — **NE PAS TOUCHER** |
| `vps_pusher.py` | Push live vers dashboard |
| `api_server.py` | Dashboard PWA |
| `dashboard.py` | Dashboard Streamlit (legacy) |
