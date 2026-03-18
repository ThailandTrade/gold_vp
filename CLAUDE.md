# CLAUDE.md — VP Swing Explorer (XAUUSD 5m)

## Portfolio actif : 2BAR+B+D2+FADE+GAP+KZ (0.4%/trade)

| Metrique | Valeur |
|---|---|
| Rendement | +565.6% |
| Max DD | -5.2% |
| Calmar | 108.7 |
| PF | 1.91 |
| WR | 59% |
| Trades | 1112 (~3.5/jour) |
| Mois positifs | 13/13 |
| Tiers | 3/3 |
| Directions | Long + Short |

## Strategies

| Strat | Description | Dir | PF | Quand | Sortie |
|---|---|---|---|---|---|
| D2 | IB 5h-5h15 break UP + body >= 50% range | Long | 2.52 | Tokyo 5h15-6h | Trail SL=0.75 act=0.5 trail=0.3, 24b |
| GAP | Gap Tokyo close (6h) vs London open (8h) > 0.5 ATR, continuation | L+S | 2.16 | London open 8h | Trail SL=0.75 act=0.5 trail=0.3, 24b |
| KZ | London Kill Zone 8h-10h move > 0.5 ATR, fading a 10h | L+S | 2.00 | London 10h | Trail SL=0.75 act=0.5 trail=0.3, 24b |
| 2BAR | Two-bar reversal Tokyo: 2 grosses bougies opposees (> 0.5 ATR chaque), 2eme > 1ere | L+S | 1.73 | Tokyo 0h-6h | Trail SL=0.75 act=0.5 trail=0.3, 24b |
| FADE | Tokyo move > 1 ATR, inverse a London open 8h | L+S | 1.42 | London open 8h | Trail SL=0.75 act=0.5 trail=0.3, 24b |
| B | IB 0h-1h (12 bougies) break UP | Long | 1.35 | Tokyo 1h-6h | Trail SL=0.75 act=0.5 trail=0.3, 24b |

### Regles
- Jamais 2 trades simultanes en sens opposes
- ATR du jour precedent
- Spread reel MT5 + slippage $0.10
- Trailing: stop verifie AVANT best update, ATR fixe au trade
- 1 trigger max par strat par jour

### Horaires cles (UTC)
- 0h00: IB B commence, 2BAR actif
- 1h00: B break UP possible
- 5h15: D2 break UP possible
- 6h00: Tokyo close (reference pour GAP et FADE)
- 8h00: London open -> GAP et FADE triggent
- 10h00: KZ trigger (fade du move 8h-10h)

## Scripts
| Script | Role |
|---|---|
| `find_best_v3.py` | Optimisation v3 (9 strats, toutes combos) |
| `live_paper.py` | Paper trading live |
| `dashboard.py` | Dashboard Streamlit |
| `simu_custom.py` | Simulation: `python simu_custom.py [capital] [risk%]` |

## Infrastructure
- PostgreSQL: `candles_mt5_xauusd_5m`, `market_ticks_xauusd`
- DST IC Markets: US (2eme dim mars, 1er dim nov)
- Sessions UTC: Tokyo 0-6 | London 8-14h30 | NY 14h30-21h30
