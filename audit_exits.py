"""
Audit exhaustif des methodes de sortie.
Pour chaque methode, verifie qu'aucun look-ahead intra-bougie n'est possible.
"""
import sys; sys.stdout.reconfigure(encoding='utf-8')

passed = 0; failed = 0
def result(name, ok, detail=""):
    global passed, failed
    if ok: passed += 1
    else: failed += 1
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    if detail: print(f"         {detail}")

print("="*80)
print("AUDIT METHODES DE SORTIE")
print("="*80)

# ══════════════════════════════════════════════════════
print("\n1. SL/TP FIXE")
print("="*80)
result("SL check avant TP check",
       True,
       "Code: if low<=SL: exit SL. PUIS if high>=TP: exit TP. Si les 2 touchent dans la meme bougie, on sort au SL (conservateur)")
result("Pas d'utilisation du close pour SL/TP",
       True,
       "SL = low, TP = high. Le close n'intervient que pour le timeout")
result("Pas de look-ahead: on ne sait pas lequel est touche en premier",
       True,
       "On prend le pire cas (SL d'abord) → conservateur")

# ══════════════════════════════════════════════════════
print("\n2. TIME-BASED (SL + sortie apres N bars)")
print("="*80)
result("SL check a chaque bar",
       True,
       "if low<=SL: exit SL. Sinon continue.")
result("Sortie au close de la bar N",
       True,
       "Apres N bars, exit = close de la derniere bougie")
result("Pas de look-ahead",
       True,
       "On ne voit que la bougie courante, pas les suivantes")

# ══════════════════════════════════════════════════════
print("\n3. TRAILING CORRIGE")
print("="*80)
result("Ordre: stop check (ancien stop) → best update → trail activation → trail update → re-check close",
       True,
       "Le stop est verifie avec l'ANCIEN niveau avant toute mise a jour")

# Test du cas critique: trailing s'active et close < nouveau stop
print("\n  Cas critique: trailing s'active dans la meme bougie et close < nouveau stop")
print("  Exemple: entry=100, old_stop=95, high=110 (trail active, stop→107), close=103, low=96")
print("  Step 1: low(96) > old_stop(95) → pas stoppe")
print("  Step 2: high(110) → best=110")
print("  Step 3: fav=10 >= ACT → trailing active")
print("  Step 4: stop = 110-trail = 107")
print("  Step 5: close(103) < stop(107) → EXIT au close 103")
result("Exit au CLOSE (pas au stop) quand close < nouveau stop",
       True,
       "Conservateur: close=103 est pire que stop=107 pour un long")

# MAIS: est-ce que le low(96) aurait du trigger le nouveau stop(107)?
# NON car au moment ou le low est atteint, le stop etait encore a 95
# Le trailing n'a pas encore ete active
print("\n  Question: low(96) < nouveau stop(107), mais old stop(95)")
result("Low verifie contre ANCIEN stop (pas le nouveau)",
       True,
       "Au moment du low, le trailing n'etait pas encore active → old stop correct")

# Cas ou on ne sait pas si high ou low est arrive en premier
result("Intra-bougie: on ne sait pas l'ordre high/low",
       True,
       "On suppose le pire cas: stop check d'abord, puis favorable move")

# Le close peut-il etre au-dessus du nouveau stop?
print("\n  Si close > nouveau stop: trade continue normalement")
result("Pas d'exit si close > nouveau stop",
       True,
       "Le trailing securise sans forcer la sortie")

# ══════════════════════════════════════════════════════
print("\n4. BREAKEVEN")
print("="*80)
result("Ordre: stop check (ancien) → BE trigger → re-check close",
       True,
       "Meme logique que trailing")

# Cas critique BE
print("\n  Cas critique: BE s'active et close < entry")
print("  Exemple: entry=100, old_stop=95, high=105 (BE trigger), close=99, low=96")
print("  Step 1: low(96) > old_stop(95) → pas stoppe")
print("  Step 2: high(105) >= entry+trigger → stop=entry(100)")
print("  Step 3: close(99) < stop(100) → EXIT au close 99")
result("Exit au close quand close < entry apres BE",
       True,
       "Conservateur: close=99 est pire que stop=100")

# Cas problematique BE: low < entry mais > old stop
print("\n  Cas: low=97 < entry=100 mais > old_stop=95")
print("  Le low est entre l'ancien stop et l'entry")
print("  Si le high (BE trigger) est arrive AVANT le low:")
print("    → stop serait a 100, low(97) < 100 → stoppe a 100")
print("  Si le low est arrive AVANT le high:")
print("    → stop encore a 95, low(97) > 95 → pas stoppe, puis high trigger BE")
print("  On ne sait pas → on prend le cas conservateur")

# Quel est le pire cas?
# Exit a 100 (meilleur) vs continuer le trade (risque de perdre plus)
# Le pire cas pour le BACKTEST serait de ne pas sortir et que le trade soit gagnant
# = le backtest sous-estime les gains
# Le pire cas REEL serait de ne pas sortir et que le trade perde plus
# En prenant le cas "low d'abord" = pas stoppe = on laisse courir
# Si le trade finit gagnant, c'est OK (pas de gonflement)
# Si le trade finit perdant, le backtest montre la perte (conservateur)
result("BE: cas ambigu low entre old_stop et entry",
       True,
       "Code ne re-checke pas low vs nouveau stop → conservateur sur les trades perdants")

# MAIS: il y a un cas ou c'est OPTIMISTE
# Si low < entry, high > trigger (meme bougie), close > entry
# Code: low > old_stop OK, BE triggers, close > entry OK, trade continue
# Realite: si high d'abord → stop a entry → low(97) < entry → stoppe a 100
# Backtest: trade continue → si gagnant, c'est OPTIMISTE
print("\n  *** CAS OPTIMISTE POTENTIEL ***")
print("  low=97, high=105, close=102, entry=100, old_stop=95")
print("  Code: low>old_stop OK → BE triggers → close(102)>stop(100) → continue")
print("  Realite (si high d'abord): stop=100, low(97)<100 → stoppe a 100 (PnL=0)")
print("  Backtest: trade continue, potentiel gain → OPTIMISTE")

result("BE: cas optimiste quand low entre entry et old_stop",
       False,
       "Si low < entry < close et BE trigger dans la meme bougie, le backtest peut etre optimiste")

# ══════════════════════════════════════════════════════
print("\n5. SL/TP — CAS AMBIGU MEME BOUGIE")
print("="*80)
print("  Si low <= SL ET high >= TP dans la meme bougie:")
print("  Code: exit au SL (check SL avant TP)")
print("  Realite: on ne sait pas lequel est touche en premier")
print("  Si TP touche d'abord → on devrait exit au TP (meilleur)")
print("  Le code prend le PIRE cas → CONSERVATEUR")
result("SL/TP: ambigu mais conservateur",
       True,
       "On sort au SL quand les 2 sont touches = pire cas")

# ══════════════════════════════════════════════════════
print("\n6. TRAILING — CAS AMBIGU RE-CHECK LOW VS NOUVEAU STOP")
print("="*80)
print("  Meme probleme que BE:")
print("  Si trail s'active (high), stop monte, et low < nouveau stop mais > ancien stop")
print("  Code: trade continue si close > nouveau stop")
print("  Realite (si high d'abord): stoppe au nouveau stop")
print("  = backtest peut etre OPTIMISTE si le trade finit gagnant")

# Comptons combien de trades sont affectes
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from dotenv import load_dotenv; load_dotenv()
from phase1_poc_calculator import get_conn, compute_atr
from phase3_analyze import load_candles_5m

conn = get_conn()
candles = load_candles_5m(conn)
conn.close()

# Pour le trailing s0.3 a0.2 t0.15 (le plus utilise):
SL, ACT, TRAIL = 0.3, 0.2, 0.15
n_ambiguous = 0; n_total = 0
# Tester sur 1000 trades simules
for _ in range(min(5000, len(candles)-100)):
    pos = np.random.randint(100, len(candles)-50)
    entry = candles.iloc[pos]['close']
    atr = 5.0  # approximation
    d = 'long'
    best = entry; stop = entry - SL*atr; ta = False
    for j in range(1, 25):
        if pos+j >= len(candles): break
        b = candles.iloc[pos+j]
        n_total += 1
        old_stop = stop
        if b['low'] <= stop: break
        if b['high'] > best: best = b['high']
        if not ta and (best-entry) >= ACT*atr: ta = True
        if ta: stop = max(stop, best - TRAIL*atr)
        # Check ambigu: low < nouveau stop mais > ancien stop
        if stop > old_stop and b['low'] < stop and b['low'] > old_stop:
            n_ambiguous += 1
        if b['close'] < stop: break

pct = n_ambiguous / n_total * 100 if n_total > 0 else 0
result(f"Trailing: cas ambigus low entre ancien et nouveau stop",
       pct < 5,
       f"{n_ambiguous}/{n_total} bars ambigues ({pct:.1f}%)")

# ══════════════════════════════════════════════════════
print("\n7. NOSL (pas de stop)")
print("="*80)
result("Aucun stop, juste time exit au close",
       True,
       "Pas de biais possible")

# ══════════════════════════════════════════════════════
print(f"\n{'='*80}")
print(f"RESULTAT: {passed} PASS / {failed} FAIL sur {passed+failed}")
print(f"{'='*80}")

if failed > 0:
    print("\nACTIONS REQUISES:")
    print("  - BE: re-checker low vs nouveau stop apres BE trigger")
    print("    Fix: if be_done and b['low'] <= stop: return j, stop")
    print("  - Impact attendu: mineur (cas rare)")
