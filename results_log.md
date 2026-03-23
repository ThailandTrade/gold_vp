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
