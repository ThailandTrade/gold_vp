# Catalogue des stratégies 15m — laboratoire cleanup-v2

**Mis a jour:** 2026-04-17 (Phase 1 du lab)

Catalogue structure de strategies candidates pour le timeframe 15m sur FTMO (XAUUSD, indices) et extensibles a 5ers / ICM / crypto.

Priorites:
- **P1** = a tester en premier (evidence empirique solide, pas implementee)
- **P2** = a tester apres P1 (evidence probable)
- **P3** = speculative / a considerer plus tard
- **DONE** = deja implementee

## Methodologie

Tout candidat doit passer:
1. Implementation dans `detect_all()` de `strats.py`
2. Optimize grid exits (TPSL + TRAIL)
3. Walk-forward OOS (6m IS / 1m OOS / 7 fenetres) + median PF_OOS >= 1.20 + pct profitable >= 70%
4. Double validation PF 6m et 12m >= 1.20
5. Bootstrap portefeuille (au niveau instrument) - contribution positive au CI95 lower

## Familles

### A. Trend Following

| Code | Description | Params | Status | Priorite |
|---|---|---|---|---|
| MACD_RSI | MACD(8,17,9) cross + RSI(14) > 50 | - | DONE | - |
| MACD_HIST | MACD histogram reversal | - | DONE | - |
| EMA_{513,821,921} | EMA crossovers | - | DONE | - |
| HMA_CROSS | HMA(9,21) cross | - | DONE | - |
| SUPERTREND | Supertrend direction change | - | DONE | - |
| ICHI_TK | Ichimoku Tenkan/Kijun cross | - | DONE | - |
| PSAR_EMA | Parabolic SAR + EMA20 filter | - | DONE | - |
| ADX_FAST | ADX(7) + EMA21 + DI cross | - | DONE | - |
| **KAMA_CROSS** | KAMA (Kaufman Adaptive MA) cross price/EMA | fast=2, slow=30, er=10 | NEW | **P1** |
| **TEMA_DEMA** | Triple vs Double Exp Moving Avg cross | periods 10,21 | NEW | P2 |
| **ALLIGATOR** | Williams Alligator 3 MAs (smoothed+offset) | 13/5, 8/3, 5/2 | NEW | P3 |
| **COPPOCK** | Coppock Curve zero cross (classic momentum) | 10mo, 14mo, 11mo | NEW | P3 |
| **TRIX_FAST** | TRIX(9) signal cross (faster than TRIX(15)) | - | NEW | P2 |

### B. Mean Reversion

| Code | Description | Params | Status | Priorite |
|---|---|---|---|---|
| BB_REV | Bollinger Band reversal | 20, 2 | DONE | - |
| RSI_EXTREME | RSI < 20 or > 80 | 14 | DONE | - |
| CMO_{9,14} | Chande Momentum Oscillator reversal | - | DONE | - |
| WILLR_{7,14} | Williams %R reversal | - | DONE | - |
| STOCH_OB | Stochastic overbought/oversold | 14,3,3 | DONE | - |
| **ZSCORE_MR** | Z-score > |2| mean reversion | lookback=20 | NEW | **P1** |
| **CONNORS_RSI2** | RSI(2) < 10 buy / > 90 sell (Larry Connors) | - | NEW | **P1** |
| **VWAP_DEV** | Price > VWAP + 2 SD -> fade short | session VWAP | NEW | **P1** |
| **KELTNER_MR** | Fade at KC bands (opposite of KC_BRK) | 20,1.5 | NEW | P2 |
| **BB_EXTREME_REV** | BB 3SD reversal with RSI confirmation | 20,3 | NEW | P2 |

### C. Breakout / Range

| Code | Description | Params | Status | Priorite |
|---|---|---|---|---|
| KC_BRK | Keltner channel breakout | 20,1.5 | DONE | - |
| BB_TIGHT | Tight Bollinger breakout | 10,1.5 | DONE | - |
| BB_SQUEEZE | BB width at 20-bar min | - | DONE | - |
| KB_SQUEEZE | BB inside KC squeeze | - | DONE | - |
| DC_{10,50} | Donchian breakout | - | DONE | - |
| MTF_BRK | Multi-timeframe 1H breakout | 12 bars | DONE | - |
| NR4 | Narrow range 4 breakout | - | DONE | - |
| INSIDE_BRK | Inside bar breakout | - | DONE | - |
| **TTM_SQUEEZE** | TTM squeeze (BB + KC with momentum) | - | NEW | **P1** |
| **DONCHIAN_CONTRACTION** | Donchian narrowing then expand | 10 | NEW | P2 |
| **RANGE_EXPANSION** | Today ATR > 1.5x yesterday ATR | - | NEW | P2 |
| **ORB_PREMARKET** | First 15m of London session breakout | - | NEW | **P1** |

### D. Multi-Timeframe (MTF)

| Code | Description | Params | Status | Priorite |
|---|---|---|---|---|
| MTF_BRK | 1H rolling breakout | 12 bars = 1H | DONE | - |
| **MTF_TREND_PB** | 1H trend + 15m pullback entry | EMA21 1H + RSI<40 on 15m | NEW | **P1** |
| **MTF_DAILY_BIAS** | Daily close direction + 15m trigger | - | NEW | **P1** |
| **TRIPLE_TF** | 4H + 1H + 15m alignment | - | NEW | P2 |

### E. Volatility / Regime

| Code | Description | Params | Status | Priorite |
|---|---|---|---|---|
| **HURST_TREND** | Hurst > 0.6 = trend regime, trade only trend strats | lookback=100 | NEW | **P1** |
| **HURST_MR** | Hurst < 0.4 = mean-revert regime, trade only MR strats | - | NEW | **P1** |
| **CHOPPINESS** | Choppiness Index filter | 14 | NEW | P2 |
| **ATR_REGIME** | ATR today / ATR 20-day average - filter vol spikes | - | NEW | P2 |

### F. Session / Time of Day

| Code | Description | Params | Status | Priorite |
|---|---|---|---|---|
| TOK_*, LON_*, NY_* | Session-filtered patterns | - | DONE | - |
| LON_KZ, LON_BIGGAP, etc | | - | DONE | - |
| **LONDON_FIX** | 16:00 GMT London fix behavior | - | NEW | P2 |
| **NY_OPEN_REVERSAL** | Reversal 30min after 14:30 UTC open (mentioned academic: 10am high/low) | - | NEW | **P1** |
| **MIDDAY_FADE** | 11:00-14:00 UTC: fade moves (low vol period) | - | NEW | P2 |

### G. Structure / Pivots / S-R

| Code | Description | Params | Status | Priorite |
|---|---|---|---|---|
| PIVOT_BOUNCE / BRK | Daily pivot (HLC/3) + S1/R1 | - | DONE | - |
| IDX_PREV_HL | Previous day HL breakout | - | DONE | - |
| **CAMARILLA** | Camarilla H3/L3 pivots (tighter than classic) | - | NEW | P2 |
| **FIB_PIVOTS** | Fibonacci pivot levels | 0.382, 0.618 | NEW | P2 |
| **WEEKLY_HL** | Previous week high/low breakout | - | NEW | **P1** |
| **PRIOR_SWING** | Break of 20-bar swing high/low | - | NEW | P2 |

### H. Gap-based

| Code | Description | Params | Status | Priorite |
|---|---|---|---|---|
| IDX_GAP_FILL, IDX_GAP_CONT | Gap fill / continuation | - | DONE | - |
| LON_GAP, LON_BIGGAP, NY_GAP | Session gaps | - | DONE | - |
| EXH_GAP | Exhaustion gap fade | 0.5 ATR | DONE | - |
| **WEEKEND_GAP_FADE** | Lundi gap > N ATR -> fade (historique 61% fill) | - | NEW | **P1** |
| **GAP_MIDDLE** | Entry at mid-gap during fill | - | NEW | P3 |

### I. Candlestick / Price Action

| Code | Description | Params | Status | Priorite |
|---|---|---|---|---|
| ENGULF, HAMMER, MSTAR, DOJI_REV | Classics | - | DONE | - |
| 3SOLDIERS | Three white soldiers/black crows | - | DONE | - |
| CONSEC_REV | 5-bar exhaustion reversal | - | DONE | - |
| PIN_BAR | Pin bar at key level | - | DONE | - |
| **OUTSIDE_BAR** | Outside bar (fully engulfing prior range) with body > 0.5 ATR | - | NEW | P2 |
| **MOTHER_BAR** | Inside bar within large mother bar | - | NEW | P3 |
| **PIN_AT_PIVOT** | Pin bar + daily pivot level confluence | - | NEW | P2 |

### J. VWAP variants

| Code | Description | Params | Status | Priorite |
|---|---|---|---|---|
| IDX_VWAP_BOUNCE | Price bounces off VWAP | - | DONE | - |
| AVWAP_RECLAIM | Anchored VWAP from swing reclaim | - | DONE | - |
| **VWAP_1SD** | VWAP +/- 1 SD as S/R | - | NEW | **P1** |
| **AVWAP_WEEK** | Anchored VWAP from weekly open | - | NEW | P2 |
| **AVWAP_SESSION** | Anchored VWAP per session (Tokyo/London/NY) | - | NEW | P2 |

### K. ML/Features (speculatif, priorite P3)

Pas prioritaire tant qu'on n'a pas exploite les strats plus simples. Mais prevoir:
- Random Forest sur 40+ features (EMA, RSI, ATR, bb width, etc.) predict next N-bar return
- Feature importance pour decouvrir nouvelles strats
- Regime detection supervise (HMM light)

### L. Confluences (Phase 4 future)

- **Trend filter + mean reversion entry**: EMA50 up + RSI<30 bounce = long
- **MTF alignment**: signaux 15m seulement si 1H + 4H concordent
- **Session + structure**: London breakout seulement si casse pivot daily
- **Hurst + strat type**: Hurst > 0.6 -> trend strats only, < 0.4 -> MR only

## Priorite immediate

**P1 strats (10 candidates a implementer d'abord):**
1. KAMA_CROSS
2. ZSCORE_MR
3. CONNORS_RSI2
4. VWAP_DEV
5. TTM_SQUEEZE
6. ORB_PREMARKET (London 08:00-08:15 UTC breakout)
7. MTF_TREND_PB
8. MTF_DAILY_BIAS
9. HURST_TREND / HURST_MR (en fait 1 filtre)
10. WEEKEND_GAP_FADE

+ **NY_OPEN_REVERSAL** (mention academique: 10am reversal frequent)
+ **WEEKLY_HL** (prev week high/low breakout)

Total: 10-12 nouvelles strats solides a tester.

## Sources principales

- [QuantifiedStrategies](https://www.quantifiedstrategies.com/) - backtests nombreux avec regles explicites
- [SSRN papers](https://papers.ssrn.com/) - recherche academique (Zarattini 2024 ORB, Aronson evidence-based)
- [Evidence-Based TA (Aronson)](https://www.evidencebasedta.com/) - methodologie statistique rigoureuse
- [Edgeful](https://www.edgeful.com/blog/) - statistiques intraday
- [CrackingMarkets](https://www.crackingmarkets.com/) - edges intraday
- [RobotWealth](https://robotwealth.com/) - quant systematique

## Notes

- **ICT / Smart Money Concepts: exclus** (user consider bullshit marketing).
- **Volume-based**: limite sur FX (pas de vrai volume). Sur indices CFD, le tick volume MT5 est une approximation - usable mais moins fiable que futures.
- **Backtests publics**: a prendre avec pincettes, tous optimises et biaises. Notre WF + bootstrap les ejecte vite si c'est juste du marketing.
