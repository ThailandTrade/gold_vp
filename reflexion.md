# Réflexion stratégique : refonte du système vers du 4h swing trading

> Document de travail pour Claude Code.
> Contexte : système systématique multi-asset/multi-strat actuellement basé sur ~82 stratégies pensées pour du day trading / scalping (15m-1h). Constat empirique : OOS catastrophique en 5 ans IS / 1 an OOS, dégradation -25 à -60% du capital. Hypothèse principale : **mismatch fondamental entre la nature scalping des stratégies et le TF 4h** sur lequel on tente de les déployer.

---

## 1. Diagnostic complet du système actuel

### 1.1 Forces

- **Méthodologie de sélection rigoureuse** (filtres conjoints : h1>0 ET h2>0, M+ 7/12, outlier_share, PF, n minimum)
- **Architecture multi-dimensionnelle** : 17 symboles × 2 TF × ~80 strats × 3 grilles d'exit
- **Infrastructure technique solide** : PostgreSQL pour tick data, Python pour scan/backtest
- **Données long historique acquises** : 17-18 ans sur FX majors et XAUUSD, 6-10 ans sur indices, 7-8 ans sur crypto
- **Cost réaliste intégré** : passage de 0.01R à 0.05R par trade
- **Re-calibrage adaptatif** validé (V3 >> V2 sur OOS Mai 2026)

### 1.2 Faiblesses critiques

**A. Mismatch fondamental TF/Stratégies**

L'inventaire actuel de 82 stratégies se décompose en :

| Catégorie | Nombre | Compatibilité 4h |
|---|---|---|
| Trend / breakout structurel (universel) | ~26 | Élevée |
| Oscillators court / scalping mean reversion | ~28 | Faible |
| Session-specific (TOK_*, IDX_* intraday) | ~13 | Nulle |
| Concepts ICT/SMC intraday (FVG, PO3, EXH_GAP) | ~3 | Nulle |
| Reste (marginal) | ~12 | Variable |

Concrètement, **~50% des stratégies sont structurellement inadaptées au 4h** :
- Les `TOK_*` supposent une session de cotation séparable, concept détruit en 4h
- Les `IDX_*` intraday (ORB30, NY_MOM, VWAP_BOUNCE, GAP_CONT, LATE_REV, TREND_DAY) sont par essence intraday
- Les oscillators périodes courtes (WILLR_7, STOCH_OB, CCI_*, RSI_EXTREME) sont conçus pour des extrêmes scalping
- Les concepts FVG, PO3, EXH_GAP sont des structures intraday ICT

**B. Sample size par paire en 4h**

Avec ~1,500 bougies 4h par an et 1 trade tous les 10-20 bougies :
- 75-150 trades par paire (sym, strat) par an
- En 17 ans : 1,275-2,550 trades par paire → statistiquement robuste
- Seuil `n ≥ 100` reste largement atteignable, on peut même durcir à `n ≥ 300`

**C. Logique de signal contre-productive en 4h**

Une stratégie scalping cherche typiquement à :
1. Détecter une micro-déviation
2. Anticiper un retour rapide
3. Sortir vite avec petit gain

Sur 4h, cette logique :
1. Capture des "déviations" qui sont en fait des bougies de continuation
2. Anticipe à contresens des tendances qui s'installent
3. Sort trop tôt sur des mouvements qui font des centaines de pips

**D. OOS sur 5 ans IS / 1 an OOS dégrade fortement**

Le test rigoureux (5 ans IS / 1 an OOS rolling) a probablement révélé que la majorité des stratégies actuelles **n'ont pas d'edge en 4h** au-delà de la chance statistique de l'historique court précédent.

---

## 2. Pourquoi le 4h reste le bon choix

Avant de tout casser, rappelons pourquoi le 4h est le TF cible :

1. **Robustesse aux régimes** : filtrage du bruit news-driven, moins de whipsaw
2. **Coûts proportionnels** : spread/SL ratio 3-5× meilleur qu'en 15m
3. **Slippage news** divisé par 4-6 vs 15m
4. **Commission cumulée** divisée par 4 (moins de trades total)
5. **Sample par paire** : suffisant avec 7-18 ans d'historique
6. **Documenté académiquement** : <quote>"le choix de l'échelle temporelle pour le calcul de la tendance est primordial, les stratégies doivent s'aligner avec les caractéristiques de retour de l'actif. La méthodologie importe moins que la sélection de l'horizon temporel approprié" (Shi & Lian 2025)</quote>

Le 4h est **structurellement adapté au swing trading**, qui est **bien documenté** comme exploitable avec des edges réels (time-series momentum, breakout structurel, cross-sectional momentum, carry).

Le problème n'est pas le TF. **Le problème, c'est notre arsenal.**

---

## 3. Sources théoriques solides pour les nouvelles stratégies

### 3.1 Carver — Advanced Futures Trading Strategies (2022)

Ouvrage de référence. 30 stratégies fully tested sur 50 ans de données, plus de 100 instruments. Carver a passé une décennie chez AHL (hedge fund Man Group, $25B+). Ses recommandations principales :

**Familles validées académiquement** :
1. **Trend following** (multi-speed : slow, medium, fast)
2. **Carry** (différentiel de taux / contango/backwardation)
3. **Breakout** (rupture de range/canal)
4. **Cross-sectional momentum** (ranking d'assets par momentum)
5. **Skew** (asymétrie de distribution)
6. **Acceleration** (dérivée seconde du prix)
7. **Mean reversion** (uniquement en intraday court, ou cross-sectional sur stocks)
8. **Value** (déviation par rapport à un fondamental long-terme)

**Principes structurants** :
- Combiner plusieurs vitesses de la même famille (slow + medium + fast trend)
- Volatility targeting par instrument (taille adaptée à l'ATR)
- Position size = f(signal_strength × inverse_volatility × correlation_adjustment)
- "Quality over quantity" : 10 stratégies robustes > 80 marginales
- Sharpe attendu en multi-strat diversifié : 0.7-1.2 net

### 3.2 AQR — Time Series Momentum (Moskowitz, Ooi, Pedersen 2012)

Papier fondateur. Time-series momentum (TSMOM) sur 58 instruments futures sur 25 ans :
- Returns positifs sur 1, 3, 6, 12 mois lookback à travers TOUS les assets testés
- Sharpe ratios > 0.7 sur la majorité des combinaisons
- Convexité positive : performance forte en crises (crisis alpha)

**Implémentation** : `signal = sign(return_lookback) × scale(volatility_lookback)`

### 3.3 Donchian / Turtle Trading

Stratégie historique sur N-day breakout :
- Entry sur cassure du High/Low des N derniers jours (typiquement 20-55 jours)
- Exit sur cassure inverse du High/Low des M derniers jours (M < N)
- Validée sur des décennies de données futures
- Simplicité extrême, robustesse remarquable

### 3.4 Carry strategies (FX, Futures)

- En FX : long currencies à haut taux, short à bas taux
- En futures : long contango / short backwardation (ou inverse selon design)
- Sharpe historique 0.4-0.6 standalone
- Décorrélé avec trend → diversification précieuse

### 3.5 Cross-sectional momentum

Au lieu de tester chaque asset isolément :
- Ranker tous les assets de l'univers par momentum
- Long top quintile, short bottom quintile
- Rééquilibrage périodique
- Documenté depuis Jegadeesh & Titman (1993) en equities, étendu aux autres assets

---

## 4. Inventaire des nouvelles stratégies à développer

### 4.1 Principe directeur

**Chaque stratégie doit avoir une thèse économique claire**. Pas de "ALL_INDICATOR_X_PERIOD_Y" sans rationale. Si on ne peut pas expliquer pourquoi l'inefficience existe et persiste, c'est qu'on ne l'a pas vraiment trouvée.

### 4.2 Catégorie A : Trend following structurel (10 stratégies à développer)

**A1 — Donchian Breakout N=20**
- Cassure du High/Low des 20 dernières bougies 4h (= 5 jours)
- Stop : cassure inverse N=10
- Thèse : trends de moyen terme, capture les ruptures de range

**A2 — Donchian Breakout N=55**
- Cassure du High/Low des 55 dernières bougies 4h (= 14 jours)
- Stop : cassure inverse N=20
- Thèse : trends de long terme, Turtle Trading classique adapté 4h

**A3 — EMA 20/50 Cross with ADX confirmation**
- Cross EMA 20 au-dessus de EMA 50 + ADX > 25
- Direction confirmée par EMA 200 sur TF supérieur (daily)
- Thèse : trend filter classique, robuste multi-asset

**A4 — EMA 50/200 Golden/Death Cross (avec retest)**
- Cross majeur + attendre retest de la moyenne mobile cross
- Entry sur reprise dans le sens de la tendance
- Thèse : capture des cycles macro, signal lent mais puissant

**A5 — Time-Series Momentum (TSMOM) 3M**
- `sign(close - close_60_periods_ago)`
- Re-évaluer chaque bougie, repondérer
- Thèse : AQR papier fondateur, validé sur 25 ans/58 assets

**A6 — Time-Series Momentum (TSMOM) 6M**
- Version plus lente du TSMOM
- Capture des trends macro plus long terme
- Décorrélée du TSMOM 3M sur de courtes périodes

**A7 — Multi-Speed Trend (combo)**
- Combinaison pondérée de TSMOM 1M + 3M + 6M
- Position size = somme des signaux normalisés
- Thèse Carver : diversification de vitesse

**A8 — Triple MA alignment (8/21/55)**
- Signal long si EMA 8 > EMA 21 > EMA 55 ET prix > EMA 8
- Signal short inverse
- Stop : prix sous EMA 21
- Thèse : alignement de tendance robuste, peu de faux signaux

**A9 — Slope of Linear Regression 50**
- Régression linéaire sur 50 bougies, signal = signe de la pente
- Magnitude pondérée par R² (qualité du fit)
- Thèse : mesure objective de la tendance

**A10 — Adaptive Trend (Kaufman AMA / KAMA)**
- Moyenne mobile adaptative à la volatilité
- Plus lente en marché ranging, plus rapide en trend
- Signal sur cross de la KAMA
- Thèse : auto-ajustement au régime

### 4.3 Catégorie B : Breakout structurel (8 stratégies)

**B1 — Weekly High/Low Breakout**
- Cassure du High/Low de la semaine précédente
- TP = mesure de la range hebdo précédente
- Stop : retour dans la range
- Thèse : niveaux psychologiques majeurs, breakout sur volume institutionnel

**B2 — Monthly High/Low Breakout**
- Idem mais sur le mois précédent
- Très puissant en 4h car peu de touches
- Thèse : niveaux macro, capture des moves de fond

**B3 — N-Day Consolidation Breakout**
- Détection de range < 1 ATR sur 5-10 jours consécutifs
- Entry sur cassure haute/basse avec confirmation 1 bougie
- Stop : retour dans le milieu de la consolidation
- Thèse : énergie accumulée se libère

**B4 — Triangle / Wedge Breakout**
- Détection algorithmique de triangles (highs descendants, lows montants ou inverse)
- Cassure de la trendline
- Thèse : pattern technique chartiste validé

**B5 — Bollinger Squeeze Breakout (lent)**
- Bandes de Bollinger 50 périodes très resserrées (BB width < 25e percentile)
- Breakout d'une des bandes
- Thèse : compression de volatilité → expansion explosive

**B6 — Keltner Channel Breakout 50**
- Cassure du Keltner Channel 50/2 ATR
- Différent du Bollinger : basé sur ATR, plus stable
- Thèse : breakout volatility-adjusted

**B7 — Failed Breakout Reversal**
- Cassure d'un niveau majeur SUIVI d'un retour brutal dans la range
- Signal contre la cassure
- Thèse : faux signaux des participants peu informés, fade institutionnel

**B8 — Asian Session Range Break (24h)**
- Range de la session asiatique (12-16h locale par exemple)
- Cassure pendant les sessions London/NY
- Adapté au 4h en regroupant 2 bougies asiatiques
- Thèse : la session calme définit les bornes du marché

### 4.4 Catégorie C : Pullback en tendance établie (5 stratégies)

**C1 — Pullback to 20 EMA in established trend**
- Tendance majeure définie par 50 EMA > 200 EMA (ou inverse)
- Entry sur retest de 20 EMA dans le sens de la tendance
- Confirmation : bougie de rejet (pin bar, engulfing)
- Thèse : continuation de trend sur retracement technique

**C2 — Fibonacci 38-50-61% Retracement Entry**
- Identification automatique du dernier swing significatif (> 2 ATR)
- Entry sur retracement vers 38%, 50% ou 61.8%
- Thèse : niveaux de retracement statistiquement significatifs

**C3 — 3-Bar Pullback in Strong Trend**
- Trend défini par ADX > 30
- 3 bougies consécutives contre-tendance
- Entry à la 4ème bougie dans le sens du trend
- Stop : sous le low/high des 3 bougies
- Thèse : profit-taking court terme dans un trend qui reprendra

**C4 — Pullback to Previous Resistance turned Support (or inverse)**
- Détection de niveaux cassés au moins 1 jour avant
- Entry sur retest et rejet
- Thèse : niveaux structurels gardent leur mémoire

**C5 — Anchored VWAP (Daily) Reclaim**
- VWAP ancré sur l'open de la journée
- Cassure puis retour sous/sur le VWAP daily
- Thèse : prix de référence institutionnel, mean-reversion intra-trend

### 4.5 Catégorie D : Reversal sur niveau majeur (5 stratégies)

**D1 — Double Top / Double Bottom (20+ bougies)**
- Détection algorithmique de patterns double top/bottom
- Confirmation par cassure du neckline
- Thèse : pattern technique classique, reversal puissant

**D2 — Triple Top / Triple Bottom**
- Variante 3 touches, signal plus fort
- Thèse : zone fortement défendue par les participants

**D3 — Engulfing on Major S/R (weekly)**
- Engulfing pattern AU TOUCH d'un High/Low hebdomadaire
- Thèse : confluence price action + niveau structurel

**D4 — Pin Bar on Major Level**
- Pin bar / hammer / shooting star sur niveau majeur (R/S, EMA 200, Fibo)
- Thèse : rejection visible, smart money en action

**D5 — Divergence RSI (4h) on Major Level**
- Divergence RSI ENTRE le prix et l'indicateur
- Sur un niveau majeur (R/S, BB extreme)
- Thèse : exhaustion de momentum, reversal probable

### 4.6 Catégorie E : Cross-sectional & meta (5 stratégies)

**E1 — Cross-Sectional Momentum (CSMOM) on FX**
- Ranking de toutes les paires forex par momentum 3M
- Long top 3, short bottom 3
- Rééquilibrage hebdomadaire
- Thèse : Jegadeesh-Titman étendu au FX

**E2 — Cross-Sectional Momentum sur Indices**
- Idem sur les indices mondiaux
- Long les leaders, short les laggards
- Thèse : rotation sectorielle/géographique

**E3 — Currency Carry (FX)**
- Long currencies à haut taux interbancaire, short à bas taux
- Inclusion d'un filtre de volatilité (skip si VIX > 30)
- Thèse : carry trade classique, validé académiquement

**E4 — Volatility Regime Filter (overlay)**
- Mesure de l'ATR multi-asset sur 20 jours
- Si > percentile 80 historique → réduire exposition à 50%
- Si < percentile 20 → exposition normale
- Thèse : éviter les régimes hostiles, validé empiriquement

**E5 — Skew-Based Position Sizing**
- Mesure du skew des returns récents par asset
- Augmenter size sur positive skew (trend-friendly)
- Réduire size sur negative skew (mean-reversion likely)
- Thèse : Carver, exploitation de l'asymétrie des distributions

### 4.7 Catégorie F : Patterns swing (4 stratégies)

**F1 — Flag / Pennant Breakout**
- Détection algorithmique d'impulsion suivie de consolidation
- Cassure dans le sens de l'impulsion
- Thèse : pattern continuation classique

**F2 — Cup and Handle**
- Pattern technique en U + petite consolidation à droite
- Breakout de la résistance horizontale
- Thèse : classique CANSLIM (William O'Neil), validé sur stocks et étendu aux autres assets

**F3 — Head and Shoulders / Inverse H&S**
- Reversal pattern majeur sur 30-50 bougies
- Entry sur cassure du neckline
- TP = hauteur de la tête projetée
- Thèse : pattern reversal le plus connu, statistiquement validé

**F4 — Symmetrical Triangle**
- Convergence highs descendants + lows montants
- Entry sur cassure d'un côté avec volume
- Thèse : indécision suivie de résolution

### 4.8 Catégorie G : Adaptation au régime (3 stratégies + overlays)

**G1 — VIX-Based Position Sizing Overlay**
- VIX < 20 : exposition normale
- VIX 20-30 : exposition 70%
- VIX > 30 : exposition 40% + désactivation des MR
- Pour les forex/commodities : utiliser un VIX-équivalent (ATR multi-asset normalisé)

**G2 — Correlation-Based Diversification**
- Calcul matrice de corrélation 20-jour rolling
- Si corrélation moyenne portfolio > 0.6 → réduire taille positions
- Thèse : protection contre l'effondrement de la diversification en stress

**G3 — Regime Detection (Trend vs Range)**
- ADX > 30 : régime trend → activer les stratégies trend
- ADX < 20 : régime range → activer les stratégies reversal
- Désactivation conditionnelle des familles inadaptées

---

## 5. Stratégies de l'arsenal actuel à conserver

Sur les 82 stratégies actuelles, **certaines restent valables en 4h** :

### À conserver tel quel (probablement ~20)

**Trend following universel** :
- ALL_ADX_FAST, ALL_ADX_RSI50
- ALL_EMA_513, ALL_EMA_821, ALL_EMA_921
- ALL_HMA_CROSS
- ALL_MACD_ADX, ALL_MACD_STD_SIG
- ALL_SUPERTREND
- ALL_TRIX
- ALL_PSAR_EMA
- ALL_ICHI_TK (Ichimoku conçu à l'origine pour daily)

**Breakout structurel** :
- ALL_DC10, ALL_DC50 (Donchian, à compléter avec DC20, DC55 manquants)
- ALL_LR_BREAK
- ALL_MTF_BRK
- ALL_KB_SQUEEZE
- ALL_BB_TIGHT
- ALL_INSIDE_BRK
- ALL_KC_BRK

**Price action significatif en 4h** :
- ALL_3SOLDIERS
- ALL_ENGULF
- ALL_HAMMER
- ALL_MSTAR
- ALL_DOJI_REV

**Reversal valides** :
- ALL_CONSEC_REV (5 bougies = 20h, significatif)
- ALL_DPO_14
- ALL_AROON_CROSS

### À retirer impérativement (28 stratégies)

**Tokyo session** (concept incompatible 4h) :
- TOK_2BAR, TOK_BIG, TOK_FISHER, TOK_NR4, TOK_STOCH, TOK_TRIX, TOK_WILLR

**Index intraday-specific** :
- IDX_NY_MOM, IDX_ORB30, IDX_VWAP_BOUNCE, IDX_GAP_CONT, IDX_LATE_REV, IDX_TREND_DAY, IDX_3SOLDIERS, IDX_CONSEC_REV

**Concepts intraday ICT/SMC** :
- ALL_FVG_BULL, PO3_SWEEP, EXH_GAP

**Oscillators scalping (périodes trop courtes pour 4h)** :
- ALL_WILLR_7
- ALL_STOCH_OB, ALL_STOCH_PIVOT
- ALL_RSI_EXTREME
- ALL_CCI_100, ALL_CCI_14_ZERO
- ALL_MOM_10
- ALL_CMO_9

### À tester en B (laisser les filtres trancher)

Les autres (~24 stratégies) : oscillators medium, pivots daily, etc. Garder dans le scan mais sans illusion.

---

## 6. Architecture cible

### 6.1 Sélection finale visée

| Famille | N strats | Source |
|---|---|---|
| Trend following classique | 15-20 | 10 nouvelles + 10 existantes |
| Breakout structurel | 10-12 | 8 nouvelles + 4 existantes |
| Pullback en tendance | 5 | Toutes nouvelles |
| Reversal sur niveau | 5 | Toutes nouvelles |
| Cross-sectional & meta | 5 | Toutes nouvelles |
| Patterns swing | 4 | Toutes nouvelles |
| Price action existante | 5 | Existantes |
| **TOTAL** | **~50-55** | dont **~35 nouvelles** |

C'est un **passage de 82 à ~50 stratégies**, mais avec un **taux de pertinence 4h** beaucoup plus élevé.

### 6.2 Sélection attendue après filtres

Avec 17 ans de données et filtres durcis :
- 17 symboles × ~50 strats = 850 paires (sym, strat)
- Taux de survie attendu après filtres : 5-15%
- **~50-120 instances retenues**

C'est beaucoup plus que les 20 actuelles. La sélection finale pourra être affinée par :
- Poids par classe d'actif (max 30% par classe)
- Diversification de styles (max 40% trend, etc.)
- Décorrélation effective (matrice de corrélation des PnL)

### 6.3 Filtres recommandés pour 4h avec long historique

| Filtre | Valeur actuelle | Valeur recommandée 4h |
|---|---|---|
| n minimum | 100 | **300** |
| h1>0 ET h2>0 | 2 moitiés | **3 tiers chronologiques >0** |
| M+ minimum | 7/12 | **70% des mois positifs sur l'IS complet** |
| PF | ≥1.10 | **≥1.25** |
| outlier_share | <30% | **<25%** |
| Sharpe mensuel | non filtré | **≥0.8** |
| Cost par trade | 0.05R | **0.03-0.04R** (cost relatif plus bas en 4h) |

---

## 7. Plan de déploiement pour Claude Code

### Phase 1 : Nettoyage de l'inventaire (1-2 jours)

1. **Retirer explicitement** les 28 stratégies inadaptées 4h listées en section 5
2. **Garder** les 20 stratégies "trend/breakout/price-action" universelles
3. **Garder en zone grise** les 24 stratégies marginales
4. Documenter les retraits avec justification dans le code

### Phase 2 : Implémentation des nouvelles stratégies (3-6 semaines)

Ordre de priorité :

**Sprint 1 (1 semaine) — Trend following nouveau**
- A1-A2 : Donchian 20 et 55 (Turtle adapté 4h)
- A3-A4 : EMA cross avec ADX/MA filter
- A5-A6 : TSMOM 3M et 6M
- A8 : Triple MA alignment 8/21/55

**Sprint 2 (1 semaine) — Breakout structurel**
- B1-B2 : Weekly et Monthly H/L breakout
- B3 : N-Day Consolidation Breakout
- B5-B6 : BB Squeeze 50 et Keltner Channel 50
- B7 : Failed Breakout Reversal

**Sprint 3 (1 semaine) — Pullback & Reversal**
- C1-C2 : Pullback to 20 EMA et Fibo retracement
- C3 : 3-Bar Pullback
- D1-D2 : Double et Triple top/bottom
- D3-D4 : Engulfing/Pin sur niveau majeur

**Sprint 4 (1 semaine) — Cross-sectional & patterns**
- E1-E2 : CSMOM FX et indices
- F1-F3 : Flag, Cup&Handle, H&S
- A9-A10 : LR slope, KAMA

**Sprint 5 (1-2 semaines) — Overlays & meta**
- E4 : Volatility Regime Filter
- G1 : VIX-based position sizing
- G2 : Correlation-based diversification
- G3 : Regime Detection (ADX-based)

### Phase 3 : Validation rigoureuse (2-3 semaines)

**Étape A — Scan complet 4h avec nouvel arsenal**
- IS jusque fin 2024, OOS 2025-mai 2026 (17 mois)
- Filtres durcis (section 6.3)
- Identifier les survivantes

**Étape B — Walk-forward rolling**
- IS 3 ans / OOS 1 an, shift 1 an
- Sur FX et gold (17 ans) : 13-14 OOS distincts
- Sur indices (8-10 ans) : 5-7 OOS distincts
- Sur crypto (7-8 ans) : 4-5 OOS distincts
- Calcul WFE (Walk Forward Efficiency) par segment, cible > 50%

**Étape C — Stress tests historiques nommés**
- 2008 crisis (sur FX, gold)
- 2015 SNB unpeg (CHF crisis)
- 2016 Brexit, Trump election
- 2018 Volmageddon + Q4 selloff
- 2020 covid crash
- 2022 inflation/Ukraine war
- 2023 banking crisis (SVB)
- 2025-2026 Iran war

Pour chaque période, mesurer :
- Drawdown maximum
- Recovery time
- Comportement par famille de stratégie

### Phase 4 : Production (1-2 semaines)

1. Sélection finale (50-100 instances)
2. Pondération par classe d'actif, style, corrélation
3. Documentation de chaque stratégie (thèse économique, paramètres, références)
4. Implémentation des overlays (volatility, correlation, regime)
5. Re-calibrage mensuel automatisé
6. Préparation pour forward live

### Phase 5 : Forward live (3-6 mois)

- Capital modeste ($5-10k) sur 2 brokers différents
- Logging exhaustif (slippage, delay, fills)
- Comparaison continue live vs backtest
- Re-calibrage mensuel automatique
- Décision de scaling après 3-6 mois de live conforme

---

## 8. Principes méthodologiques pour les nouvelles stratégies

### 8.1 Chaque stratégie doit avoir

1. **Une thèse économique claire** (pourquoi cette inefficience existe)
2. **Des paramètres justifiés** (pas de magic numbers, basés sur la littérature ou des défauts standards)
3. **Une logique testable** (entry, exit, stop bien définis)
4. **Une stabilité paramétrique** (marche aussi à ±20% des params optimaux)
5. **Une cohérence multi-instruments** (si elle marche sur EURUSD, devrait marcher partiellement sur GBPUSD)

### 8.2 Anti-patterns à éviter

- **Magic numbers spécifiques** (RSI 7 sur EURUSD 4h spécifiquement) → curve fitting
- **Logique intraday** appliquée à du swing
- **Pile de filtres** (5+ conditions conjointes) → overfitting
- **Période d'optimisation longue** (ex : moyenne mobile period entre 5 et 200) → overfitting paramétrique
- **Sélection a posteriori** (tester 80 combinaisons et garder la meilleure sans correction de multiple testing)

### 8.3 Diversification de styles attendue

Sharpe agrégé d'un portfolio multi-style typique (Carver) :
- Trend pur : 0.4-0.6
- Trend + Carry : 0.6-0.8
- Trend + Carry + Breakout : 0.8-1.0
- Multi-style complet (5+ familles) : 1.0-1.4

Cible pour notre système : **Sharpe ≥ 1.0** sur walk-forward OOS.

---

## 9. Métriques de validation

### 9.1 Métriques par instance

- Trades count ≥ 300 sur IS
- PF ≥ 1.25 sur IS
- WR cohérent avec le style (50-65% trend, 40-50% breakout, 55-70% MR)
- Sharpe mensuel ≥ 0.8
- M+ ≥ 70% sur IS
- DD max ≤ 15%
- WFE (OOS/IS Sharpe) ≥ 0.5

### 9.2 Métriques agrégées

- Sharpe portfolio mensuel ≥ 1.0 sur walk-forward
- DD max agrégé ≤ 20%
- 80%+ mois positifs sur walk-forward concaténé
- Aucune classe d'actif > 35% du PnL total
- Aucune famille de style > 45% du PnL total
- Corrélation moyenne entre instances < 0.4

### 9.3 Stress tests obligatoires

Performance acceptable sur AU MOINS 3 des 4 stress tests majeurs :
- 2008 crisis
- 2020 covid
- 2022 inflation
- 2025-2026 Iran war

"Acceptable" = OOS PnL > -15% du capital sur la période de crise.

---

## 10. Évolution de la source de données

### 10.1 Actuelle

- Données broker (Exness Standard)
- 17-18 ans FX/XAU acquis récemment
- Limitation : qualité variable, pas de référence externe

### 10.2 Recommandée

**Court terme** :
- Continuer avec les données acquises (suffisant pour validation initiale)
- Faire tourner le scan complet 4h avec long historique

**Moyen terme (1-3 mois)** :
- Acquérir une source unique de vérité : Dukascopy gratuit (forex) + FirstRateData payant (indices, crypto, futures)
- Coût estimé : $300-1500 one-time pour 20+ ans propre
- Refaire validation complète sur cette source

**Long terme** :
- Pipeline data centralisé PostgreSQL
- Backtest sur source neutre, live sur broker
- Comparer plusieurs brokers en exécution sur la même stratégie

---

## 11. Risques et inconnues

### 11.1 Risques principaux

**1. Les nouvelles stratégies n'ont pas d'edge supérieur aux anciennes**
- Probabilité : 30-40%
- Mitigation : large diversification de familles, plusieurs stratégies dans chaque famille validée académiquement
- Plan B : revenir aux stratégies existantes qui passent les filtres durcis

**2. Le 4h n'est pas le bon TF**
- Probabilité : 15-20%
- Mitigation : si 4h échoue, tester 8h, 12h ou daily
- Indicateur d'échec : si moins de 10 instances passent les filtres après scan complet

**3. L'historique acquis a des biais broker non détectés**
- Probabilité : 20-30%
- Mitigation : migrer vers source neutre (Dukascopy, FirstRateData)

**4. Overfitting subtil malgré les filtres**
- Probabilité : 25-35%
- Mitigation : stress tests historiques nommés, forward live obligatoire

### 11.2 Inconnues

- Combien de stratégies survivront les filtres durcis avec long historique
- Quelle proportion 4h vs daily est optimale
- Impact réel des overlays (volatility, correlation, regime) sur le live
- Performance sur instruments non testés (BTC sur le crash 2018 par exemple)

---

## 12. Action items pour Claude Code

### Tâches structurantes

- [ ] Nettoyer le scanner pour exclure les 28 stratégies inadaptées 4h
- [ ] Créer un module `strategies/swing/` pour les nouvelles stratégies 4h
- [ ] Documenter chaque nouvelle stratégie avec sa thèse économique
- [ ] Implémenter les 35 nouvelles stratégies en sprints de 1 semaine
- [ ] Adapter les filtres de sélection (`find_winners.py`) pour le contexte long historique
- [ ] Implémenter walk-forward rolling 3 ans IS / 1 an OOS
- [ ] Mettre en place les stress tests historiques nommés
- [ ] Implémenter les overlays (volatility, correlation, regime)
- [ ] Préparer un harness de forward live (paper trading)

### Considérations techniques

- Performance : avec 17 ans × 17 symboles × ~50 stratégies × 3 grilles d'exit, le scan complet peut prendre des heures. Paralléliser.
- Stockage : tick data sur 17 ans = volumes importants, optimiser les requêtes PostgreSQL (indexes sur timestamp)
- Versioning : tagger chaque scan avec date + paramètres pour reproductibilité
- Logging : enregistrer toute décision de sélection avec justification

---

## 13. Conclusion

Le système actuel a **deux problèmes structurels distincts** :

1. **Arsenal inadapté** : 50% des stratégies sont scalping/intraday, incompatibles avec le 4h
2. **Historique insuffisant** : précédemment 1 an, maintenant résolu avec 7-18 ans acquis

Le **problème #2 est résolu**. Reste le **problème #1** : refondre l'arsenal.

L'objectif n'est PAS de tout réécrire. L'objectif est de :
- **Garder** les ~20 stratégies universelles qui fonctionnent à tout TF
- **Retirer** les ~28 stratégies fondamentalement intraday
- **Développer** ~35 nouvelles stratégies pensées pour le swing 4h

Avec un arsenal de ~50 stratégies vraiment adaptées au 4h, sur 17 ans de données, on aura la **première vraie validation** du système. Les chiffres actuels du backtest ne reflètent que partiellement l'edge potentiel parce qu'ils sont calibrés sur un arsenal mal aligné avec le TF.

**L'investissement en temps** : 6-10 semaines pour Phase 2 + Phase 3.
**Le gain attendu** : passage d'un système OOS-instable (-25 à -60% sur 2 mois) à un système OOS-stable (drawdown contenu sous 15%, Sharpe ≥ 1.0 sur multi-régime).

C'est probablement le travail le plus important à faire avant tout déploiement live sérieux.

---

*Document de travail. Vivant. À itérer avec les résultats des sprints.*
