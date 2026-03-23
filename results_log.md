# Results Log — Evolution des resultats

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
