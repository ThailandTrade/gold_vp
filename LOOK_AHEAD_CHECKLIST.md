# LOOK-AHEAD CHECKLIST — Stress test obligatoire

Toute strategie, tout backtest, tout script doit passer TOUS ces checks.
Un seul echec = resultats invalides.

---

## 1. ENTRY: bougie fermee uniquement

- [ ] **Close strats**: le signal utilise le OHLC d'une bougie FERMEE
- [ ] **Entry price = close** de la bougie fermee (≈ open de la suivante en live)
- [ ] **Open strats** (gap, session open): entry = open de la bougie, SL check sur la meme bougie (check_entry_candle=True)
- [ ] **Jamais de signal sur une bougie non fermee** (pas de high/low/close d'une bougie en cours)

**Erreur type**: utiliser `tv.iloc[-1]['close']` quand la derniere bougie n'est pas fermee (NY_DAYMOM — corrige 2026-03-22)

---

## 2. EXIT: coherence avec les ordres MT5

### TPSL (Stop Loss + Take Profit fixes)
- [ ] **SL long**: declenche quand `low <= stop`, exit au prix `stop` (sell stop order)
- [ ] **SL short**: declenche quand `high >= stop`, exit au prix `stop` (buy stop order)
- [ ] **TP long**: declenche quand `high >= target`, exit au prix `target` (sell limit order)
- [ ] **TP short**: declenche quand `low <= target`, exit au prix `target` (buy limit order)
- [ ] **TP JAMAIS sur close** — close peut depasser target, ca surestime le profit
- [ ] **TP JAMAIS exit au close** — en live l'ordre limite s'execute au target exact
- [ ] **Si SL et TP touches sur la meme bougie**: SL prioritaire (conservateur, on ne sait pas l'ordre)

**Erreur type**: `if b['close'] >= target: return j, b['close']` — double bug: check sur close + exit au close (corrige 2026-03-23)

### TRAIL (Trailing Stop)
- [ ] **best = max(close)**, pas max(high) — coherence temporelle
- [ ] **Apres trailing update, PAS de re-check low/high vs nouveau stop**
- [ ] **Seul re-check**: close vs nouveau stop (MT5 ModifyPosition immediat)
- [ ] **Exit au close** quand close < stop apres trailing (pas au stop)

**Erreur type**: best = max(high) au lieu de max(close) (corrige 2026-03-21)

### General
- [ ] **Entry candle SL check** pour open strats (j=0: seulement SL, pas de trailing/TP)
- [ ] **Pas de timeout artificiel** sauf si justifie (MX=12 retire 2026-03-22)

---

## 3. INDICATEURS: calcul sequentiel uniquement

- [ ] **EMA, MACD, RSI**: `ewm()` = forward-only, OK
- [ ] **Supertrend/PSAR**: boucle forward, chaque step utilise uniquement data <= i, OK
- [ ] **Verification**: l'indicateur dans strats.py doit etre IDENTIQUE a celui du backtest
- [ ] **Pas de Parabolic SAR quand le backtest utilise Supertrend** (ou inversement)
- [ ] **Rolling indicators** (Donchian, BB, etc.): lookback window uniquement, OK

**Erreur type**: compute_indicators() utilisait le vrai Parabolic SAR, le backtest utilisait Supertrend (corrige 2026-03-23)

---

## 4. DONNEES: pas d'information future

### Spread
- [ ] **monthly_spread**: calculee sur le mois ENTIER — look-ahead mineur
- [ ] **En live**: utiliser le spread bid/ask reel, pas la moyenne mensuelle
- [ ] **Impact**: faible (spread varie peu intra-mois), mais techniquement impur

### ATR
- [ ] **ATR du jour = ATR de la VEILLE** (daily_atr[prev_day])
- [ ] **global_atr** (moyenne sur tout le dataset) = look-ahead, utilise uniquement comme fallback jour 1
- [ ] **En live**: ATR calcule sur les bougies passees uniquement

### Donnees de la veille
- [ ] **prev_day_data**: OHLC du jour PRECEDENT, pas du jour courant
- [ ] **prev2_day_data**: avant-veille (pour D8 inside day)

---

## 5. SIGNAL: pas de biais directionnel non teste

- [ ] **Si le backtest ne teste que LONG, le live ne doit pas avoir SHORT**
- [ ] **Verifier que chaque direction (long ET short) a ete validee dans le backtest**

**Erreur type**: ALL_FIB_618 — backtest LONG only, j'avais ajoute SHORT dans detect_all (corrige 2026-03-23)

---

## 6. CONDITIONS: identiques backtest ↔ live

- [ ] **Les conditions de detection dans strats.py doivent etre IDENTIQUES a celles du backtest (find_combo_greedy.py)**
- [ ] **Pas de conditions supplementaires** (overlap, wick check, etc.) non presentes dans le backtest
- [ ] **Pas de conditions manquantes** presentes dans le backtest
- [ ] **Verification**: audit_signals.py doit montrer 100% match sur tous les signaux

**Erreur type**: ALL_3SOLDIERS — j'avais ajoute des checks d'overlap et de wick absents du backtest (corrige 2026-03-23)

---

## 7. TIMING: coherence horaire

- [ ] **1 trigger max par strat par jour** (trig dict reset a chaque nouveau jour)
- [ ] **Reset _triggered quotidien dans le live** (pas seulement au restart)
- [ ] **Filtres horaires identiques** backtest ↔ live (PO3_SWEEP: 7h-9h, etc.)
- [ ] **UTC partout** — pas de confusion de timezone

**Erreur type**: _triggered jamais reset dans live_paper → aucun signal apres jour 1 (corrige 2026-03-23)

---

## 8. OPTIMISATION: pas d'overfitting

- [ ] **Split test**: premiere moitie ET deuxieme moitie doivent etre rentables
- [ ] **PF >= 1.1 minimum** apres spread
- [ ] **n >= 20 trades minimum** par strat
- [ ] **Configs optimisees avec la BONNE logique d'exit** (pas avec des bugs)

**Erreur type**: configs TPSL optimisees avec TP sur close (bug) — resultats surestimes (identifie 2026-03-23)

---

## Historique des corrections

| Date | Bug | Impact | Fichiers |
|---|---|---|---|
| 2026-03-21 | Trailing sur HIGH au lieu de CLOSE | PF gonfle | strats.py, tous les live |
| 2026-03-21 | Re-check low/high vs nouveau stop apres trailing | Incoherence temporelle | strats.py |
| 2026-03-22 | NY_DAYMOM: close de bougie non fermee | Look-ahead signal | strats.py |
| 2026-03-22 | Entry candle SL skip pour open strats | SL non verifie sur bougie d'entree | strats.py |
| 2026-03-22 | Timeout MX=12 retire | Artificiel, trailing suffit | strats.py |
| 2026-03-23 | Parabolic SAR ≠ Supertrend dans backtest | Indicateur different = signaux differents | strats.py |
| 2026-03-23 | ALL_3SOLDIERS conditions trop strictes | Moins de signaux que backtest | strats.py |
| 2026-03-23 | ALL_FIB_618 SHORT non teste | Direction non validee | strats.py |
| 2026-03-23 | _triggered jamais reset dans live | 0 signaux apres jour 1 | live_paper_icmarkets.py |
| 2026-03-23 | TPSL TP sur CLOSE au lieu de HIGH/LOW | PF surestime (+20%), exit au close > target | strats.py |

---

## Comment utiliser cette checklist

1. **Nouveau script/strat**: parcourir TOUS les points avant de valider
2. **Modification d'exit**: re-verifier sections 2 et 8
3. **Ajout d'indicateur**: re-verifier section 3
4. **Ajout de strat**: re-verifier sections 1, 5, 6 et lancer audit_signals.py
5. **Avant mise en live**: TOUT re-verifier
