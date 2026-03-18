# CLAUDE.md — VP Swing Explorer (XAUUSD 5m)

## Portfolio actif : A+C+D+E+F+G+H+I+J (0.4%/trade)

| Metrique | Valeur |
|---|---|
| Rendement | +1,908.6% |
| Max DD | -5.3% |
| Calmar | 358.5 |
| PF | 1.94 |
| WR | 56% |
| Trades | 1561 (~5.0/jour) |
| Mois positifs | 13/13 |
| Tiers | 3/3 |
| Directions | Long + Short |

## Strategies (lettres = find_best_v4.py)

| Lettre | Nom | Description | Dir | PF | Session | Horaire |
|---|---|---|---|---|---|---|
| A | IB_tok_1h_UP | IB 0h-1h (12 bougies) break UP | Long | 1.35 | Tokyo | 1h-6h |
| C | FADE_tok_lon | Tokyo move >1ATR, inverse a London open | L+S | 1.42 | London | 8h |
| D | GAP_tok_lon | Gap Tokyo close vs London open >0.5ATR, continuation | L+S | 2.16 | London | 8h |
| E | KZ_lon_fade | London Kill Zone 8h-10h move >0.5ATR, fade a 10h | L+S | 2.00 | London | 10h |
| F | 2BAR_tok_rev | Two-bar reversal Tokyo (body >0.5ATR, 2eme > 1ere) | L+S | 1.73 | Tokyo | 0h-6h |
| G | NY1st_candle | 1ere bougie NY >0.3ATR, trader dans le meme sens | L+S | 2.22 | NY | 14h35 |
| H | TOKEND_3b | 3 dernieres bougies Tokyo >1ATR, continuation London | L+S | 2.26 | London | 8h |
| I | FADENY_1h | NY 1ere heure move >1ATR, inverse apres | L+S | 1.61 | NY | 15h30 |
| J | LON1st_candle | 1ere bougie London >0.3ATR, trader dans le meme sens | L+S | 1.72 | London | 8h05 |

### Strats eliminees
- B (D2_tok_5h_body): PF 2.52 solo mais n'ameliore pas le Calmar du combo
- K (TOK1st_candle): PF 1.60, absorbe par A et F
- L (3BAR_tok): PF 1.36, trop faible

### Regles
- Jamais 2 trades simultanes en sens opposes
- ATR du jour precedent
- Trailing: SL=0.75 act=0.5 trail=0.3, max 24 barres (toutes strats)
- Spread dans les prix bid/ask (entree) ou au stop level (sortie)
- 1 trigger max par strat par jour

### Horaires cles UTC
- 0h00: IB A commence, 2BAR(F) actif
- 1h00: A break UP possible
- 5h30: TOKEND(H) calcul du momentum fin Tokyo
- 6h00: Tokyo close → reference pour GAP(D), FADE(C), TOKEND(H)
- 8h00: London open → FADE(C), GAP(D), TOKEND(H), LON1st(J) triggent
- 10h00: KZ(E) trigger
- 14h30: NY open → NY1st(G) trigger
- 15h30: FADENY(I) trigger

## Scripts
| Script | Role |
|---|---|
| `find_best_v4.py` | Optimisation v4 (12 strats A-L, toutes combos) |
| `live_paper.py` | Paper trading live |
| `dashboard.py` | Dashboard Streamlit |
| `simu_perso.py` | Simulation: `python simu_perso.py [capital] [risk%]` |

## Infrastructure
- PostgreSQL: `candles_mt5_xauusd_5m`, `market_ticks_xauusd`
- DST IC Markets: US (2eme dim mars, 1er dim nov)
- Connexion autocommit (pas de lock)
