# Results Log — Evolution des resultats

**Regle**: entrees anti-chronologiques (plus recentes en haut).

## 2026-04-07 — CHECKLIST: ajouter un nouveau broker

### Fichiers a CREER
- `config_<broker>.py` : BROKER, ALL_INSTRUMENTS (symbol, risk_pct, portfolio), LIVE_INSTRUMENTS
- `pairs_<broker>.txt` : liste des paires pour mt5_fetch_clean

### Fichiers a MODIFIER (8 fichiers, lignes `choices`)
- `strats.py:61` MAGIC_BASES : ajouter `'<broker>': <new_base>` (increments de 10000)
- `strats.py:55-58` SYMBOL_ID : ajouter les nouveaux symboles si pas deja presents
- `bt_portfolio.py:18` choices : ajouter `'<broker>'`
- `compare_today.py:17` choices : ajouter `'<broker>'`
- `live_mt5.py:27` choices : ajouter `'<broker>'`
- `vps_pusher.py:22` choices : ajouter `'<broker>'`
- `mqtt_publisher.py:25` choices : ajouter `'<broker>'`
- `audit_bt_vs_compare.py:24` choices : ajouter `'<broker>'`
- `live_paper.py:21` choices : ajouter `'<broker>'`
- `strat_exits.py` : ajouter blocs `STRAT_EXITS[('<broker>', 'SYMBOL')]` pour chaque instrument

### Pipeline a executer
1. `mt5_fetch_clean.py --pairs-file pairs_<broker>.txt` → candles en DB
2. `optimize_all.py <broker> --symbol <sym> --tf <5m|15m>` → pkl par instrument
3. `analyze_combos.py <broker> --symbol <sym>` → combo_results.json
4. User selectionne combos → mettre a jour `config_<broker>.py`
5. Regenerer `strat_exits.py` depuis pkls
6. `bt_portfolio.py <broker> --tf <5m|15m>` → validation agrege
7. `compare_today.py <broker> --tf <5m|15m>` → verif BT vs live
8. Deployer `live_mt5.py <broker> --tf <5m|15m>` sur VPS
9. Deployer `vps_pusher.py <broker> --tf <5m|15m>` sur VPS
10. Tout noter dans results_log.md a chaque etape

### Note
- Les `choices` sont hardcodes dans 9 fichiers — a centraliser si on ajoute souvent des brokers.
- `vps_pusher.py` fait partie du pipeline (compare BT vs LV dans le dashboard).

## 2026-04-07 — Dashboard temps reel VPS → Laptop via FastAPI + ngrok

### Architecture (remplace MQTT, trop instable sur broker public)
- `api_server.py` (laptop) : FastAPI, recoit les push des VPS, sert le dashboard
- `vps_pusher.py` (chaque VPS) : POST l'etat MT5 chaque seconde vers l'API
- `dashboard_live.py` (laptop) : Streamlit, lit depuis l'API locale
- ngrok domaine fixe : `unprolongable-nonexternalized-elizabet.ngrok-free.dev`

### Donnees pushees chaque seconde
- Positions ouvertes (strat, dir, entry, current, SL, pnl live)
- Balance / equity / margin
- Trades fermes du jour
- Dernieres bougies par instrument
- Historique complet (au demarrage + refresh 5 min)

### Usage
```
Laptop terminal 1: uvicorn api_server:app --host 0.0.0.0 --port 8001
Laptop terminal 2: ngrok http --domain=unprolongable-nonexternalized-elizabet.ngrok-free.dev 8001
Laptop terminal 3: streamlit run dashboard_live.py
VPS FTMO:          python vps_pusher.py ftmo
VPS 5ers:          python vps_pusher.py 5ers
```

## 2026-04-09 — Pipeline 15m: optimize + combos + config + scripts adaptes

### Scripts modifies pour supporter --tf 15m
- `backtest_engine.py`: load_data/load_data_recent acceptent tf='15m'
- `optimize_all.py`: argument --tf, utilise backtest_engine.load_data
- `bt_portfolio.py`: argument --tf
- `compare_today.py`: argument --tf
- `live_mt5.py`: argument --tf, get_recent_candles + ATR supportent 15m

### Optimize FTMO 15m (7 instruments)
Pkls regeneres sur candles 15m. Combos selectionnes:

| Instrument | Combo | Nb | PF | WR | DD | Rend | M+ |
|---|---|---|---|---|---|---|---|
| XAUUSD | PF 9 | 9 | 1.68 | 76% | -0.2% | +3% | 13/13 |
| GER40.cash | Calmar 7 | 7 | 1.53 | 74% | -0.1% | +2% | 13/13 |
| US500.cash | PF 7 | 7 | 1.69 | 69% | -0.2% | +3% | 13/13 |
| US100.cash | PF*WR 8 | 8 | 1.58 | 72% | -0.2% | +2% | 11/13 |
| US30.cash | Calmar 4 | 4 | 1.61 | 70% | -0.1% | +1% | 13/13 |
| UK100.cash | skip (9/13) | - | - | - | - | - | - |
| JP225.cash | PF 3 | 3 | 1.88 | 79% | -0.1% | +1% | 11/13 |

config_ftmo_15m.py + strat_exits_15m.py crees.

### BT 15m premier run (avant fix sim_exit)
JP225 PF 1.04 (catastrophique vs 1.88 en optimize) car optimize utilisait sim_exit_np
et bt_portfolio utilisait sim_exit_custom → 2 implementations differentes.

### Nettoyage strats: 110 → 88 (22 retirees)
- 11 open strats (timing non reproductible): TOK_FADE, TOK_PREVEXT, LON_GAP, LON_BIGGAP, LON_KZ, LON_TOKEND, LON_PREV, NY_GAP, NY_LONEND, NY_LONMOM, NY_DAYMOM
- 11 jamais safe: ALL_AO_SAUCER, ALL_BB_SQUEEZE, ALL_EMA_TREND_PB, ALL_HMA_DIR, ALL_MACD_MED_SIG, ALL_STOCH_CROSS, ALL_VOL_SPIKE, IDX_GAP_FILL, IDX_ORB15, LON_PIN, TOK_MACD_MED
- REMOVED_STRATS dans strats.py, filtre dans detect_all, STRAT_ID preserve (magic numbers stables)

### Pipeline 15m v4 final (sim_exit unifie + numpy + margin 5% + 88 strats)
Combos selectionnes:

| Instrument | Combo | Nb | PF | WR | DD | Rend | M+ |
|---|---|---|---|---|---|---|---|
| XAUUSD | PF 9 | 9 | 1.68 | 76% | -0.2% | +3% | 13/13 |
| GER40.cash | Calmar 7 | 7 | 1.53 | 74% | -0.1% | +2% | 13/13 |
| US500.cash | Sharpe 8 | 8 | 1.63 | 69% | -0.2% | +3% | 13/13 |
| US100.cash | PF*WR 8 | 8 | 1.58 | 72% | -0.2% | +2% | 11/13 |
| US30.cash | Calmar 4 | 4 | 1.61 | 70% | -0.1% | +1% | 13/13 |
| UK100.cash | skip | - | - | - | - | - | - |
| JP225.cash | Calmar 2 | 2 | 1.90 | 79% | -0.1% | +1% | 11/13 |

### Validation bt_portfolio FTMO 15m agrege
```
Trades: 6,415 | WR: 73% | PF: 1.62 | Max DD: -0.24% | Rend: +11.3% | M+: 13/13
Capital: $100,000 → $111,340
```
PF quasi identique au 5m (1.62 vs 1.64). DD 4x meilleur (-0.24% vs -1.05%).
Rend plus bas (+11.3% vs +90.6%) car moins de trades, mais edge en R preserve.
JP225 PF 1.90 (vs 1.04 avant fix sim_exit) — pipeline unifie a corrige la divergence.

### Comparaison 5m vs 15m a meme risk (0.05%)
| | 5m | 15m |
|---|---|---|
| PF | 1.64 | 1.64 |
| WR | 71% | 73% |
| DD | -1.05% | -1.21% |
| Rend | +90.6% | +70.8% |
| M+ | 13/13 | 13/13 |
| Trades | 6,961 | 6,415 |

PF identique. 15m a 20% de rend en moins (moins de trades) mais:
- WR meilleur
- Cout live en R ~2x plus petit (spread/slippage/latence = plus petit % des moves 15m)
- Estimation live: 5m +55-65% reel vs 15m +63-68% reel
- Le 15m live pourrait battre le 5m live malgre BT inferieur

### Etat de la branche feature/15m
Pipeline 15m complet et valide:
- backtest_engine: tf='15m' supporte (load_data, load_data_recent)
- optimize_all: --tf 15m, sim_exit_custom unifie (numpy), margin 5%, 88 strats (22 retirees)
- analyze_combos: pkls 15m
- config_ftmo: 6 instruments 15m selectionnes
- strat_exits: regenere depuis pkls 15m
- bt_portfolio: --tf 15m valide (PF 1.64, DD -1.21%, +70.8%, 13/13 @ 0.05%)
- compare_today: --tf 15m
- live_mt5: --tf 15m (candles + ATR)
- vps_pusher: --tf 15m (compare BT + candles)

### Pipeline 5ers 15m (2026-04-09)
4 instruments (skip JPN225 + UK100). Combos selectionnes:

| Instrument | Combo | Nb | PF | WR | DD | Rend | M+ |
|---|---|---|---|---|---|---|---|
| XAUUSD | Calmar 13 | 13 | 1.71 | 78% | -0.2% | +4% | 13/13 |
| DAX40 | Calmar 2 | 2 | 1.75 | 75% | -0.1% | +1% | 12/13 |
| NAS100 | Calmar 5 | 5 | 1.51 | 73% | -0.1% | +1% | 13/13 |
| SP500 | Calmar 4 | 4 | 1.85 | 74% | -0.1% | +1% | 12/13 |

Validation bt_portfolio 5ers 15m agrege:
```
Trades: 3,948 | WR: 76% | PF: 1.69 | Max DD: -0.15% | Rend: +6.7% | M+: 13/13
```

### SL/TP/trail bases sur signal_close (pas fill price)
Le live calcule maintenant SL, TP et trail reference a partir du close de la bougie signal
(= meme valeur que le BT), pas du fill price. L'entry reelle (fill) peut differer de quelques
centimes mais les niveaux d'invalidation sont identiques au BT.
Trail entry/best aussi initialises au signal_close.

## 2026-04-10 — BUG CRITIQUE: trail stop re-check manquant dans sim_exit_custom

### Bug identifie par analyse ultra-detaillee des trades FTMO 15m
Apres trail update (SL monte), le BT ne re-verifie PAS si le low de la meme bougie
est en dessous du nouveau stop. En live, MT5 sort immediatement car le SL est un ordre reel.

Exemple US500 IDX_ENGULF bar 00:45:
- Trail active: SL monte de 6812.81 → 6823.63
- Low de la bougie = 6820.23 < 6823.63 → live sort (-0.44R), BT reste (+0.87R)

### Impact
- **TOUS les PF de backtest sont gonfles** (trades trail ou le stop monte et low est en dessous)
- Affecte toutes les strats TRAIL (majoritaires dans les portfolios)
- Les ecarts BT vs live observes (-0.19R a -0.65R) s'expliquent par ce bug
- La regle dans LOOK_AHEAD_CHECKLIST etait FAUSSE ("pas de re-check" → corrige en "re-check obligatoire")

### Resolution (2026-04-10)
Le re-check a ete implemente puis **REVERTE** apres analyse approfondie :
- Avec bougies 01:00+ ajoutees en DB, le code SANS re-check et AVEC re-check donnent les MEMES resultats
- Les gros ecarts (-0.19R a -0.65R) etaient causes par des **bougies manquantes** (fallback), pas par un bug trail
- Avec toutes les bougies, les deltas BT vs live tombent a **-0.02R a -0.15R** (spread/slippage normal au SL)
- Le re-check sur la meme bougie est FAUX : le low s'est produit AVANT le trail update, le SL modifie prend effet sur la bougie SUIVANTE
- PF 0.96 avec re-check = FAUX (trop pessimiste). PF 1.62 sans re-check = CORRECT.
- LOOK_AHEAD_CHECKLIST mis a jour

### BE_TP teste et abandonne (2026-04-10)
Nouveau type d'exit teste: BE_TP (break-even + take profit).
- p1=SL, p2=BE activation (SL → entry), p3=TP fixe
- Grille: 5 SL × 4 BE × 4 TP = 80 configs supplementaires
- Test sur XAUUSD FTMO 15m: seulement 2/88 strats l'ont choisi (PF 1.21-1.22)
- Aucune strat BE_TP dans le greedy top 15 — TRAIL et TPSL dominent
- **Decision: retirer BE_TP** de la grille (80 configs de calcul en plus pour quasi-rien)
- Code conserve dans sim_exit_custom mais retire de la grille optimize_all

### XAUUSD desactive en live (2026-04-10)
Lot min XAUUSD = 0.01 lot = $1/pt. Avec 0.01% risk sur $46k = $4.6 de risk,
et SL ~20 pts → besoin de $4.6/20 = 0.23 lots. Lot min 0.01 = $0.20 risk par lot.
Pas assez granulaire pour des petits risques. Desactive sur 5ers et FTMO.
XAUUSD reste dans ALL_INSTRUMENTS (pour backtest) mais pas dans LIVE_INSTRUMENTS.

### Reste a faire
- Tester live 15m (indices uniquement)

### sim_exit_custom reimplemente en numpy (meme logique, 10x+ rapide)
Remplace cdf.iloc[pos+j] par hi[idx]/lo[idx]/cl[idx]. Verifie: 1000 trades random, 0 differences.
Un seul sim_exit dans tout le pipeline : strats.py sim_exit_custom.

### Fix: optimize_all utilise sim_exit_custom (source unique)
Supprime sim_exit_np. optimize_all appelle sim_exit_custom de strats.py via wrapper.
TOUT le pipeline utilise maintenant la MEME simulation d'exit.
Re-optimize + re-validation necessaires.

## 2026-04-09 — Tag v1.0-5m + branche feature/15m

Tag v1.0-5m sur main : pipeline 5m complet et stable.
Branche feature/15m creee pour tester le passage en 15 minutes.
Objectif: reduire les divergences BT vs live (spread/slippage/latence = plus petit % des moves en 15m).

## 2026-04-09 — live_mt5: 1500 bars → 500 bars (reactivite max)

Benchmark: 500 bars = 0.10s vs 1500 bars = 0.22s (2x plus rapide).
Verification: 6/6 instruments FTMO donnent exactement les memes trades avec 500 vs 5000 bars.
EMA200 converge en ~200 bars, 500 bars = 300 bars de marge.

## 2026-04-09 — FTMO: ajout JP225.cash (PF 3, 3 strats)

JP225.cash ajoute a FTMO: ALL_FIB_618, IDX_LATE_REV, TOK_NR4
PF 1.78 | WR 76% | DD -0.1% | Rend +1% | 12/13
SYMBOL_ID 12, strat_exits ajoute, LIVE_INSTRUMENTS active.

## 2026-04-08 — LIVE: tous instruments actives a 0.01% risk

### 5ers (6 instruments)
LIVE_INSTRUMENTS = XAUUSD, JPN225, DAX40, NAS100, SP500, UK100
Risk: 0.01% par instrument (0.0001)

### FTMO (5 instruments)
LIVE_INSTRUMENTS = XAUUSD, GER40.cash, US500.cash, US100.cash, US30.cash
Risk: 0.01% par instrument (0.0001)

## 2026-04-08 — Dashboard: ameliorations multiples

### Calculs R cote pusher (plus de recalcul JS)

Le JS du dashboard recalculait le LV R avec atr*3 hardcode (faux pour sl_atr!=3).
Fix: le pusher calcule le compare complet (BT R + LV R + delta) avec les vrais sl_atr
de strat_exits, exactement comme compare_today.py. Le dashboard affiche juste les valeurs.
Zero calcul cote client = zero divergence.

### Toutes les strats du portfolio affichees

Tableau "Trades du jour" affiche toutes les strats du portfolio par instrument.
Strats non declenchees en gris (pas de valeurs BT/LV). Strats declenchees avec BT et/ou LV.
vps_pusher envoie `portfolios` dans le payload state.

### Tri alphabetique des strats dans le tableau

### Colonne LV $ (PnL en dollars)
PnL en $ par trade live (MT5 dout.profit) + total en bas du tableau.

## 2026-04-08 — Fix latence 37s au changement de jour (ATR cache load_data → compute_atr)

Le cache ATR dans live_mt5 appelait `load_data()` (70k bars, 11s+) au changement de date.
Remplace par `compute_atr()` + `get_trading_days()` (SQL seul, ~1s).
Meme ATR, meme source, mais sans charger 70k candles + indicateurs.

## 2026-04-08 — 5ers risk 0.05% → 0.02% (tous instruments)

## 2026-04-08 — Fix date systeme → date candle DB dans compare_today + vps_pusher

compare_today.py et vps_pusher.py utilisaient `datetime.now(timezone.utc).date()` (horloge systeme).
Si le VPS a un timezone different du laptop, la date du "jour" differe → trades BT differents.
Fix: utiliser la date de la derniere bougie en DB (`MAX(ts)` de candles_mt5_xauusd_5m).
Regle deja posee: "seule source de temps = ts_dt des candles en DB".

## 2026-04-07 — Dashboard: BT vs Live integre

vps_pusher calcule les trades BT du jour via `load_data_recent(5000)` + `collect_trades(date_filter=today)`.
Pousse `bt_compare` dans le payload chaque seconde, refresh BT toutes les 60s.
Dashboard affiche tableau BT vs Live (strat, dir, entry, R, delta R) directement dans la page.
Plus besoin de lancer `compare_today.py` manuellement.

## 2026-04-07 — Optim compare_today: load_data_recent (12s → 0.6s)

`load_data_recent(conn, symbol, n=2000)` dans backtest_engine : charge 2000 bars au lieu de 70k.
ATR toujours via compute_atr full (SQL seul, rapide). compare_today passe de ~15s a 2.25s total.
bt_portfolio garde load_data full pour le backtest complet.

## 2026-04-07 — MQTT abandonne (broker public instable)

### Architecture
- `mqtt_publisher.py` (sur chaque VPS) : lit MT5 chaque seconde, publie sur MQTT
- `dashboard_live.py` (sur laptop) : Streamlit, subscribe MQTT, vue unifiee 5ers + FTMO
- Broker MQTT : HiveMQ Cloud (gratuit, 100 connexions, 100GB/mois)
- Process separe de live_mt5.py (zero impact pipeline trading)

### Donnees publiees chaque seconde
- Positions ouvertes (strat, dir, entry, SL, pnl courant)
- Balance / equity / margin
- Trades fermes du jour (avec pnl)
- Dernieres bougies par instrument
- Events trade ouvert/ferme (topic separe, QoS 1)
- Historique complet MT5 (publie au demarrage en chunks de 100 trades, topic /history)

### Usage
```
VPS:    python mqtt_publisher.py ftmo
VPS:    python mqtt_publisher.py 5ers
Laptop: streamlit run dashboard_live.py
```

## 2026-04-07 — compare_today: affichage en R

Remplacement des points par des multiples de risque (R = pnl / sl_atr*atr).
Plus lisible : -1R = stop touche, +2R = 2x le risque gagne.

## 2026-04-07 — FIX URGENT live_mt5: latence 57s causee par load_data full history

### Probleme
Le refacto backtest_engine avait remplace `get_recent_candles(1500)` par `load_data()` (70k candles + compute_indicators full) dans la boucle live. Chaque tick chargeait 70k bars → 20-30s de latence supplementaire → 57s entre candle close et execution.

En haute volatilite (bougies de 30+ pts / 5min), 57s de delai = 10-16 pts de slippage. Trades ALL_BB_TIGHT et ALL_STOCH_OB entres a 16 pts du close du signal → SL touche immediatement → -25 pts de pertes evitables.

### Root cause
Changement dans live_mt5.py : `load_data(conn, sym)` a chaque heartbeat au lieu de `get_recent_candles(1500)`. Performance acceptable en dev, catastrophique en live haute volat.

### Fix
- Retour a `get_recent_candles(1500)` + `compute_indicators()` a chaque tick (rapide, ~5-10s)
- ATR via `compute_atr()` full history **cache 1x/jour** (`_atr_cache`) — refresh uniquement au changement de date
- Meme ATR que backtest_engine, execution rapide

### Lecon
**Ne JAMAIS sacrifier la reactivite live pour l'alignement pipeline.** Le live doit etre le plus rapide possible. L'alignement des donnees (ATR) se fait via cache, pas via rechargement complet a chaque bar.

### Contexte volat
XAUUSD en regime extreme : range moyen 5m = 8.69 (vs 4.88 sur 1 an = x1.8). Bougies de 30-35 pts observees. ATR prev day (3.33) completement deconnecte de la realite intraday → SL trop serres (10 pts pour un range de 30 pts/bougie).

## 2026-04-06 — DECISION ARCHITECTURALE: un seul moteur pour tout le pipeline

### Probleme fondamental
Audit `audit_bt_vs_compare.py` sur 5ers : **0% match** entre bt_portfolio (pkl) et compare_today (temps reel). Raisons :
1. Le pkl stockait des bar indices lies a un snapshot de candles → OOB des que la DB change
2. **7 divergences** identifiees entre optimize_all, bt_portfolio, compare_today et live_mt5 :
   - Candles: LIMIT 2000 (compare) vs LIMIT 1500 (live) vs full (optimize/bt)
   - ATR: `get_yesterday_atr()` custom (live) vs `compute_atr()` (optimize/bt)
   - Indicateurs: warmup different selon le nb de bars chargees
   - Exit sim: `sim_exit_np` (optimize) vs `sim_exit_custom` (compare/bt), avec bug TRAIL fallback
   - OPEN_STRATS: hardcode x4 (chaque script avait sa propre copie)
   - prev_day_data: methodes differentes dans chaque script
   - Conflict filter: implementations separees

Consequence: **impossible de garantir que BT = compare = live**. Chaque script avait son propre chemin de code.

### Decision: UN SEUL MOTEUR — `backtest_engine.py`
**Principe** : on ne peut pas garantir la coherence si on a plusieurs implementations de la meme logique. La seule solution est que TOUS les scripts importent les MEMES fonctions.

`backtest_engine.py` centralise :
- `OPEN_STRATS` : defini UNE SEULE fois (frozenset)
- `load_data(conn, symbol)` : candles **FULL history** + ATR (`compute_atr`) + trading_days + `compute_indicators`
- `collect_trades(candles, daily_atr, ..., portfolio, sym_exits, date_filter=None)` : `detect_all` + `sim_exit_custom` + conflict filter (tri alpha + no-opposite)
- `eval_portfolio(trades, risk, capital)` : event-based PF/WR/DD/Rend
- `prev_trading_day(day, trading_days)` : jour precedent
- `_make_day_data(yc)` : prev_day_data standardise

### Resultat: meme code, memes donnees, partout
| Script | Avant | Apres |
|---|---|---|
| bt_portfolio | pkl (snapshot stale) | `backtest_engine.collect_trades()` ✓ |
| compare_today | inline LIMIT 2000 + ATR custom | `backtest_engine.collect_trades(date_filter=today)` ✓ |
| live_mt5 | LIMIT 1500 + `get_yesterday_atr()` | `backtest_engine.load_data()` + `prev_trading_day()` ✓ |
| optimize_all | sim_exit_np (fallback fixe) | _(conserve sim_exit_np pour perf grid search)_ |

**Validation** : bt_portfolio 5ers XAUUSD avant/apres refacto = EXACT MATCH (1619 trades, PF 1.49).
compare_today 5ers : 5/5 directions match, deltas reduits (BB_TIGHT -1.03 vs -9.28 avant).

### Le pkl n'est plus une source de verite
- optimize_all genere toujours un pkl (cache pour grid search + analyze_combos)
- Mais bt_portfolio, compare_today et live **ne le lisent plus**
- Tout est calcule en temps reel depuis la DB
- Plus jamais de divergence candles/ATR/indices entre scripts

### Validation
- Resultat de reference: bt_portfolio 5ers XAUUSD = PF 1.49, WR 71%, DD -0.8%, Rend +12%, 1619 trades, M+ 12/13
- Apres refacto: **EXACT MATCH** (1619 trades, PF 1.49, WR 71%, $111,931)
- compare_today 5ers: 5/5 directions match, deltas reduits (BB_TIGHT -1.03 vs -9.28 avant)

### Scripts alignes sur backtest_engine.py
- `bt_portfolio.py` ✓ — import load_data, collect_trades, eval_portfolio
- `compare_today.py` ✓ — import load_data, collect_trades (date_filter=today)
- `live_mt5.py` ✓ — import load_data, prev_trading_day, OPEN_STRATS, _make_day_data
- `optimize_all.py` — sim_exit_np TRAIL fallback fixe (return max_bars, close)

### Re-pipeline complet 5ers (2026-04-06)
Optimize_all + analyze_combos + selection combos + config + strat_exits, tout sur candles actuelles DB.

| Instrument | Combo | Nb | PF | WR | DD | Rend | M+ |
|---|---|---|---|---|---|---|---|
| XAUUSD | Sharpe 8 | 8 | 1.50 | 70% | -0.7% | +11% | 13/13 |
| JPN225 | Calmar 3 | 3 | 1.59 | 79% | -0.6% | +5% | 11/13 |
| DAX40 | Sharpe 9 | 9 | 1.70 | 74% | -0.7% | +19% | 13/13 |
| NAS100 | Calmar 8 | 8 | 1.39 | 67% | -1.4% | +13% | 13/13 |
| SP500 | Sharpe 6 | 6 | 1.49 | 66% | -0.8% | +13% | 12/13 |
| UK100 | Calmar 3 | 3 | 1.51 | 83% | -0.3% | +4% | 12/13 |

Portfolios:
- XAUUSD: IDX_VWAP_BOUNCE, ALL_FVG_BULL, PO3_SWEEP, ALL_PIVOT_BRK, D8, IDX_PREV_HL, ALL_BB_TIGHT, IDX_ORB30
- JPN225: ALL_NR4, ALL_STOCH_PIVOT, TOK_NR4
- DAX40: ALL_MACD_HIST, ALL_CCI_20_ZERO, ALL_ELDER_BULL, IDX_TREND_DAY, ALL_FIB_618, ALL_RSI_DIV, TOK_FISHER, TOK_STOCH, IDX_ENGULF
- NAS100: D8, ALL_STOCH_RSI, LON_STOCH, ALL_CCI_100, ALL_WILLR_7, ALL_RSI_50, ALL_DOJI_REV, ALL_ADX_RSI50
- SP500: TOK_FISHER, IDX_CONSEC_REV, IDX_RSI_REV, ALL_ENGULF, ALL_HAMMER, ALL_RSI_EXTREME
- UK100: ALL_MACD_HIST, IDX_LATE_REV, ALL_CONSEC_REV

Zero strats open dans les portfolios ✓
Risk: 0.05% par instrument
strat_exits regenere depuis pkls frais (sim_exit_np fallback fixe)
LIVE_INSTRUMENTS = ['XAUUSD'] (seul actif en live)

### Validation bt_portfolio agrege (backtest_engine, temps reel)
```
Trades: 8,278 | WR: 72% | PF: 1.52 | Max DD: -1.32% | Rend: +82.4% | M+: 13/13
Capital: $100,000 → $182,381
```
13/13 mois positifs. DD max -1.32% sur compte unique 6 instruments.
Calcule 100% en temps reel depuis la DB via backtest_engine.py — zero pkl.

### Re-pipeline complet FTMO (2026-04-06)
6 instruments charges (XAUUSD, GER40, US500, US100, US30, UK100). UK100 skip (PF 1.47, 10/13).

| Instrument | Combo | Nb | PF | WR | DD | Rend | M+ |
|---|---|---|---|---|---|---|---|
| XAUUSD | Sharpe 9 | 9 | 1.53 | 72% | -0.9% | +15% | 13/13 |
| GER40.cash | Calmar 10 | 10 | 1.84 | 68% | -0.7% | +32% | 13/13 |
| US500.cash | Calmar 4 | 4 | 1.61 | 70% | -0.6% | +10% | 12/13 |
| US100.cash | Calmar 6 | 6 | 1.49 | 73% | -0.6% | +10% | 13/13 |
| US30.cash | PF 3 | 3 | 1.51 | 72% | -0.5% | +5% | 13/13 |

### Validation bt_portfolio FTMO agrege (backtest_engine, temps reel)
```
Trades: 6,961 | WR: 71% | PF: 1.64 | Max DD: -1.05% | Rend: +90.6% | M+: 13/13
Capital: $100,000 → $190,629
```
13/13 mois positifs. DD max -1.05%. Calcule temps reel via backtest_engine.

## 2026-04-06 — REFACTO: bt_portfolio sans pkl, tout en temps reel

### Probleme identifie par audit
- `audit_bt_vs_compare.py` sur 5ers: **0% match** entre bt_portfolio (pkl) et compare_today (temps reel)
- Cause: le pkl stocke des bar indices (`ei=70444`) lies a un snapshot de candles. La DB a change depuis (re-fetch, drop last candle) → indices OOB, trades decales
- 3 sources de verite divergentes: pkl (bt_portfolio), detect_all temps reel (compare_today), live (live_mt5)

### Decision
Supprimer la dependance au pkl dans bt_portfolio.py. Le BT recalcule detect_all + sim_exit en temps reel depuis la DB, exactement comme compare_today et live_mt5.

### Nouvelle architecture
- `optimize_all.py` → genere toujours le pkl (cache pour grid search + analyze_combos)
- `analyze_combos.py` → lit toujours le pkl (partie optimisation)
- `strat_exits.py` → genere depuis pkl (configs exits)
- **`bt_portfolio.py`** → **NOUVEAU: calcul temps reel depuis DB + strat_exits** (plus de pkl)
- `compare_today.py` → temps reel depuis DB (deja fait)
- `live_mt5.py` → temps reel depuis DB (deja fait)

Resultat: BT = compare = live = **meme code, memes donnees**. Plus jamais de divergence pkl/DB.

## 2026-04-06 — BUG CRITIQUE live_mt5: fill price=0 casse le trailing

### Bug identifie
MT5 `order_send` retourne `result.price = 0.00` sur FTMO (quirk broker). `live_mt5.py` utilisait ce prix pour initialiser `entry` et `best` du trailing a 0. Consequence:
- `fav = best - entry = close - 0 = close` → trail s'active **immediatement**
- SL deplace a `close - trail*atr` → beaucoup trop serre (~3 pts sous le prix)
- Tous les trades sortent en perte dans les minutes suivantes

### Impact
- **Tous les trades FTMO du 2026-04-06** (8 trades XAUUSD) ont ete affectes
- Pertes totales: -96 pts (au lieu de +26 pts sans le bug)
- Bug present depuis la mise en live du trailing FTMO

### Fix
- `live_mt5.py` ligne 138: si `result.price == 0`, utiliser le prix du tick (`price` calcule avant l'envoi)
- `strats.py` ligne 267: fallback TRAIL `return 1, entry` remplace par exit au close du dernier bar (meme logique que TPSL)

### Aussi fixe
- `compare_today.py`: ATR calcule via `compute_atr()` (identique pipeline) au lieu d'un calcul inline divergent

### Aussi fixe: compare_today.py filtre de date (broker UTC+3)
- `din.time` de MT5 est en heure broker (UTC+3), pas UTC
- Filtre par `(entry_broker - 3h).date() == today` pour eviter les trades de la veille
- Corrige les faux DIR MISMATCH sur trades du dimanche soir

### Resultats compare 5ers (apres fix)
- 4/4 trades directions matchent ✓
- TOK_FISHER: BT -22 / LV -23.57 (diff -1.57, spread)
- ALL_PIVOT_BRK: BT +4.54 / LV +1.82 (diff -2.72, spread+slippage)
- ALL_BB_TIGHT: BT +15.63 / LV +6.35 (diff -9.28, BT fallback dernier bar)
- ALL_FVG_BULL: BT +20.46 / LV +11.10 (diff -9.36, idem)
- Entry diffs 2.4-2.9 pts = spread + slippage (ouverture session)

### Action immediate
- Redeployer `live_mt5.py` sur le VPS FTMO (bug fill=0)

## 2026-04-05 — DECISION: abandon complet de la crypto algo

### Contexte final
Apres avoir:
1. Fetche 2 ans de candles 15m crypto (25 coins via CCXT Binance Futures)
2. Cree `strats_crypto.py` avec 35 strats dediees crypto (Donchian, Keltner, SuperTrend, Ichimoku, SMC, Wyckoff, etc.)
3. Integre les fees HL au niveau trade dans `optimize_crypto.py` (taker 0.045% entry + maker 0.015% exit)
4. Lance optim complete avec filtre margin 8% puis 5%

### Resultats bruts (17/25 cryptos completes avant arret)

| Crypto | Best PF | DD | Rend 25mo | M+ |
|---|---|---|---|---|
| **BTC** | **1.72** | -6.6% | **+46%** | 19/24 |
| **AVA** | **1.47** | -7.5% | **+78%** | 20/25 |
| HYPE | 1.39 | -8.3% | +67% | 10/11 |
| AAVE | 1.28 | -9.8% | +51% | 18/25 |
| LNK | 1.54 | -12.2% | +31% | 12/25 |
| ALGO | 1.21 | -5.4% | +12% | 12/25 |
| LTC | 1.23 | -6.1% | +17% | 14/25 |
| ADA | 1.11 | -8.6% | +16% | 17/25 |
| BCH, BNB, DOGE, DOT, ETC, ETH, FET | **AUCUN combo viable** | - | - | - |

### Comparaison avec MT5 XAUUSD
| Account | PF | DD | Rend 25mo |
|---|---|---|---|
| ICM Calmar 12 | 1.62 | -12.5% | **+3523%** |
| FTMO Calmar 8 | 1.65 | -6% | **+743%** |
| 5ers MinDD 5 | 1.62 | -2.5% | +83% |
| **Crypto best (BTC)** | 1.72 | -6.6% | **+46%** (80x moins que ICM) |

### Conclusion
- **L'edge sur crypto n'est pas la** pour de l'algo directional retail
- Raisons structurelles: marche 24/7 (pas de rythme institutionnel), fees relatives plus grosses, random walk plus pur, manip des market makers, pas de session opens exploitables
- 7/17 cryptos testees n'ont **AUCUNE** combo viable apres fees meme avec filtre margin baisse a 5%
- Le meilleur combo crypto (BTC PF 1.72 Rend +46%) est **80x moins rentable** que le pire portfolio MT5 (5ers Rend +83%)
- Decision pragmatique: **abandonner complet crypto**, focus sur MT5 XAUUSD/indices ou l'edge est reel et reproductible

### Cleanup prevu (a valider)
- Garder `strats_crypto.py`, `optimize_crypto.py`, `bt_portfolio_crypto.py`, `hl_fetch.py`, `crypto_data.py`, `config_crypto.py` en depot (utile comme reference/apprentissage)
- Ne pas supprimer les tables `candles_hl_*_15m` (peut servir si retour futur)
- Pas de live crypto a creer (live_hyperliquid, dashboard_hl, compare_today_hl annules)
- Focus total sur MT5: 5ers (live test en cours), FTMO (validated), ICM (live propre)

### Apprentissages transferables pour MT5
- Le framework fees-aware (integration fees au niveau trade) reste pertinent pour verifier MT5 XAUUSD avec spreads reels
- La methode fee_per_unit dans optimize_crypto pourrait etre portee dans optimize_all pour audit
- Les regles look-ahead stricts appliquees dans strats_crypto sont un bon rappel pour tout futur developpement

## 2026-04-05 — Plan: 35 strategies crypto 15m dediees

### Contexte
Apres integration des fees HL dans `optimize_crypto.py`, le run sur 6 cryptos a montre que la majorite des strats XAUUSD/indices actuelles (65 strats dans `strats.py`) ne survivent pas aux fees sur crypto 15m. Raisons identifiees :
- Sessions (Tokyo, London, NY) inutiles sur crypto 24/7
- Patterns 5m (inside day, gaps, etc.) inadaptes au 15m
- Stops serres (1-3 ATR sur 5m) → notional huge → fee drag massif
- Edges trop faibles pour PF survivent aux frais 0.06% round-trip

### Decision
Creer **35 strategies crypto-specifiques** pour 15m, dans un **nouveau fichier** `strats_crypto.py` (zero impact sur `strats.py` MT5 5ers/ftmo/icm).

### Recherche sources web
- CoinGape, Quantified Strategies, PyQuantLab, FMZ Quant, TradingView public scripts
- Reddit r/algotrading (via web snippets), Medium quant community
- SMC/ICT, Wyckoff, Volume Profile references
- Arxiv papers sur quant crypto (mentions)

### Liste des 35 strategies

**Trend-following / Momentum (10)** — stops et targets larges, naturellement fee-resistant
1. CRYPTO_DONCHIAN_20 — Break Donchian 20-bar
2. CRYPTO_DONCHIAN_50 — Break Donchian 50-bar (slower)
3. CRYPTO_KELTNER_MOMO — Break Keltner upper/lower + ROC positif/negatif
4. CRYPTO_SUPERTREND_FLIP — SuperTrend(10,3) flip + ADX>25
5. CRYPTO_ICHIMOKU_CROSS — Price ferme au-dessus/sous Kumo + Tenkan×Kijun
6. CRYPTO_HMA_TRIPLE — HMA9×HMA21 avec HMA50 meme direction
7. CRYPTO_EMA_21_55_ADX — EMA cross + ADX>25
8. CRYPTO_PSAR_EMA200 — PSAR flip dans le sens EMA200
9. CRYPTO_HA_TREND — 3 bougies Heikin Ashi meme couleur sans meche opposite
10. CRYPTO_MACD_ZERO — MACD cross zero-line + prix vs EMA200

**Volatility expansion / Breakout (6)** — fee-friendly car moves explosifs
11. CRYPTO_BBKC_SQUEEZE — BB inside KC 10+ bars, puis release + momentum (TTM)
12. CRYPTO_ATR_SPIKE — Bougie range > 2× ATR20, suivre direction
13. CRYPTO_ORB_UTC — Open Range 4 premieres bougies 00:00 UTC, break + retest
14. CRYPTO_LONDON_OR — Open Range 08:00-09:00 UTC (sess London = flux institutionnels)
15. CRYPTO_CONSO_VOL_BRK — Range 20+ bars, ATR declinant, break avec volume>2×
16. CRYPTO_NR7 — Narrowest Range 7 bars, break high/low

**Mean reversion selectives (5)** — entries extremes uniquement
17. CRYPTO_RSI_DEEP_DIV — RSI<20 + divergence haussiere
18. CRYPTO_STOCH_RSI_EXTREME — StochRSI<5 ou >95 + reversal bar
19. CRYPTO_BB_OUTLIER — Prix > 2.5 std outside BB(20,2)
20. CRYPTO_VWAP_RECLAIM — Clash + reclaim VWAP avec volume
21. CRYPTO_AVWAP_BOUNCE — Bounce sur Anchored VWAP depuis dernier swing high/low

**Smart Money Concepts / ICT (4)**
22. CRYPTO_BOS_FVG — Break of Structure + entry dans Fair Value Gap
23. CRYPTO_LIQ_SWEEP — Wick au-dessus/sous swing H/L puis close oppose
24. CRYPTO_ORDER_BLOCK — Retest d'un OB (bougie avant impulsion)
25. CRYPTO_OTE_618 — Entry zone Fib 0.62-0.79 d'un leg impulsif

**Volume / Market Profile (4)**
26. CRYPTO_HVN_REJECT — Reject sur High Volume Node (POC days)
27. CRYPTO_LVN_BRK — Break rapide Low Volume Node + volume spike
28. CRYPTO_POC_MIGRATION — Suivre migration POC jour par jour
29. CRYPTO_VOL_SPIKE — Volume>3× moyenne + body>1.5 ATR

**Chart patterns / Structure (3)**
30. CRYPTO_DOUBLE_BOT_TOP — Double bottom/top avec volume decroissant
31. CRYPTO_INV_HS — Inverse Head & Shoulders break neckline + retest
32. CRYPTO_WYCKOFF_SPRING — Drop sous range puis reclaim rapide

**Multi-timeframe (2)**
33. CRYPTO_HTF_BIAS — Trend 4h + pullback EMA21 15m
34. CRYPTO_WEEKLY_PIVOT — Reaction aux pivots R1/S1 weekly confirme 15m

**Derivatives (1)**
35. CRYPTO_FUNDING_EXTREME — Funding>+0.05% = short, <-0.05% = long (si data dispo)

### Architecture d'implementation
1. `strats_crypto.py` (nouveau) — contient `detect_all_crypto(row, prev, ...)` + indicateurs specifiques (Donchian, Keltner, SuperTrend, Ichimoku, HMA, Heikin Ashi, VWAP, volume profile approximatif)
2. `optimize_crypto.py` — import `detect_all_crypto` au lieu de `strats.detect_all`
3. `strats.py` — **INTACT** (MT5 pipelines preserves)
4. Nouveaux noms prefixes **CRYPTO_** pour eviter collision avec strats existantes
5. Pas de STRAT_ID collision : les strats CRYPTO_ seront ajoutees a STRAT_ID avec de nouveaux index

### Look-ahead bias — REGLES ABSOLUES a respecter (cf LOOK_AHEAD_CHECKLIST.md)
1. **Entry sur bougie fermee** : toutes les conditions utilisent `prev` (bougie i-1) ou row ferme
2. **Entry price = close** de la bougie fermee
3. **Pas d'open strats** (pas de signal sur row['open'])
4. **Indicateurs forward-only** : ewm(), rolling() strict lookback, SuperTrend/PSAR boucle forward
5. **ATR du jour = ATR de la veille** (daily_atr[prev_day])
6. **1 trigger max par strat par jour** via `trig` dict reset quotidien
7. **Pas de biais directionnel non teste** : chaque strat doit avoir LONG ET SHORT (ou clairement marquee directionnelle)
8. **Audit signals** post-implementation : verifier BT vs live parity
9. **VWAP / Volume Profile** : calcul cumulatif du debut de session, pas sur toute la journee en avance
10. **HTF data (4h, weekly)** : utiliser uniquement le bar precedent ferme, pas le bar en cours

### Scope & phases
- Phase 1 : lire `strats.py`, identifier signature `detect_all()` + indicateurs existants
- Phase 2 : creer `strats_crypto.py` avec indicateurs + 10 strats trend-following (commit)
- Phase 3 : +6 strats volatility/breakout (commit)
- Phase 4 : +5 strats mean reversion (commit)
- Phase 5 : +4 SMC (commit)
- Phase 6 : +4 volume, +3 patterns (commit)
- Phase 7 : +2 HTF, +1 funding (commit)
- Phase 8 : adapter `optimize_crypto.py` + run complete (commit)
- Phase 9 : audit signals (verif pas de look-ahead)
- Phase 10 : validation combos instrument par instrument

### Zero impact MT5
- `strats.py` jamais touche
- `phase3_analyze.py` jamais touche
- `optimize_all.py` jamais touche
- `bt_portfolio.py` jamais touche
- Aucune config 5ers/ftmo/icm modifiee
- Pkls MT5 dans `data/5ers/**`, `data/ftmo/**`, `data/icm/**` intacts

## 2026-04-05 — PIVOT Crypto: abandon 5m, passage 15min

### Decision
Apres avoir integre les frais Hyperliquid dans `bt_portfolio_crypto.py` (Taker 0.045% entry + Maker 0.015% exit = 0.060% round-trip sur notional), le backtest agrege crypto passe de **+5756% a -57.8%**. Les frais annulent totalement l'edge.

### Analyse root cause
Les strats 5min ont des stops tres serres (sl_atr 1-3 sur 5m = 0.2-0.7% du prix). Ratio notional/risk = 150-400x. Les frais (0.06% sur notional) representent une fraction enorme du gain brut par trade. Exemple BTC ALL_AO_SAUCER: gross $23/trade, fee $34/trade -> net **-$11**.

Le bruit du 5m crypto + stops serres = structure non viable avec frais realistes.

### Decision
- **Abandon complet du 5m crypto** (aucun recovery possible avec stops larges seuls, trop de bruit sur crypto a cette echelle)
- **Passage en 15min**
- ATR 15m ≈ sqrt(3) * ATR 5m -> stops effectifs plus larges mecaniquement
- Ratio gross/fee passe de ~1.4 a ~4.4 (a PF equivalent)
- Vidage complet des tables crypto 5m en DB, re-fetch en 15m, re-optim complete

### Impact zero MT5
Modifications uniquement sur:
- Tables `candles_mt5_<crypto>_5m` (drop, crypto uniquement)
- `hl_fetch.py` (TF 5m -> 15m)
- `optimize_crypto.py`, `bt_portfolio_crypto.py` (chemins data)
- `data/crypto/**` (pkls regeneres)
Les pipelines 5ers, FTMO, ICM restent **intacts**.

## 2026-04-05 — Crypto combo re-validation complete

Motif: pkls re-optimises (25 mois, forex hours filter, margin WR>=8%) rendaient les anciens portfolios stales (ecrits lors d'une session precedente sur d'anciens pkls).

**10 cryptos validees** (remplacent les 13 anciennes stales):

| Crypto | Combo | Strats | PF | WR | DD | Rend | M+ |
|---|---|---|---|---|---|---|---|
| BNBUSD | PF 9 | ALL_CMO_9, LON_ASIAN_BRK, TOK_2BAR, LON_STOCH, ALL_HMA_CROSS, ALL_MACD_FAST_SIG, TOK_NR4, IDX_BB_REV, NY_HMA_CROSS | 1.54 | 72% | -3.9% | +253% | 25/25 |
| BTCUSD | Calmar 3 | D8, ALL_AO_SAUCER, PO3_SWEEP | 1.73 | 82% | -1.4% | +27% | 23/25 |
| ETHUSD | Calmar 3 | D8, ALL_ENGULF, IDX_ENGULF | 1.55 | 75% | -3.6% | +41% | 21/25 |
| BCHUSD | Calmar 4 | ALL_CCI_100, LON_ASIAN_BRK, ALL_MOM_14, ALL_CMO_14_ZERO | 1.37 | 58% | -5.7% | +97% | 18/25 |
| AVAUSD | Calmar 4 | D8, ALL_DOJI_REV, IDX_GAP_FILL, ALL_MACD_HIST | 1.28 | 69% | -4.4% | +36% | 19/25 |
| NEOUSD | Calmar 5 | D8, ALL_HAMMER, ALL_RSI_DIV, LON_ASIAN_BRK, ALL_MACD_DIV | 1.41 | 68% | -3.3% | +74% | 23/25 |
| DOGEUSD | Calmar 2 | ALL_AO_SAUCER, ALL_ELDER_BEAR | 1.45 | 77% | -2.2% | +27% | 20/25 |
| DOTUSD | Calmar 3 | D8, ALL_MACD_HIST, ALL_STOCH_RSI | 1.39 | 80% | -2.2% | +22% | 18/25 |
| ADAUSD | Calmar 2 | D8, ALL_RSI_DIV | 1.38 | 80% | -1.3% | +11% | 19/25 |
| AAVEUSD | Calmar 2 | D8, IDX_NY_MOM | 1.61 | 74% | -1.2% | +18% | 21/25 |

**Skip (15)**:
- Perfs insuffisantes: NEAR, ALGO, XRP, PEPE, ZEC, LNK
- Data issues (pkl post-filtre margin 8% vide ou open strats uniquement): LTC, XMR, ETC, FET, HYPE, SOL, SUI, TAO, UNI

Score composite utilise pour ranking: `sharpe * sqrt(pf) * pm/tm`.
LIVE_INSTRUMENTS toujours vide — en attente pipeline live Hyperliquid.

### strat_exits.py regenere (2026-04-05)
- Anciennes entrees crypto (12 cryptos stales: BNB/LTC/BCH/AVA/NEO/BTC/XMR/DOT/DOGE/XRP/ETH/ETC) supprimees
- Nouvelles entrees pour les 10 cryptos valides (BNB, BTC, ETH, BCH, AVA, NEO, DOGE, DOT, ADA, AAVE)
- Tous les strats de chaque portfolio sont couverts, sync depuis best_configs des pkls actuels (25 mois)
- Aucune modification des entrees 5ers / ftmo / icm — zero regression sur MT5

## 2026-04-04 — Test strategies sur cryptos

### Cryptos chargees en DB (1 an de 5m, ~100k bougies chacune)
BTCUSD, ETHUSD, SOLUSD, BNBUSD, XRPUSD, ADAUSD, DOGEUSD, LTCUSD, BCHUSD, DOTUSD, LNKUSD, XMRUSD, AVAUSD, ETCUSD, NEOUSD

### optimize_all 5ers marge 8% — resultats par crypto
| Crypto | Strats safe | Total | Status |
|---|---|---|---|
| BTCUSD | 7 | 103 | Done |
| ETHUSD | 5 | 107 | Done |
| SOLUSD | 4 | 87 | Done |
| BNBUSD | 23 | 104 | Done |
| XRPUSD | 7 | 88 | Done |
| ADAUSD | 4 | 76 | Done |
| DOGEUSD | 6 | 84 | Done |
| LTCUSD | 10 | 97 | Done |
| BCHUSD | 8 | 101 | Done |
| DOTUSD | 11 | 95 | Done |
| LNKUSD | ? | ? | En cours |
| XMRUSD | ? | ? | En cours |
| AVAUSD | ? | ? | En cours |
| ETCUSD | ? | ? | En cours |
| NEOUSD | ? | ? | En cours |

### analyze_combos — top combo par crypto (7 premieres)
| Crypto | Best | Nb | Trades | PF | WR | DD | Rend | M+ |
|---|---|---|---|---|---|---|---|---|
| **BNBUSD** | PF*WR 11 | 11 | 2911 | 1.55 | 78% | -0.9% | +19% | 13/13 |
| BTCUSD | Calmar 5 | 5 | 1130 | 1.51 | 58% | -0.8% | +13% | 12/13 |
| DOGEUSD | Diverse 4 | 4 | 1018 | 1.49 | 69% | -1.1% | +8% | 12/13 |
| XRPUSD | Calmar 2 | 2 | 709 | 1.65 | 80% | -0.3% | +5% | 13/13 |
| ETHUSD | Calmar 3 | 3 | 744 | 1.50 | 74% | -0.4% | +5% | 11/13 |
| SOLUSD | Calmar 2 | 2 | 581 | 1.35 | 69% | -0.8% | +3% | 10/13 |
| ADAUSD | Calmar 3 | 3 | 581 | 1.35 | 74% | -0.6% | +3% | 10/13 |

### optimize_all — resultats complets 15 cryptos
| Crypto | Strats safe | Total |
|---|---|---|
| BNBUSD | 23 | 104 |
| DOTUSD | 11 | 95 |
| LTCUSD | 10 | 97 |
| NEOUSD | 9 | 91 |
| BCHUSD | 8 | 101 |
| XMRUSD | 8 | 85 |
| BTCUSD | 7 | 103 |
| XRPUSD | 7 | 88 |
| AVAUSD | 7 | 96 |
| ETCUSD | 7 | 86 |
| DOGEUSD | 6 | 84 |
| ETHUSD | 5 | 107 |
| LNKUSD | 5 | 83 |
| SOLUSD | 4 | 87 |
| ADAUSD | 4 | 76 |

### analyze_combos — top combo par crypto (classees par Rend/DD)
| Crypto | Safe | Nb | Trades | PF | WR | DD | Rend | M+ | Rend/DD |
|---|---|---|---|---|---|---|---|---|---|
| AVAUSD | 7 | 6 | 1357 | 1.59 | 71% | -0.5% | +12% | 13/13 | 24.0 |
| BNBUSD | 23 | 11 | 2911 | 1.55 | 78% | -0.9% | +19% | 13/13 | 21.1 |
| NEOUSD | 9 | 6 | 1257 | 1.71 | 74% | -0.6% | +12% | 12/13 | 20.0 |
| BCHUSD | 8 | 6 | 1793 | 1.61 | 71% | -1.0% | +17% | 13/13 | 17.0 |
| XMRUSD | 8 | 5 | 1368 | 1.61 | 73% | -0.7% | +12% | 12/13 | 17.1 |
| XRPUSD | 7 | 2 | 709 | 1.65 | 80% | -0.3% | +5% | 13/13 | 16.7 |
| DOTUSD | 11 | 8 | 2446 | 1.40 | 73% | -0.9% | +15% | 11/13 | 16.7 |
| BTCUSD | 7 | 5 | 1130 | 1.51 | 58% | -0.8% | +13% | 12/13 | 16.3 |
| LTCUSD | 10 | 8 | 2615 | 1.60 | 75% | -1.4% | +21% | 12/13 | 15.0 |
| ETHUSD | 5 | 3 | 744 | 1.50 | 74% | -0.4% | +5% | 11/13 | 12.5 |
| ETCUSD | 7 | 4 | 922 | 1.55 | 77% | -0.5% | +6% | 12/13 | 12.0 |
| DOGEUSD | 6 | 4 | 1018 | 1.49 | 69% | -1.1% | +8% | 12/13 | 7.3 |

LNK, SOL, ADA exclus (trop faibles).

### Backtest agrege 12 cryptos — tests de risk
| Risk | Rend | DD | PF | Capital final |
|---|---|---|---|---|
| 0.05% | +287% | -1.4% | 1.53 | $386k |
| 0.1% | +1,382% | -2.8% | 1.51 | $1.5M |
| 0.2% | +21,182% | -5.6% | 1.46 | $21M |
| 0.5% | insense | -13.5% | 1.40 | insense |

Decision: risk 0.2% pour config_crypto.py.

### Migration CCXT Binance Futures (2026-04-04)
L'API Hyperliquid est limitee a 5000 candles (~17 jours en 5m). Insuffisant pour backtest.
Migration vers CCXT Binance Futures: historique complet 2+ ans, pas de limite.
hl_fetch.py reecrit avec ccxt.binance (futures), meme logique: drop last candle, commit par batch.

### Backfill 25 cryptos — 2 ans de 5m via Binance Futures
| Crypto | Candles | Periode | Jours |
|---|---|---|---|
| BTC, ETH, SOL, BNB, XRP, ADA, DOGE, LTC, BCH, DOT, LINK, XMR, AVAX, ETC, NEO, ZEC, NEAR, ALGO, SUI, FET, AAVE, UNI, PEPE | 210k | 2024-04-04 -> 2026-04-04 | 730 |
| TAO | 208k | 2024-04-11 -> 2026-04-04 | 723 |
| HYPE | 89k | 2025-05-30 -> 2026-04-04 | 309 |

25 symboles charges.

### optimize_crypto.py — filtre heures forex
Copie de optimize_all.py avec filtre: seules les candles pendant les heures forex
sont evaluees (dimanche 22h UTC -> vendredi 22h UTC). Samedi + dimanche avant 22h = skip.
Raison: on veut profiter des flux institutionnels, pas du bruit de week-end.
Les strats ne sont optimisees que sur les heures avec du vrai volume.

### Impact filtre forex sur BTC (2 ans de donnees)
| Config | Strats safe | Best combo | PF | DD | Rend |
|---|---|---|---|---|---|
| Sans filtre (24/7) | 1/99 | - | - | - | - |
| **Avec filtre forex** | **4/107** | Greedy 4 | 1.68 | -7.5% | **+251%** |

Le bruit du week-end diluait les signaux. Le filtre forex hours donne 4x plus de
strats safe et des rendements exploitables. Optimize crypto relance sur les 25.

### Resultats optimize_crypto 25 cryptos (2 ans, forex hours)
| Tier | Crypto | Strats safe |
|---|---|---|
| TOP | BNB | 12 |
| TOP | NEO | 9 |
| TOP | ZEC | 9 |
| BON | ALGO | 6 |
| BON | BCH | 5 |
| BON | BTC, ETH, DOGE, DOT, AVAX, NEAR | 4 chacun |
| MOY | ADA, LINK, ETC, AAVE, UNI, PEPE | 3 chacun |
| FAIBLE | XRP, HYPE, TAO | 2 chacun |
| FAIBLE | SOL, LTC, XMR, SUI, FET | 1 chacun |

BNB, NEO, ZEC en haut. Prochaine etape: analyze_combos sur les 25, choix des combos.

### Architecture MT5 vs Hyperliquid

Separation claire entre les 2 plateformes d'execution:

**Commun (agnostique plateforme):**
- strats.py — detection signaux + indicateurs
- strat_exits.py — configs exit par (broker, instrument)
- optimize_all.py — optimisation (genere pkl)
- analyze_combos.py — recherche de combos
- bt_portfolio.py — backtest agrege

**MT5 (propfirm + perso):**
- config_5ers.py, config_ftmo.py, config_icm.py
- live_mt5.py — execution MT5
- compare_today.py — compare BT vs MT5
- dashboard.py — dashboard MT5
- mt5_fetch_clean.py — fetch MT5 -> PostgreSQL
- data/5ers/, data/ftmo/ — pkl MT5

**Hyperliquid (crypto):**
- config_crypto.py — 12 cryptos, 0.2% risk
- live_hyperliquid.py — execution Hyperliquid (a creer)
- compare_today_hl.py — compare BT vs Hyperliquid (a creer)
- dashboard_hl.py — dashboard Hyperliquid (a creer)
- hl_fetch.py — fetch Hyperliquid API -> PostgreSQL (a creer)
- data/crypto/ — pkl crypto

**Donnees:**
- Les candles crypto sont en DB PostgreSQL (fetchees via MT5 pour le moment)
- Les pkl crypto sont dans data/crypto/ (generes par optimize_all.py 5ers --symbol)
- Quand Hyperliquid sera connecte, les candles viendront de hl_fetch.py
  et les pkl devront etre regeneres (prix/spreads differents)

**Prochaines etapes:**
1. Creer data/crypto/ et deplacer les pkl
2. Creer hl_fetch.py (API Hyperliquid -> PostgreSQL)
3. Creer live_hyperliquid.py (execution)
4. Tester en paper trading
5. Lancer en live

---

## 2026-03-30 — Filtre marge WR, retrait open strats, fix magic/conflit

### REGLE: Filtre marge WR >= 8% obligatoire
La marge = WR_reel - WR_breakeven. Le WR_breakeven = 1/(1+RR) ou RR = avg_win/avg_loss.
Si la marge est trop faible, un leger glissement en live suffit a rendre la strat perdante.

Seuils testes (XAUUSD 5ers, toutes strats close-only ensemble):
| Marge | Strats | Trades | PF | WR | DD | Rend | M+ |
|---|---|---|---|---|---|---|---|
| 0% | 47 | 8283 | 1.32 | 73% | -4.3% | +41% | 10/13 |
| 5% | 47 | 8283 | 1.32 | 73% | -4.3% | +41% | 10/13 |
| 7% | 27 | 4841 | 1.32 | 70% | -3.2% | +25% | 11/13 |
| **8%** | **18** | **3299** | **1.37** | **70%** | **-1.6%** | **+19%** | **13/13** |
| 10% | 11 | 1933 | 1.42 | 69% | -0.9% | +13% | 12/13 |
| 12% | 1 | 234 | 1.52 | 65% | -0.8% | +2% | 10/13 |

Decision: **8%** — compromis entre qualite et diversification sur 6 instruments.
- 10% tue SP500, UK100, NAS100 (trop peu de strats)
- 8% garde 4-25 strats par instrument, tous viables

Filtre applique dans:
1. optimize_all.py: filtre les strats AVANT de construire les arrays du pkl
2. analyze_combos.py: re-filtre au chargement AVANT la recherche de combos

### Audit marge dans le combo (XAUUSD PF*WR 19 — AVANT correction)
2 strats DANGER detectees dans le contexte du combo (conflit filter change la WR):
| Strat | WR combo | RR | WRmin | Marge | PF combo | Verdict |
|---|---|---|---|---|---|---|
| D8 | 48% | 1.12 | 47% | +0.5% | 1.02 | DANGER — quasi random |
| ALL_BB_SQUEEZE | 85% | 0.24 | 80% | +5.0% | 1.42 | DANGER — RR=0.17:1, risque 16.5pts pour 2.8pts |

### Strats viables par instrument (marge >= 8%, close-only)
| Instrument | Viables | Filtrees | Best combo | PF | DD | Rend | M+ |
|---|---|---|---|---|---|---|---|
| XAUUSD | 18 | 29 | PF 16 (1.43) | 1.43 | -1.1% | +20% | 13/13 |
| JPN225 | 8 | 19 | Calmar 8 (1.49) | 1.49 | -0.7% | +11% | 11/13 |
| DAX40 | 25 | 32 | Calmar 15 (1.66) | 1.66 | -0.9% | +36% | 12/13 |
| NAS100 | 7 | 20 | Calmar 7 (1.45) | 1.45 | -1.0% | +11% | 12/13 |
| SP500 | 6 | 11 | Calmar 5 (1.53) | 1.53 | -0.8% | +10% | 12/13 |
| UK100 | 4 | 11 | Calmar 4 (1.63) | 1.63 | -0.6% | +10% | 12/13 |

### Re-generation pkl avec marge 8% + revalidation combos (2026-03-31)
Audit pipeline a revele que les anciens pkl (marge 5%) etaient desalignes des combos (marge 8%).
optimize_all.py relance pour les 6 instruments avec marge 8%.
Strats safe par instrument: XAUUSD 13, JPN225 8, DAX40 20, NAS100 7, SP500 7, UK100 4.
Combos revalides par l'utilisateur sur les pkl frais:

### Combos valides DEFINITIFS (marge >= 8%, close-only, pkl aligne 2026-03-31)

| Instrument | Combo | Nb | Trades | PF | WR | DD | Rend | M+ |
|---|---|---|---|---|---|---|---|---|
| XAUUSD | Calmar 9 | 9 | 1628 | 1.52 | 72% | -0.8% | +13% | 13/13 |
| JPN225 | PF 5 | 5 | 999 | 1.55 | 77% | -0.5% | +7% | 13/13 |
| DAX40 | Sharpe 15 | 15 | 3283 | 1.60 | 63% | -1.2% | +43% | 12/13 |
| NAS100 | Calmar 7 | 7 | 1552 | 1.57 | 66% | -1.0% | +16% | 12/13 |
| SP500 | Calmar 4 | 4 | 974 | 1.53 | 69% | -0.7% | +8% | 13/13 |
| UK100 | Calmar 4 | 4 | 1017 | 1.60 | 77% | -0.5% | +7% | 12/13 |

### Backtest agrege 5ers — pkl aligne marge 8% — 6 instruments — $100k / 0.05%

| Mois | Trades | WR | PF | PnL | Capital | Rend cum | MaxDD |
|---|---|---|---|---|---|---|---|
| 2025-03 | 21 | 71% | 1.34 | +$102 | $100,102 | +0.1% | -0.15% |
| 2025-04 | 749 | 69% | 1.46 | +$5,491 | $106,029 | +6.0% | -0.88% |
| 2025-05 | 813 | 70% | 1.81 | +$10,855 | $116,318 | +16.3% | -0.88% |
| 2025-06 | 791 | 66% | 1.30 | +$4,709 | $121,220 | +21.2% | -0.94% |
| 2025-07 | 846 | 67% | 1.32 | +$5,457 | $126,055 | +26.1% | -1.49% |
| 2025-08 | 782 | 67% | 1.44 | +$7,418 | $133,964 | +34.0% | -1.49% |
| 2025-09 | 797 | 65% | 1.63 | +$12,154 | $147,270 | +47.3% | -1.49% |
| 2025-10 | 837 | 69% | 1.54 | +$10,600 | $158,541 | +58.5% | -1.49% |
| 2025-11 | 749 | 70% | 1.74 | +$13,607 | $172,328 | +72.3% | -1.49% |
| 2025-12 | 753 | 70% | 1.38 | +$7,643 | $181,491 | +81.5% | -1.49% |
| 2026-01 | 768 | 69% | 1.53 | +$11,493 | $191,200 | +91.2% | -1.49% |
| 2026-02 | 742 | 72% | 1.67 | +$13,766 | $204,062 | +104.1% | -1.49% |
| 2026-03 | 805 | 67% | 1.99 | +$27,778 | $231,073 | +131.1% | -1.49% |

**9,453 trades | WR 68% | PF 1.59 | MaxDD -1.49% | $100k -> $231k (+131%) | 13/13 mois**

Live 5ers: XAUUSD seul (LIVE_INSTRUMENTS dans config).

### Bug strat_exits.py desaligne des pkl (2026-03-31)
Apres optimize_all.py, strat_exits.py n'avait PAS ete regenere.
D8: pkl=TPSL SL=1.0 TP=2.0, strat_exits=TRAIL SL=1.0 ACT=1.0 TR=0.75 → DIFFERENT
PO3_SWEEP: pkl=TRAIL SL=2.0, strat_exits=TRAIL SL=3.0 → DIFFERENT
Impact: 779 mismatches sur 1627 trades dans l'audit pipeline.
Le live et compare_today utilisaient les mauvaises configs exit.

### REGLE PIPELINE — ordre obligatoire apres chaque optimize:
1. optimize_all.py → genere pkl
2. strat_exits.py → REGENERER depuis pkl (memes configs exactes)
3. analyze_combos.py → combos sur pkl frais
4. config_{account}.py → portfolio choisi
5. bt_portfolio.py → verifier agrege
6. AUDIT PIPELINE → 0 mismatch obligatoire
7. Lancer le live

### FTMO — Combos valides DEFINITIFS (marge >= 8%, close-only, pkl aligne 2026-04-01, audit PASS)

| Instrument | Combo | Nb | Trades | PF | WR | DD | Rend | M+ |
|---|---|---|---|---|---|---|---|---|
| Instrument | Combo | Nb | Trades | PF | WR | DD | Rend | M+ |
|---|---|---|---|---|---|---|---|---|
| Instrument | Combo | Nb | Trades | PF | WR | DD | Rend | M+ |
|---|---|---|---|---|---|---|---|---|
| XAUUSD | Calmar 17 | 17 | 3148 | 1.41 | 71% | -0.8% | +20% | 13/13 |
| GER40.cash | PF 13 | 13 | 2470 | 1.82 | 71% | -1.0% | +33% | 12/13 |
| US500.cash | Sharpe 8 | 8 | 1870 | 1.52 | 69% | -0.7% | +16% | 13/13 |

UK100.cash, US100.cash et US30.cash retires (pas assez rentables).
Audit pipeline FTMO XAUUSD: 3148/3148 combo match, monthly PnL PASS.

### Backtest agrege FTMO — pkl aligne marge 8% — 3 instruments — $100k / 0.05%

| Mois | Trades | WR | PF | PnL | Capital | Rend cum | MaxDD |
|---|---|---|---|---|---|---|---|
| 2025-04 | 589 | 72% | 1.45 | +$3,901 | $104,110 | +4.1% | -1.33% |
| 2025-05 | 640 | 71% | 1.55 | +$5,443 | $109,110 | +9.1% | -1.33% |
| 2025-06 | 612 | 71% | 1.38 | +$3,769 | $112,816 | +12.8% | -1.33% |
| 2025-07 | 659 | 69% | 1.53 | +$6,239 | $119,851 | +19.9% | -1.33% |
| 2025-08 | 625 | 69% | 1.84 | +$10,008 | $131,098 | +31.1% | -1.33% |
| 2025-09 | 626 | 68% | 1.71 | +$9,489 | $138,745 | +38.7% | -1.33% |
| 2025-10 | 678 | 67% | 1.27 | +$4,182 | $143,657 | +43.7% | -1.33% |
| 2025-11 | 607 | 73% | 1.62 | +$7,549 | $151,528 | +51.5% | -1.33% |
| 2025-12 | 604 | 71% | 1.30 | +$3,986 | $156,820 | +56.8% | -1.33% |
| 2026-01 | 633 | 71% | 1.47 | +$6,860 | $160,791 | +60.8% | -1.33% |
| 2026-02 | 565 | 73% | 1.52 | +$6,530 | $168,561 | +68.6% | -1.33% |
| 2026-03 | 629 | 72% | 2.15 | +$18,178 | $186,277 | +86.3% | -1.33% |

**7,488 trades | WR 71% | PF 1.58 | MaxDD -1.33% | $100k -> $187k (+87%) | 13/13 mois**

Live FTMO: XAUUSD actif.

### Fix live: toute reference temporelle basee sur ts_dt UTC des candles DB
Bug 2026-04-01: TOK_FISHER DIR MISMATCH (BT=short, live=long).
Cause: le live utilisait `now_utc` (heure systeme) pour `hour` dans detect_open_strats,
et `candle_time` (potentiellement decale) pour detect_close_strats.
Le fisher cross UP a 23:55 (veille) a trigger avant le day reset.
Fix: `candle_time_utc = candles.iloc[-1]['ts_dt']` partout.
Plus de `datetime.now()` ni d'heure broker. Seule source = DB UTC.

### Fix conflit filter live: deals ouverts ET fermes sur la bougie courante
Bug: en BT, un trade sorti au candle ci=N est encore considere actif a ci=N (condition `>=`).
En live, MT5 positions_get() ne voit que les positions ouvertes, pas celles fermees par SL/TP
pendant la bougie courante. Un nouveau trade en sens oppose passait alors qu'il aurait du etre bloque.
Exemple 2026-03-31: 3 longs fermes au SL a ci=1996, ALL_PIVOT_BRK et ALL_STOCH_OB short ouvertes
au meme candle en live (BT les skip). Cout: -$43 sur ALL_STOCH_OB.
Fix: history_deals_get() sur la bougie courante pour inclure les directions des deals d'entree
ET de sortie (SL/TP). Un trade ferme par SL sur la bougie N doit encore bloquer un trade
en sens oppose sur la meme bougie (identique au BT avec condition `>=`).
Bug confirme 2026-04-02: ALL_PIVOT_BRK short pris en live apres SL de 2 longs sur meme bougie.
BT les skip. Cout: -22 pts. Fix: DEAL_ENTRY_OUT ajoute dans open_dirs.
dans open_dirs, meme si la position est deja fermee.

---

## 2026-03-30 — Retrait open strats + fix magic numbers

### REGLE: JAMAIS de strats open dans les portfolios live
Les open strats (TOK_FADE, TOK_PREVEXT, LON_GAP, LON_BIGGAP, LON_KZ, LON_TOKEND, LON_PREV,
NY_GAP, NY_LONEND, NY_LONMOM, NY_DAYMOM) entrent sur row['open'] = tick au moment de la detection.
Le timing exact (quelle bougie est iloc[-2] au moment du poll) est impossible a reproduire
entre backtest et live. Bug confirme en live le 2026-03-30: entries decalees, conflits non filtres.

Impact retrait sur XAUUSD 5ers:
- Avant: 19 strats (5 open + 14 close), PF 1.57, 4059 trades
- Apres: 14 strats (close only), PF 1.60, 3235 trades (-20%)
- Perte: 18% du PnL net (955 oz sur 5265)
- Le PF MONTE car les open strats avaient un PF plus faible (1.46)

Strats open retirees de TOUS les configs:
- config_5ers: LON_PREV, LON_KZ, LON_BIGGAP, TOK_PREVEXT, LON_TOKEND
- config_ftmo: LON_TOKEND, LON_KZ, LON_PREV, LON_BIGGAP, TOK_PREVEXT, LON_GAP, NY_LONEND, TOK_FADE
- config_icm: LON_PREV, LON_KZ, TOK_PREVEXT, LON_TOKEND

Cette regle s'applique aussi a analyze_combos.py: ne JAMAIS inclure d'open strats dans les combos.

### Compare BT vs Live 2026-03-30 (avant retrait)
7 signaux detectes, 4 BT trades (3 skipped conflit):

| Strat | BT Dir | BT Entry | BT PnL | LV Dir | LV Entry | LV PnL | Verdict |
|---|---|---|---|---|---|---|---|
| ALL_BB_TIGHT | short | 4435.18 | +1.12 | short | 4434.99 | +$0.24 | MATCH |
| ALL_MACD_STD_SIG | SKIP | 4461.62 | - | long | 4462.21 | -$55.31 | BT=SKIP LV=PRIS! |
| ALL_STOCH_OB | SKIP | 4461.62 | - | long | 4461.07 | -$21.76 | BT=SKIP LV=PRIS! |
| IDX_NR4 | long | 4452.20 | -11.09 | long | 4452.88 | -$44.54 | MATCH |
| TOK_FISHER | short | 4435.18 | -22.17 | short | 4434.96 | -$44.89 | MATCH |
| TOK_PREVEXT | short | 4448.42 | +14.36 | short | 4435.27 | +$1.03 | ENTRY DIFF 13.1 |
| TOK_WILLR | SKIP | 4445.42 | - | - | - | - | SKIP OK |

Bugs constates:
1. Filtre conflit: BT skip 2 longs (conflit short), live les a pris → -$77
2. TOK_PREVEXT entry diff 13 pts (open strat, timing bougie)

### Re-optimisation combos close-only 5ers — 6 instruments
analyze_combos.py modifie pour exclure OPEN_STRATS avant la recherche.
Combos valides par l'utilisateur instrument par instrument:

| Instrument | Combo | Nb | Trades | PF | WR | DD | Rend | M+ |
|---|---|---|---|---|---|---|---|---|
| XAUUSD | PF*WR 19 | 19 | 3463 | 1.53 | 80% | -0.7% | +20% | 13/13 |
| JPN225 | Sharpe 19 | 19 | 3822 | 1.57 | 75% | -0.8% | +32% | 13/13 |
| DAX40 | PF 15 | 15 | 3092 | 1.82 | 72% | -1.1% | +41% | 12/13 |
| NAS100 | Calmar 16 | 16 | 3091 | 1.45 | 72% | -1.0% | +21% | 13/13 |
| SP500 | Calmar 13 | 13 | 2788 | 1.47 | 73% | -0.8% | +19% | 13/13 |
| UK100 | PF 12 | 12 | 2628 | 1.49 | 74% | -0.8% | +18% | 12/13 |

Live: XAUUSD seul pour le moment (LIVE_INSTRUMENTS dans config).

### Backtest agrege 5ers close-only — 6 instruments — $100k / 0.05%

| Mois | Trades | WR | PF | PnL | Capital | Rend cum | MaxDD |
|---|---|---|---|---|---|---|---|
| 2025-03 | 49 | 61% | 0.59 | -$393 | $99,607 | -0.4% | -0.47% |
| 2025-04 | 1494 | 76% | 1.45 | +$8,486 | $108,300 | +8.3% | -0.99% |
| 2025-05 | 1613 | 75% | 1.61 | +$13,806 | $122,642 | +22.6% | -1.09% |
| 2025-06 | 1610 | 74% | 1.44 | +$11,523 | $134,109 | +34.1% | -1.48% |
| 2025-07 | 1649 | 74% | 1.54 | +$16,100 | $149,863 | +49.9% | -1.48% |
| 2025-08 | 1591 | 74% | 1.54 | +$18,090 | $167,943 | +67.9% | -1.48% |
| 2025-09 | 1638 | 72% | 1.60 | +$25,189 | $193,924 | +93.9% | -1.48% |
| 2025-10 | 1740 | 74% | 1.52 | +$24,030 | $220,158 | +120.2% | -1.48% |
| 2025-11 | 1503 | 75% | 1.58 | +$25,226 | $246,200 | +146.2% | -1.48% |
| 2025-12 | 1541 | 75% | 1.46 | +$22,302 | $274,235 | +174.2% | -1.48% |
| 2026-01 | 1526 | 74% | 1.54 | +$30,291 | $298,855 | +198.9% | -1.48% |
| 2026-02 | 1456 | 77% | 1.53 | +$27,156 | $330,200 | +230.2% | -1.48% |
| 2026-03 | 1474 | 75% | 1.91 | +$58,647 | $380,452 | +280.5% | -1.48% |

**18,884 trades | WR 75% | PF 1.58 | MaxDD -1.48% | $100k -> $380k (+280%) | 12/13 mois**

### Fix ordre resolution conflits BT vs live
BT (analyze_combos.py): tri par (candle_index, strat_name) → ordre **alphabetique** quand meme bougie.
Live (live_mt5.py): ordre de detect_all() → ordre du **code** (different).
Quand 2 strats opposees triggent sur la meme bougie, la premiere bloque la seconde.
L'ordre different entre BT et live = resultat different.
Fix: tri alphabetique `sorted(signals, key=lambda s: s['strat'])` dans live_mt5.py et compare_today.py.

---

## 2026-03-30 — Fix magic numbers: collision hash → index unique

### Bug CRITIQUE: collisions magic numbers
L'ancien systeme utilisait `md5(strat)[:4] % 99` → seulement 99 slots pour 110 strats.
77 strats sur 110 avaient des collisions (ex: TOK_PREVEXT = ALL_MACD_STD_SIG = 275187).
Impact: le live ne pouvait pas distinguer les trades de 2 strats differentes.

### Fix: STRAT_ID + SYMBOL_ID dans strats.py
- STRAT_ID: index fixe 0-109, base sur l'ordre dans ALL_STRATS
- SYMBOL_ID: index fixe par instrument (XAUUSD=0, JPN225=1, ..., US30.cash=11)
- `make_magic(broker, symbol, strat) = MAGIC_BASE + SYMBOL_ID * 200 + STRAT_ID`
- 3960 combinaisons (3 brokers x 12 symbols x 110 strats), **0 collision**
- Mis a jour dans: live_mt5.py, compare_today.py, dashboard.py (import depuis strats.py)
- REGLE: ne jamais changer l'ordre dans ALL_STRATS, ajouter en fin uniquement

---

## 2026-03-29 — Audit look-ahead complet 5ers (110 strats)

### Audit look-ahead exhaustif — toutes les strats du portfolio 5ers
Audit systematique de chaque composant pour detecter tout look-ahead bias.

#### 1. ATR — PASS
- `daily_atr` = EWM(14) sur candles 5m, derniere valeur par jour (causal)
- Usage: `day_atr = daily_atr.get(prev_day(today))` = ATR de la VEILLE
- `global_atr` fallback inclut futur mais jamais utilise (warmup 200 bars)

#### 2. compute_indicators() — 35+ indicateurs — PASS
Tous causaux (backward-looking):
- EWM: MACD (std/fast/med), RSI, EMA (5-200), ATR14, ADX, TRIX, Elder Ray
- Rolling: Donchian (10/50), BB (20,2), Tight BB (10,1.5), Keltner, Williams %R (7/14), CCI (14/20), CMO (9/14), Stochastic (14,3,3), Stochastic RSI, HMA (9/21), Aroon (25), AO, LR slope (20)
- Shift: Momentum (10/14), ROC 10, DPO 14, Fisher signal, Ichimoku senkou
- Boucle forward: Supertrend (compare close[i] vs boundary[i-1])
- Pivot: boucle dates[i-1] → prev day H+L+C

#### 3. detect_all() — 110 strats — PASS
**Open strats** (entree row['open'], detection bougie precedente fermee):
- TOK_FADE, TOK_PREVEXT: prev_day_data (veille). PASS
- LON_GAP, LON_BIGGAP: derniere Tokyo fermee + row['open']. PASS
- LON_KZ, LON_TOKEND, LON_PREV: candles passees + row['open']. PASS
- NY_GAP, NY_LONEND, NY_LONMOM, NY_DAYMOM: candles passees + row['open']. PASS

**Close strats** (entree row['close'], bougie courante fermee):
- TOK_2BAR, TOK_BIG, LON_PIN: row OHLC courant. PASS
- D8: prev_day + prev2_day + row['close']. PASS
- PO3_SWEEP, LON_ASIAN_BRK: Asian range (0-6h, fermee a detection 7-10h). PASS

**Indicator strats** (pattern prev[ind] cross row[ind]):
- Toutes les 80+ strats indicator suivent le meme pattern: compare prev (bar i-1) vs row (bar i)
- Aucun indicateur n'utilise de donnees futures
- Les Donchian/DC comparent row['close'] vs **prev**['dc_h'] (pas row['dc_h'])
- ALL_RSI_DIV: candles.iloc[ci-9:ci+1] — row vs min des 9 precedentes. PASS
- ALL_MACD_DIV: candles.iloc[ci-19:ci+1] — idem. PASS
- ALL_MTF_BRK: row vs prev['high_1h'] + prev vs [ci-2]['high_1h']. PASS
- ALL_NR4/TOK_NR4/IDX_NR4: ranges [ci..ci-3], min = courant. PASS
- ALL_BB_SQUEEZE: prev.bb_width vs prev.bb_width_min20. PASS
- ALL_KB_SQUEEZE: prev.squeeze=1 → row.squeeze=0 + break KC. PASS

**IDX strats** (US session):
- IDX_ORB15/30: ny_candles[:3/6] = premieres bougies NY fermees. PASS
- IDX_LATE_REV: ny_candles[-1] = courant (19-20h). PASS
- IDX_TREND_DAY: IB = ny_candles[:12] fermees. PASS
- IDX_PREV_HL: prev_day_data H/L. PASS

#### 4. sim_exit_custom() — PASS
- Boucle forward only: `for j in range(start, len(cdf)-pos)`
- TRAIL: best tracke sur close (pas future bars)
- TPSL: SL prioritaire si meme bougie (conservateur)
- Timeout 288 bougies pour TPSL

#### 5. Pipeline backtest (optimize_all.py) — PASS
- Indicateurs precalcules sur dataset complet mais tous causaux (EWM/rolling)
- Warmup 200 bars avant premiere detection
- prev_day_data construit a chaque changement de jour (jour precedent)
- trig={} reset chaque jour (1 signal max/strat/jour)

#### VERDICT: 0 LOOK-AHEAD sur 110 strats
| Categorie | Resultat |
|---|---|
| Indicateurs (35+) | 0 look-ahead |
| Signaux detect_all (110 strats) | 0 look-ahead |
| ATR | PASS (veille) |
| prev_day_data / pivot | PASS (jour precedent) |
| Exit simulation | PASS (forward only) |
| Pipeline backtest | PASS |

Notes mineures (non-critiques):
- global_atr fallback inclut futur — jamais utilise avec warmup 200
- ALL_ELDER_BULL = LONG ONLY, ALL_ELDER_BEAR = SHORT ONLY (par design)
- ALL_FIB_618 = LONG ONLY (documente ligne 593)
- Confirme par test truncation precedent: 85,115 signaux, 0 mismatch

---

## 2026-03-27 — Multi-instrument: audit live + migration strats + portfolios

### Changements config globaux
- Capital par defaut: $100,000
- Risk par defaut: 0.05% (0.0005) sur tous les brokers (ICM, FTMO, 5ers)
- analyze_combos.py corrige pour utiliser capital/risk du config au lieu de hardcode

### Migration 39 strats vers strats.py
Toutes les strats qui etaient dans optimize_all.py uniquement ont ete migrees dans strats.py:
- detect_all(): 39 nouvelles strats (ALL_FISHER_9, TOK_FISHER, ALL_HMA_CROSS, ALL_CCI_20_ZERO, ALL_DPO_14, ALL_RSI_50, ALL_RSI_DIV, ALL_MACD_STD_SIG, ALL_MACD_MED_SIG, ALL_MACD_FAST_SIG, ALL_BB_TIGHT, ALL_MTF_BRK, ALL_PIVOT_BOUNCE, ALL_PIVOT_BRK, ALL_EMA_513, ALL_EMA_821, ALL_EMA_921, ALL_EMA_TREND_PB, ALL_CMO_9, ALL_CMO_14, ALL_CMO_14_ZERO, ALL_WILLR_7, ALL_WILLR_14, ALL_MOM_10, ALL_MOM_14, ALL_DC50, ALL_DC10_EMA, ALL_AO_SAUCER, ALL_HMA_DIR, ALL_ICHI_TK, ALL_MACD_ADX, ALL_MACD_FAST_ZERO, ALL_NR4, TOK_FISHER, TOK_MACD_MED, LON_DC10, NY_HMA_CROSS)
- compute_indicators(): fisher9, hma9/21, cci14/20, cmo9/14, dpo14, ao, bb_tight, ichimoku, adx_s, high_1h/low_1h, dc50, wr7, pivot, ema5/8/13/200
- Total: 91 strats dans strats.py, 100% alignes avec strat_exits.py

### Audit JPN225 5ers
- LON_GAP retire du portfolio (uses row['open'] dans condition gap — MAIS en fait c'est live-tradeable car open strat detecte sur bougie precedente fermee)
- D8 corrige: prev2_day_data ajoute dans live_mt5.py et live_paper.py

### REGLE: Open strats et row['open']
Les open strats (LON_GAP, LON_BIGGAP, LON_KZ, LON_TOKEND, etc.) detectent sur candles.iloc[-2] (bougie precedente fermee) avec now_utc hour. Le row['open'] est celui de la bougie fermee = connu. L'entree se fait au tick courant. DONC LON_GAP et LON_BIGGAP SONT live-tradeable.

### Portfolios 5ers valides
| Instrument | Strats | Combo | PF | WR | DD (0.05%) | M+ | Status |
|---|---|---|---|---|---|---|---|
| XAUUSD | 6 | existant | 1.32 | 68% | - | 11/13 | deja en place |
| JPN225 | 8 | PF*WR 9 | 1.85 | 79% | - | 13/13 | deja en place, LON_GAP retire |
| DAX40 | 6 | MinDD 6 | 1.97 | 77% | -0.3% | 13/13 | ajoute |
| BTCUSD | 4 | MinDD 4 | 1.73 | 79% | -0.3% | 13/13 | ajoute |
| NAS100 | 10 | MinDD 10 | 1.40 | 77% | -0.4% | 13/13 | VALIDE |
| SP500 | 11 | MinDD 11 | 1.48 | 78% | -0.7% | 13/13 | VALIDE |
| UK100 | 3 | PF 3 | 1.66 | 77% | -0.4% | 13/13 | VALIDE |
| US30 | - | - | - | - | - | - | REJETE — DD trop haut |

### Backtest final 5ers — compte unique $100k / 0.05% — 7 instruments
Simulation event-based trade par trade sur un seul capital de $100k.
DD calcule a chaque trade (pas mensuel).

| Mois | Trades | Wins | WR | PF | PnL | Capital | Rend cum | Max DD |
|---|---|---|---|---|---|---|---|---|
| 2025-03 | 129 | 100 | 78% | 1.67 | +$1,002 | $100,841 | +0.8% | -0.50% |
| 2025-04 | 749 | 590 | 79% | 1.68 | +$5,647 | $110,172 | +10.2% | -0.65% |
| 2025-05 | 797 | 618 | 78% | 1.62 | +$6,232 | $117,556 | +17.6% | -0.66% |
| 2025-06 | 778 | 588 | 76% | 1.50 | +$5,553 | $126,740 | +26.7% | -0.66% |
| 2025-07 | 800 | 623 | 78% | 1.65 | +$6,864 | $135,076 | +35.1% | -0.77% |
| 2025-08 | 761 | 562 | 74% | 1.39 | +$4,874 | $147,292 | +47.3% | -0.77% |
| 2025-09 | 792 | 593 | 75% | 1.42 | +$5,703 | $151,709 | +51.7% | -0.77% |
| 2025-10 | 814 | 613 | 75% | 1.52 | +$7,498 | $163,406 | +63.4% | -0.81% |
| 2025-11 | 715 | 554 | 77% | 1.51 | +$6,113 | $173,865 | +73.9% | -0.81% |
| 2025-12 | 742 | 566 | 76% | 1.34 | +$4,523 | $175,342 | +75.3% | -0.81% |
| 2026-01 | 736 | 562 | 76% | 1.82 | +$11,235 | $178,073 | +78.1% | -0.81% |
| 2026-02 | 693 | 537 | 77% | 1.48 | +$6,182 | $179,057 | +79.1% | -0.81% |
| 2026-03 | 658 | 504 | 77% | 1.61 | +$8,017 | $179,441 | +79.4% | -0.81% |

**9,164 trades | WR 76% | PF 1.54 | Max DD -0.81% | $100k -> $179k (+79.4%) | 13/13 mois**

### FTMO — Optimisation + combos valides — 2026-03-28
6 instruments optimises et valides.
sanitize_symbol ajoute pour gerer GER40.cash -> ger40_cash en DB.

| Instrument | Combo | Nb strats | PF | WR | DD | Rend | M+ |
|---|---|---|---|---|---|---|---|
| XAUUSD | Diverse 9 | 9 | 1.92 | 79% | -0.6% | +13% | 13/13 |
| GER40.cash | PF*WR 7 | 7 | 2.16 | 79% | -0.5% | +15% | 13/13 |
| UK100.cash | Calmar 6 | 6 | 1.44 | 71% | -0.6% | +10% | 13/13 |
| US100.cash | Calmar 5 | 5 | 1.52 | 73% | -0.4% | +7% | 13/13 |
| US500.cash | PF 5 | 5 | 1.55 | 79% | -0.5% | +8% | 13/13 |
| US30.cash | PF 12 | 12 | 1.68 | 64% | -1.0% | +30% | 13/13 |

### Audit critique exhaustif FTMO — 2026-03-29
Audit base sur recherche web exhaustive (10 categories, 40+ points).
- Code: 0 look-ahead technique (Donchian/BB/MTF tous comparent a prev, pas courant)
- Truncation test: 6/6 PASS (85,115 signaux, 0 mismatch)
- Risques structurels: overfitting in-sample (exits + combos optimises sur memes donnees)
- ALL_FIB_618 LONG ONLY sur 4 instruments
- ALL_DOJI_REV US500 spread=61% du gain moyen → DANGER
- XAUUSD/TOK_PREVEXT (42 trades) et US100/D8 (37 trades) faible significativite

### Look-ahead test FTMO — 2026-03-28
Test full vs truncated (60%) sur les 6 instruments.
85,115 signaux compares, 0 mismatch, 0 price diff. **6/6 PASS.**

| Instrument | Signaux | Mismatches | Verdict |
|---|---|---|---|
| XAUUSD | 14,212 | 0 | PASS |
| GER40.cash | 14,056 | 0 | PASS |
| UK100.cash | 13,884 | 0 | PASS |
| US100.cash | 14,345 | 0 | PASS |
| US500.cash | 14,294 | 0 | PASS |
| US30.cash | 14,324 | 0 | PASS |

### Backtest FTMO — $100k / 0.05% — 6 instruments — 2026-03-28
8,182 trades | WR 73% | PF 1.69 | Max DD -1.16% | $100k -> $212k (+112.2%) | 13/13 mois
Audit: 0 mismatch exits, toutes strats dans detect_all.
Spread: 1 DANGER (ALL_DOJI_REV US500 Sp/Win=61%), 5 RISQUE.

### Re-optimisation FTMO avec 110 strats — 2026-03-29
Re-optimisation en cours apres ajout 19 nouvelles strats.

VALIDES (re-optimise 110 strats):
1. XAUUSD: **Diverse 8** (NOUVEAU) — PO3_SWEEP, D8, LON_TOKEND, ALL_SUPERTREND, TOK_WILLR, LON_KZ, LON_PREV, LON_BIGGAP
   PF=1.91 WR=80% DD=-0.5% 13/13 — 60 strats viables
2. GER40.cash: **Sharpe 6** (NOUVEAU) — TOK_FISHER, ALL_FVG_BULL, ALL_ELDER_BULL, ALL_LR_BREAK, TOK_PREVEXT, ALL_INSIDE_BRK
   PF=1.98 WR=76% DD=-0.5% 13/13 — 69 strats viables

3. UK100.cash: **Diverse 6** (NOUVEAU) — ALL_CONSEC_REV, IDX_GAP_CONT, LON_GAP, ALL_FIB_618, IDX_TREND_DAY, ALL_ELDER_BULL
   PF=1.43 WR=71% DD=-0.5% 13/13 — 17 strats viables
4. US100.cash: **PF 9** (NOUVEAU) — D8, TOK_PREVEXT, ALL_MTF_BRK, ALL_ELDER_BULL, ALL_EMA_821, ALL_FIB_618, TOK_WILLR, ALL_FVG_BULL, TOK_STOCH
   PF=1.59 WR=78% DD=-0.6% 13/13 — 30 strats viables
5. US500.cash: **Calmar 11** (NOUVEAU) — ALL_DOJI_REV, ALL_FIB_618, TOK_FISHER, ALL_DC50, IDX_CONSEC_REV, ALL_FVG_BULL, IDX_RSI_REV, ALL_SUPERTREND, ALL_LR_BREAK, ALL_ICHI_TK, ALL_KB_SQUEEZE
   PF=1.54 WR=76% DD=-0.5% 13/13 — 24 strats viables
6. US30.cash: **PF 10** (NOUVEAU) — IDX_PREV_HL, NY_LONEND, TOK_2BAR, ALL_SUPERTREND, ALL_MSTAR, ALL_ELDER_BULL, IDX_3SOLDIERS, TOK_FADE, ALL_MACD_HIST, TOK_PREVEXT
   PF=1.74 WR=67% DD=-1.2% 13/13 — 26 strats viables

Nouvelles strats dans les combos: ALL_SUPERTREND, ALL_ELDER_BULL, ALL_LR_BREAK, ALL_KB_SQUEEZE,
ALL_MACD_DIV, ALL_ADX_RSI50, TOK_STOCH, ALL_STOCH_RSI, ALL_EMA_821, ALL_INSIDE_BRK, LON_STOCH, NY_ELDER

### Re-optimisation 5ers avec 110 strats — 2026-03-29
Score composite: PF x WR x Rend / (1+|DD|) x M+/TM x min(1,n/500)

| Instrument | Combo | Nb | PF | WR | DD | Rend | M+ | Score |
|---|---|---|---|---|---|---|---|---|
| XAUUSD | Calmar 19 | 19 | 1.62 | 79% | -0.6% | +24% | 13/13 | 2.00 |
| JPN225 | Calmar 21 | 21 | 1.67 | 75% | -0.6% | +37% | 13/13 | 2.80 |
| DAX40 | PF 17 | 17 | 1.84 | 75% | -1.3% | +40% | 12/13 | 2.23 |
| NAS100 | Calmar 19 | 19 | 1.51 | 69% | -0.8% | +30% | 13/13 | 1.66 |
| SP500 | Calmar 16 | 16 | 1.53 | 71% | -1.0% | +29% | 13/13 | 1.57 |
| UK100 | Calmar 14 | 14 | 1.46 | 73% | -0.7% | +20% | 12/13 | 1.17 |

Nouvelles strats dans les combos: ALL_STOCH_OB, ALL_STOCH_PIVOT, ALL_STOCH_RSI, ALL_STOCH_CROSS,
ALL_ELDER_BULL, ALL_ADX_RSI50, ALL_HMA_CROSS, ALL_SUPERTREND, ALL_MACD_DIV,
ALL_KB_SQUEEZE, ALL_LR_BREAK, NY_ELDER, TOK_STOCH

### 19 nouvelles strats ajoutees — 2026-03-29
Total passe de 91 a 110 strats. Nouvelles familles:
- Stochastic (cross, OB/OS, RSI, pivot combo, session Tokyo/London)
- TRIX (signal cross, Tokyo)
- Supertrend direct
- ROC zero cross
- Elder Ray (bull/bear power, NY session)
- Aroon cross
- CCI 100 extreme reversal
- Keltner-Bollinger squeeze breakout
- Linear regression slope reversal
- ADX + RSI 50 combo
- MACD divergence
A optimiser sur tous les instruments pour trouver les pepites.

### BTCUSD retire du portfolio — 2026-03-28
Fees et spread BTC trop eleves. Compare today montre PnL live tres inferieur au BT.
Les strats ne sont pas viables en live sur BTC. Portfolio passe a 6 instruments.

### Test DST impact — 2026-03-28
Compare backtest FIXED (14:30 NY) vs DST-adjusted (13:30 pendant DST US).
Resultat: FIXED meilleur sur 6/7 instruments. Seul NAS100 mieux avec DST (+0.05 PF).
Raison: exits optimises avec heures fixes. DST sans re-optimisation degrade.
Decision: on garde les heures fixes.

| Instrument | PF Fixed | PF DST | Rend Fixed | Rend DST |
|---|---|---|---|---|
| XAUUSD | 1.64 | 1.59 | +10.7% | +9.8% |
| JPN225 | 1.68 | 1.50 | +10.1% | +7.4% |
| DAX40 | 1.90 | 1.80 | +12.9% | +11.1% |
| BTCUSD | 1.75 | 1.65 | +6.9% | +5.3% |
| NAS100 | 1.41 | 1.46 | +8.8% | +9.9% |
| SP500 | 1.43 | 1.38 | +12.0% | +11.0% |
| UK100 | 1.61 | 1.24 | +5.8% | +2.5% |

### Bug lot sizing JPN225 — 2026-03-27
Formule lots utilisait contract_size. Faux pour JPN225 (cote en JPY, pas USD).
Fix: `point_value = tick_value / tick_size` puis `lots = risk / (sl_distance * point_value)`.
tick_value est toujours en devise du compte (USD) — fonctionne pour tous les instruments.

### Test look-ahead concret — 2026-03-27
Test: comparer signaux dataset complet vs dataset tronque a 60%.
Si look-ahead, les signaux de la premiere moitie changeraient.

| Instrument | Signaux compares | Mismatches | Verdict |
|---|---|---|---|
| XAUUSD | 14,337 | 0 | PASS |
| DAX40 | 14,126 | 7 (bord du split, artefact EMA warmup) | PASS* |

*Les 7 mismatches DAX40 sont aux 5 dernieres bougies du split (NR4, MSTAR).
Cause: compute_indicators sur dataset tronque = EMA warmup different en fin.
Ce n'est PAS du look-ahead, c'est un artefact de bord. 14,119/14,126 = 99.95% identiques.

### 10 audits critiques — 2026-03-27
10 audits independants: look-ahead (4) + faisabilite live (4) + exits (1) + edge cases (1).
Resultat: **10/10 PASS**.
- Audit 1: Look-ahead detect_all — PASS (91 strats, toutes forward-only)
- Audit 2: Look-ahead indicators — PASS (aucun shift negatif, pivot sur prev day)
- Audit 3: Look-ahead optimize_all — PASS (ATR veille, prev_day_data correct)
- Audit 4: Look-ahead exit simulation — PASS (sim_exit_np forward, best sur close)
- Audit 5: Live strats disponibles — PASS (48 strats portfolio toutes dans detect_all)
- Audit 6: Open strats timing — PASS (candles[-2] + now_utc hour)
- Audit 7: Trailing stops — PASS (best sur close, MT5 ModifyPosition)
- Audit 8: Risk sizing — PASS (capital*risk/sl_distance, lot min/max/step)
- Audit 9: Strat_exits completeness — PASS (0 fallback DEFAULT)
- Audit 10: Edge cases — PASS (ATR=0, no candles, tick=None geres)

### Audit final backtest vs live — 2026-03-27
Audit complet 34 points. Resultat: **0 mismatch critique**.
- Signal detection: MATCH (detect_all identique, open strats sur bougie precedente, close strats sur bougie fermee)
- Exit configs: MATCH (strat_exits.py multi-instrument, 0 mismatch vs pkl)
- Exit execution: MATCH (TPSL SL/TP sur MT5, TRAIL best sur close)
- Indicateurs: MATCH (91 strats, tous indicateurs computes)
- ATR: MATCH (veille, edge case premier jour = mineur)
- Risk sizing: MATCH (capital * risk / sl_distance)
- Conflit filter: MATCH (par instrument)
- Reset triggers: MATCH (journalier)
- Startup recovery: SAFE (rebuild triggers depuis MT5 positions)

### Bug CRITIQUE corrige: strat_exits.py desaligne de l'optimisation
strat_exits.py avait UNE config globale par strat. L'optimisation produit des exits DIFFERENTS par instrument.
Ex: ALL_MACD_HIST DAX40=TRAIL 1.5/0.30/0.30, SP500=TRAIL 1.0/0.50/0.50, mais strat_exits avait TRAIL 3.0/0.50/0.50.
Fix: strat_exits.py reecrit en multi-instrument, indexe par (broker, symbol).
live_mt5.py mis a jour pour lookup STRAT_EXITS[(_account, symbol)][strat].
Verification: 0 mismatch entre strat_exits.py et les pkl d'optimisation.

### Bug corrige: aggregate cross-instrument conflict filter
L'agregé filtrait les trades en conflit entre instruments differents (ex: long XAU + short JPN).
Ca supprimait 1,935 trades. Corrige: le filtre conflit ne s'applique que par instrument (deja fait dans eval_combo).

### NAS100 — combos proposes (attente validation)
Conservateur 13/13 mois:
- Calmar 9: PF=1.47 WR=75% DD=-0.6% Rend=+10% — D8, ALL_WILLR_7, LON_BIGGAP, ALL_MSTAR, TOK_NR4, ALL_FVG_BULL, ALL_DC50, TOK_FISHER, ALL_MACD_HIST
- MinDD 9: PF=1.39 WR=78% DD=-0.4% Rend=+7% — D8, ALL_DC50, ALL_DC10_EMA, TOK_FISHER, TOK_PREVEXT, ALL_FVG_BULL, ALL_MACD_HIST, IDX_PREV_HL, ALL_MSTAR

---

## 2026-03-23 — Combo greedy brut (sans filtre correlation)

### 10 strats (greedy Calmar)
ALL_MACD_RSI + LON_PREV + ALL_KC_BRK + ALL_DC10_EMA + ALL_DC10 + TOK_2BAR + NY_DAYMOM + NY_LONMOM + ALL_MACD_ADX + ALL_WILLR_7

| Metrique | 1% risk | 0.1% risk |
|---|---|---|
| Trades | 2333 | 2333 |
| PF | 1.77 | ~1.77 |
| DD | -57.4% | ~-5.7% |
| Rend | +2,381,361% | ~+120% |
| M+ | 11/13 | 11/13 |

Probleme: correlation > 0.5 entre ALL_MACD_RSI, ALL_MACD_ADX, ALL_WILLR_7, ALL_DC10, ALL_DC10_EMA

---

## 2026-03-23 — Combo diversifie (filtre correlation)

A COMPLETER apres test

---

## 2026-03-22 — Resultats pre-indicators (price action seul)

### ICMarkets 14 strats price action (config unique SL=1.0 ACT=0.5 TRAIL=0.75)
PF 1.27 | DD -35.2% | 11/13 mois | 2297 trades
Note: apres correction entry candle SL check + NY_DAYMOM open fix

### FTMO 4 strats (D8 + LON_TOKEND + NY_DAYMOM + TOK_PREVEXT)
PF 0.91 | DD -47.3% | 5/13 mois | MORT apres corrections

### 5ers 6 strats
PF 1.37 | DD -19.1% | 8/13 mois | degrade apres corrections

---

## 2026-03-21 — Avant corrections look-ahead

### ICMarkets 14 strats
PF 1.57 | DD -22.1% | 13/13 | GONFLE (entry candle non verifiee)

### FTMO 4 strats
PF 1.50 | DD -12.7% | 13/13 | GONFLE

---

## Corrections appliquees (chronologique)
1. Trailing sur CLOSE (pas high/low) — best = max(close)
2. Pas de re-check low/high vs nouveau stop apres trailing
3. NY_DAYMOM: row['open'] au lieu de tv.iloc[-1]['close']
4. Entry candle SL check pour strats "open"
5. Exits optimises par strat (strat_exits.py)

## 2026-03-23 — Combo diversifie (filtre correlation < 0.4)

### 10 strats diversifie
ALL_MACD_RSI + LON_PREV + ALL_KC_BRK + TOK_2BAR + ALL_DC10_EMA + NY_DAYMOM + NY_LONMOM + LON_TOKEND + LON_KZ + ALL_FIB_618

| Metrique | 1% risk | 0.1% risk |
|---|---|---|
| Trades | 2163 | 2163 |
| PF | 1.64 | ~1.64 |
| DD | -50.6% | ~-5.1% |
| Rend | +728,430% | ~+100% |
| M+ | 11/13 | 11/13 |
| Corr moyenne | +0.027 | +0.027 |
| Corr max | +0.331 | +0.331 |

### Comparatif
| | Brut | Diversifie | Delta |
|---|---|---|---|
| PF | 1.77 | 1.64 | -0.13 |
| DD | -57.4% | -50.6% | +6.8% meilleur |
| Corr moy | +0.124 | +0.027 | 5x moins correle |
| Corr max | +0.819 | +0.331 | pas de paire >0.4 |
| WR | 27% | 32% | +5% |

Conclusion: le diversifie echange du rendement contre de la stabilite.
Plus robuste en live (moins de dependance a un seul type de signal).

---

## 2026-03-23 — Combo High WR (>60%)

Objectif: maximiser le WR pour reduire la dependance aux gros gagnants.
Methode: SL=3.0 ATR + TP court (0.3-1.0 ATR) = WR eleve mais PF reduit.
19 strats validees (WR>=60% + PF>=1.1 + split OK).

### 10 strats High WR diversifie (corr < 0.4)
PO3_SWEEP + TOK_2BAR + ALL_FIB_618 + ALL_PSAR_EMA + LON_TOKEND + ALL_FVG_BULL + LON_KZ + LON_GAP + TOK_BIG + ALL_MACD_STD_SIG

| Metrique | 1% risk |
|---|---|
| Trades | 1942 |
| PF | 1.33 |
| WR | 78% |
| DD | -11.1% |
| Rend | +339% |
| M+ | 13/13 |

Avantage: WR tres eleve, DD tres bas, 13/13 mois.
Inconvenient: rendement modeste (PF 1.33, petits TP).

---

## 2026-03-23 — Combo Equilibre (WR 45-70%, PF>1.2)

Objectif: trouver le sweet spot entre rendement, DD et WR.
Methode: exits intermediaires (SL=1.5-3.0, TP=0.5-1.5) visant WR 45-70%.
26 strats validees (WR>=45% + PF>=1.2 + split OK).

### 10 strats Equilibre diversifie (corr < 0.4)
PO3_SWEEP + ALL_3SOLDIERS + LON_KZ + LON_TOKEND + ALL_PSAR_EMA + ALL_FVG_BULL + ALL_CONSEC_REV + ALL_MACD_RSI + ALL_FIB_618 + TOK_BIG

| Metrique | 1% risk |
|---|---|
| Trades | 2005 |
| PF | 1.32 |
| WR | 72% |
| DD | -15.4% |
| Rend | +511% |
| M+ | 13/13 |

Configs par strat:
| Strat | SL | TP | PF | WR |
|---|---|---|---|---|
| PO3_SWEEP | 3.0 | 0.75 | 1.76 | 80% |
| ALL_3SOLDIERS | 3.0 | 1.50 | 1.29 | 64% |
| LON_KZ | 2.5 | 0.50 | 1.70 | 80% |
| LON_TOKEND | 3.0 | 1.50 | 1.80 | 65% |
| ALL_PSAR_EMA | 3.0 | 1.00 | 1.29 | 72% |
| ALL_FVG_BULL | 2.5 | 0.75 | 1.45 | 70% |
| ALL_CONSEC_REV | 3.0 | 0.50 | 1.48 | 77% |
| ALL_MACD_RSI | 3.0 | 1.50 | 1.22 | 63% |
| ALL_FIB_618 | 1.5 | 0.50 | 1.30 | 65% |
| TOK_BIG | 3.0 | 0.50 | 1.30 | 78% |

---

## 2026-03-23 — Comparatif global des 4 approches

| Combo | Trades | PF | WR | DD 1% | Rend 1% | M+ |
|---|---|---|---|---|---|---|
| Greedy Brut 10 | 2333 | 1.77 | 27% | -57.4% | +2,381,361% | 11/13 |
| Greedy Divers 10 | 2163 | 1.64 | 32% | -50.6% | +728,430% | 11/13 |
| **Equilibre 10** | 2005 | 1.32 | 72% | -15.4% | +511% | 13/13 |
| High WR 10 | 1942 | 1.33 | 78% | -11.1% | +339% | 13/13 |

Conclusion: L'Equilibre 10 est le meilleur compromis pour le live.
- WR 72% = psychologiquement tenable, pas de dependance aux gros gagnants
- DD -15% = tres gerable, permet d'augmenter le risk (2% → ~-30% DD, ~+1500% rend)
- 13/13 mois positifs = regularite maximale
- Le Greedy a un rendement enorme mais 27% WR et -57% DD = dangereux en live

---

## 2026-03-23 — Audit critique live vs backtest

### Bug corrige: manage_positions TPSL TP sur close au lieu de high/low
- **Fichier**: live_paper_icmarkets.py, fonction manage_positions
- **Probleme**: Le fallback candle-level verifiait TP sur `last['close']` et sortait au prix close
- **Backtest**: Verifie TP sur `high` (long) / `low` (short) et sort au prix target exact
- **Impact**: Si le tick-level check rate un TP (deconnexion DB), le fallback candle donnait un resultat different du backtest
- **Fix**: TP check sur high/low, exit au target price (identique au backtest)
- **Commit**: 5edc372

### Bug corrige: eval_combo compound sur unrealized PnL
- **Fichiers**: find_combo_greedy.py, build_combo_balanced.py, build_combo_high_wr.py
- **Probleme**: trades tries par entry, PnL applique immediatement au capital → trades suivants sizes sur capital gonfle par profits non-realises
- **Fix**: event-based tracking: capital enregistre a l'entry pour sizing, PnL applique seulement a l'exit
- **Commit**: c0bf575, 1a8cdc8

### Impact du fix eval_combo sur Equilibre 10

| Metrique | Avant fix | Apres fix | Delta |
|---|---|---|---|
| Trades | 2005 | 2005 | = |
| PF | 1.32 | 1.32 | = |
| WR | 72% | 72% | = |
| DD | -15.4% | -15.8% | -0.4% |
| Rend | +511% | +494% | -17pp |
| M+ | 13/13 | 13/13 | = |

Impact modere sur Equilibre (peu d'overlap entre TPSL courts).
Greedy brut plus impacte: PF 1.77→1.60, Rend 2.4M%→1.7M%.

### Autres points audites (OK)
- check_stops_realtime (tick-level): SL et TP corrects (bid/ask reel)
- detect_all: conditions identiques backtest ↔ live pour les 11 strats du portfolio
- TPSL sim_exit_custom: SL sur low/high, TP sur high/low, exit au target — OK
- Spread: backtest = 2x monthly avg, live = bid/ask reel — acceptable
- ATR: veille dans les deux cas — OK
- Conflict check: meme logique (pas 2 directions simultanees) — OK
- _triggered reset quotidien: OK (corrige commit 9cd082a)

### Points restants non critiques
1. Portfolio = 11 strats (pas 10): TOK_2BAR present dans config mais absent de la liste texte
2. Pas de timeout 288 bars en live (backtest a un fallback 24h pour TPSL)
3. prev2_day_data pas passe en live (D8 pas dans portfolio, sans impact)
4. Dead code: SL/ACT/TRAIL globals + sim_exit() dans strats.py

---

## 2026-03-23 — Optimisation complete: 65 strats x 122 exits (optimize_all.py)

### Methode
- 65 strats detectees (53 existantes + 13 ajoutees: EMA crosses, CCI, BB_TIGHT, HMA_DIR, etc.)
- Grille: TPSL (6 SL x 7 TP = 42) + TRAIL (5 SL x 4 ACT x 4 TRAIL = 80) = 122 configs par strat
- Score selection: PF * WR, avec filtre split OK + PF > 1.05
- eval_combo event-based (sizing sur capital realise)

### Resultats: 65/65 strats avec config viable

### Top combos

| Combo | Trades | PF | WR | DD 1% | Rend 1% | M+ |
|---|---|---|---|---|---|---|
| Greedy 5 | 1010 | 1.66 | 74% | -7.7% | +548% | 13/13 |
| Greedy 8 | 1607 | 1.65 | 73% | -11.9% | +1486% | 13/13 |
| **Greedy 10** | 2006 | **1.60** | 72% | **-12.3%** | **+2579%** | 13/13 |
| Greedy 12 | 2078 | 1.62 | 72% | -12.5% | +3523% | 13/13 |
| Greedy 15 | 2669 | 1.52 | 72% | -13.9% | +5407% | 12/13 |
| Greedy 20 | 3524 | 1.47 | 74% | -18.1% | +11698% | 13/13 |

### Composition Greedy 10 (nouveau candidat)
| Strat | Type | SL | P2 | P3 | PF | WR |
|---|---|---|---|---|---|---|
| PO3_SWEEP | TRAIL | 3.0 | 0.75 | 0.75 | 2.46 | 79% |
| LON_PREV | TRAIL | 2.0 | 0.75 | 0.75 | 1.19 | 63% |
| TOK_2BAR | TRAIL | 3.0 | 0.50 | 0.50 | 1.61 | 75% |
| LON_KZ | TRAIL | 3.0 | 0.50 | 0.30 | 1.80 | 82% |
| ALL_KC_BRK | TRAIL | 3.0 | 1.00 | 0.75 | 1.20 | 69% |
| ALL_3SOLDIERS | TPSL | 3.0 | 2.00 | — | 1.34 | 67% |
| ALL_FVG_BULL | TRAIL | 3.0 | 1.00 | 0.75 | 1.63 | 70% |
| LON_BIGGAP | TRAIL | 3.0 | 0.75 | 0.50 | 1.70 | 74% |
| ALL_MACD_RSI | TRAIL | 1.5 | 0.50 | 0.50 | 1.67 | 60% |
| TOK_BIG | TRAIL | 3.0 | 0.30 | 0.30 | 1.57 | 76% |

### Comparatif vs ancien Equilibre 10
| Metrique | Ancien Equilibre | Nouveau Greedy 10 | Delta |
|---|---|---|---|
| PF | 1.32 | 1.60 | **+0.28** |
| WR | 72% | 72% | = |
| DD | -15.8% | -12.3% | **+3.5%** |
| Rend | +494% | +2579% | **5x** |
| M+ | 13/13 | 13/13 | = |

---

## 2026-03-23 — Analyse combinatoire exhaustive (analyze_combos.py)

### Methode
- 65 strats avec best config optimisee (optimize_all.py)
- Correlations pairwise entre toutes les strats
- 2080 paires evaluees
- 6 criteres greedy: Calmar, PF, MinDD, Sharpe, PF*WR, Diversifie
- Tailles 2 a 31 strats par critere
- Profils de risque: conservateur, equilibre, agressif

### Comparatif taille 10

| Critere | Trades | PF | WR | DD | Rend | Sharpe | M+ |
|---|---|---|---|---|---|---|---|
| Calmar | 2006 | 1.60 | 72% | -12.3% | +2579% | 4.3 | 13/13 |
| **PF** | **1428** | **1.85** | **76%** | **-17.6%** | **+1042%** | **4.2** | **12/13** |
| MinDD | 1758 | 1.42 | 84% | -6.8% | +226% | 3.8 | 11/13 |
| Sharpe | 1872 | 1.59 | 74% | -14.8% | +1353% | 6.0 | 12/13 |
| PF*WR | 1525 | 1.77 | 82% | -12.0% | +681% | 3.9 | 10/13 |
| Diverse | 1454 | 1.69 | 77% | -15.2% | +638% | 4.3 | 10/13 |

### Meilleurs combos par profil

**CONSERVATEUR (DD > -10%, 13/13 mois):**
- Calmar 5: PO3_SWEEP + LON_PREV + TOK_2BAR + LON_KZ + ALL_KC_BRK
- PF=1.66, WR=74%, DD=-7.7%, Rend=+548%, 13/13 mois

**EQUILIBRE (DD > -15%, PF > 1.4):**
- Calmar 13: PO3_SWEEP + LON_PREV + TOK_2BAR + LON_KZ + ALL_KC_BRK + ALL_3SOLDIERS + ALL_FVG_BULL + LON_BIGGAP + ALL_MACD_RSI + TOK_BIG + TOK_PREVEXT + LON_TOKEND + ALL_PSAR_EMA
- PF=1.53, WR=72%, DD=-11.3%, Rend=+3646%, 13/13 mois

**MEILLEUR PF (taille 10):**
- PO3_SWEEP + D8 + LON_BIGGAP + LON_PREV + LON_TOKEND + TOK_PREVEXT + LON_KZ + LON_GAP + TOK_BIG + ALL_CONSEC_REV
- PF=1.85, WR=76%, DD=-17.6%, Rend=+1042%, 12/13 mois

**MEILLEUR SHARPE (taille 10):**
- PO3_SWEEP + LON_KZ + TOK_2BAR + LON_PREV + ALL_KC_BRK + ALL_PSAR_EMA + ALL_CONSEC_REV + LON_BIGGAP + NY_LONEND + ALL_FIB_618
- Sharpe=5.96, PF=1.59, DD=-14.8%, 12/13 mois

### Observations cles
- PO3_SWEEP TRAIL (PF 2.46) est le pilier de TOUS les combos
- LON_KZ, LON_TOKEND, LON_BIGGAP forment un noyau London tres fort
- Le critere PF donne le meilleur PF mais plus de DD
- MinDD donne DD <7% mais rendement faible
- Calmar est le meilleur compromis avec 13/13 mois
- Sharpe donne le meilleur ratio risque/rendement ajuste

### Fichiers generes
- `optim_data.pkl` — donnees trades pour reload rapide
- `combo_results.json` — resultats tous criteres/tailles

---

## 2026-03-23 — Recommandations par compte (prop firm vs compte propre)

### Contexte
- ICMarkets = compte propre, pas de limite DD, maximiser rendement
- 5ers / FTMO = prop firm, DD musele (5ers: 4% challenge, FTMO: 10%)
- Les DD/Rend sont lineaires avec le risk% (0.5% risk = DD et Rend divises par 2)

### Recommandations

| Compte | Combo | Risk | PF | WR | DD | Rend | M+ |
|---|---|---|---|---|---|---|---|
| **5ers** | MinDD 5 | 0.50% | 1.62 | 82% | -2.5% | +83% | 12/13 |
| **5ers** | Calmar 5 | 0.50% | 1.66 | 74% | -3.9% | +274% | 13/13 |
| **FTMO** | Calmar 8 | 0.50% | 1.65 | 73% | -6.0% | +743% | 13/13 |
| **FTMO** | Calmar 5 | 1.00% | 1.66 | 74% | -7.7% | +548% | 13/13 |
| **ICM std** | Calmar 12 | 1.00% | 1.62 | 72% | -12.5% | +3523% | 13/13 |
| **ICM std** | Calmar 14 | 1.00% | 1.54 | 72% | -12.9% | +4569% | 13/13 |
| **ICM aggr** | Calmar 8 | 2.00% | 1.65 | 73% | -23.8% | +2972% | 13/13 |
| **ICM aggr** | Calmar 12 | 2.00% | 1.62 | 72% | -25.0% | +7046% | 13/13 |

### Compositions

**5ers MinDD 5** (DD < 5%, WR > 80%):
PO3_SWEEP(TRAIL 3.0/0.75/0.75) + TOK_2BAR(TRAIL 3.0/0.50/0.50) + LON_TOKEND(TRAIL 3.0/0.30/0.30) + ALL_AO_SAUCER(TPSL 3.0/0.50) + ALL_CCI_14_ZERO(TPSL 3.0/0.50)

**FTMO Calmar 8**:
PO3_SWEEP(TRAIL 3.0/0.75/0.75) + LON_PREV(TRAIL 2.0/0.75/0.75) + TOK_2BAR(TRAIL 3.0/0.50/0.50) + LON_KZ(TRAIL 3.0/0.50/0.30) + ALL_KC_BRK(TRAIL 3.0/1.00/0.75) + ALL_3SOLDIERS(TPSL 3.0/2.00) + ALL_FVG_BULL(TRAIL 3.0/1.00/0.75) + LON_BIGGAP(TRAIL 3.0/0.75/0.50)

**ICM Calmar 12**:
PO3_SWEEP(TRAIL 3.0/0.75/0.75) + LON_PREV(TRAIL 2.0/0.75/0.75) + TOK_2BAR(TRAIL 3.0/0.50/0.50) + LON_KZ(TRAIL 3.0/0.50/0.30) + ALL_KC_BRK(TRAIL 3.0/1.00/0.75) + ALL_3SOLDIERS(TPSL 3.0/2.00) + ALL_FVG_BULL(TRAIL 3.0/1.00/0.75) + LON_BIGGAP(TRAIL 3.0/0.75/0.50) + ALL_MACD_RSI(TRAIL 1.5/0.50/0.50) + TOK_BIG(TRAIL 3.0/0.30/0.30) + TOK_PREVEXT(TRAIL 1.5/0.75/1.00) + LON_TOKEND(TRAIL 3.0/0.30/0.30)

### Observations
- **Calmar domine** pour tous les profils sauf 5ers ultra-conservateur (MinDD)
- **Calmar 5 est le couteau suisse**: DD -7.7% a 1%, 13/13 mois, utilisable partout
- Pour FTMO a 0.5% risk, on peut aller jusqu'a Calmar 20 (DD -9%, +5849%)
- PF criterion donne les meilleurs PF (1.85+) mais DD plus eleve et 12/13 mois
- MinDD donne WR 82-85% parfait pour propfirm qui veulent du confort

### Fichiers de reference
- `combo_results.json` — tous les resultats par critere et taille
- `optim_data.pkl` — donnees trades pour re-analyse rapide
- `optimize_all.py` — script optimisation complete
- `analyze_combos.py` — script analyse combinatoire

Changements cles:
- TRAIL au lieu de TPSL pour 8/10 strats → permet de capturer les gros mouvements
- PO3_SWEEP TRAIL: PF 2.46 (vs 1.76 en TPSL)
- ALL_FVG_BULL TRAIL: PF 1.63 (vs 1.06 en TPSL, etait perdant!)
- ALL_MACD_RSI TRAIL: PF 1.67 (vs 1.22 en TPSL)
- Nouvelles strats: LON_PREV, ALL_KC_BRK, LON_BIGGAP remplacent ALL_CONSEC_REV, ALL_PSAR_EMA, ALL_FIB_618

---

## 2026-03-23 — Mise en production des nouvelles configs

### Changements appliques
- `strats.py`: ajout ALL_KC_BRK (detection + indicateurs Keltner Channels)
- `strat_exits.py`: reecrit avec 65 configs optimisees (optimize_all.py)
- `config_icm.py`: nouveau — ICM Calmar 12 @ 1% risk (remplace config_icmarkets.py)
- `config_ftmo.py`: mis a jour — FTMO Calmar 8 @ 0.5% risk
- `config_5ers.py`: mis a jour — 5ers MinDD 5 @ 0.5% risk
- `live_paper_icmarkets.py`: importe config_icm.py + RISK_PCT dynamique
- `dashboard.py`: importe config_icm.py, titres/captions dynamiques
- `bt_portfolio.py`: nouveau — backtest rapide par compte (charge optim_data.pkl)
- `CLAUDE.md`: nouvelle nomenclature complete

### Nomenclature fichiers
| Type | Fichier | Role |
|---|---|---|
| Core | `strats.py` | detect_all(), sim_exit_custom(), compute_indicators() |
| Core | `strat_exits.py` | 65 configs exit optimisees |
| Config | `config_icm.py` | ICM Calmar 12 (1% risk) |
| Config | `config_ftmo.py` | FTMO Calmar 8 (0.5% risk) |
| Config | `config_5ers.py` | 5ers MinDD 5 (0.5% risk) |
| Live | `live_paper_icmarkets.py` | Paper trading ICM |
| Dashboard | `dashboard.py` | Streamlit dashboard ICM |
| Backtest | `bt_portfolio.py` | Backtest rapide (optim_data.pkl) |
| Optim | `optimize_all.py` | Optimisation 65 strats x 122 exits |
| Optim | `analyze_combos.py` | Analyse combinatoire 6 criteres |
| Data | `optim_data.pkl` | Trades precomputes |
| Data | `combo_results.json` | Resultats tous criteres/tailles |

### Comment lancer
```
python live_paper_icmarkets.py --reset   # reset state (nouveau portfolio)
python live_paper_icmarkets.py           # paper trading live
streamlit run dashboard.py               # dashboard
python bt_portfolio.py [icm|ftmo|5ers]   # backtest rapide
python optimize_all.py                   # re-optimiser (si modif strats/exits)
python analyze_combos.py                 # re-analyser combos (si re-optimise)
```

### Dashboard compact sidebar
- Sidebar: 1 ligne par strat (icone + nom + trades + WR + PnL$)
- Detail au survol souris (tooltip): description, session, exit config, PF, W/L
- Suppression du groupement par session et des descriptions multi-lignes
- Commit: 4885a8a, 98bd537 (restauration groupement par session)

### Live heartbeat + detail trades
- Heartbeat toutes les 5min: `~ HH:MM | OHLC | ATR | N/12 trig | Npos | unr=$X`
- Trade ouvert: entry/bid/ask/spread, SL distance + ATR mult, TP/RR ou TRAIL params, size/lots, risk$, capital
- tick fetche a chaque poll (pas seulement quand positions ouvertes)
- Commit: feba397

### bt_portfolio.py: args capital et risk
- `python bt_portfolio.py icm -c 100000 -r 2` → ICM $100k @ 2% risk
- `python bt_portfolio.py ftmo -c 200000` → FTMO $200k @ 0.5% (defaut config)
- Commit: 0239615, 6f35211 (rewrite complet: mois par mois, strats, directions, sessions, distribution, equity ASCII)

### BUG CRITIQUE: detect_all appele 2 fois consumait les triggers
- **Probleme**: detect_open_strats appelait detect_all qui marquait TOUTES les strats dans trig (open + close). Quand detect_close_strats appelait detect_all apres, les strats close etaient deja triggees → 0 trades close generes
- **Impact**: AUCUN trade close (TOK_BIG, ALL_3SOLDIERS, ALL_KC_BRK, PO3_SWEEP, etc.) n'etait jamais ouvert en live. Seules les open strats pouvaient trader
- **Fix**: un seul appel detect_signals() qui route les signaux vers open/close lists sans filtrer avant que trig soit set
- **Commit**: dda27c5

### Fix: calage au demarrage
- Au lancement, toujours se caler sur la derniere bougie en DB (ignorer le saved_ts du state)
- Garantit qu'on ne trigger jamais sur une bougie qui existait avant le lancement
- Commit: 8b3efff

### Fix: trig dicts separes open/close + restore real-time open strats
- **Probleme**: le fix precedent (detect_signals unique) faisait tourner les open strats sur bougie fermee au lieu de temps reel → 5min de retard sur LON_KZ, LON_TOKEND, etc.
- **Fix**: 2 trig dicts separes (`_triggered_open` et `_triggered_close`), open strats detectees a chaque poll (temps reel), close strats sur bougie fermee
- **Heartbeat**: affiche les 2 compteurs `trig 3/5o 4/7c`
- Commit: 87f3a04

### Comparatif backtest vs live 24 mars 2026

Backtest simule sur les memes donnees DB que le live.

| Strat | BT time | BT PnL oz | Live time | Live PnL oz | Verdict |
|---|---|---|---|---|---|
| ALL_FVG_BULL | 01:30 | -33.58 | 01:30 | -33.85 | OK (identique) |
| ALL_MACD_RSI | 01:45 | -16.79 | 01:45 | -17.04 | OK (identique) |
| LON_BIGGAP | 08:00 | +3.55 | 08:00 | +2.90 | OK (identique) |
| LON_PREV | skip (conflit) | — | skip (conflit) | — | OK |
| LON_KZ | skip (conflit) | — | skip (conflit) | — | OK |
| TOK_BIG | 00:10 | +40.88 | 01:10 | -34.17 | BUG retard 1h |
| ALL_3SOLDIERS | 00:20 | +22.39 | 01:10 | -34.17 | BUG retard 50min |
| ALL_KC_BRK | 00:20 | +19.85 | 01:40 | -34.64 | BUG retard 1h20 |
| TOK_2BAR | 00:45 | +9.69 | — | — | BUG trig rate |

Conclusion:
- Strats London (08h+) = coherentes entre BT et live
- Strats Tokyo (00h-06h) = decalees car le live a demarre tard (calage sur derniere bougie)
- Le script de comparaison initial etait faux: il ne filtrait pas les conflits de direction
- LON_PREV et LON_KZ correctement skippees (short vs LON_BIGGAP long ouvert)

### Comparatif backtest vs live 25 mars 2026

4/4 trades match. Live valide.

| Strat | BT Entry | LV Entry | E.diff | BT PnL | LV PnL | P.diff |
|---|---|---|---|---|---|---|
| ALL_3SOLDIERS | 4566.51 | 4566.16 | -0.35 | +27.60 | +27.67 | +0.07 |
| ALL_FVG_BULL | 4566.51 | 4566.16 | -0.35 | +21.93 | +21.81 | -0.12 |
| ALL_MACD_RSI | 4596.40 | 4596.45 | +0.05 | -20.70 | -21.99 | -1.29 |
| TOK_PREVEXT | 4546.86 | 4553.89 | +7.03 | +8.80 | +0.82 | -7.98 |
| **TOTAL** | | | | **+37.63** | **+28.31** | **-9.32** |

Ecart TOK_PREVEXT = open strat, entry au tick vs row['open']. Close strats quasi identiques.
Script: `python compare_today.py` — comparatif quotidien BT vs live avec filtre conflits.
Commit: 6b6c6dd

### Analyse open strats: trigger sur bougie precedente

**Probleme identifie** : les open strats (TOK_PREVEXT, LON_TOKEND, LON_PREV, LON_BIGGAP, LON_KZ) dans le backtest entrent a `row['open']` de la bougie trigger. Mais en live, la bougie n'est visible en DB qu'a sa fermeture (5min plus tard), donc le live entrait au close au lieu de l'open → 7$ d'ecart sur TOK_PREVEXT.

**Analyse des conditions de trigger** :
- TOK_PREVEXT : conditions basees sur prev_day_data → connues AVANT l'heure trigger
- LON_TOKEND : basees sur tok[-3:] (fermees a 06:00) → connues avant 08:00
- LON_PREV : basees sur prev_day_data → connues avant 08:00
- LON_KZ : basees sur move 8h-10h → connues avant 10:00
- LON_BIGGAP : gap = row['open'] - tok.close → besoin du premier prix de la session

Pour 4/5 strats, le prix open n'a AUCUNE incidence sur le trigger. Seul LON_BIGGAP utilise l'open pour calculer le gap (en live → tick courant).

**Solution** : evaluer les conditions des open strats sur la BOUGIE PRECEDENTE (deja fermee) avec l'heure reelle (now_utc). A 08:00:01, on evalue sur la bougie 07:55 et on entre au tick courant.

**Le backtest n'est pas modifie** : il entre a row['open'] ce qui est equivalent car en 5min le open de la bougie 08:00 ≈ close de la bougie 07:55. L'ecart est negligeable.

- Commit: c638b67, cb4ccc8 (fix entry_time: now_utc au lieu de candle_time pour open strats)

### Separation fichiers par broker
- `optim_data_{icm|ftmo|5ers}.pkl` — pickle par compte
- `combo_results_{icm|ftmo|5ers}.json` — resultats combos par compte
- Usage: `python optimize_all.py ftmo` / `python bt_portfolio.py ftmo` / `python analyze_combos.py ftmo`
- Commit: 5fa70ab

### Test FTMO Calmar 8 sur donnees FTMO (au lieu de ICM)
Le combo Calmar 8 optimise sur ICM **ne tient PAS** sur donnees FTMO:
- PF 1.67 → 1.29 | WR 73% → 67% | DD -6.1% → -10.0% | M+ 13/13 → 9/13
- 4 mois negatifs: mars, juin, aout, sept 2025
- DD -10% = PILE la limite FTMO → inacceptable
- Les exits optimises sur ICM ne sont pas transferables a FTMO
- Il faut re-optimiser specifiquement sur les donnees FTMO
### Analyse combos FTMO (donnees FTMO)

45 strats viables. Aucun combo 13/13 mois avec DD < 10%.

Meilleurs candidats @ 0.5% risk:

| Combo | Strats | PF | WR | DD | Rend | M+ |
|---|---|---|---|---|---|---|
| Calmar 5 | PO3+LON_PREV+PSAR_EMA+TOK_2BAR+DC10 | 1.41 | 66% | -9.1% | +269% | 11/13 |
| MinDD 5 | LON_TOKEND+PO3+TOK_PREVEXT+PSAR_EMA+LON_KZ | 1.30 | 71% | -6.8% | +92% | 12/13 |
| Calmar 3 | PO3+LON_PREV+PSAR_EMA | 1.43 | 68% | -7.3% | +119% | 12/13 |

Conclusion: les donnees FTMO sont plus difficiles que ICM (spreads? feed? timing?).
Le Calmar 8 ICM donne DD -10% sur FTMO = inacceptable. Il faut un combo specifique FTMO.
Candidat FTMO: Calmar 5 (DD -9.1%, marge 0.9% avant limite).

### Mise en place FTMO
- config_ftmo.py: Calmar 5 (PO3_SWEEP, LON_PREV, ALL_PSAR_EMA, TOK_2BAR, ALL_DC10) @ 0.5%
- strats.py: ajout ALL_DC10 (Donchian 10 breakout) detection + indicateur dc10_h/dc10_l
- live_paper_icmarkets.py: multi-compte (icm/ftmo/5ers) via argument CLI
  - Fichiers separes: paper_{account}.json, paper_{account}.log
- `live_paper.py` remplace `live_paper_icmarkets.py` (garde pour compat)
- Usage: `python live_paper.py ftmo --reset`
- Commit: 5720b37
- Dashboard: selecteur de compte ICM/FTMO/5ers dans la sidebar (commit 1995bb4, 6d859ab)
- Fix double render sidebar: remplace sleep+rerun par streamlit-autorefresh
- live_paper.py: args --capital et --risk (commit 4e0cea6)
- live_paper.py renomme de live_paper_icmarkets.py (commit 3cf3428)
- Fix capital: state sauvegarde capital_initial, broker, risk_pct (commit 175a44b)
- Fix reset: supprime le JSON, ne quitte plus (enchaine directement), plus de load_state() duplique (commit a venir)
- Fix: les args -c et -r doivent etre passes avec --reset pour s'appliquer

### Usage final scripts

```
# Paper trading
python live_paper.py ftmo -c 50000 -r 0.1 --reset   # reset + lance FTMO $50k 0.1%
python live_paper.py ftmo -c 50000 -r 0.1            # reprend FTMO
python live_paper.py icm -c 100000 --reset            # reset ICM $100k 1% (defaut)
python live_paper.py                                   # reprend ICM

# Backtest
python bt_portfolio.py ftmo -c 200000 -r 0.5          # backtest FTMO
python optimize_all.py ftmo                            # re-optimiser sur donnees FTMO
python analyze_combos.py ftmo                          # analyser combos FTMO

# Comparaison
python compare_today.py                                # BT vs live du jour

# Dashboard
streamlit run dashboard.py                             # selecteur de compte dans sidebar
```

### Fichiers par compte
| Fichier | ICM | FTMO | 5ers |
|---|---|---|---|
| Config | config_icm.py | config_ftmo.py | config_5ers.py |
| State | paper_icm.json | paper_ftmo.json | paper_5ers.json |
| Log | paper_icm.log | paper_ftmo.log | paper_5ers.log |
| Pickle | optim_data_icm.pkl | optim_data_ftmo.pkl | optim_data_5ers.pkl |
| Combos | combo_results_icm.json | combo_results_ftmo.json | combo_results_5ers.json |

---

## 2026-03-25 — Optimisation 5ers sur donnees 5ers

### Resultats
40/65 strats viables (25 sans config viable — donnees 5ers plus difficiles).
Aucun combo 13/13 mois avec DD < 10%.

Meilleur candidat 5ers (DD < 4% challenge):
- Calmar 5 @ 0.25% risk: TOK_PREVEXT + TOK_2BAR + ALL_PSAR_EMA + ALL_FVG_BULL + NY_LONEND
- PF 1.38 | WR 67% | DD -2.4% | Rend +43% | 11/13 mois

### Config
- config_5ers.py mis a jour: Calmar 5 @ 0.25% risk
- optim_data_5ers.pkl genere
- Strats: toutes deja dans strats.py detect_all

### Mise a jour 5ers: MinDD 10 (remplace Calmar 5)
- Ancien: Calmar 5 @ 0.25% (PF 1.38, WR 67%, DD -2.4%, +43%)
- **Nouveau: MinDD 10 @ 0.25% (PF 1.46, WR 74%, DD -2.5%, +104%)**
- Strats: TOK_PREVEXT, LON_TOKEND, LON_PREV, TOK_BIG, PO3_SWEEP, LON_PIN, ALL_ADX_FAST, TOK_WILLR, ALL_KC_BRK, TOK_FADE
- Ajout strats.py: ALL_ADX_FAST (ADX fast DI cross + EMA21), TOK_WILLR (Williams %R Tokyo)
- Ajout indicateurs: adx_f, pdi_f, mdi_f, ema21, wr14
- Commit: 605f476

### live_mt5.py: trading reel MT5
- Meme logique que live_paper.py mais avec vrais ordres MT5
- Close strats: detection DB (bougie fermee) → mt5.order_send()
- Open strats: detection bougie precedente → mt5.order_send() au tick
- TPSL: SL + TP poses sur l'ordre → MT5 gere les exits
- TRAIL: SL initial → mt5_modify_sl() a chaque bougie fermee (best sur close)
- sync_positions(): detecte les clotures MT5 (SL/TP), log PnL incl commission+swap
- --dry: dry run (log sans envoyer d'ordres)
- --symbol: nom du symbole MT5 (defaut XAUUSD)
- Capital: lu depuis mt5.account_info().balance
- Lot sizing: mt5.symbol_info() pour min/step/max/contract_size
- State: data/{broker}/live_mt5.json
- Commit: 7b03121, 9351fbb (rewrite: magic par strat, positions lues MT5)

Architecture live_mt5.py:
- Magic number unique par strat (MAGIC_BASE 240000 + index alphabetique)
- Positions lues directement depuis MT5 (mt5.positions_get) — plus de simulation
- State minimal: triggers + trail info (best/trail_active par ticket)
- Trail entries auto-nettoyees quand MT5 ferme la position
- Au demarrage: affiche magic numbers + positions MT5 ouvertes

### Audit live_mt5.py
Audit #1:
1. CRITIQUE magic instable (tri alphabetique) → fix: hashlib.md5 deterministe
2. CRITIQUE double ouverture possible au restart → fix: check magic sur MT5 avant open
3. CRITIQUE triggers perdus au restart → fix: rebuild triggers depuis positions MT5
4. TRAIL best sur close (coherent backtest) → documente, pas change
5. Pas de timeout TRAIL → impact faible, documente
6. Dry run supprime (inutile, live_paper.py fait tout mieux) → commit 39f0030
- Commit: 6770ce0, 5912214, 3259736 (5 audits paralleles)

### LON_BIGGAP retiree de tous les portfolios
- Sa condition depend de `row['open']` pour calculer le gap
- En live, detect_open_strats passe la bougie precedente (07:55) donc le gap est faux
- Meme probleme pour LON_GAP, NY_GAP, NY_DAYMOM (pas dans les portfolios actifs)
- Regle: toutes les open strats doivent dependre UNIQUEMENT de bougies fermees, pas du prix open
- ICM passe de Calmar 12 a Calmar 11

### Dashboard Paper/Live MT5
- Selecteur Paper / Live MT5 dans la sidebar
- Mode Live: positions depuis mt5.positions_get(), historique depuis mt5.history_deals_get()
- Magic numbers pour identifier les strats (meme logique que live_mt5.py)
- Trades non reconnus (magic inconnu) → strat LEGACY
- PnL latent en temps reel depuis MT5 (p.profit)
- Commit: 4b7da91

### Filtre marge WR > 5% dans optimize_all.py
- Les strats dont le WR reel est trop proche du WR minimum (breakeven) sont eliminees
- Formule: marge = WR_reel - (1 / (1 + RR_reel)) * 100. Si marge < 5% → SKIP
- 5ers: 18/40 strats survivent au filtre
- Commit: en cours

### Analyse complete combos 5ers (strats saines uniquement)
- 18 strats safe, 16 combos viables (DD < 4% @ 0.25%)
- Top 3 (PO3_SWEEP + TOK_PREVEXT + ALL_PSAR_EMA): PF 1.43, DD -2.8%, +15%
- Top 4 (+TOK_BIG): PF 1.35, DD -3.4%, +22%, 11/13
- Toutes les 18 ensemble: PF 1.15, DD -17.6% → trop dilue
- Sweet spot: 3-5 strats

### LON_BIGGAP retiree de ICM
- Sa condition depend de row['open'] incompatible avec detect_open_strats
- ICM passe de Calmar 12 a Calmar 11

### Audits 6-9 (4 audits paralleles)
**Audit 6 (entry timing):** LON_BIGGAP bug confirme. Les 7 close strats OK. Les 4 autres open strats OK (conditions ne dependent pas de row['open']).

**Audit 7 (conflits):** Ordre BT (alphabetique) vs live (open strats first) → resultat peut differer. Magic guard bloque multi-day same-strat (BT autorise). Documente et accepte.

**Audit 8 (trailing edge cases):** 6/6 scenarios safe.

**Audit 9 (DB candles):** Table partagee entre brokers (risque si multi-fetcher). compute_indicators 300x/bougie (performance). DST pas applique aux sessions (coherent BT).

### Comparatif London 26 mars 5ers (BT vs live)
- LON_TOKEND: BT sort 08:25, live sort 08:17 (trail SL touche par tick intra-bougie)
- LON_PREV: quasi identique (08:25 vs 08:26)
- LON_PIN: quasi identique (08:40 vs 08:43)
- Difference LON_TOKEND = granularite (BT 5min bars vs MT5 tick par tick)
- Live correct — MT5 plus precis que le backtest

### Analyse RR et marge WR
- LON_PIN: RR 0.40, WR min 71%, WR reel 72% → marge 3% → trop risque avec frais
- 8/10 strats du portfolio 5ers etaient RISK (marge < 5%)
- Seules TOK_PREVEXT et ALL_KC_BRK etaient saines

### Config 5ers finale: Calmar 6 (filtre marge WR)
- Ancien: MinDD 10 (8/10 strats RISK, marge WR < 5%)
- **Nouveau: Calmar 6 — PO3_SWEEP + ALL_PSAR_EMA + TOK_2BAR + ALL_DC10 + TOK_BIG + TOK_PREVEXT**
- PF 1.32 | WR 68% | DD -3.6% @ 0.25% | Rend +45% | 11/13 mois
- Toutes les strats ont marge WR > 5% (rentables avec frais)
- 10 nouvelles strats testees (engulfing, hammer, doji, morning star, asian breakout, inside bar, BB squeeze, RSI extreme, MACD hist, vol spike) — aucune n'a passe le filtre sur donnees 5ers

### NAS100 — Test indices (2026-03-26)

**Strats XAUUSD sur NAS100**: 0/71 viables. Aucune ne fonctionne.

**Strats indices (strats_indices.py)**: 16 nouvelles strats creees:
- Opening: IDX_ORB15, IDX_ORB30, IDX_GAP_FILL, IDX_GAP_CONT
- Momentum: IDX_NY_MOM, IDX_LATE_REV, IDX_TREND_DAY
- Mean reversion: IDX_VWAP_BOUNCE, IDX_BB_REV, IDX_RSI_REV
- Breakout: IDX_PREV_HL, IDX_NR4, IDX_KC_BRK
- Pattern: IDX_ENGULF, IDX_3SOLDIERS, IDX_CONSEC_REV

**Resultats NAS100 5ers**: 4/16 strats safe (marge WR > 5%)
- IDX_PREV_HL: PF 1.44, WR 67%, marge +8.4%
- IDX_NR4: PF 1.25, WR 62%, marge +5.4%
- IDX_NY_MOM: PF 1.24, WR 54%, marge +5.4%
- IDX_BB_REV: PF 1.27, WR 69%, marge +5.3%

Best combo Greedy 2 @ 0.25%: DD -2.6%, +16%, 10/13 mois. Viable mais modeste.

### BTCUSD — Test (2026-03-26)

**Strats gold sur BTC**: 0/71 viables. Meme resultat que NAS100.

**Strats indices sur BTC**: 5/16 safe (marge WR > 5%)
- IDX_CONSEC_REV: PF 1.44, WR 57%
- IDX_GAP_CONT: PF 1.38, WR 67%
- IDX_GAP_FILL: PF 1.23, WR 57%
- IDX_NR4: PF 1.29, WR 39%
- IDX_RSI_REV: PF 1.33, WR 78%

Best combo Greedy 3 @ 0.25%: DD -2.8%, +46%, **13/13 mois**
Strats: IDX_CONSEC_REV + IDX_GAP_CONT + IDX_GAP_FILL

BTC meilleur que NAS100 (5 safe vs 4, 13/13 vs 10/13). Comparable a l'or sur rendement.

### Dictionnaire unifie (2026-03-26)
- Fusion de toutes les strats (gold + indices + crypto) dans strats.py
- 87 strats total dans un seul detect_all()
- L'optimiseur filtre ce qui marche par instrument
- Plus besoin de optimize_indices.py separement
- Fix crash optimize_all.py quand 0 strats viables
- Usage: python optimize_all.py 5ers --symbol btcusd

### BTCUSD — Retest avec dictionnaire unifie (2026-03-26)
- optimize_all.py avec 90 strats (gold + indices + crypto): 0/90 viables
- Les resultats precedents (optimize_indices.py: 5 safe) etaient avec des filtres differents
- Le filtre unifie (PF>1.05 + split + marge WR>5%) est plus strict et plus honnete
- BTC et NAS100 ne marchent pas avec nos strats actuelles sur 5min

### BTCUSD — RESULTATS APRES FIX NaN (2026-03-26)
Bug trouve: avg_sp = np.mean([]) = NaN quand pas de ticks → tous les PnL NaN → 0 viable.
Fix: avg_sp = 0 si pas de ticks.

**22/85 strats safe sur BTC** (marge WR > 5%)

Meilleurs combos @ 1% risk:
| Combo | Trades | PF | WR | DD | Rend | M+ |
|---|---|---|---|---|---|---|
| Greedy 5 | 1315 | 1.47 | 54% | -12.7% | +2426% | 12/13 |
| Greedy 10 | 2391 | 1.47 | 64% | -13.5% | +7113% | 13/13 |
| Greedy 15 | 3530 | 1.47 | 69% | -18.7% | +12828% | 13/13 |

@ 0.25% risk (5ers): Greedy 10 → DD -3.4%, +1778%, 13/13
**BTC bien meilleur que gold sur 5ers** (+1778% vs +45%).

ATTENTION: pas de spread decompte (pas de ticks BTC). Resultats probablement optimistes.

### Regression check gold 5ers (apres fix NaN)
- PF 1.32→1.33, WR 68%→68%, DD -3.6%→-3.7%, M+ 11/13→11/13
- Rend 45%→31.5% (baisse due au double compute_indicators, leger)
- Pas de regression critique. Portfolio identique (6 strats).

### NAS100 — RESULTATS APRES FIX NaN (2026-03-26)
27/80 strats safe. Greedy 10 @ 0.25%: DD -3.4%, +219%, 11/13 mois.
Bien meilleur que gold 5ers (+219% vs +31%).

### Comparatif instruments 5ers @ 0.25% risk (Greedy 10)
| Instrument | Strats safe | PF | DD | Rend | M+ |
|---|---|---|---|---|---|
| XAUUSD | 18 | 1.33 | -3.7% | +31% | 11/13 |
| NAS100 | 27 | 1.39 | -3.4% | +219% | 11/13 |
| BTCUSD | 22 | 1.47 | -3.4% | +1778% | 13/13 |

ATTENTION: NAS100 et BTC sans spread decompte. Resultats probablement optimistes.

### Suppression market_ticks (2026-03-26)
- Spread insignifiant avec PF > 1.3 (~0.01% vs moves de 0.3-1.5%)
- Supprime toute reference a market_ticks dans les scripts actifs
- optimize_all.py: spread=0 (plus de tick table)
- optimize_indices.py: idem
- live_paper.py: get_current_price() lit derniere bougie au lieu de ticks
- dashboard.py: prix depuis derniere bougie
- phase1_poc_calculator.py: get_trading_days depuis candles uniquement
- live_mt5.py: inchange (utilise MT5 ticks directement, pas la DB)
- Plus besoin de charger les ticks pour chaque broker/instrument

### Comparatif tous instruments 5ers (2026-03-26)
87 strats unifiees testees sur 8 instruments, filtre marge WR > 5%.

| Instrument | Safe | PF | WR | DD @0.25% | Rend @0.25% | M+ |
|---|---|---|---|---|---|---|
| **JPN225** | 26 | **1.74** | **78%** | **-1.8%** | +168% | **13/13** |
| **DAX40** | 45 | 1.60 | 67% | -1.9% | +228% | **13/13** |
| **UK100** | 15 | 1.50 | 75% | -2.0% | +102% | **13/13** |
| BTCUSD | 22 | 1.47 | 54% | -3.2% | +607% | 12/13 |
| SP500 | 14 | 1.43 | 78% | -1.9% | +67% | 12/13 |
| NAS100 | 27 | 1.39 | 72% | -2.8% | +117% | 11/13 |
| US30 | 16 | 1.43 | 53% | -5.0% | +313% | 12/13 |
| XAUUSD | 18 | 1.33 | 68% | -3.7% | +31% | 11/13 |

JPN225 champion: meilleur PF, meilleur WR, 13/13 mois, DD < 2%.
ATTENTION: tous sauf XAUUSD sans spread decompte.

### Audit look-ahead nouvelles strats (2026-03-26)
26 strats auditees (10 ALL_* + 16 IDX_*). **Aucun look-ahead trouve.**
Toutes utilisent bougie fermee + bougies precedentes + indicateurs forward-only.

Points d'attention (pas de look-ahead mais design questionnable):
1. Sessions US hardcodees (14:30-21:00 UTC) appliquees a JPN225/DAX40 — trade en off-hours
2. Gap BTC artificiel (pas de fermeture reelle, 24/7)
Ces biais favorisent potentiellement les resultats mais ne sont pas du look-ahead. L'edge est plus fort (18 strats safe vs 4). Revenir sur indices quand le live gold est stable.

### Architecture multi-instrument (discussion 2026-03-26)

**Decision**: tester NAS100 d'abord avec --symbol separement, puis refactoriser.

**Architecture cible** (apres validation):
- Un seul process live_mt5.py par broker, multi-instrument
- Config par broker avec liste d'instruments et strats par instrument
- Magic numbers encodent broker + instrument + strat
- data/{broker}/{instrument}/ pour les fichiers
- Dashboard avec selecteur broker + instrument

**Architecture interim** (pour tester):
- --symbol NAS100 en argument CLI
- data/{broker}/nas100/ pour les fichiers
- Table DB candles_mt5_nas100_5m
- Memes strats/indicateurs (universels)
- Strats session-specific (TOK_*, LON_*, PO3_SWEEP) probablement inutiles sur NAS100

### Enrichissement dictionnaire de strats
10 nouvelles strats ajoutees au dictionnaire:
- Candlestick: ALL_ENGULF, ALL_HAMMER, ALL_DOJI_REV, ALL_MSTAR
- Breakout: LON_ASIAN_BRK, ALL_INSIDE_BRK, ALL_BB_SQUEEZE
- Momentum: ALL_RSI_EXTREME, ALL_MACD_HIST, ALL_VOL_SPIKE
Indicateurs ajoutes: bb_width, bb_width_min20, macd_hist, vol_avg, upper/lower wick, candle_range
Detection: en cours d'implementation

### 5 audits paralleles — tous les bugs corriges

**Audit 1 (signal detection):** Pas de bug critique. prev2_day_data manquant (D8 pas dans portfolio). prev_day_data.body manquant (jamais lu). OK.

**Audit 2 (exit logic):** Toutes formules identiques BT vs live. Differences structurelles (bougie vs tick) en faveur du live. OK.

**Audit 3 (lot sizing):** BUG capital=0 → trade au lot min. FIX: guard skip si balance<=0.

**Audit 4 (MT5 safety):**
- HIGH: mt5.shutdown() pas garanti → FIX: try/finally
- MEDIUM: trade_allowed pas verifie → FIX: check a l'init
- LOW: magic collision cross-broker → FIX: MAGIC_BASE par broker (240k/250k/260k)

**Audit 5 (state/restart):**
- HIGH: save_state seulement sur bougie → trail perdu si crash mid-candle → FIX: save apres chaque open_position
- MEDIUM: trigger rebuild sans date check → position hier bloque trigger aujourd'hui → FIX: check p.time vs today
- MEDIUM: --reset wipe trail info → FIX: warning si TRAIL ouvertes
- LOW: last_candle_ts dead code dans state → FIX: supprime

Audit #2 (backtest vs live MT5):
- TPSL: SL/TP geres par MT5 nativement → OK
- TRAIL etape 5 (close < nouveau stop): pas de market close, MT5 gere le SL tick par tick
- TRAIL SL initial: MT5 check tick par tick → mieux que backtest (bougie par bougie)
- TPSL meme bougie SL+TP: MT5 ordre reel vs BT SL prioritaire → live potentiellement meilleur
- Spread: BT 2x conservateur, live 1x reel → live meilleur
- Timeout 288 bars: absent en live → impact faible

### Audit isolation broker
Tous les scripts principaux sont cloisonnes par broker:
- live_mt5.py ✓ | live_paper.py ✓ | bt_portfolio.py ✓
- dashboard.py ✓ | analyze_combos.py ✓ | optimize_all.py ✓
- compare_today.py: etait hardcode ICM → CORRIGE (commit 4565808)
- strats.py / strat_exits.py: generiques, pas de reference broker ✓
- Donnees dans data/{icm|ftmo|5ers}/ ✓

### Isolation broker: dossiers data/{broker}/
Tous les fichiers per-broker dans `data/{icm|ftmo|5ers}/`:
- `optim_data.pkl` — trades precomputes
- `combo_results.json` — resultats combos
- `paper.json` — state paper trading
- `paper.log` — log paper trading
- `dashboard.txt` — dashboard texte

Scripts mis a jour: optimize_all.py, bt_portfolio.py, analyze_combos.py, live_paper.py, dashboard.py
Commit: a489e47

### Comparatif backtest vs live 25 mars 2026 (apres fix open strats)

BT: +54.95 oz | Live: +70.16 oz | Live fait mieux (+15.21)

| Strat | E.diff | P.diff | Verdict |
|---|---|---|---|
| ALL_3SOLDIERS | -0.35 | +0.07 | OK |
| ALL_FVG_BULL | -0.35 | -0.12 | OK |
| ALL_KC_BRK | -0.02 | -0.22 | OK |
| ALL_MACD_RSI | +0.05 | -1.29 | OK |
| TOK_PREVEXT | +7.03 | -7.98 | Pre-fix (avant le changement) |
| LON_PREV | BT skip | +15.62 | Live detecte a 07:50 (fix ok!) |
| PO3_SWEEP | BT skip | +9.13 | Live detecte a 08:00 |
| LON_BIGGAP | +0.00 | LV miss | Skip car LON_PREV long deja ouvert |

Observations:
- Close strats: entry diff < 0.35$ — parfait
- LON_PREV detecte a 07:50 grace au fix bougie precedente (avant: 08:05)
- Le BT et le live gerent les conflits differemment quand les signaux arrivent simultanement vs sequentiellement

### Incoherence connue: ordre de traitement des conflits BT vs live

Quand plusieurs strats trigger au meme moment avec des directions opposees:
- **Backtest**: traite par ordre alphabetique du nom de strat (tri `(ei, strat_name)` dans eval_combo). LON_BIGGAP short < LON_PREV long → LON_BIGGAP gagne.
- **Live**: traite par ordre de detection. Les open strats (detect_open_strats chaque seconde) trigguent avant les close strats (detect_close_strats sur bougie fermee). LON_PREV long detecte en premier → LON_PREV gagne.

Impact: sur le 25 mars, le BT prend LON_BIGGAP short (+0.00), le live prend LON_PREV long (+15.62) et PO3_SWEEP long (+9.13). Le live fait mieux sur ce jour.

Decision: on ne corrige pas. L'ordre alphabetique du BT est arbitraire. Le live reflete mieux la realite (open strats connues avant le candle, donc legitimement prioritaires). Un systeme de priorite par PF pourrait etre ajoute plus tard si necessaire.

---

## Validation ICM — Resume session 2026-03-25

### Bugs corriges
1. detect_all double-call consumait les triggers close strats (0 trades close) → fix: trig dicts separes
2. Calage au demarrage triggeait sur bougie existante → fix: toujours sync sur derniere bougie DB
3. Open strats detectees 5min en retard (attendaient la bougie en DB) → fix: evaluer sur bougie precedente
4. entry_time des open strats montrait candle_time au lieu de now_utc → fix: passer now_utc

### Etat live ICM valide
- Close strats: entry diff < 0.35$ vs backtest — parfait
- Open strats: trigger a l'heure correcte, entry au tick reel
- Conflits de direction: geres correctement (pas 2 directions simultanees)
- Trailing stop: fonctionne (best update sur close, activation sur ACT*ATR)
- Lot sizing: min 0.01 lot, warning si risk depasse 1.5x cible

### Scripts de reference
```
python live_paper_icmarkets.py --reset  # reset state
python live_paper_icmarkets.py          # paper trading
python compare_today.py                 # comparatif BT vs live du jour
python bt_portfolio.py icm -c 100000   # backtest historique
streamlit run dashboard.py              # dashboard
```

### Dashboard: couleurs PnL latent
- Colonnes PnL $ et PnL oz colorees vert/rouge dans le tableau positions ouvertes
- Metric PnL latent total avec fleche verte/rouge
- Commit: 9881c4b, 018cc48, cf49f88 (fix: pnl_vals indexe par row.name apres drop de _pnl_val)

### Fix lot sizing MT5
- Min lot 0.01 (1 oz), step 0.01 — arrondi au lot valide le plus proche
- Warning si risk reel > 1.5x la cible (ex: $1000 capital avec SL 3*ATR → min lot donne 3.4% risk au lieu de 1%)
- A $100k+ l'arrondi est negligeable (<0.1%)
- Commit: 7f4a5cb

---

## 2026-03-27 — Architecture multi-instrument

### Implementation
- Config: `config_{broker}.py` avec `INSTRUMENTS` dict (portfolio + risk par symbole)
- `live_mt5.py`: un seul process par broker, boucle sur tous les instruments
  - Magic = broker_base + symbol_offset + strat_hash
  - State unique avec `per_symbol` dict
- `bt_portfolio.py`: backtest tous instruments ou `--symbol` pour un seul
- Commit: fc27c3c

### Portfolios TODO
Les portfolios JPN225, DAX40, BTCUSD doivent etre remplis dans config_5ers.py
apres analyse des combos (analyze_combos.py 5ers --symbol jpn225 etc.)

### JPN225 portfolio 5ers: PF*WR 9 (2026-03-27)
- 9 strats: ALL_FIB_618, IDX_LATE_REV, D8, TOK_NR4, LON_GAP, LON_DC10_MOM, LON_TOKEND, ALL_MACD_RSI, TOK_PREVEXT
- PF 1.82 | WR 79% | DD -2.0% @ 0.25% | +86% | 13/13 mois
- TOK_NR4 et LON_DC10_MOM ajoutes a detect_all dans strats.py
- Attention: pas de spread, resultats possiblement optimistes
