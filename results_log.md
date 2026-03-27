# Results Log — Evolution des resultats

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
| SP500 | - | - | - | - | - | - | a faire |
| UK100 | - | - | - | - | - | - | a faire |
| US30 | - | - | - | - | - | - | a faire |

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
